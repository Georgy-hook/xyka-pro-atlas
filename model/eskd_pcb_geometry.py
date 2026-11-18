"""Mechanical facts from a modern native KiCad board; stdlib only, millimetres.

File frame everywhere: X right, Y down; positive KiCad pad angles turn CCW.
Use SVG fill-rule="evenodd" when filling edge_path (one closed subpath per loop).
Neither Edge.Cuts stroke nor copper graphics are tracks. Counts are native
objects, not an estimate of plotted copper, electrical joins or manufacturability.
"""

import hashlib
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple, Optional


Point = tuple[float, float]
Bounds = tuple[float, float, float, float]
_SIDES = ("F.Cu", "B.Cu")


class Hole(NamedTuple):
    x: float
    y: float
    dx: float  # full drill axes in pad-local X, Y (not projected bounding box)
    dy: float
    angle: float  # orientation of the local +X axis, even when dy > dx
    kind: str  # file type only: PTH, NPTH, VIA
    ref: str
    pad_size: Optional[Point]  # native land size before rotation; None if bare
    pad_shape: Optional[str]


class Board(NamedTuple):
    bounds: Bounds
    edge_path: str
    holes: list[Hole]
    thickness: Optional[float]
    counts: dict[str, dict[str, int]]
    routes: dict[str, Optional[Bounds]]
    sha256: str
    widths: dict[str, list[float]]
    inspection: dict[str, Optional[Point]]


# Tokenize once, including quoted parentheses/escapes and UTF-8 reference text.
_TOKEN = re.compile(r'(?P<comment>^[ \t]*#[^\n]*)|\n|[^\S\n]+|[()]|"(?:[^"\\]|\\.)*"|[^\s()"]+',
                    re.M | re.S)
_ESC = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}


def _parse(text):
    stack = [[]]
    end = 0
    for match in _TOKEN.finditer(text):
        if match.start() != end:
            raise ValueError(f"Invalid KiCad token at character {end}")
        end = match.end()
        token = match[0]
        if token[0].isspace() or match.lastgroup == "comment":
            continue
        if token == "(":
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            if len(stack) < 2 or not stack[-1] or not isinstance(stack[-1][0], str):
                raise ValueError(f"Unexpected ')' or unnamed form at character {end}")
            stack.pop()
        else:
            if token[0] == '"':
                token = re.sub(r"\\(.)", lambda m: _ESC.get(m[1], m[0]), token[1:-1])
            stack[-1].append(token)
    if end != len(text) or len(stack) != 1 or len(stack[0]) != 1:
        raise ValueError("Malformed or incomplete KiCad S-expression")
    root = stack[0][0]
    if not isinstance(root, list) or root[0] != "kicad_pcb":
        raise ValueError("Expected a native (kicad_pcb ...) board")
    if any(not isinstance(c, list) for c in root[1:]):
        raise ValueError("Expected named forms inside kicad_pcb")
    return root


def _children(node):
    return (c for c in node[1:] if isinstance(c, list))


def _field(node, name, required=True):
    matches = [c for c in _children(node) if c[0] == name]
    if len(matches) > 1 or (not matches and required):
        raise ValueError(f"Expected one ({name} ...) in {node[0]}")
    return matches[0] if matches else None


def _numbers(values, counts, context):
    if len(values) not in counts or not all(isinstance(s, str) for s in values):
        raise ValueError(f"Unexpected {context} geometry: {values}")
    nums = tuple(map(float, values))
    if not all(map(math.isfinite, nums)):
        raise ValueError(f"Non-finite value in {context}")
    return nums


def _nums(node, name, *counts):
    return _numbers(_field(node, name)[1:], counts, name)


def _size(node, name, n):
    values = _nums(node, name, n)
    if min(values) <= 0:
        raise ValueError(f"{node[0]} {name} must be positive (not a rule/default)")
    return values


def _supported(node, names):
    for child in _children(node):
        if child[0] not in names:
            raise ValueError(f"Unsupported {node[0]} field: {child[0]}")


def _layers(node):
    many = _field(node, "layers", False)
    one = _field(node, "layer", False)
    if bool(many) == bool(one) or (one and len(one) != 2):
        raise ValueError(f"Ambiguous or missing layer specification in {node[0]}")
    layers = (many or one)[1:]
    if not layers or not all(isinstance(s, str) for s in layers):
        raise ValueError(f"Expected named layers in {node[0]}")
    return layers


