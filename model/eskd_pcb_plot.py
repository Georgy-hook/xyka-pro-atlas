"""Isolated KiCad 10.0.8 copper SVGs for embedding on the PCB drawing sheets.

plot_copper(board_path, cli_path, work_dir) returns F.Cu and B.Cu CopperPlot
records. Coordinates and bounds are absolute board XY mm (+X right, +Y down),
including on B.Cu. Do not undo a crop, translate the datum, or mirror again
here. The caller lays out/crops the group and mirrors the reverse view once.

The CLI opens a byte-identical snapshot, *not* the source or its project. Use
one positive, unmirrored layer per file, scale 1, uncropped page, no drawing
sheet or common layers. Do not refill zones: this reports the saved artwork,
not a new routing/fill solution. Verify the separate drill-free Edge.Cuts
plot against the independent mechanical reader before accepting either side.

10.0.8 can draw NPTH drill marks BLACK even in an empty single-layer export.
The matching drill-option-0 plot identifies the positive artwork exactly;
only the additional actual-size drill marks in option 2 are subtractions.
Their locations, sizes, and slot angles are checked against file drill records.
Do not draw these as white objects on the sheet. Uncut primitives retain the
CLI's vector commands. Boolean cuts are self-contained vector paths with true
holes (no white paint, mask/clip IDs, raster, external CSS, or dependencies on
SVG compositing support). Only KiCad's invisible searchable text duplicate is
omitted; its actual copper glyph paths are kept like other copper artwork. No
silk/page labels are requested. Unoutlined visible text fails rather than being
silently dropped. ink_count counts surviving positive SVG primitives, not drills,
XML groups, board objects or nets.

Bounds measure visible filled/stroked geometry after drill subtraction. Curves
and round strokes are measured with chord sagitta <= CURVE_TOL_MM per step;
Boolean-cut paths use that same approximation and 0.0000001 mm serialization.
This is plot metrology, not manufacturing tolerance: the CLI itself typically
rounds coordinates/radii to 0.0001 mm. Near-tangent intersections are inherently
sensitive to that precision. REGISTRATION_TOL_MM is a separate fail threshold.

Dependencies: fontTools (SVG path dialect), Shapely (planar areas), and sibling
eskd_pcb_geometry.read_board. Raw CLI SVGs/logs persist in a fresh run directory
under work_dir. sha256 hashes the exact drill-option-2 SVG, including KiCad's
timestamp/title; source_sha256 instead hashes the exact .kicad_pcb bytes.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from fontTools.svgLib.path import parse_path
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, unary_union

SVG = "{http://www.w3.org/2000/svg}"
CURVE_TOL_MM = 0.00005
REGISTRATION_TOL_MM = 0.01
# Factory colors in a clean 10.0.8 profile. Fail closed on layer contamination,
# including text/frame in another color; never infer polarity from black alone.
COLORS = {"F.Cu": "#c83434", "B.Cu": "#4d7fc4", "Edge.Cuts": "#d0d2cd"}
DRILL_COLORS = {"#ffffff", "#000000"}
Box = tuple[float, float, float, float]


class PlotError(ValueError):
    """A native plot or its geometric registration could not be verified."""


@dataclass(frozen=True)
class CopperPlot:
    svg_group: ET.Element
    bounds: Box | None
    sha256: str
    ink_count: int
    source_sha256: str
    raw_path: Path


def _num(value):
    n = float(value)
    if not math.isfinite(n):
        raise PlotError(f"nonfinite SVG coordinate: {value!r}")
    return n


def _fmt(n):
    return f"{n:.7f}".rstrip("0").rstrip(".") or "0"


def _arc_step(radius, tol):
    # The 4*asin expression for 2*acos(1-tol/r) avoids cancellation.
    return min(math.pi / 2, 4 * math.asin(math.sqrt(min(1, tol / (2 * radius)))))


def _quad_segments(radius):
    return max(1, math.ceil(math.pi / (2 * _arc_step(radius, CURVE_TOL_MM))))


class _Pen:
    """fontTools resolves implicit/relative path commands. Flatten in user units."""

    def __init__(self, tol):
        self.tol = tol
        self.paths = []

    def moveTo(self, pt):
        self.paths.append([pt])

    def lineTo(self, pt):
        self.paths[-1].append(pt)

    def closePath(self):
        path = self.paths[-1]
        if path[-1] != path[0]:
            path.append(path[0])

    def endPath(self):
        pass  # Nothing to close: keep the true ends for stroke caps.

    def _bezier(self, pts):
        # The control hull stays within tol of its chord. Use the segment, not
        # its infinite line: collinear control points can overshoot the ends.
        a, b = pts[0], pts[-1]
        d = b - a
        def distance(p):
            t = ((p - a) * d.conjugate()).real / abs(d) ** 2 if d else 0
            return abs(p - a - max(0, min(1, t)) * d)
        if max(map(distance, pts[1:-1])) <= self.tol:
            self.lineTo((b.real, b.imag))
            return
        levels = [pts]
        while len(levels[-1]) > 1:
            q = levels[-1]
            levels.append([(p + r) / 2 for p, r in zip(q, q[1:])])
        self._bezier([row[0] for row in levels])
        self._bezier([row[-1] for row in reversed(levels)])

    def curveTo(self, *points):
        self._bezier([complex(*pt) for pt in (self.paths[-1][-1], *points)])

    qCurveTo = curveTo

    def arcTo(self, rx, ry, rotation, large, sweep, end):
        # SVG endpoint-to-center algorithm; do not replace a semicircle with a
        # single cubic. A radius rounded slightly short must be scaled up.
        a, b = complex(*self.paths[-1][-1]), complex(*end)
        rx, ry = abs(rx), abs(ry)
        if a == b:
            return
        if not rx or not ry:
            self.lineTo(end)
            return
        phi = math.radians(rotation)
        rot = complex(math.cos(phi), math.sin(phi))
        p = (a - b) / (2 * rot)
        u = complex(p.real / rx, p.imag / ry)
        if abs(u) > 1:
            factor = abs(u)
            rx, ry, u = rx * factor, ry * factor, u / factor
        k = math.sqrt(max(0, 1 / abs(u) ** 2 - 1))
        c = (-1j if bool(large) != bool(sweep) else 1j) * u * k
        center = (a + b) / 2 + rot * complex(rx * c.real, ry * c.imag)
        first, last = u - c, -u - c
        theta = math.atan2(first.imag, first.real)
        delta = (math.atan2(last.imag, last.real) - theta) % math.tau
        if not sweep:
            delta -= math.tau
        n = max(1, math.ceil(abs(delta) / _arc_step(max(rx, ry), self.tol)))
        for i in range(1, n):
            t = theta + delta * i / n
            z = center + rot * complex(rx * math.cos(t), ry * math.sin(t))
            self.lineTo((z.real, z.imag))
        self.lineTo(end)


def _subpaths(d, frame):
    s, dx, dy = frame
    if not d.strip():
        raise PlotError("missing SVG path data")
    pen = _Pen(CURVE_TOL_MM / s)
    parse_path(d, pen)
    return [[(_num(x) * s + dx, _num(y) * s + dy) for x, y in path]
            for path in pen.paths if len(path) >= 2]


def _winding(x, y, ring):
    crossings = 0
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        cross = (bx - ax) * (y - ay) - (x - ax) * (by - ay)
        if ay <= y < by and cross > 0:
            crossings += 1
        elif by <= y < ay and cross < 0:
            crossings -= 1
    return crossings


def _filled(paths, rule):
    rings = [p if p[0] == p[-1] else [*p, p[0]] for p in paths if len(p) >= 3]
    if len(rings) == 1:
        p = Polygon(rings[0])
        if p.is_valid:
            return p
    # KiCad zones can use a retraced bridge between an exterior and a void.
    # Do not simply take the exterior/buffer(0) or fill each subpath alone.
    cells = polygonize(unary_union([LineString(ring) for ring in rings]))
    material = []
    for cell in cells:
        pt = cell.representative_point()
        w = sum(_winding(pt.x, pt.y, ring) for ring in rings)
        inside = bool(w % 2) if rule == "evenodd" else w != 0
        if inside:
            material.append(cell)
    return unary_union(material)


_DEFAULTS = {"fill": "#000000", "stroke": "none", "stroke-width": "1",
             "fill-rule": "nonzero", "stroke-linecap": "butt", "stroke-linejoin": "miter",
             "stroke-miterlimit": "4", "fill-opacity": "1", "stroke-opacity": "1"}
_SHAPES = {"path": {"d"}, "circle": {"cx", "cy", "r"}, "ellipse": {"cx", "cy", "rx", "ry"},
           "rect": {"x", "y", "width", "height", "rx", "ry"}, "line": {"x1", "y1", "x2", "y2"},
           "polygon": {"points"}, "polyline": {"points"}}
_CAP = {"round": 1, "butt": 2, "square": 3}
_JOIN = {"round": 1, "miter": 2, "bevel": 3}


def _viewport(root):
    if root.tag != SVG + "svg":
        raise PlotError("not a native SVG document")
    def mm(key):
        v = root.get(key, "").strip()
        if not v.endswith("mm"):
            raise PlotError(f"physical SVG {key} in mm required: {v!r}")
        return _num(v[:-2])
    x, y, w, h = map(_num, root.attrib["viewBox"].replace(",", " ").split())
    pw, ph = mm("width"), mm("height")
    if min(w, h, pw, ph) <= 0 or not math.isclose(pw / w, ph / h, rel_tol=1e-8):
        raise PlotError("degenerate or anisotropic SVG viewport")
    s = pw / w
    return (s, -s * x, -s * y), (x, y, w, h, pw, ph)


def _style(node, tag, inherited):
    # Accept the *native plotter dialect*, not arbitrary SVG/CSS. In particular
    # do not silently ignore an unknown transform, dashed stroke, mask, or use.
    keys = set(_DEFAULTS) | {"transform", "style", "id"} | _SHAPES.get(tag, set())
    if tag == "svg":
        keys |= {"version", "width", "height", "viewBox"}
    if tag == "g" and node.get("class") == "stroked-text":
        keys.add("class")  # These children are real glyph paths on the selected layer.
    if extra := set(node.attrib) - keys:
        raise PlotError(f"unsupported SVG attributes on {tag}: {sorted(extra)}")
    if trans := node.get("transform", "").strip():
        if trans.replace(",", " ").split() != "translate(0 0) scale(1 1)".split():
            raise PlotError(f"unexpected plot transform {trans!r}; refusing to guess board datum")
    styles = {**inherited, **{k: v for k, v in node.attrib.items() if k in _DEFAULTS}}
    for item in node.get("style", "").split(";"):
        if item.strip():
            key, val = (v.strip() for v in item.split(":", 1))
            if key not in _DEFAULTS:
                raise PlotError(f"unsupported SVG style {key!r}")
            styles[key] = val
    if (styles["fill-rule"] not in ("nonzero", "evenodd") or
            styles["stroke-linecap"] not in _CAP or styles["stroke-linejoin"] not in _JOIN or
            _num(styles["fill-opacity"]) != 1 or _num(styles["stroke-opacity"]) != 1):
        raise PlotError(f"unsupported SVG ink style {styles}")
    return styles


@dataclass
class _Mark:
    tag: str
    attrs: dict
    style: dict
    color: str

    def element(self, for_sheet=False):
        el = ET.Element(SVG + self.tag, self.attrs.copy())
        if for_sheet:
            st = self.style.copy()
            st.update({k: "#000000" for k in ("fill", "stroke") if st[k] != "none"})
            el.attrib.update(st)
        return el

    def _paths(self, frame):
        a = self.attrs
        if self.tag == "path":
            return _subpaths(a["d"], frame)
        if self.tag in ("polyline", "polygon"):
            return _subpaths("M" + a["points"] + ("Z" if self.tag == "polygon" else ""), frame)
        if self.tag == "line":
            x1, y1, x2, y2 = (a.get(k, "0") for k in ("x1", "y1", "x2", "y2"))
            return _subpaths(f"M{x1},{y1} L{x2},{y2}", frame)
        if self.tag in ("circle", "ellipse"):
            # Do not round-trip absolute mm through %g (six significant digits
            # can move a 0.17-mm drill appreciably). Include all four extrema.
            s, tx, ty = frame
            cx = _num(a.get("cx", 0)) * s + tx
            cy = _num(a.get("cy", 0)) * s + ty
            rx, ry = ((_num(a["r"]) * s,) * 2 if self.tag == "circle" else
                      (_num(a["rx"]) * s, _num(a["ry"]) * s))
            if min(rx, ry) <= 0:
                raise PlotError(f"nonpositive {self.tag} radius")
            n = 4 * _quad_segments(max(rx, ry))
            pts = [(cx + rx * math.cos(math.tau * i / n), cy + ry * math.sin(math.tau * i / n))
                   for i in range(n)]
            return [pts + [pts[0]]]
        if self.tag == "rect":
            x, y = _num(a.get("x", 0)), _num(a.get("y", 0))
            w, h = _num(a["width"]), _num(a["height"])
            rx = min(w / 2, _num(a.get("rx", a.get("ry", 0))))
            ry = min(h / 2, _num(a.get("ry", a.get("rx", 0))))
            if min(w, h) <= 0 or min(rx, ry) < 0:
                raise PlotError("invalid SVG rectangle dimensions")
            if not rx or not ry:
                return _subpaths(f"M{x},{y}H{x+w}V{y+h}H{x}Z", frame)
            arc = f"A{rx},{ry} 0 0 1 "
            d = (f"M{x+rx},{y}H{x+w-rx}{arc}{x+w},{y+ry}V{y+h-ry}{arc}{x+w-rx},{y+h}"
                 f"H{x+rx}{arc}{x},{y+h-ry}V{y+ry}{arc}{x+rx},{y}Z")
            return _subpaths(d, frame)
        raise PlotError(f"unsupported native {self.tag}")

    def measure(self, frame, *, centerline=False):
        parts = self._paths(frame)
        lines = [LineString(p) if any(q != p[0] for q in p) else Point(p[0]) for p in parts]
        if centerline:
            return unary_union(lines)
        pieces = []
        if self.style["fill"] != "none":
            pieces.append(_filled(parts, self.style["fill-rule"]))
        if self.style["stroke"] != "none":
            r = _num(self.style["stroke-width"]) * frame[0] / 2
            if r < 0:
                raise PlotError("negative SVG stroke width")
            if r > 0:
                n = _quad_segments(r)
                for line in lines:
                    pieces.append(line.buffer(r, n, cap_style=_CAP[self.style["stroke-linecap"]],
                                              join_style=_JOIN[self.style["stroke-linejoin"]],
                                              mitre_limit=_num(self.style["stroke-miterlimit"])))
        return unary_union(pieces)


def _decode(raw):
    root = ET.fromstring(raw)
    frame, viewport = _viewport(root)
    marks = []
    def walk(node, inherited):
        tag = node.tag.removeprefix(SVG)
        if tag in ("desc", "title"):
            return
        if tag == "text":
            if _num(node.get("opacity", "1")) == 0 and "style" not in node.attrib:
                return  # Only KiCad's searchable duplicate, not its glyph strokes.
            raise PlotError("visible SVG text without certified native outlines; refusing to discard copper")
        if tag == "svg" and node is not root:
            raise PlotError("unexpected nested SVG viewport")
        st = _style(node, tag, inherited)
        if tag in ("svg", "g"):
            for child in node:
                walk(child, st)
        elif tag in _SHAPES and not len(node):
            paints = {st[k].lower() for k in ("stroke", "fill")} - {"none"}
            if len(paints) != 1:
                raise PlotError(f"ambiguous or invisible native {tag} paints: {paints}")
            marks.append(_Mark(tag, {k: v for k, v in node.attrib.items() if k in _SHAPES[tag]},
                               st, paints.pop()))
        else:
            raise PlotError(f"unsupported native SVG element: {tag}")
    walk(root, _DEFAULTS)
    return frame, viewport, marks


def _polygons(shape):
    if shape.geom_type == "Polygon":
        if not shape.is_empty:
            yield shape
    elif hasattr(shape, "geoms"):
        for part in shape.geoms:
            yield from _polygons(part)


def _boolean_path(shape):
    # Use explicit opposite contour winding as well as evenodd: this works in
    # SVG/PDF consumers that default to nonzero. No ID or white overlay leaks.
    contours = []
    for poly in _polygons(shape):
        p = orient(poly)
        for ring in (p.exterior, *p.interiors):
            contours.append("M" + " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in ring.coords[:-1]) + "Z")
    if not contours:
        raise PlotError("positive-area drill subtraction yielded no vector contours")
    return ET.Element(SVG + "path", {"d": " ".join(contours), "fill": "#000000",
                                    "fill-rule": "evenodd", "stroke": "none"})


def _union_box(a, b):
    if a is None:
        return tuple(b)
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def _validate_edge(edge, board):
    frame, _, marks = edge
    if not marks or any(m.color != COLORS["Edge.Cuts"] or m.style["fill"] != "none" for m in marks):
        raise PlotError("expected only native, stroked Edge.Cuts centerlines in calibration plot")
    plotted = unary_union([m.measure(frame, centerline=True) for m in marks])
    source = unary_union([LineString(p) for p in _subpaths(board.edge_path, (1., 0., 0.))])
    if plotted.is_empty or source.is_empty:
        raise PlotError("empty calibration contour")
    # Check the actual contour too: mere width/height (or even the same page
    # bounds) does not rule out mirroring a notched board about its center.
    error = plotted.hausdorff_distance(source)
    box_error = max(abs(a - b) for a, b in zip(plotted.bounds, board.bounds))
    if not math.isfinite(error) or max(error, box_error) > REGISTRATION_TOL_MM:
        raise PlotError(f"absolute Edge.Cuts mismatch: plotted {plotted.bounds}, board {board.bounds}, "
                        f"contour displacement {error:.6g} mm; refusing a guessed scale/offset/mirror")


def _reference_hole(hole):
    """Independent capsule, used only as a check. Never used to draw copper."""
    r = min(hole.dx, hole.dy) / 2
    half = abs(hole.dx - hole.dy) / 2
    theta = math.radians(-hole.angle + (90 if hole.dy > hole.dx else 0))
    vx, vy = half * math.cos(theta), half * math.sin(theta)
    axis = (LineString([(hole.x - vx, hole.y - vy), (hole.x + vx, hole.y + vy)])
            if half else Point(hole.x, hole.y))
    return axis.buffer(r, _quad_segments(r))


def _checked_drills(layer, drills, frame, records):
    # A black or white primitive is not necessarily a drill! Require a native
    # aperture to coincide with its independently read circle or rotated slot.
    tol = 0.001  # mm: covers four-decimal KiCad endpoint/radius rounding
    ordered = sorted(records, key=lambda h: h.x)
    xs = [h.x for h in ordered]
    reference = [_reference_hole(h) for h in ordered]
    missing = set(range(len(ordered)))
    seen = []
    for mark in drills:
        actual = mark.measure(frame)
        if actual.is_empty or actual.area <= 0:
            raise PlotError(f"{layer}: degenerate actual-drill mark")
        xmin, ymin, xmax, ymax = actual.bounds
        x, y = (xmin + xmax) / 2, (ymin + ymax) / 2
        candidates = range(bisect_left(xs, x - tol), bisect_right(xs, x + tol))
        hits = [i for i in candidates if abs(y - ordered[i].y) <= tol and
                actual.boundary.hausdorff_distance(reference[i].boundary) <= tol]
        if not hits:
            raise PlotError(f"{layer}: unexpected drill/foreign ink at ({x:.5f}, {y:.5f}) mm")
        missing.difference_update(hits)  # coincident stacked drill records are harmless
        seen.append(actual)
    return unary_union(seen), unary_union([reference[i] for i in missing])


def _compose(layer, dry, actual, edge_viewport, board, raw_sha, raw_path):
    frame, vp, positive = dry
    _, vp2, all_marks = actual
    if vp != vp2 or vp != edge_viewport:
        raise PlotError(f"{layer}: inconsistent physical plot viewports")
    color = COLORS[layer]
    if any(m.color != color for m in positive):
        raise PlotError(f"{layer}: material in unexpected color on the drill-free single-layer plot")
    if [m for m in all_marks if m.color == color] != positive:
        raise PlotError(f"{layer}: actual-drill export changed the native copper primitives")
    drills = [m for m in all_marks if m.color != color]
    if any(m.color not in DRILL_COLORS for m in drills):
        raise PlotError(f"{layer}: foreign layers/colors in actual-drill export")
    holes, missing = _checked_drills(layer, drills, frame, board.holes)
    group = ET.Element(SVG + "g", {"fill": "#000000", "stroke": "none"})
    ink_box = route_box = None
    n = 0
    for mark in positive:
        area = mark.measure(frame)
        if area.is_empty or area.area <= 0:
            raise PlotError(f"{layer}: degenerate positive {mark.tag} primitive, cannot certify ink")
        if not missing.is_empty and area.intersection(missing).area > 0:
            raise PlotError(f"{layer}: native plot omitted a source drill intersecting copper")
        if mark.style["stroke"] != "none":
            route_box = _union_box(route_box, area.bounds)
        if not holes.is_empty and holes.intersects(area):
            cut = area.difference(holes)
            if cut.area == 0:
                continue
            if cut.area < area.area:
                node = _boolean_path(cut)
                area = cut
            else:
                node = None  # Only touched the boundary.
        else:
            node = None
        if node is None:
            node = mark.element(for_sheet=True)
            if frame != (1., 0., 0.):
                s, dx, dy = frame
                node.set("transform", f"matrix({s:.15g} 0 0 {s:.15g} {dx:.15g} {dy:.15g})")
        group.append(node)
        ink_box = _union_box(ink_box, area.bounds)
        n += 1
    counts = board.counts[layer]
    if not positive and any(counts[k] for k in ("pads", "segments", "arcs", "vias", "zones")):
        raise PlotError(f"{layer}: drill-free plot has no copper but source inventory is {counts}")
    reference = board.routes[layer]
    if reference is not None:
        if route_box is None or any(delta > REGISTRATION_TOL_MM for delta in
                (route_box[0] - reference[0], route_box[1] - reference[1],
                 reference[2] - route_box[2], reference[3] - route_box[3])):
            raise PlotError(f"{layer}: native stroked extents {route_box} omit source routes {reference}")
    return CopperPlot(group, ink_box, raw_sha, n, board.sha256, raw_path)


def _cli_run(command, work, env, log_name):
    try:
        proc = subprocess.run(command, cwd=work, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
                              check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PlotError(f"cannot run {command[0]} ({log_name}): {exc}") from exc
    log = work / (log_name + ".log")
    log.write_bytes(proc.stdout)
    output = proc.stdout.decode("utf-8", "replace").strip()
    if proc.returncode != 0:
        raise PlotError(f"{log_name}: kicad-cli exited {proc.returncode}: {output[-2000:]} (see {log})")
    return output


def _plot_file(cli, snapshot, work, env, layer, drill):
    label = f"{layer}-drill{drill}"
    dest = work / (label + ".svg")
    command = [str(cli), "pcb", "export", "svg", "--mode-single", "--layers", layer,
               "--page-size-mode", "1", "--exclude-drawing-sheet", "--scale", "1",
               "--drill-shape-opt", str(drill), "--output", str(dest), str(snapshot)]
    _cli_run(command, work, env, label)
    if not dest.is_file() or not dest.stat().st_size:
        raise PlotError(f"{layer}: CLI reported success without writing {dest}")
    raw = dest.read_bytes()
    try:
        return _decode(raw), hashlib.sha256(raw).hexdigest(), dest
    except (ValueError, ET.ParseError, KeyError, IndexError) as exc:
        raise PlotError(f"cannot verify native SVG {dest}: {exc}") from exc


def plot_copper(board_path, cli_path, work_dir):
    """Return {layer: CopperPlot} or raise PlotError; writes only below work_dir.

    cli_path is the explicit executable (or a `cli-path` file containing its
    absolute path). The run directory holds Edge.Cuts-drill0.svg and each
    layer's -drill0.svg and -drill2.svg for independent reproduction/inspection.
    A successful blank side has bounds=None, ink_count=0, and an empty <g>.
    """
    if __package__:
        from .eskd_pcb_geometry import read_board
    else:
        from eskd_pcb_geometry import read_board

    board_path = Path(board_path).resolve(strict=True)
    cli = Path(cli_path).resolve(strict=True)
    if cli.name == "cli-path" and not os.access(cli, os.X_OK):
        pointed = Path(cli.read_text(encoding="utf-8").strip())
        if not pointed.is_absolute():
            raise PlotError(f"{cli}: expected an absolute executable path")
        cli = pointed.resolve(strict=True)
    if not cli.is_file() or not os.access(cli, os.X_OK):
        raise PlotError(f"not an executable kicad-cli: {cli}")
    base = Path(work_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="copper-", dir=base))
    # KiCad may write a .kicad_prl beside the board *even on export*.
    # Retain a snapshot and all ancillary files/configuration under the run.
    (run / "input").mkdir()
    snapshot = run / "input" / board_path.name
    data = board_path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    snapshot.write_bytes(data)
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "LC_ALL": "C", "LANG": "C"}
    for name, rel in {"HOME": "home", "XDG_CONFIG_HOME": "config", "XDG_CACHE_HOME": "cache",
                      "XDG_DATA_HOME": "data", "KICAD_CONFIG_HOME": "config",
                      "KICAD_DOCUMENTS_HOME": "data", "TMPDIR": "temp", "TEMP": "temp",
                      "TMP": "temp"}.items():
        folder = run / rel
        folder.mkdir(exist_ok=True)
        env[name] = str(folder)
    ver = _cli_run([str(cli), "version"], run, env, "version")
    if ver != "10.0.8":
        raise PlotError(f"expected calibrated kicad-cli version 10.0.8, found {ver!r}")
    board = read_board(snapshot)
    if board.sha256 != sha:
        raise PlotError("independent geometry reader saw different PCB source bytes")
    edge, _, _ = _plot_file(cli, snapshot, run, env, "Edge.Cuts", 0)
    _validate_edge(edge, board)
    result = {}
    for layer in ("F.Cu", "B.Cu"):
        dry, _, _ = _plot_file(cli, snapshot, run, env, layer, 0)
        actual, raw_sha, path = _plot_file(cli, snapshot, run, env, layer, 2)
        result[layer] = _compose(layer, dry, actual, edge[1], board, raw_sha, path)
    if hashlib.sha256(board_path.read_bytes()).hexdigest() != sha:
        raise PlotError("source board changed during export; refusing a stale result")
    return result
