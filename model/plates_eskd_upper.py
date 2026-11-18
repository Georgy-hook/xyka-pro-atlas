"""Верхняя часть, лист 1: установленный узел, разрез по опоре и подложки плат."""

import FreeCAD as App
import numpy as np
import Part
from matplotlib.patches import Ellipse
from shapely.affinity import scale as scale_area
from shapely.geometry import Point

from plates_eskd_geom import Drawing
from plates_eskd_positions import position_by_id
from plates_render import root_anchors
from plates_scene import BOTTOM, board_layers, frame_box, substrate
from plates_section import cap_point, section


_REFERENCE = 'Размеры для справок.'
_PHOTO_NOTE = 'Размеры оценены по фотографиям. Обмеры не выполнялись.'


def _dim(value):
    return f'{value:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def _material(caps, role, bounds=None, region=None):
    """A point in actual section material, optionally within the magnifier."""
    area = caps.get(role)
    if area is not None and region is not None:
        area = area.intersection(region)
    p = cap_point(area, bounds)
    if p is None:
        raise ValueError(f'No section material for {role} in the marked region')
    return p


def _full_view(d, proj, x, y, size, center):
    w, h = size
    box = (x - w / 2, y - h / 2, w, h)
    m = d.view(proj, box, 1, center=center, weight=.5)
    x0, y0, x1, y1 = m.uvbox(proj.bounds)
    if x0 < box[0] or y0 < box[1] or x1 > box[0] + w or y1 > box[1] + h:
        raise ValueError('Full-size view does not fit its field')
    return m


def _laminate(d, a, root, cx, caption):
    """True length/width in the board plane; thickness normal to that plane."""
    scene = a.scene
    core = substrate(scene, root)
    layers = board_layers(scene, root)
    if any(i.unit != 'UpperUnit' for i in layers):
        raise ValueError(f'{root}: laminate is not in the upper unit')
    u, v, normal = scene.board_frame(root)
    frame = np.array((v, -u, normal))  # along goes right; no reflection
    lo, hi = frame_box(layers, frame)
    length, width, thickness = hi - lo
    # Show the outline, apertures and native end features of the bare core;
    # when masks are included in the thickness, identify them on the view.
    plan = a.line([core], frame)
    m = _full_view(d, plan, cx, 98, (78, 38), (lo[:2] + hi[:2]) / 2)
    points = np.concatenate([*plan.lines, *plan.light])
    if not np.allclose([points.min(0), points.max(0)], [lo[:2], hi[:2]], atol=.015):
        raise ValueError(f'{root}: outline does not witness the laminate dimensions')

    # Extension lines meet HLR end points at the extrema, not the corners
    # of an imaginary rectangle around the rounded or notched substrate.
    def ends(axis, toward):
        out = []
        for limit in (points[:, axis].min(), points[:, axis].max()):
            edge = points[np.abs(points[:, axis] - limit) < 1e-5]
            out.append(m.uv(*edge[np.argmax(toward * edge[:, 1-axis])]))
        return out

    p, q = ends(0, -1)
    d.dim_h(p[0], q[0], (p[1], q[1]), 73, _dim(length))
    p, q = ends(1, 1)
    d.dim_v(p[1], q[1], (p[0], q[0]), cx + length / 2 + 10, _dim(width))
    d.text(cx, 129, caption, h=3.5, ha='center', va='center')
    what = 'Толщина с масками' if len(layers) > 1 else 'Толщина'
    d.text(cx, 121, f'{what} {_dim(thickness)}', h=3.5, ha='center', va='center')


