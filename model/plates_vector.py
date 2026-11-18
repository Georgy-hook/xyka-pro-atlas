"""Orthographic vector geometry in model millimetres, without a document or GUI.

Frames have world-space rows (right, up, towards the eye). Work on located
B-reps, not object placements, labels, bounding-box illustrations or pixels.
"""

from collections import defaultdict
from dataclasses import dataclass, field

import FreeCAD as App  # Initialise FreeCAD before importing its extension modules.
import MeshPart
import Part
import TechDraw
import numpy as np
import shapely as sh
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.strtree import STRtree


__all__ = ["Projection", "line_view", "colour_view", "cut_view"]

# Polygonisation is the last step for B-rep wires. The angular limit also
# resolves very small rounds for which the absolute chord error alone is lax.
_CHORD = 0.008  # mm
_ANGLE = 0.16  # radians
_GRID = 1e-7  # mm, overlay precision (OCCT's nominal linear confusion)
_ZEPS = 1e-7
_EYE = App.Vector(0, 0, 1)
_HLR_BUDGET = 900  # edges per spatial batch, not a geometry/detail cutoff
Area = Polygon | MultiPolygon


@dataclass
class Projection:
    """2-D strokes, opaque material regions and cut regions in the SAME frame.

    Rings are closed, exteriors counterclockwise and holes clockwise. Draw
    fills in order, preserving their interiors. Empty bounds are four zeros.
    """

    lines: list[np.ndarray] = field(default_factory=list)
    light: list[np.ndarray] = field(default_factory=list)
    fills: list[tuple[Area, str]] = field(default_factory=list)
    hatches: list[tuple[Area, str]] = field(default_factory=list)
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


def _finish(view):
    boxes = [g.bounds for g, _ in (*view.fills, *view.hatches)]
    for paths in (view.lines, view.light):
        if paths:
            xy = np.concatenate(paths)
            boxes.append((*xy.min(axis=0), *xy.max(axis=0)))
    if boxes:
        b = np.asarray(boxes)
        view.bounds = tuple(map(float, (*b[:, :2].min(0), *b[:, 2:].max(0))))
    return view


def _pieces(shape):
    # childShapes composes parent orientation AND location. Unlike .Solids,
    # this also preserves standalone faces, shells and printed wires.
    if shape.ShapeType in ("Compound", "CompSolid"):
        for child in shape.childShapes():
            yield from _pieces(child)
    elif shape.ShapeType != "Vertex":
        yield shape


def _located(items, frame):
    f = np.asarray(frame, dtype=float)
    if f.shape != (3, 3) or not np.allclose(f @ f.T, np.eye(3), atol=1e-7, rtol=0):
        raise ValueError("frame must have three orthonormal rows: right, up, eye")
    m = np.eye(4)
    m[:3, :3] = f
    matrix = None if np.array_equal(f, np.eye(3)) else App.Matrix(*m.ravel())
    for item in items:
        s = item.shape
        if not s.isNull():
            for piece in _pieces(s.transformed(matrix) if matrix is not None else s):
                yield item, piece


def _points(edge):
    """Sample a trimmed edge in natural parameter order (including endpoints)."""
    curve = edge.Curve
    if isinstance(curve, Part.Line):
        p = [edge.valueAt(edge.FirstParameter), edge.valueAt(edge.LastParameter)]
    elif isinstance(curve, (Part.Circle, Part.Ellipse)):
        # Include true coordinate extrema (important for dimensioning), not
        # just the extrema of an inscribed polygon with an arbitrary start.
        if isinstance(curve, Part.Circle):
            major = minor = curve.Radius
        else:
            major, minor = curve.MajorRadius, curve.MinorRadius
        u, v = major * np.asarray(curve.XAxis), minor * np.asarray(curve.YAxis)
        lo, hi = edge.ParameterRange
        step = min(0.10, 4 * np.arcsin(np.sqrt(min(1, _CHORD / (2 * major)))))
        ts = np.linspace(lo, hi, max(1, int(np.ceil((hi - lo) / step))) + 1)
        extrema = np.arctan2(v, u)
        extrema += np.ceil((lo - extrema) / np.pi) * np.pi
        extra = np.r_[extrema, extrema + np.pi]
        ts = np.unique(np.r_[ts, extra[(extra > lo) & (extra < hi)]])
        return np.asarray(curve.Center) + np.outer(np.cos(ts), u) + np.outer(np.sin(ts), v)
    else:
        p = edge.discretize(Angular=_ANGLE, Curvature=_CHORD)
    return np.asarray(p, dtype=float).reshape(-1, 3)


