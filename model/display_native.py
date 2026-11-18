"""Stock FreeCAD profiles and B-rep helpers for the 20260305A feature.

Rounded layer outlines are actual tangent arcs, not chamfered polygons. Sketch,
Pad and Pocket own the dependencies; no runtime FeaturePython proxy is stored.
"""

import math
from pathlib import Path
import sys

import FreeCAD as App
import Part
import Sketcher


V = App.Vector
Z = V(0, 0, 1)
C = Sketcher.Constraint
P = 'Parameters.'

MASK = (0.105, 0.108, 0.115)
CORE = (0.62, 0.55, 0.39)
SILK = (0.89, 0.90, 0.88)
TIN = (0.74, 0.75, 0.72)
NICKEL = (0.55, 0.57, 0.57)
BRASS = (0.77, 0.62, 0.33)


def scale_u(value):
    return f'{P}UiW * ({value / 28.2:.10f})'


def scale_v(value):
    return f'{P}UiL * ({value / 50.4:.10f})'


def move_uv(c, obj, u, v, w=0.0):
    return c.at(obj, scale_u(u), scale_v(v), w)


def drawing_constraint(sk, constraint, expression=None):
    idx = sk.addConstraint(constraint)
    if expression:
        sk.setExpression(f'Constraints[{idx}]', expression)
    return idx


def dimension(sk, geometry, point, axis, value, expression=None):
    """Coordinate of a point or circle centre; exact zero is an axis constraint."""
    if value == 0 and expression is None:
        sk.addConstraint(C('PointOnObject', geometry, point, -2 if axis == 'X' else -1))
    else:
        drawing_constraint(sk, C('Distance' + axis, geometry, point, value), expression)


def circle(sk, x, y, radius, ex=None, ey=None, er=None):
    idx = sk.addGeometry(Part.Circle(V(x, y, 0), Z, radius), False)
    dimension(sk, idx, 3, 'X', x, ex)
    dimension(sk, idx, 3, 'Y', y, ey)
    drawing_constraint(sk, C('Radius', idx, radius), er)
    return idx


def sketch(body, name, label):
    result = body.newObject('Sketcher::SketchObject', name)
    result.Label = label
    return result


def pad(body, profile, name, label, length, expression, reverse=False):
    result = body.newObject('PartDesign::Pad', name)
    result.Label = label
    result.Profile = profile
    result.Length = length
    if expression:
        result.setExpression('Length', expression)
    result.Reversed = reverse
    profile.Visibility = False
    return result


def constrained_polygon(sk, vertices):
    """Closed linework. Each vertex drives the following edge's start point."""
    edges = []
    for i, (x, y, _, _) in enumerate(vertices):
        nx, ny, _, _ = vertices[(i + 1) % len(vertices)]
        edges.append(sk.addGeometry(Part.LineSegment(V(x, y, 0), V(nx, ny, 0)), False))
    for i, idx in enumerate(edges):
        sk.addConstraint(C('Coincident', idx, 2, edges[(i + 1) % len(edges)], 1))
    for idx, (x, y, ex, ey) in zip(edges, vertices):
        dimension(sk, idx, 1, 'X', x, ex)
        dimension(sk, idx, 1, 'Y', y, ey)


def rounded_edges(x0, y0, width, length, radius, z=0):
    """CCW line/arc sequence, starting on the front tangent."""
    x1 = x0 + width
    y1 = y0 + length
    r = radius
    corners = [
        ((x0 + r, y0), (x1 - r, y0), (x1 - r, y0 + r), -90),
        ((x1, y0 + r), (x1, y1 - r), (x1 - r, y1 - r), 0),
        ((x1 - r, y1), (x0 + r, y1), (x0 + r, y1 - r), 90),
        ((x0, y1 - r), (x0, y0 + r), (x0 + r, y0 + r), 180),
    ]
    geometry = []
    for a, b, center, start in corners:
        geometry.append(Part.LineSegment(V(*a, z), V(*b, z)))
        arc = Part.Circle(V(*center, z), Z, r)
        geometry.append(Part.ArcOfCircle(arc, math.radians(start), math.radians(start + 90)))
    return geometry