def _detail(d, a, cut, proj, parent, caps):
    # One ellipse, in the section's own (u,v) space, defines both the
    # locator and the crop. Nothing in the detail is shifted or re-stacked.
    seat_u, seat_v = cut.seat_frame[:2] @ cut.mount_point
    center = (seat_u + 3.35, seat_v + 10.4)
    rx, ry = 8.25, 15.4
    region = scale_area(Point(center).buffer(1, quad_segs=64), rx, ry, origin=center)
    angle = np.linspace(0, 2 * np.pi, 193)
    outline = np.array(center) + np.column_stack((rx * np.cos(angle), ry * np.sin(angle)))
    d.line([parent.uv(*p) for p in outline], width=.25, zorder=7)
    tag = parent.uv(*outline[72])
    d.line([tag, (37, 221), (28, 221)], width=.25, zorder=7)
    d.text(32.5, 222, 'В', h=5, ha='center', va='bottom')

    scale = 5
    cx, cy = 338, 190
    dx, dy = scale * rx, scale * ry
    before = len(d.ax.collections)
    m = d.view(proj, (cx-dx, cy-dy, 2*dx, 2*dy), scale, center=center, weight=.5)
    clip = Ellipse((cx, cy), 2*dx, 2*dy, transform=d.ax.transData)
    for collection in d.ax.collections[before:]:
        collection.set_clip_path(clip)
    d.text(cx, 278, 'В (5:1)', h=5, ha='center', va='center')

    def dot(role, low, high, material=None):
        bounds = (center[0]-rx, seat_v+low, center[0]+rx, seat_v+high)
        return m.uv(*_material(material if material is not None else caps, role, bounds, region))

    for role, low, high, elbow, label in (
        ('Glass', 18.5, 21, (300, 247), 'Стекло дисплея'),
        ('OuterKey', 7, 9, (297, 199), 'Клавиша'),
        ('KeyMembrane', 4.7, 6.2, (296, 171), 'Мембрана'),
        ('DisplaySeat', -1.5, -.3, (296, 132),
         'Левая опора платы' if cut.mount.name == 'MechDisplaySeatL' else 'Правая опора платы'),
    ):
        d.callout(dot(role, low, high), elbow, label, side='left')

    # Test the two actual substrates separately: the common DisplayPCB hatch
    # also contains the LCD backing, cell and switch; that is not the board.
    for pos, root, low, high, y in (
        (6, 'MainPCB', 15, 18, 237), (7, 'DisplayPCB', 12, 14, 206),
    ):
        core = substrate(a.scene, root)
        part = a.section([core], cut.seat_depth, cut.seat_frame)
        stock = {key: area.intersection(caps[key]) for area, key in part.hatches}
        d.leader(dot(root, low, high, stock), (386, y), pos)


def _closure_pin(d, a, items):
    """Locate the exposed end on the installed underside, not the adjacent guide."""
    pin = a.scene.named['MechClosurePin']
    pos = position_by_id('100', pin.name, a)
    ends = [face for face in pin.shape.Faces
            if abs(face.BoundBox.ZMax - pin.box[0, 2]) < 1e-5]
    if len(ends) != 1 or not ends[0].isInside(ends[0].CenterOfMass, 1e-6, False):
        raise ValueError('No unambiguous lower end face on MechClosurePin')
    tip = ends[0].CenterOfMass
    start_z = min(item.box[0, 2] for item in items) - 1
    ray = Part.makeLine(App.Vector(tip.x, tip.y, start_z), tip)
    for item in items:
        lo, hi = item.box
        if (item is not pin and lo[2] <= tip.z + 1e-6
                and lo[0] - 1e-6 <= tip.x <= hi[0] + 1e-6
                and lo[1] - 1e-6 <= tip.y <= hi[1] + 1e-6
                and item.shape.common(ray).Vertexes):
            raise ValueError(f'{item.name} obscures the pin in the underside view')

    # One HLR of all upper-unit leaves, one frame, two scales. The mark on
    # the 1:2 view describes exactly the region enlarged at 5:1.
    proj = a.line(items, BOTTOM)
    locator = d.view(proj, (246, 63, 48, 54), .5, weight=.5)
    x0, y0, x1, y1 = locator.uvbox(proj.bounds)
    if x0 < 246 or y0 < 63 or x1 > 294 or y1 > 117:
        raise ValueError('Installed underside no longer fits its 1:2 field')
    d.text(270, 122, 'Вид снизу (1:2)', h=3.5, ha='center', va='center')
    uv = BOTTOM[:2] @ np.array(tip)
    radius = 3.5
    angle = np.linspace(0, 2 * np.pi, 129)
    circle = uv + radius * np.column_stack((np.cos(angle), np.sin(angle)))
    d.line([locator.uv(*p) for p in circle], width=.25, zorder=7)
    d.line([locator.uv(*circle[-17]), (295, 70), (303, 70)], width=.25, zorder=7)
    d.text(299, 71, 'П', h=3.5, ha='center', va='bottom')

    cx, cy, scale = 338, 85, 5
    r = scale * radius
    start = len(d.ax.collections)
    detail = d.view(proj, (cx-r, cy-r, 2*r, 2*r), scale, center=uv, weight=.5)
    clip = Ellipse((cx, cy), 2*r, 2*r, transform=d.ax.transData)
    for lines in d.ax.collections[start:]:
        lines.set_clip_path(clip)
    d.text(cx, 108, 'П (5:1)', h=3.5, ha='center', va='center')
    d.leader(detail.uv(*uv), (366, 94), pos)
    # Linear scale of this fragment, outside the geometry (not marks on the pin).
    x, y = 367, 74
    d.line([(x, y), (x + 2*scale, y)], width=.25)
    for mm in range(3):
        tick = x + mm*scale
        d.line([(tick, y), (tick, y + 1.5)], width=.25)
        d.text(tick, y + 2, str(mm), h=2.5, ha='center', va='bottom')
    d.text(x + 2*scale + 4, y + 2, 'мм', h=2.5, va='bottom')


