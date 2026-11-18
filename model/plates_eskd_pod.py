"""Installed lower unit, three-piece pod and their detail drawings.

World +Z is towards the heater: the perforated *floor* of the cup is up,
its loose grid is inside, and its separate returned-edge lid is down.
All views, including the enlarged elements, use the opened document.
"""

from dataclasses import replace
from math import pi, sqrt

import FreeCAD as App
import numpy as np
from matplotlib.patches import Circle, Polygon
from shapely.geometry import MultiLineString, Point, box
from shapely.ops import nearest_points

from plates_eskd_geom import Drawing, moved_items
from plates_eskd_positions import position_by_id
from plates_scene import FRONT, LEFT, TOP, combined_box


CUP, GRID, LID = 'MechRemovablePod', 'MechPodScreen', 'MechPodLid'
RECEIVER = 'MechChamberInsert'
ROLES = {CUP: 'PodBody', GRID: 'PodScreen', LID: 'PodLid', RECEIVER: 'Receiver'}
NOTES = ('Размеры для справок.',
         'Размеры модели оценены по фотографиям; обмеры не выполнялись.')
TOL = 1e-4  # circular-loop recognition, not a part tolerance


def _size(value, digits=1):
    return f'{value:.{digits}f}'.rstrip('0').rstrip('.').replace('.', ',')


def _parts(a):
    named = {i.name: i for i in a.scene.by['Pod']}
    return [named[n] for n in (CUP, GRID, LID)]


def _place(d, proj, at, datum, scale, weight=.5):
    """Land a shared model datum on the sheet without clipping or fitting."""
    lo, hi = np.split(np.asarray(proj.bounds), 2)
    half = np.maximum(hi - datum, datum - lo) * scale + 1.5
    x, y = np.asarray(at) - half
    return d.view(proj, (x, y, *(2 * half)), scale, center=datum, weight=weight)


def _width(d, p, m, value, y, prefix='', digits=1):
    points = np.concatenate(p.lines + p.light)
    contacts = []
    for x in (points[:, 0].min(), points[:, 0].max()):
        group = points[np.abs(points[:, 0] - x) < TOL]
        contacts.append(m.uv(*min(group, key=lambda q: abs(m.uv(*q)[1] - y))))
    (x0, a), (x1, b) = contacts
    d.dim_h(x0, x1, (a, b), y, prefix + _size(value, digits))


def _height(d, p, m, value, x, digits=1):
    points = np.concatenate(p.lines + p.light)
    contacts = []
    for y in (points[:, 1].min(), points[:, 1].max()):
        group = points[np.abs(points[:, 1] - y) < TOL]
        contacts.append(m.uv(*min(group, key=lambda q: abs(m.uv(*q)[0] - x))))
    (a, y0), (b, y1) = contacts
    d.dim_v(y0, y1, (a, b), x, _size(value, digits))


def _axis(d, p, m, u):
    x, low = m.uv(u, p.bounds[1])
    _, high = m.uv(u, p.bounds[3])
    d.axis((x, low - 3), (x, high + 3))


def _plan_axes(d, m, cx, cy, radius):
    x, y = m.uv(cx, cy)
    reach = radius * m.scale + 3
    d.axis((x - reach, y), (x + reach, y))
    d.axis((x, y - reach), (x, y + reach))


def _horizontal_cut(d, p, m, cy):
    x0, y = m.uv(p.bounds[0], cy)
    x1, _ = m.uv(p.bounds[2], cy)
    d.cutline((x0 - 11, y), (x1 + 11, y), (0, 1), 'А')


def _view_arrow(d, tip, letter):
    """Single direction arrow on the plan, not a second cutting plane."""
    x, y = tip
    d.line(((x, y - 10), (x, y)), width=.5)
    d.ax.add_patch(Polygon(((x, y), (x - .7, y - 4), (x + .7, y - 4)),
                           facecolor='black', linewidth=0, zorder=9))
    d.text(x, y - 12, letter, h=5, ha='center', va='top')


def _material_point(cap, right):
    """A section leader ends in material, not the centre of a hollow body."""
    pieces = list(getattr(cap, 'geoms', (cap,)))
    lo, _, hi, _ = cap.bounds
    middle = (lo + hi) / 2
    subset = [p for p in pieces if (p.representative_point().x >= middle) == right]
    q = max(subset or pieces, key=lambda p: p.area).representative_point()
    return q.x, q.y