def rounded_loop(sk, x0, y0, width, length, radius, bounds, r_expr):
    """Constrain closed CCW profile by its four tangencies on each axis.

    bounds = expressions for left, lower, right, upper extrema in sketch frame.
    Packaged surfaces sharing a stack use the same sheet aliases.
    """
    geometry = rounded_edges(x0, y0, width, length, radius)
    ids = [sk.addGeometry(curve, False) for curve in geometry]
    constraints = []
    for i, edge in enumerate(ids):
        constraints.append(C('Tangent', edge, 2, ids[(i + 1) % len(ids)], 1))
    for i in (0, 4):
        constraints.append(C('Horizontal', ids[i]))
    for i in (2, 6):
        constraints.append(C('Vertical', ids[i]))
    sk.addConstraint(constraints)
    for i in (1, 3, 5, 7):
        drawing_constraint(sk, C('Radius', ids[i], radius), r_expr)
    for i, axis, coordinate, expr in [
        (6, 'X', x0, bounds[0]), (0, 'Y', y0, bounds[1]),
        (2, 'X', x0 + width, bounds[2]), (4, 'Y', y0 + length, bounds[3]),
    ]:
        dimension(sk, ids[i], 1, axis, coordinate, expr)


def round_wire(x0, y0, width, length, r, z=0):
    return Part.Wire([g.toShape() for g in rounded_edges(x0, y0, width, length, r, z)])


def round_slab(x0, y0, z, width, length, r, thickness):
    return Part.Face(round_wire(x0, y0, width, length, r, z)).extrude(V(0, 0, thickness))


def ring(ro, ri, h, center=None):
    start = V() if center is None else center
    return Part.makeCylinder(ro, h, start).cut(Part.makeCylinder(ri, h, start))


def prism(points, z, height):
    path = [V(x, y, z) for x, y in points]
    return Part.Face(Part.makePolygon(path + path[:1])).extrude(V(0, 0, height))


def stroke(points, width, height, z=0):
    """A flat continuous ink/metal trace, not a cable or electrical net."""
    poles = [V(x, y, z) for x, y in points]
    pieces = [Part.makeCylinder(width / 2, height, pt) for pt in poles]
    for a, b in zip(poles, poles[1:]):
        d = b - a
        if d.Length <= 1e-8:
            continue
        n = V(-d.y, d.x, 0) * (width / (2 * d.Length))
        wire = Part.makePolygon([a - n, b - n, b + n, a + n, a - n])
        pieces.append(Part.Face(wire).extrude(V(0, 0, height)))
    return pieces[0].multiFuse(pieces[1:]).removeSplitter()


def text_solid(text, height, thickness):
    """Extruded font outlines, persisted as native solids; no font needed on reopen."""
    candidates = [
        Path(sys.prefix) / f'lib/python{sys.version_info.major}.{sys.version_info.minor}'
        / 'site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf',
        Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        Path('C:/Windows/Fonts/arialbd.ttf'),
    ]
    font = next((path for path in candidates if path.is_file()), None)
    if font is None:
        raise FileNotFoundError('A bold sans-serif font is needed to rebuild PCB ink; see display_native.text_solid')
    glyphs = Part.makeWireString(text, str(font.parent) + '/', font.name, height, 0)
    solids = []
    for wires in glyphs:
        if wires:
            face = Part.makeFace(wires, 'Part::FaceMakerBullseye')
            solids.append(face.extrude(V(0, 0, thickness)))
    obj = Part.makeCompound(solids)
    bounds = obj.BoundBox
    obj.translate(V(-bounds.XMin, -bounds.YMin, -bounds.ZMin))
    return obj