def _ring(wire):
    parts = []
    for e in wire.OrderedEdges:
        p = _points(e)
        if len(p) >= 2:
            if e.Orientation == "Reversed":
                p = p[::-1]
            parts.append(p[:-1, :2])
    if not parts:
        return np.empty((0, 2))
    return np.concatenate([*parts, parts[0][:1]])


def _area(g):
    """Keep only material (never line/point debris from an overlay)."""
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    if g.geom_type == "GeometryCollection":
        parts = [_area(p) for p in g.geoms]
        return _union([p for p in parts if not p.is_empty])
    return Polygon()


def _union(parts):
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return _area(sh.union_all(parts, grid_size=_GRID))


def _face_area(face):
    outer = face.OuterWire
    shell = _ring(outer)
    if len(shell) < 4:
        return Polygon()
    holes = [_ring(w) for w in face.Wires if not outer.isSame(w)]
    g = Polygon(shell, [ring for ring in holes if len(ring) >= 4])
    return g if g.is_valid else _area(sh.make_valid(g))


def _line_arrays(g):
    if g.is_empty:
        return
    if g.geom_type in ("LineString", "LinearRing"):
        yield np.asarray(g.coords)[:, :2].copy()
    elif hasattr(g, "geoms"):
        for part in g.geoms:
            yield from _line_arrays(part)


def _stroke_key(xy):
    # Canonical direction, and start vertex for closed edges. Only quantise
    # the lookup key; output coordinates retain their original precision.
    q = np.rint(xy / _GRID).astype(np.int64)
    if np.array_equal(q[0], q[-1]):
        q = q[:-1]
        i = np.lexsort((q[:, 1], q[:, 0]))[0]
        q = np.roll(q, -i, axis=0)
        return min(q.tobytes(), np.roll(q[::-1], 1, axis=0).tobytes())
    return min(q.tobytes(), q[::-1].tobytes())


def _hlr_batches(shapes):
    """Tile a dense view. Every body that could hide a ray in a tile is included."""
    records = []
    weights = []
    for s in shapes:
        b = s.BoundBox
        records.append((b.XMin, b.YMin, b.XMax, b.YMax))
        weights.append(s.countElement("Edge"))
    bounds = np.asarray(records)
    weights = np.asarray(weights)

    def walk(ids, tile=None):
        cost = weights[ids].sum()
        if len(ids) > 1 and cost > _HLR_BUDGET:
            b = bounds[ids]
            region = np.r_[b[:, :2].min(0) - _CHORD, b[:, 2:].max(0) + _CHORD]
            if tile is not None:
                region = tile
            # Split by middle centre, not equal world-mm widths (clusters
            # can be quite uneven). Keep straddling solids in both batches.
            centres = (b[:, :2] + b[:, 2:]) / 2
            for axis in np.argsort(np.ptp(centres, axis=0))[::-1]:
                mid = np.median(centres[:, axis])
                if not region[axis] < mid < region[axis + 2]:
                    continue
                left = ids[b[:, axis] <= mid + _CHORD]
                right = ids[b[:, axis + 2] >= mid - _CHORD]
                # Do not solve an expensive, tile-spanning board anew for
                # each individual mark if subdivision hardly reduces HLR.
                if max(weights[left].sum(), weights[right].sum()) > 0.90 * cost:
                    continue
                lo, hi = region.copy(), region.copy()
                lo[axis + 2] = hi[axis] = mid
                yield from walk(left, lo)
                yield from walk(right, hi)
                return
        yield [shapes[i] for i in ids], (box(*tile) if tile is not None else None)

    if shapes:
        yield from walk(np.arange(len(shapes)))


