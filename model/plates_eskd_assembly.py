"""Габаритный чертёж и первый лист сборки. Все три функции возвращают Drawing."""

import numpy as np

from plates_eskd_geom import Drawing
from plates_scene import BOTTOM, FRONT, LEFT, REAR, RIGHT, TOP, combined_box
from plates_section import cap_point, section


REFERENCE_NOTE = 'Размеры для справок.'
PHOTO_NOTE = 'Размеры оценены по фотографиям. Обмеры не выполнялись.'


def _dimension(value):
    return f'{value:.1f}'.removesuffix('.0').replace('.', ',')


def _placed_view(d, proj, at, center, size, scale, weight):
    """Place the stated world datum at a paper point (not the centre of the ink)."""
    x, y = at
    w, h = size
    box = (x-w/2, y-h/2, w, h)
    m = d.view(proj, box, scale, center=center, weight=weight)
    left, bottom, right, top = m.uvbox(proj.bounds)
    if (left < box[0] or bottom < box[1] or right > box[0]+w or top > box[1]+h):
        raise ValueError('Installed view would be clipped; re-layout the sheet')
    return m


def _witnesses(proj, axis, toward):
    """Return actual extension-line contacts at the two HLR silhouette extrema.

    Among points on an extremal edge choose the one nearest the dimension line.
    Thus the height extension meets the cap itself, not an empty AABB corner.
    """
    pts = np.concatenate([*proj.lines, *proj.light])
    limits = [pts[:, axis].min(), pts[:, axis].max()]
    result = []
    for end in limits:
        at_end = pts[np.abs(pts[:, axis] - end) < 1e-5]
        result.append(at_end[np.argmax(toward * at_end[:, 1-axis])])
    return result


def _width(d, proj, m, value, y):
    p, q = (m.uv(*xy) for xy in _witnesses(proj, 0, -1))
    d.dim_h(p[0], q[0], (p[1], q[1]), y, _dimension(value))


def _height(d, proj, m, value, x):
    p, q = (m.uv(*xy) for xy in _witnesses(proj, 1, +1))
    d.dim_v(p[1], q[1], (p[0], q[0]), x, _dimension(value))


def _level_circles(shape):
    for edge in shape.Edges:
        try:
            curve = edge.Curve
        except TypeError:
            # An OCC edge with no underlying 3-D curve cannot supply an axis.
            continue
        if curve.TypeId == 'Part::GeomCircle' and abs(curve.Axis.z) > .999999:
            yield curve


def _horizontal_ring(scene, name):
    """A circular B-rep edge supplies its own axis; no axis at an assumed datum."""
    item = scene.named.get(name)
    if item is None:
        return None
    return max(_level_circles(item.shape), key=lambda c: c.Radius, default=None)


def _plan_axes(d, scene, name, frame, m):
    circle = _horizontal_ring(scene, name)
    if circle is None:
        return
    center = frame[:2] @ np.array(circle.Center)
    x, y = m.uv(*center)
    r = m.scale * circle.Radius
    # The cross belongs to this opening/cap, not to the asymmetric whole case.
    d.axis((x-r-3, y), (x+r+3, y))
    d.axis((x, y-r-3), (x, y+r+3))


def _overall_items(scene):
    """At 1:2 omit only registered microfacet inserts, never the backed key or its sign."""
    keys = ('MechOuterKeyL', 'MechOuterKeyC', 'MechOuterKeyR',
            'MechFrontUnlockKey', 'MechPackReleaseKey', 'MechRearEjectKey')
    fields = set()
    for key in keys:
        cap = scene.named.get(key)
        field = scene.named.get(key + 'Field')
        if cap is not None and field is not None and cap.chain == field.chain:
            fields.add(field)
    return [i for i in scene.items if i not in fields]


def overall(a):
    """Six views in first-angle projection, with one scale and one 3-D datum."""
    sc = a.scene
    d = Drawing('XKAH.43.000 ГЧ', 'Габаритный чертёж', '1:2', product='Электронная чаша')
    lo, hi = combined_box(sc.items)
    center = (lo + hi) / 2
    # Right view left of front, left view right of front, rear beyond it;
    # top view below front and bottom view above. The signed frame rows also
    # give the correct reversal of Y in the bottom view and X in the rear.
    views = [('right', RIGHT, (83, 169), (73, 91)),
             ('front', FRONT, (162, 169), (63, 91)),
             ('left', LEFT, (247, 169), (73, 91)),
             ('rear', REAR, (337, 169), (63, 91)),
             ('top', TOP, (162, 78), (63, 68)),
             ('bottom', BOTTOM, (162, 253), (63, 68))]
    shown = _overall_items(sc)
    drawings = {}
    for key, frame, at, size in views:
        proj = a.line(shown, frame)
        m = _placed_view(d, proj, at, frame[:2] @ center, size, .5, .5)
        drawings[key] = (proj, m)
    w, depth, h = hi-lo
    front, mf = drawings['front']
    _width(d, front, mf, w, 118)
    _height(d, front, mf, h, 194)
    # The top view contains the outline of the projecting front lip as well as
    # the hinge. In a side HLR the lip's very tip can be a single tangent ray.
    plan, mt = drawings['top']
    _height(d, plan, mt, depth, 196)
    for key, frame, item in [('top', TOP, 'MechPackCap'), ('bottom', BOTTOM, 'MechStemSocket')]:
        _, m = drawings[key]
        _plan_axes(d, sc, item, frame, m)
    notes = [REFERENCE_NOTE, PHOTO_NOTE]
    if len(shown) < len(sc.items):
        notes.append('Мелкая фактура клавиш не показана.')
    d.tech(notes, x=28, y=37)
    return d