def _ring(wire, axes=(0, 1)):
    """Read an actual closed circular loop, including a NURBS representation."""
    if not wire.isClosed():
        raise ValueError('Open wire in circular section')
    b = wire.optimalBoundingBox(False, False)
    c = np.array(b.Center)
    r = wire.Length / (2 * pi)
    p = np.asarray(wire.discretize(Number=25)) - c
    if (r <= TOL or np.max(abs(np.linalg.norm(p[:, axes], axis=1) - r)) > TOL
            or np.ptp(p[:, 3 - sum(axes)]) > TOL):
        raise ValueError('Non-circular section: a diameter cannot be inferred from its bounds')
    return c, r


def _waist(item, z):
    loops = item.shape.slice(App.Vector(0, 0, 1), float(z))
    if len(loops) != 2:
        raise ValueError(f'{item.name}: expected two waist walls')
    (a, ri), (b, ro) = sorted(map(_ring, loops), key=lambda pair: pair[1])
    if np.linalg.norm(a - b) > TOL or ro <= ri:
        raise ValueError(f'{item.name}: not a concentric annular waist')
    return a, ri, ro


def _holes(item):
    """Match both rims of each pierced hole in horizontal native sheet faces.

    A cup's flat lands are annuli, so their concentric inner boundaries must
    not get added to the count of repeated off-axis bores. Conversely the
    centre of the staggered lid array really is one of its equal-diameter holes.
    """
    pairs = {}
    for f in item.shape.Faces:
        wires = f.Wires
        if len(wires) < 3:
            continue
        b = f.optimalBoundingBox(False, False)
        if b.ZLength > TOL:
            continue
        outer = f.OuterWire
        for w in wires:
            if w.isSame(outer):
                continue
            c, r = _ring(w)
            key = tuple(np.round((c[0], c[1], r), 5))
            pairs.setdefault(key, []).append(c[2])
    groups = {}
    for (x, y, r), levels in pairs.items():
        if len(levels) != 2 or abs(levels[0] - levels[1]) <= TOL:
            continue
        if item.shape.isInside(App.Vector(x, y, float(np.mean(levels))), 1e-7, False):
            continue
        groups.setdefault(r, []).append((x, y, min(levels), max(levels)))
    if not groups:
        raise ValueError(f'{item.name}: cannot establish a through-hole field')
    return max(groups.items(), key=lambda group: len(group[1]))


def _hole_label(d, m, item, radius, holes, elbow, hint):
    xy = np.array([h[:2] for h in holes])
    k = np.argmin(np.linalg.norm(xy - (item.center[:2] + hint), axis=1))
    center = np.asarray(m.uv(*xy[k]))
    direction = np.asarray(elbow) - center
    rim = center + m.scale * radius * direction / np.linalg.norm(direction)
    d.callout(rim, elbow, f'{len(holes)} отв. ⌀{_size(2 * radius, 2)}')


def _detail(d, p, parent, center, r, at, scale, elbow, side, caption_y):
    """Match the circular window on the parent with the SAME enlarged HLR/cap."""
    origin = np.asarray(parent.uv(*center))
    d.ax.add_patch(Circle(origin, r * parent.scale, fill=False, edgecolor='black',
                          linewidth=.3 * 72 / 25.4, zorder=6))
    towards = np.asarray(elbow) - origin
    contact = origin + r * parent.scale * towards / np.linalg.norm(towards)
    sign = 1 if side == 'right' else -1
    end = (elbow[0] + 8 * sign, elbow[1])
    d.line((contact, elbow, end), width=.3)
    d.text(elbow[0] + 4 * sign, elbow[1] + .8, 'Б', h=5, ha='center', va='bottom')
    R = r * scale
    start = len(d.ax.collections)
    m = d.view(p, (at[0] - R, at[1] - R, 2 * R, 2 * R), scale,
               center=center, weight=.5)
    clip = Circle(at, R, transform=d.ax.transData)
    for collection in list(d.ax.collections)[start:]:
        collection.set_clip_path(clip)
    d.text(at[0], caption_y, f'Б ({scale:g}:1)', h=5, ha='center', va='center')
    return m