def _linework(shapes):
    unique = []
    by_hash = defaultdict(list)
    for s in shapes:
        bucket = by_hash[hash(s)]
        if not any(s.isEqual(old) for old in bucket):
            unique.append(s)
            bucket.append(s)
    sharp, light = {}, {}
    for batch, tile in _hlr_batches(unique):
        shape = Part.makeCompound(batch) if len(batch) > 1 else batch[0]
        groups = TechDraw.projectEx(shape, _EYE)
        # V (sharp), VO (outline), V1 (G1), VN (sewn/seam). No hidden
        # compounds 5..9 and no display isoparameters (VI).
        for idx, target in ((0, sharp), (3, sharp), (1, light), (2, light)):
            if groups[idx].isNull():
                continue
            for e in groups[idx].Edges:
                xy = _points(e)[:, :2].copy()
                if len(xy) < 2 or np.ptp(xy, axis=0).max() <= _GRID:
                    continue
                paths = (xy,) if tile is None else _line_arrays(tile.intersection(LineString(xy)))
                for path in paths:
                    if len(path) >= 2 and np.ptp(path, axis=0).max() > _GRID:
                        target.setdefault(_stroke_key(path), path)
    return Projection(list(sharp.values()), [v for k, v in light.items() if k not in sharp])


def line_view(items, frame):
    """Visible sharp/silhouette and tangent/seam edges of the combined B-reps.

    OCCT performs HLR on B-reps from +w before curves are chord-sampled.
    Loose wires in a mixed scene are chord-clipped against front surfaces.
    No input shape is repositioned.
    """
    return _finish(_ink([shape for _, shape in _located(items, frame)]))


@dataclass
class _Patch:
    poly: Area
    plane: np.ndarray  # w = a*u + b*v + c
    low: float
    high: float
    owner: int


def _plane_patch(g, surface, owner):
    nx, ny, nz = surface.Axis
    a, b = -nx / nz, -ny / nz
    x, y, z = surface.Position
    c = z - a * x - b * y
    x0, y0, x1, y1 = g.bounds
    du, dv = (a * x0, a * x1), (b * y0, b * y1)
    return _Patch(g, np.array([a, b, c]), min(du) + min(dv) + c, max(du) + max(dv) + c, owner)


def _mesh_patches(shape, owner, solid):
    # Mesh the whole connected body, NOT individual faces: a trimmed cap
    # must have the very same rim vertices as the adjoining curved wall.
    mesh = MeshPart.meshFromShape(
        Shape=shape, LinearDeflection=_CHORD, AngularDeflection=0.36, Relative=False
    )
    vertices, indices = mesh.Topology
    if not indices:
        return
    tri = np.asarray(vertices)[np.asarray(indices)]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    good = (n[:, 2] if solid else abs(n[:, 2])) > _GRID**2
    tri, n = tri[good], n[good]
    ab = -n[:, :2] / n[:, 2:3]
    c = tri[:, 0, 2] - np.sum(ab * tri[:, 0, :2], axis=1)
    planes = np.column_stack([ab, c])
    # Snap shared nodes before union/difference. Independently rounding
    # partially dissolved triangle fans can introduce long, false hairlines.
    polygons = sh.set_precision(sh.polygons(tri[:, :, :2]), _GRID)
    for g, plane, low, high in zip(polygons, planes, tri[:, :, 2].min(1), tri[:, :, 2].max(1)):
        if not g.is_empty:
            yield _Patch(g, plane, low, high, owner)


