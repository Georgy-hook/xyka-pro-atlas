"""Small deterministic KiCad 8+ file writer. Coordinates supplied in local u/v.

It emits native board and library geometry, not Gerber-as-graphics. Signed v is
flipped once here. KiCad 10 CLI reads and DRCs these versioned S-expressions.
"""

import json
import math
import uuid


NAMESPACE = uuid.UUID('868b5a32-6629-4de8-8faf-23bf0a1ca900')


def qi(text):
    return json.dumps(text, ensure_ascii=False)


def f(x):
    ans = f'{x:.6f}'.rstrip('0').rstrip('.')
    return '0' if ans in ('', '-0') else ans


def uid(key):
    return f'(uuid {uuid.uuid5(NAMESPACE, key)})'


def xy(pt, board=False):
    u, v = pt
    origin = 100 if board else 0
    return f'{f(origin + u)} {f(origin - v)}'


def line(a, b, layer, width, key, board=False):
    kind = 'gr' if board else 'fp'
    return (f'({kind}_line (start {xy(a, board)}) (end {xy(b, board)}) '
            f'(stroke (width {f(width)}) (type default)) (layer {qi(layer)}) {uid(key)})')


def arc(a, m, b, layer, width, key, board=False):
    kind = 'gr' if board else 'fp'
    return (f'({kind}_arc (start {xy(a, board)}) (mid {xy(m, board)}) (end {xy(b, board)}) '
            f'(stroke (width {f(width)}) (type default)) (layer {qi(layer)}) {uid(key)})')


def rect(a, b, layer, width, key, board=False):
    kind = 'gr' if board else 'fp'
    return (f'({kind}_rect (start {xy(a, board)}) (end {xy(b, board)}) '
            f'(stroke (width {f(width)}) (type default)) (fill none) (layer {qi(layer)}) {uid(key)})')


def circle(u, v, radius, layer, width, key, board=False):
    kind = 'gr' if board else 'fp'
    return (f'({kind}_circle (center {xy((u,v), board)}) (end {xy((u+radius,v), board)}) '
            f'(stroke (width {f(width)}) (type default)) (fill none) (layer {qi(layer)}) {uid(key)})')


def native_pad(number, center, size, key, shape='roundrect', drill=0):
    attr = 'np_thru_hole' if drill else 'smd'
    layers = '"*.Cu" "*.Mask"' if drill else '"F.Cu" "F.Mask"'
    corner = ' (roundrect_rratio 0.22)' if shape == 'roundrect' else ''
    hole = f' (drill {f(drill)})' if drill else ''
    return (f'(pad {qi(number)} {attr} {shape} (at {xy(center)}) (size {f(size[0])} {f(size[1])})'
            f'{hole} (layers {layers}){corner} {uid(key)})')


def custom_pad(number, polygons, key, anchor=.015):
    """Polygons are portions of the same observed land, not separate nets."""
    prims = []
    for poly in polygons:
        pts = ' '.join(f'(xy {xy(p)})' for p in poly)
        prims.append(f'(gr_poly (pts {pts}) (width 0) (fill yes))')
    primitive_text = '\n      '.join(prims)
    return (f'(pad {qi(number)} smd custom (at 0 0) (size {f(anchor)} {f(anchor)}) '
            f'(layers "F.Cu" "F.Mask") (options (clearance outline) (anchor circle))\n'
            f'    (primitives\n      {primitive_text}) {uid(key)})')


def ring_points(radius, count=96):
    return [(radius * math.cos(i * math.tau / count), radius * math.sin(i * math.tau / count))
            for i in range(count)]


def clip_left(points, a, b, inset=0.):
    """Keep the interior to the left of a CCW board edge. Local half-plane."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    limit = inset * math.hypot(dx, dy)

    def signed(p):
        return dx * (p[1] - a[1]) - dy * (p[0] - a[0]) - limit

    out = []
    for p, q in zip(points[-1:] + points[:-1], points):
        vp, vq = signed(p), signed(q)
        if (vp >= 0) != (vq >= 0):
            ratio = vp / (vp - vq)
            out.append((p[0] + ratio * (q[0] - p[0]), p[1] + ratio * (q[1] - p[1])))
        if vq >= 0:
            out.append(q)
    return out


def field_polygons(rows):
    """Partition one rectangular pad into joined polygons with circular voids.

    The negative spaces are photo-observed surface pits ONLY; the board does
    not acquire drills or plated-through vias at these coordinates. 24 edges
    per circular void (<0.0011 mm chordal approximation for R=0.116).
    """
    w, h, radius = 4.32, 6.10, 0.116
    band0 = 0.0
    pieces = []
    for y, cols in sorted(rows.items()):
        lo, hi = y - radius, y + radius
        pieces.append([(0, band0), (w, band0), (w, lo), (0, lo)])
        left = [(0, lo), (0, hi)]
        for x in sorted(cols):
            semis = []
            for sign in (-1, 1):
                semis.append([(x + sign * radius * math.cos(-math.pi / 2 + j * math.pi / 12),
                                y + radius * math.sin(-math.pi / 2 + j * math.pi / 12)) for j in range(13)])
            pieces.append(left + list(reversed(semis[0])))
            left = semis[1]
        pieces.append(left + [(w, hi), (w, lo)])
        band0 = hi
    pieces.append([(0, band0), (w, band0), (w, h), (0, h)])
    return [[(u - w / 2, v - h / 2) for u, v in poly] for poly in pieces]