def lower(a):
    """One installed pod in its lower receiver. Left-side A–A is on the right."""
    parts = _parts(a)
    body = parts[0]
    items = a.scene.by['LowerBody'] + a.scene.by['Pod']
    receiver = next(i for i in a.scene.by['LowerBody'] if i.name == RECEIVER)
    cx, cy, _ = body.center
    lo, hi = combined_box(items)
    d = Drawing('XKAH.43.200 СБ', 'Часть нижняя. Сборочный чертёж', '1:1')
    section = a.section([replace(i, root=ROLES.get(i.name, i.root)) for i in items],
                        -float(cx), LEFT)
    side = _place(d, section, (294, 129), (-cy, 0.), 2, .5)
    _axis(d, section, side, -cy)
    d.text(283, 262, 'А–А (2:1)', h=5, ha='center', va='center')
    caps = {role: geom for geom, role in section.hatches}
    d.leader(side.uv(*_material_point(caps['LowerBody'], False)), (206, 242),
             position_by_id('200', receiver), side='left')
    # Pick the upper lip instead of superimposing two leaders on the narrow
    # interface between cup and receiver at mid-height.
    u0, v0, u1, v1 = caps['PodBody'].bounds
    lip = caps['PodBody'].intersection(box(u1 - .15*(u1-u0), v1 - .12*(v1-v0), u1, v1))
    d.leader(side.uv(*_material_point(lip, True)), (355, 240), position_by_id('200', body))
    z = np.mean(body.box[:, 2])
    bore, ri, _ = _waist(receiver, z)
    d.callout(side.uv(-bore[1] - ri, z), (257, 184), 'Гнездо ⌀' + _size(2 * ri, 2))
    front = a.line(items, FRONT)
    fm = _place(d, front, (104, 233), (cx, (lo[2] + hi[2]) / 2), 1)
    _axis(d, front, fm, cx)
    _width(d, front, fm, hi[0] - lo[0], 194)
    _height(d, front, fm, hi[2] - lo[2], 159)
    top = a.line(items, TOP)
    tm = _place(d, top, (104, 123), (cx, cy), 1, .4)
    _plan_axes(d, tm, cx, cy, np.ptp(body.box[:, 0]) / 2)
    _height(d, top, tm, hi[1] - lo[1], 49)
    x, y0 = tm.uv(cx, top.bounds[1])
    _, y1 = tm.uv(cx, top.bounds[3])
    d.cutline((x, y0 - 11), (x, y1 + 11), (1, 0), 'А')
    d.tech(['Чаша (поз. 2) установлена крышкой на уступ гнезда корпуса (поз. 1).',
            *NOTES], x=26, y=43)
    return d


def pod(a):
    """The same three bodies are cut installed and projected after native disassembly."""
    parts = _parts(a)
    body = parts[0]
    cx, cy, _ = body.center
    lo, hi = combined_box(parts)
    diameter = np.ptp(body.box[:, 0])
    d = Drawing('XKAH.43.220 СБ', 'Чаша съёмная. Сборочный чертёж', '2:1')
    cut = a.section([replace(i, root=ROLES[i.name]) for i in parts], -float(cy), FRONT)
    m = _place(d, cut, (109, 225), (cx, (lo[2] + hi[2]) / 2), 2, .47)
    _axis(d, cut, m, cx)
    d.text(109, 274, 'А–А', h=5, ha='center', va='center')
    _width(d, cut, m, diameter, 258, '⌀')
    _height(d, cut, m, hi[2] - lo[2], 165)
    plan = a.line(parts, TOP)
    tm = _place(d, plan, (109, 134), (cx, cy), 2, .4)
    _plan_axes(d, tm, cx, cy, diameter / 2)
    _horizontal_cut(d, plan, tm, cy)
    _view_arrow(d, (96, tm.uv(cx, plan.bounds[1])[1] - 3), 'Б')

    moved = moved_items(parts, a.scene.leaf_offsets)
    spread = a.line(moved, FRONT)
    ex = _place(d, spread, (292, 170), np.mean(np.array(spread.bounds).reshape(2, 2), axis=0), 2, .45)
    # The native screen can move sideways as well as down. Give each component
    # its own projected axis; do not draw a false common installation line.
    for item in moved:
        x, y0 = ex.uv(item.center[0], item.box[0, 2])
        _, y1 = ex.uv(item.center[0], item.box[1, 2])
        d.axis((x, y0 - 2.5), (x, y1 + 2.5))
    d.text(292, 262, 'Б (разнесённое положение)', h=5, ha='center', va='center')
    # The native gaps, including the small gap from mesh tips to the cup lip,
    # are retained. Each position dot is on its own projected visible edge.
    visible = MultiLineString(spread.lines + spread.light)
    shelf = ex.uv(spread.bounds[2], 0)[0] + 15
    for item, lift in zip(moved, (15, -11, 9)):
        low, high = item.box[:, (0, 2)]
        local = visible.intersection(box(*(low - TOL), *(high + TOL)))
        wanted = Point(low + (high - low) * (.91, .50))
        _, target = nearest_points(wanted, local)
        contact = ex.uv(target.x, target.y)
        d.leader(contact, (shelf, contact[1] + lift), position_by_id('220', item))
    d.tech(['Сетка (поз. 2) расположена внутри корпуса (поз. 1), у перфорированного дна.',
            'Крышка (поз. 3) обращена к выходу нижнего корпуса.', *NOTES], x=26, y=45)
    return d