def upper(a):
    """XKAH.43.100 СБ. Первый лист сборочного чертежа верхней части."""
    scene = a.scene
    items = scene.by_unit['UpperUnit']
    cut = a.cuts()
    if cut.mount not in items or cut.mount.name not in ('MechDisplaySeatL', 'MechDisplaySeatR'):
        raise ValueError('Б–Б requires a registered display mounting seat in UpperUnit')
    d = Drawing('XKAH.43.100 СБ', 'Верхняя часть', '1:1', paper='A3',
                number=1, sheets=3, form='1')

    # Both large views share a vertical datum. Looking along -section.u,
    # the cut plane is edge-on, exactly at the abscissa of the physical seat.
    side, up, eye = cut.seat_frame
    front = np.array((eye, up, -side))
    outer = a.line(items, front)
    structure = set(a.cut_items(mounting=True))
    bodies = [i for i in items if i in structure or i.root in ('Battery', 'Heater', 'Harness')
              or (i.root == 'DisplayPCB' and i.name.startswith(('UiPlunger', 'UiSwitch')))]
    proj = section(a, bodies, cut.seat_depth, cut.seat_frame, cut.mount)
    caps = {role: area for area, role in proj.hatches}
    mf = _full_view(d, outer, 205, 206, (83, 126), (0, 96))
    ms = _full_view(d, proj, 94, 206, (107, 126), (47, 96))
    trace_u = float(eye @ cut.mount_point)
    if not np.isclose(trace_u, cut.seat_depth):
        raise ValueError('Locator and section do not pass through the same seat datum')
    x, bottom = mf.uv(trace_u, outer.bounds[1])
    _, top = mf.uv(trace_u, outer.bounds[3])
    d.cutline((x, bottom-10), (x, top+10), (-1, 0), 'Б')
    d.text(94, 272, 'Б–Б', h=5, ha='center', va='center')

    # Front positions are first-hit leaf IDs, never centres of module boxes.
    visible = root_anchors(items, front, name_mode=True, width=1150)
    for pos, name, elbow, direction in (
        (1, 'MechUpperFairing', (248, 181), 'right'),
        (2, 'MechServiceCover', (160, 244), 'left'),
        (3, 'MechLightRing', (160, 265), 'left'),
    ):
        if name in visible:
            d.leader(mf.uv(*visible[name]), elbow, pos, side=direction)

    # Work within recognizable parts of the installed battery, heater plate
    # and cable, always intersecting these windows with the real solid caps.
    for pos, role, bounds, elbow, direction in (
        (4, 'Battery', (55, 130, 65, 144), (126, 274), 'right'),
        (5, 'Heater', (49, 46.3, 56, 47.85), (120, 140), 'right'),
        (8, 'Harness', (16, 61.9, 19, 64.7), (37, 160), 'left'),
    ):
        if role in caps:
            d.leader(ms.uv(*_material(caps, role, bounds)), elbow, pos, side=direction)

    _detail(d, a, cut, proj, ms, caps)
    _laminate(d, a, 'MainPCB', 84, 'Подложка основной платы (поз. 6)')
    _laminate(d, a, 'DisplayPCB', 202, 'Подложка платы дисплея (поз. 7)')
    _closure_pin(d, a, items)
    d.tech([_REFERENCE, _PHOTO_NOTE, 'Мелкие элементы монтажа плат на разрезе показаны упрощённо.'],
           x=28, y=55, h=3.5, step=7)
    return d