def _mouth_circle(scene):
    """Lower rim of the through bore, not the lowest point of its rolled lip."""
    stem = scene.named.get('MechStemSocket')
    if stem is None:
        return None
    # At mid-height the innermost axial wall bounds the through bore. Its
    # lower circular edge is the mouth even when the lip has no flat end face.
    zmid = (stem.box[0, 2] + stem.box[1, 2]) / 2
    rims = []
    for face in stem.shape.Faces:
        surface = face.Surface
        if surface.TypeId not in ('Part::GeomCone', 'Part::GeomCylinder'):
            continue
        if abs(surface.Axis.z) < .999999:
            continue
        circles = sorted(_level_circles(face), key=lambda c: c.Center.z)
        if len(circles) < 2:
            continue
        low, high = circles[0], circles[-1]
        if low.Center.z < zmid < high.Center.z:
            fraction = (zmid-low.Center.z) / (high.Center.z-low.Center.z)
            radius = low.Radius + fraction*(high.Radius-low.Radius)
            rims.append((radius, low))
    return min(rims, key=lambda pair: pair[0])[1] if rims else None


def _member_point(cap):
    # Choose a material point in the forward-most portion, on the side of the
    # position shelf. A centroid of the full ring could land in empty air.
    u0, v0, u1, v1 = cap.bounds
    return cap_point(cap, (u0, v0, u0 + .25*(u1-u0), v1)) or cap_point(cap)


def assembly(a):
    """General front and full A–A through the installed upper and lower units."""
    sc = a.scene
    if set(sc.units) != {'UpperUnit', 'LowerUnit'}:
        raise ValueError('The assembly specification requires the two native unit containers')
    d = Drawing('XKAH.43.000 СБ', 'Сборочный чертёж', '1:1', number=1, sheets=2,
                form='1', product='Электронная чаша')
    lo, hi = combined_box(sc.items)
    center = (lo + hi) / 2
    cut = a.cuts()
    observed = a.line(sc.items, FRONT)
    # Native cap roles distinguish the cup wall, perforated lid, sieve and
    # heater guard. No part behind or merely tangent to the plane is hatched.
    full = section(a, a.cut_items(), cut.x, RIGHT)
    mf = _placed_view(d, observed, (302, 168), FRONT[:2] @ center, (124, 190), 1, .5)
    ms = _placed_view(d, full, (159, 168), RIGHT[:2] @ center, (125, 190), 1, .5)
    bx0, by0, bx1, by1 = mf.uvbox(observed.bounds)
    sx0, sy0, sx1, sy1 = ms.uvbox(full.bounds)
    trace_u, _ = mf.uv(cut.x, center[2])
    d.cutline((trace_u, by0-10), (trace_u, by1+10), (-1, 0), 'А')
    d.text((sx0+sx1)/2, sy1+16, 'А–А', h=5, ha='center')

    # Specification positions refer to units, but their dots must touch the
    # actual named member skins, not an arbitrary merged hatch or a bounding box.
    skins = [sc.named['MechUpperFairing'], sc.named['MechLowerShroud']]
    actual = {role: area for area, role in a.section(skins, cut.x, RIGHT).hatches}
    caps = {role: area for area, role in full.hatches}
    for pos, unit, skin in zip((1, 2), ('UpperUnit', 'LowerUnit'), skins):
        if skin.unit != unit or skin.root not in actual or skin.root not in caps:
            raise ValueError(f'No section material for assembly position {pos}')
        cap = actual[skin.root].intersection(caps[skin.root])
        if cap.is_empty:
            raise ValueError(f'Full A–A lost material of {skin.name}')
        target = ms.uv(*_member_point(cap))
        d.leader(target, (sx0-14, target[1]+(14 if pos == 1 else -10)), pos, side='left')

    _height(d, observed, mf, hi[2]-lo[2], bx1+15)
    opening = _mouth_circle(sc)
    if opening is not None and abs(cut.x-opening.Center.x) < 1e-5:
        # The cut contains the bore axis, so this chord is a diameter.
        x, y = ms.uv(opening.Center.y, opening.Center.z)
        r = ms.scale * opening.Radius
        d.dim_h(x-r, x+r, y, sy0-11, '⌀' + _dimension(2*opening.Radius))
    d.tech([REFERENCE_NOTE, PHOTO_NOTE, 'Жгут и компоненты на платах в разрезе не показаны.'],
           x=28, y=43)
    return d


def upper(a):
    """Upper unit, sheet 1 of 3."""
    from plates_eskd_upper import upper as upper_sheet

    return upper_sheet(a)