def cup(a):
    item = _parts(a)[0]
    cx, cy, z = item.center
    d = Drawing('XKAH.43.221', 'Корпус чаши', '2:1', paper='A4')
    cut = a.section([item], -float(cy), FRONT)
    fm = _place(d, cut, (106, 231), (cx, z), 2)
    _height(d, cut, fm, np.ptp(item.box[:, 2]), 159, 2)
    _, ri, ro = _waist(item, z)
    d.callout(fm.uv(cx - (ri + ro) / 2, z), (60, 245),
              'Стенка ' + _size(ro - ri, 2), side='left')
    x0, yr = fm.uv(cx - ri, z - .24 * np.ptp(item.box[:, 2]))
    x1, _ = fm.uv(cx + ri, z)
    d.dim_h(x0, x1, yr, yr, '⌀' + _size(2 * ri, 2))
    u, bottom = fm.uv(cx, cut.bounds[1])
    _, top = fm.uv(cx, cut.bounds[3])
    d.axis((u, bottom - 3), (u, yr - 1))
    d.axis((u, yr + 7), (u, top + 3))  # leave the diameter numeral clear
    # The smallest coaxial *inner loop* in the horizontal annuli belongs to
    # the central opening, not one of the repeated holes on the surrounding lands.
    rings = [_ring(w) for f in item.shape.Faces if len(f.Wires) == 2
             and f.optimalBoundingBox(False, False).ZLength < TOL
             for w in f.Wires if not w.isSame(f.OuterWire)]
    center, rp = min(((c, r) for c, r in rings if np.linalg.norm(c[:2] - (cx, cy)) < TOL),
                     key=lambda cr: (round(cr[1], 5), -cr[0][2]))
    x0, yr = fm.uv(center[0] - rp, center[2])
    x1, _ = fm.uv(center[0] + rp, center[2])
    d.dim_h(x0, x1, yr, 264, '⌀' + _size(2 * rp, 2))
    d.text(106, 277, 'А–А', h=5, ha='center', va='center')
    top = a.line([item], TOP)
    tm = _place(d, top, (106, 147), (cx, cy), 2, .42)
    diameter = np.ptp(item.box[:, 0])
    _plan_axes(d, tm, cx, cy, diameter / 2)
    _horizontal_cut(d, top, tm, cy)
    _width(d, top, tm, diameter, 93, '⌀')
    r, holes = _holes(item)
    _hole_label(d, tm, item, r, holes, (156, 179), (15, 10))
    d.tech(NOTES, x=25, y=75)
    return d


def screen(a):
    item = _parts(a)[1]
    cx, cy, z = item.center
    d = Drawing('XKAH.43.222', 'Сетка чаши', '2,5:1', paper='A4')
    cut = a.section([item], -float(cy), FRONT)
    fm = _place(d, cut, (97, 212), (cx, z), 2.5, .35)
    _height(d, cut, fm, np.ptp(item.box[:, 2]), 41, 2)
    d.text(94, 224, 'А–А', h=5, ha='center', va='center')
    top = a.line([item], TOP)
    tm = _place(d, top, (97, 145), (cx, cy), 2.5, .35)
    # Width of the real strand ends, not a diameter of an invented outer ring.
    _width(d, top, tm, np.ptp(item.box[:, 0]), 88, digits=2)
    _horizontal_cut(d, top, tm, cy)

    # Two orthogonal section families. At each centre plane the middle strands
    # cross normally and have true round profiles, unlike arbitrary bent ends.
    stations = []
    for axis, depth, coord in [((0, 1, 0), cy, 0), ((1, 0, 0), cx, 1)]:
        loops = item.shape.slice(App.Vector(*axis), float(depth))
        rings = [_ring(w, (coord, 2)) for w in loops if
                 abs(tuple(w.optimalBoundingBox(False, False).Center)[coord] - item.center[coord])
                 < .3 * np.ptp(item.box[:, coord])]
        positive = sorted(((c[coord], r) for c, r in rings if c[coord] > item.center[coord]))
        stations.append(positive[2:4])
    ((x0, r0), (x1, r1)), ((y0, _), (y1, _)) = stations
    if abs(r0 - r1) > TOL:
        raise ValueError('Unequal central wire gauges')
    center = ((x0 + x1) / 2, (y0 + y1) / 2)
    radius = 1.15 * (x1 - x0)
    at = (139, 254)
    detail = _detail(d, top, tm, center, radius, at, 10, (149, 183), 'right', 284)
    h = 10 * sqrt(radius**2 - ((x1 - x0) / 2)**2)
    refs = [detail.uv(x, center[1])[0] for x in (x0, x1)]
    for x in refs:
        d.axis((x, at[1] - h - 1), (x, at[1] + 7))
    d.dim_h(*refs, at[1] - h - 1, 222, _size(x1 - x0, 2))
    d.callout(detail.uv(x1 + r1, center[1]), (172, 252), '⌀' + _size(2 * r1, 2))
    d.tech(NOTES, x=25, y=75)
    return d