def _sides(layers):
    result = set()
    for layer in layers:
        if layer in _SIDES:
            result.add(layer)
        elif layer in ("*.Cu", "F&B.Cu"):
            result.update(_SIDES)
        elif layer.endswith(".Cu") and not re.fullmatch(r"In\d+\.Cu", layer):
            raise ValueError(f"Unsupported copper layer selector: {layer}")
    return result


def _rotate(p, angle):
    # Transform a file-local vector, not a screen-clockwise SVG angle.
    a = angle % 360
    if a % 90 == 0:
        c, s = ((1, 0), (0, 1), (-1, 0), (0, -1))[int(a // 90)]
    else:
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return c * p[0] + s * p[1], c * p[1] - s * p[0]


def _placed(p, placement):
    x, y = _rotate(p, placement[2])
    return x + placement[0], y + placement[1]


def _at(node):
    values = _nums(node, "at", 2, 3)
    return values if len(values) == 3 else (*values, 0.0)


class _Arc(NamedTuple):
    center: Point
    r: float
    start_angle: float
    sweep: float  # positive = clockwise on a Y-down SVG

    def point(self, fraction):
        a = self.start_angle + fraction * self.sweep
        return self.center[0] + self.r * math.cos(a), self.center[1] + self.r * math.sin(a)


def _arc(a, m, b):
    # Circumcentre in a translated frame. The determinant fixes which way the
    # path passes THROUGH m; the short arc is not necessarily the correct arc.
    ux, uy = m[0] - a[0], m[1] - a[1]
    vx, vy = b[0] - a[0], b[1] - a[1]
    det = ux * vy - uy * vx
    if not det:
        raise ValueError("Degenerate three-point arc")
    uu, vv = ux * ux + uy * uy, vx * vx + vy * vy
    dx = (uu * vy - vv * uy) / (2 * det)
    dy = (vv * ux - uu * vx) / (2 * det)
    start = math.atan2(-dy, -dx)
    end = math.atan2(vy - dy, vx - dx)
    sweep = (end - start) % math.tau if det > 0 else -((start - end) % math.tau)
    return _Arc((a[0] + dx, a[1] + dy), math.hypot(dx, dy), start, sweep)


class _Span(NamedTuple):
    start: Point
    end: Point
    arc: Optional[_Arc] = None

    def bounds(self, margin=0.0):
        points = [self.start, self.end]
        arc = self.arc
        if arc:
            sign = 1 if arc.sweep > 0 else -1
            for i, (dx, dy) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
                travel = (sign * (i * math.pi / 2 - arc.start_angle)) % math.tau
                if travel <= abs(arc.sweep):
                    points.append((arc.center[0] + arc.r * dx, arc.center[1] + arc.r * dy))
        xs, ys = zip(*points)
        return min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin

    def samples(self):
        # Only the inspection ROI uses samples. Path and all bounds are analytic.
        length = self.arc.r * abs(self.arc.sweep) if self.arc else math.dist(self.start, self.end)
        n = max(2, min(512, math.ceil(length / 2)))
        yield self.start
        for i in range(1, n):
            t = i / n
            if self.arc:
                yield self.arc.point(t)
            else:
                yield tuple(a + (b - a) * t for a, b in zip(self.start, self.end))
        yield self.end


def _union(a, b):
    if a is None:
        return b
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def _edge_spans(node, placement):
    kind = node[0][3:]
    fields = {"line": "start end", "arc": "start mid end", "rect": "start end",
              "poly": "pts", "circle": "center end"}
    if kind not in fields or node[0][:3] not in ("gr_", "fp_"):
        raise ValueError(f"Unsupported Edge.Cuts object: {node[0]}")
    _supported(node, fields[kind].split() + "stroke width layer fill uuid tstamp locked".split())

    def point(name):
        return _placed(_nums(node, name, 2), placement)

    if kind == "circle":
        center = _nums(node, "center", 2)
        r = math.dist(center, _nums(node, "end", 2))
        c = _placed(center, placement)
        p, q = (c[0] + r, c[1]), (c[0] - r, c[1])
        return [_Span(p, q, _Arc(c, r, 0, math.pi)), _Span(q, p, _Arc(c, r, math.pi, math.pi))]
    if kind == "line":
        return [_Span(point("start"), point("end"))]
    if kind == "arc":
        p, m, q = (_nums(node, name, 2) for name in ("start", "mid", "end"))
        # Construct the circle before placement. A rotated/translated footprint
        # must not turn a collinear triple into an immense spurious radius.
        arc = _arc(p, m, q)
        placed_arc = _Arc(_placed(arc.center, placement), arc.r,
                          arc.start_angle - math.radians(placement[2] % 360), arc.sweep)
        return [_Span(_placed(p, placement), _placed(q, placement), placed_arc)]
    if kind == "rect":
        x, y = _nums(node, "start", 2)
        u, v = _nums(node, "end", 2)
        points = [(x, y), (u, y), (u, v), (x, v)]
    else:
        points = []
        for xy in _field(node, "pts")[1:]:
            if not isinstance(xy, list) or xy[0] != "xy":
                raise ValueError("Unsupported Edge.Cuts polygon vertex (expected xy)")
            points.append(_numbers(xy[1:], (2,), "xy"))
        if points and points[0] == points[-1]:
            points.pop()
        if len(points) < 3:
            raise ValueError("Degenerate Edge.Cuts polygon")
    points = [_placed(p, placement) for p in points]
    return [_Span(a, b) for a, b in zip(points, points[1:] + points[:1])]


def _key(p):
    # KiCad's internal length unit is 1 nm. Do not bridge visible outline gaps.
    return round(p[0], 6), round(p[1], 6)


def _xy_text(p):
    return f"{p[0]:.16g} {p[1]:.16g}"


def _contours(spans):
    if not spans:
        raise ValueError("No supported closed outline on Edge.Cuts")
    graph = defaultdict(list)
    bounds = None
    for i, span in enumerate(spans):
        if _key(span.start) == _key(span.end):
            raise ValueError(f"Zero-length Edge.Cuts primitive at {span.start}")
        for p in (span.start, span.end):
            graph[_key(p)].append(i)
        bounds = _union(bounds, span.bounds())
    for point, incident in graph.items():
        if len(incident) != 2:
            raise ValueError(f"Open or branching Edge.Cuts at {point} (degree {len(incident)})")

    used = set()
    commands = []
    for i, first in enumerate(spans):
        if i in used:
            continue
        start = here = _key(first.start)
        commands.append("M " + _xy_text(first.start))
        area2 = 0.0
        while i not in used:
            used.add(i)
            a, b, arc = spans[i]
            forward = _key(a) == here
            if not forward:
                a, b = b, a
            area2 += (a[0] - start[0]) * (b[1] - start[1]) - (a[1] - start[1]) * (b[0] - start[0])
            if arc:
                s = arc.sweep if forward else -arc.sweep
                area2 += arc.r ** 2 * (s - math.sin(s))
                large, sweep = int(abs(s) > math.pi), int(s > 0)
                commands.append(f"A {arc.r:.16g} {arc.r:.16g} 0 {large} {sweep} " + _xy_text(b))
            else:
                commands.append("L " + _xy_text(b))
            here = _key(b)
            j, k = graph[here]
            i = j if j != i else k
        if here != start or not area2:
            raise ValueError(f"Degenerate Edge.Cuts loop at {start}")
        commands.append("Z")
    return bounds, " ".join(commands)


def _inspection(tracks, pads):
    # Candidate centres are actual pad centres or on-curve samples. Score their
    # 8 x 6 mm windows, preferring both kinds, never looking at net identifiers.
    def cell(p):
        return math.floor(p[0] / 4), math.floor(p[1] / 3)

    bins = defaultdict(list)
    for kind, points in enumerate((tracks, pads)):
        for p in points:
            bins[cell(p)].append((p, kind))
    winner = best = None
    for x, y in sorted(tracks | pads):
        ix, iy = cell((x, y))
        hits = [0, 0]
        for i in range(ix - 1, ix + 2):
            for j in range(iy - 1, iy + 2):
                for (u, v), kind in bins.get((i, j), ()):
                    if abs(x - u) <= 4 and abs(y - v) <= 3:
                        hits[kind] += 1
        t, p = hits
        score = (bool(t and p), t, p, (x, y) in pads)
        if best is None or score > best:
            best, winner = score, (x, y)
    return winner


# Pad and via fields which do not introduce extra drills, padstacks or hidden
# geometry. Unknown fields fail here instead of producing a plausible hole chart.
_PAD = set("""at size layers drill roundrect_rratio rect_delta chamfer_ratio chamfer
    net pinfunction pintype property die_length pad_to_die_length clearance zone_connect
    solder_mask_margin solder_paste_margin solder_paste_margin_ratio thermal_gap thermal_width
    thermal_bridge_width thermal_bridge_angle remove_unused_layers keep_end_layers
    zone_layer_connections primitives options tstamp uuid locked teardrops tenting""".split())
_VIA = set("""at size drill layers net tstamp uuid locked free remove_unused_layers
    keep_end_layers zone_layer_connections tenting covering plugging capping filling
    teardrops""".split())


def _check_lands(node, fields):
    if _field(node, "padstack", False):
        raise ValueError(f"Unsupported {node[0]} padstack: cannot report a single land")
    remove = _field(node, "remove_unused_layers", False)
    if "remove_unused_layers" in node or (remove and remove[1:] != ["no"]):
        raise ValueError(f"Connectivity-dependent {node[0]} copper lands are unsupported")
    _supported(node, fields)


def _drill(node):
    drill = _field(node, "drill")
    _supported(drill, {"offset"})
    args = [s for s in drill[1:] if isinstance(s, str)]
    if args[:1] == ["oval"]:
        axes = _numbers(args[1:], (2,), "oval drill")
    else:
        axes = _numbers(args, (1,), "round drill") * 2
    if min(axes) <= 0:
        raise ValueError("Expected positive explicit drill axes")
    offset = _nums(drill, "offset", 2) if _field(drill, "offset", False) else (0, 0)
    return axes, offset


def _bare(node, shape, size, drill, offset):
    # Has drilling removed the entire copper land? The drill is a capsule.
    # These lands are each a rectangle expanded by a disc (circle/oval are
    # degenerate rectangles). Test its four corners against the eroded capsule.
    if shape in ("circle", "oval"):
        radius = min(size) / 2
    elif shape == "rect":
        radius = 0.0
    elif shape == "roundrect" and not _field(node, "chamfer", False):
        radius = min(size) * _nums(node, "roundrect_rratio", 1)[0]
        if not 0 <= radius <= min(size) / 2:
            raise ValueError("Invalid roundrect corner radius")
    else:
        raise ValueError(f"Unsupported drilled land geometry: {shape}")
    r = min(drill) / 2
    px, py = (v / 2 - radius for v in size)
    hx, hy = (v / 2 - r for v in drill)
    for x in (offset[0] - px, offset[0] + px):
        for y in (offset[1] - py, offset[1] + py):
            if math.hypot(max(abs(x) - hx, 0), max(abs(y) - hy, 0)) + radius > r + 1e-12:
                return False
    return True


class _Reader:
    def __init__(self):
        keys = ("pads", "segments", "arcs", "vias", "zones")
        self.counts = {s: dict.fromkeys(keys, 0) for s in _SIDES}
        self.routes = dict.fromkeys(_SIDES)
        self.widths = {s: set() for s in _SIDES}
        self.pads = {s: set() for s in _SIDES}
        self.tracks = {s: set() for s in _SIDES}
        self.edges = []
        self.holes = []
        self.nvia = 0

    def track(self, node):
        kind = node[0]
        fields = "start end width layer net uuid tstamp locked status".split()
        _supported(node, fields + (["mid"] if kind == "arc" else []))
        a, b = _nums(node, "start", 2), _nums(node, "end", 2)
        arc = _arc(a, _nums(node, "mid", 2), b) if kind == "arc" else None
        span = _Span(a, b, arc)
        width, = _size(node, "width", 1)
        for s in _sides(_layers(node)):
            self.counts[s][kind + "s"] += 1
            self.widths[s].add(width)
            self.routes[s] = _union(self.routes[s], span.bounds(width / 2))
            self.tracks[s].update(span.samples())

    def via(self, node):
        flags = [s for s in node[1:] if isinstance(s, str)]
        if set(flags) - {"locked", "free"} or set(_layers(node)) != set(_SIDES):
            raise ValueError("Only ordinary through vias with explicit F.Cu/B.Cu span are supported")
        _check_lands(node, _VIA)
        x, y = _nums(node, "at", 2)
        size, = _size(node, "size", 1)
        drill, = _size(node, "drill", 1)
        self.nvia += 1
        land = (size, size) if size > drill else None
        self.holes.append(Hole(x, y, drill, drill, 0.0, "VIA", f"VIA{self.nvia}",
                               land, "circle" if land else None))
        for s in _SIDES:
            self.counts[s]["vias"] += 1

    def pad(self, node, placement, ref, ordinal):
        if len(node) < 4 or not all(isinstance(s, str) for s in node[1:4]):
            raise ValueError("Malformed pad header")
        number, kind, shape = node[1:4]
        if shape not in ("circle", "oval", "rect", "roundrect", "trapezoid", "custom"):
            raise ValueError(f"Unsupported pad shape: {shape}")
        _check_lands(node, _PAD)
        layers = _layers(node)
        if "Edge.Cuts" in layers:
            raise ValueError("Unsupported pad shape on Edge.Cuts")
        sides = _sides(layers)
        size = _size(node, "size", 2)
        if shape == "circle" and size[0] != size[1]:
            raise ValueError("Circular pad has unequal axes")
        px, py, angle = _at(node)
        # Backside local coordinates and layer names are already flipped in the
        # saved board. Pad angles in (at ...) are absolute, unlike pad positions.
        x, y = _placed((px, py), placement)
        land_center = (x, y)
        if kind in ("thru_hole", "np_thru_hole"):
            (dx, dy), offset = _drill(node)
            # KiCad's (drill (offset ...)) offsets the LAND from the drill anchor.
            land_center = _placed(offset, (x, y, angle))
            land = any(s.endswith(".Cu") for s in layers) and not _bare(node, shape, size, (dx, dy), offset)
            if not land:
                sides.clear()
            self.holes.append(Hole(x, y, dx, dy, angle, "PTH" if kind == "thru_hole" else "NPTH",
                                   f"{ref}:{number or '#' + str(ordinal)}",
                                   size if land else None, shape if land else None))
        elif kind not in ("smd", "connect") or _field(node, "drill", False):
            raise ValueError(f"Unsupported {ref} pad/drill type: {kind}")
        for s in sides:
            self.counts[s]["pads"] += 1
            self.pads[s].add(land_center)

    def graphic_or_zone(self, node, placement):
        layer = _field(node, "layer", False) or _field(node, "layers", False)
        if layer and "Edge.Cuts" in layer[1:]:
            self.edges.extend(_edge_spans(node, placement))
        elif node[0] == "zone" and _field(node, "keepout", False) is None:
            for s in _sides(_layers(node)):
                self.counts[s]["zones"] += 1

    def footprint(self, fp, ordinal):
        if _layers(fp) not in (["F.Cu"], ["B.Cu"]):
            raise ValueError("Unsupported footprint placement layer")
        private = _field(fp, "private_layers", False)
        if private and ("Edge.Cuts" in private or _sides(private[1:])):
            raise ValueError("Unsupported private mechanical/copper footprint layer")
        ref = None
        for node in _children(fp):
            if node[:2] in (["property", "Reference"], ["fp_text", "reference"]):
                if len(node) < 3 or not isinstance(node[2], str):
                    raise ValueError("Malformed footprint reference")
                ref = node[2]
                break
        placement = _at(fp)
        count = 0
        for node in _children(fp):
            if node[0] == "pad":
                count += 1
                self.pad(node, placement, ref or f"FP{ordinal}", count)
            else:
                self.graphic_or_zone(node, placement)


def read_board(path) -> Board:
    """Read one native .kicad_pcb without side effects; no guessed defaults.

    Bounds are Edge.Cuts centreline extrema. Routes include only native tracks
    (segment/arc), swept by half their own width on each side. Inspection points
    select local geometry, not connectivity. Only the two OUTER copper sides are
    summarized. Unsupported relevant geometry raises ValueError, not a partial
    board; this reader is not a DRC or a replacement for a KiCad plot.
    """
    data = Path(path).read_bytes()
    root = _parse(data.decode("utf-8-sig"))
    version, = _nums(root, "version", 1)
    if not 20210000 <= version <= 20260206:
        raise ValueError(f"Unsupported KiCad board format version: {version:g}")
    general = _field(root, "general", False)
    thickness = None
    if general and _field(general, "thickness", False):
        thickness, = _size(general, "thickness", 1)
    reader = _Reader()
    nfp = 0
    for node in _children(root):
        kind = node[0]
        if kind == "footprint":
            nfp += 1
            reader.footprint(node, nfp)
        elif kind in ("segment", "arc"):
            reader.track(node)
        elif kind == "via":
            reader.via(node)
        elif kind.startswith("gr_") or kind in ("zone", "dimension", "target", "table", "image", "generated"):
            reader.graphic_or_zone(node, (0.0, 0.0, 0.0))
        elif kind not in ("version", "generator", "generator_version", "general", "paper", "page", "title_block",
                          "layers", "setup", "net", "net_class", "property", "uuid", "group",
                          "embedded_files", "embedded_fonts"):
            raise ValueError(f"Unsupported board-level object: {kind}")
    bounds, edge_path = _contours(reader.edges)
    return Board(bounds, edge_path, reader.holes, thickness, reader.counts, reader.routes,
                 hashlib.sha256(data).hexdigest(), {s: sorted(reader.widths[s]) for s in _SIDES},
                 {s: _inspection(reader.tracks[s], reader.pads[s]) for s in _SIDES})