def _patches(shape, owner):
    solid = shape.ShapeType == "Solid" and shape.Orientation != "Reversed"
    planes = []
    for face in shape.Faces:
        surface = face.Surface
        if isinstance(surface, Part.Plane):
            if abs(surface.Axis.z) > 1e-12 and (not solid or face.normalAt(0, 0).z > 0):
                planes.append((face, surface))
            continue
        if isinstance(surface, (Part.Cylinder, Part.SurfaceOfExtrusion)):
            axis = surface.Axis if isinstance(surface, Part.Cylinder) else surface.Direction
            if np.hypot(axis.x, axis.y) <= 1e-12:
                continue  # round holes and extruded silk seen end on: zero projected area
        yield from _mesh_patches(shape, owner, solid)
        return
    for face, surface in planes:
        g = sh.set_precision(_face_area(face), _GRID)
        if not g.is_empty:
            yield _plane_patch(g, surface, owner)


def _front_part(g, bounds, delta, wins_tie):
    """Part of blocker g with positive affine depth difference over bounds."""
    x0, y0, x1, y1 = bounds
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    a, b, c = delta
    values = [a * x + b * y + c for x, y in corners]
    low, high = min(values), max(values)
    if low >= -_ZEPS and high <= _ZEPS:
        return g if wins_tie else None
    if high <= 0:
        return None
    if low >= 0:
        return g
    # Clip the rectangle to the nearer half-plane (the equal-depth line can
    # cross INSIDE a triangle/face). Do not sort by centroid or use a Z image.
    clip = []
    for i, end in enumerate(corners):
        start = corners[i - 1]
        u, v = values[i - 1], values[i]
        if (u > 0) != (v > 0):
            t = u / (u - v)
            clip.append((start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])))
        if v > 0:
            clip.append(end)
    return _area(sh.intersection(g, Polygon(clip), grid_size=_GRID))


class _Visibility:
    """Spatially indexed vector depth test; all facets of a body share its ink."""

    def __init__(self, patches):
        self.patches = patches
        self.tree = STRtree([p.poly for p in patches])
        sh.prepare(self.tree.geometries)
        self.high = np.array([p.high for p in patches])
        self.owners = np.array([p.owner for p in patches], dtype=int)

    def visible(self, geom, plane, low, high, owner):
        ids = self.tree.query(geom)
        ids = ids[(self.high[ids] >= low - _ZEPS) & (self.owners[ids] != owner)]
        if not len(ids):
            return geom
        masks = []
        x0, y0, x1, y1 = geom.bounds
        for j in ids:
            q = self.patches[j]
            if q.low > high + _ZEPS:
                mask = q.poly
            else:
                left, bottom, right, top = q.poly.bounds
                # Expand only the test rectangle, not the geometry: a wire
                # can have a zero-width bounding box but still needs clipping.
                bounds = (
                    max(x0, left) - _GRID, max(y0, bottom) - _GRID,
                    min(x1, right) + _GRID, min(y1, top) + _GRID,
                )
                mask = _front_part(q.poly, bounds, q.plane - plane, q.owner > owner)
            if mask is not None and not mask.is_empty:
                if mask.covers(geom):
                    return None
                if mask.intersects(geom):
                    masks.append(mask)
        if masks:
            geom = sh.difference(geom, sh.union_all(masks, grid_size=_GRID), grid_size=_GRID)
        return None if geom.is_empty else geom


def _ink(shapes, vis=None):
    """Loose wires can pierce a face without a topological HLR split point."""
    wires = [s for s in shapes if s.ShapeType in ("Edge", "Wire")]
    if not wires or len(wires) == len(shapes):
        return _linework(shapes)
    bodies = [s for s in shapes if s.ShapeType not in ("Edge", "Wire")]
    view = _linework(bodies)
    if vis is None:
        vis = _Visibility([p for i, s in enumerate(shapes) for p in _patches(s, i)])
    seen = {_stroke_key(xy) for xy in view.lines}
    for wire in wires:
        for edge in wire.Edges:
            p = _points(edge)
            if len(p) < 2:
                continue
            # A constant-depth stroke can be clipped in a single overlay.
            flat = np.ptp(p[:, 2]) <= _ZEPS
            spans = (p,) if flat else (p[i:i + 2] for i in range(len(p) - 1))
            for span in spans:
                xy = span[:, :2]
                if np.ptp(xy, axis=0).max() < _GRID:
                    continue
                d = span[-1] - span[0]
                ab = np.zeros(2) if flat else d[:2] * (d[2] / (d[:2] @ d[:2]))
                plane = np.r_[ab, span[0, 2] - ab @ xy[0]]
                g = vis.visible(
                    LineString(xy), plane, span[:, 2].min(), span[:, 2].max(), len(shapes)
                )
                if g is not None:
                    for path in _line_arrays(g):
                        key = _stroke_key(path)
                        if key not in seen:
                            seen.add(key)
                            view.lines.append(path)
    return view