def lid(a):
    item = _parts(a)[2]
    cx, cy, z = item.center
    d = Drawing('XKAH.43.223', 'Крышка чаши', '2,5:1', paper='A4')
    cut = a.section([item], -float(cy), FRONT)
    fm = _place(d, cut, (104, 215), (cx, z), 2.5, .42)
    _axis(d, cut, fm, cx)
    d.text(104, 227, 'А–А', h=5, ha='center', va='center')
    top = a.line([item], TOP)
    tm = _place(d, top, (104, 146), (cx, cy), 2.5, .45)
    r, holes = _holes(item)
    _, _, low, high = holes[0]
    mid = (low + high) / 2
    # At half the sheet thickness there is a complete outer circle. The four
    # local folded ears can be slightly wider and are not a cylindrical OD.
    waist = item.shape.slice(App.Vector(0, 0, 1), float(mid))
    center, radius = max(map(_ring, waist), key=lambda cr: cr[1])
    _plan_axes(d, tm, cx, cy, radius)
    _horizontal_cut(d, top, tm, cy)
    x0, yr = tm.uv(center[0] - radius, cy)
    x1, _ = tm.uv(center[0] + radius, cy)
    d.dim_h(x0, x1, yr, 85, '⌀' + _size(2 * radius, 2))
    _hole_label(d, tm, item, r, holes, (155, 179), (12, 10))
    # Dimension neighbouring centres on the actual last row (no inferred
    # stagger angle, pattern multiplication or nominal mounting pitch).
    last_y = max(h[1] for h in holes)
    row = sorted(h[0] for h in holes if abs(h[1] - last_y) < TOL)
    a0, a1 = row[:2]
    u0, vr = tm.uv(a0, last_y)
    u1, _ = tm.uv(a1, last_y)
    for u in (u0, u1):
        d.axis((u - 1.6, vr), (u + 1.6, vr))
    d.dim_h(u0, u1, vr, 203, _size(a1 - a0, 2))

    left = cut.bounds[0]
    focus = (left + .65, z)
    dm = _detail(d, cut, fm, focus, 1.95, (113, 254), 20, (39, 227), 'left', 282)
    # Use located HLR in the magnified window for both height contacts.
    pts = np.concatenate(cut.lines + cut.light)
    visible = pts[np.linalg.norm(pts - focus, axis=1) < 1.95]
    vmin, vmax = visible[:, 1].min(), visible[:, 1].max()
    xrefs = [dm.uv(min(visible[abs(visible[:, 1] - v) < TOL, 0]), v)[0] for v in (vmin, vmax)]
    ylo, yhi = (dm.uv(focus[0], v)[1] for v in (vmin, vmax))
    d.dim_v(ylo, yhi, xrefs, 83, _size(vmax - vmin, 2))
    # The straight disk is cut off by the circular detail boundary; place its
    # thickness extensions at the two actual intersections with that boundary.
    refs = []
    for v in (low, high):
        u = focus[0] + sqrt(1.95**2 - (v - focus[1])**2)
        refs.append(dm.uv(u, v)[0])
    d.line([dm.uv(focus[0] + sqrt(1.95**2 - (v - focus[1])**2), v)
            for v in np.linspace(low, high, 17)], width=.25)
    d.dim_v(dm.uv(cx, low)[1], dm.uv(cx, high)[1], refs, 160, _size(high - low, 2))
    d.tech(NOTES, x=25, y=75)
    return d


def guard(a):
    from plates_eskd_heat import guard as upper_guard
    return upper_guard(a)