def colour_view(items, frame):
    """Opaque vector material plan: trimmed planes and chordal curved faces.

    At every overlap compare affine depths, splitting even intersecting
    inclined patches at their equal-depth line. Coplanar ties go to the later
    input. Dissolve visible patches by native body; never ink a mesh edge.
    Fills suffice to render tiny markings without outlines. Separate HLR
    strokes include true sharp/silhouette, secondary and edge-only geometry.
    """
    located = list(_located(items, frame))
    patches = [p for i, (_, s) in enumerate(located) for p in _patches(s, i)]

    vis = _Visibility(patches)
    pieces = defaultdict(list)
    depths = {}
    for p in patches:
        g = vis.visible(p.poly, p.plane, p.low, p.high, p.owner)
        if g is not None:
            g = _area(g)
            if not g.is_empty:
                pieces[p.owner].append(g)
                depths[p.owner] = max(depths.get(p.owner, -np.inf), p.high)
    view = _ink([s for _, s in located], vis)
    for i in sorted(pieces, key=lambda k: (depths[k], k)):
        g = sh.orient_polygons(_union(pieces[i]))
        if not g.is_empty:
            view.fills.append((g, located[i][0].color.lower()))
    return _finish(view)


def _on_plane(face, depth):
    p = face.Surface
    return (
        isinstance(p, Part.Plane)
        and np.hypot(p.Axis.x, p.Axis.y) <= 1e-12
        and abs(p.Position.z - depth) <= _ZEPS
    )


def cut_view(items, frame, plane_depth):
    """Regularised solid section: retain w <= plane_depth, viewed from +w.

    Intersect each crossing B-rep with a box whose only limiting face is the
    section plane. HLR sees the *retained* geometry. Only newly exposed solid
    caps supply hatch material, from their outer AND inner wires; neither an
    open sheet nor a merely tangent/existing face creates a hatch.
    """
    depth = float(plane_depth)
    if not np.isfinite(depth):
        raise ValueError("plane_depth must be finite")
    kept, caps = [], defaultdict(list)
    for item, s in _located(items, frame):
        b = s.BoundBox
        if b.ZMax <= depth + _ZEPS:
            kept.append(s)
            continue
        if b.ZMin >= depth - _ZEPS:
            continue
        if s.ShapeType == "Shell" and s.isClosed():
            s = Part.makeSolid(s)
        pad = max(1.0, 0.01 * b.DiagonalLength)
        tool = Part.makeBox(
            b.XLength + 2 * pad, b.YLength + 2 * pad, depth - b.ZMin + pad,
            App.Vector(b.XMin - pad, b.YMin - pad, b.ZMin - pad),
        )
        clipped = s.common(tool)
        if clipped.isNull():
            continue
        if s.ShapeType != "Solid":
            kept.extend(_pieces(clipped))
            continue
        solids = clipped.Solids  # discard isolated zero-volume touch results
        kept.extend(solids)
        faces = [_face_area(f) for body in solids for f in body.Faces if _on_plane(f, depth)]
        cap = _union(faces)
        if not cap.is_empty:
            existing = [_face_area(f) for f in s.Faces if _on_plane(f, depth)]
            if existing:
                cap = _area(sh.difference(cap, _union(existing), grid_size=_GRID))
            if not cap.is_empty:
                caps[item.root].append(cap)
    view = _ink(kept)
    view.hatches = [(sh.orient_polygons(_union(parts)), root) for root, parts in caps.items()]
    return _finish(view)
