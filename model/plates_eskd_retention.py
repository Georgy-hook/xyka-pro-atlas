"""XKAH.43.100 СБ, sheet 3: three installed upper-unit retention interfaces."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
from matplotlib.patches import Circle, Polygon
from shapely import union_all
from shapely.geometry import LineString, box

from plates_eskd_geom import Drawing
from plates_eskd_positions import position_by_id
from plates_scene import camera, flat_face_normal, frame_box, unit


def _dim(value):
    return f'{value:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def _uv(frame, point):
    return frame[:2] @ np.asarray(point)


def _centre(item, frame):
    # Axially symmetric fasteners: the middle of their oriented envelope lies
    # ON the axis, unlike the centre of a tilted world bounding box.
    return frame_box([item], frame).mean(axis=0) @ frame


def _heading(d, x, y, text, sub=None):
    d.text(x, y, text, h=5, ha='center', va='center')
    if sub:
        d.text(x, y-9, sub, h=3.5, ha='center', va='center')


def _direction(d, tip, direction, letter):
    vec = unit(direction)
    tip = np.asarray(tip)
    normal = np.array([-vec[1], vec[0]])
    tail = tip - 10*vec
    d.line((tail, tip), width=.5)
    d.ax.add_patch(Polygon([tip, tip-4*vec+.7*normal, tip-4*vec-.7*normal],
                           facecolor='black', edgecolor='none', zorder=9))
    d.text(*(tail + 3.8*normal), letter, h=5, ha='center', va='center')


def _spot(d, p, radius):
    d.ax.add_patch(Circle(p, radius, fill=False, edgecolor='black', linewidth=.3*72/25.4, zorder=7))


def _ends(m, frame, view, origin, along, margin):
    """Paper end marks for the real plane, just outside the locator silhouette."""
    centre = _uv(frame, origin)
    t = unit(_uv(frame, along))
    low, high = np.asarray(view.bounds).reshape(2, 2)
    bounds = [(np.array([low[k], high[k]]) - centre[k]) / t[k]
              for k in range(2) if abs(t[k]) > 1e-8]
    start = max(pair.min() for pair in bounds) - margin / m.scale
    end = min(pair.max() for pair in bounds) + margin / m.scale
    return m.uv(*(centre + start*t)), m.uv(*(centre + end*t))


def _paths(line):
    if not line.is_empty and line.geom_type == 'LineString':
        yield np.asarray(line.coords)
    elif hasattr(line, 'geoms'):
        for piece in line.geoms:
            yield from _paths(piece)


def _detail(d, cut, bounds, scale, centre):
    """Short wavy breaks only where an enlarged cut actually truncates material."""
    x, y, w, h = bounds
    corners = np.array(((x, y), (x+w, y), (x+w, y+h), (x, y+h)))
    sides = []
    for p, q in zip(corners, np.roll(corners, -1, axis=0)):
        edge = q - p
        t = np.linspace(0, 1, max(30, round(np.linalg.norm(edge) * 2)))
        n = unit((-edge[1], edge[0]))
        waves = max(1, round(np.linalg.norm(edge)/12))
        offset = .44 * (1 - np.cos(t * (2*np.pi*waves)))
        sides.append(p + t[:, None]*edge + offset[:, None]*n)
    outline = np.concatenate([s[:-1] for s in sides])
    clip = Polygon(outline, transform=d.ax.transData, closed=True)
    start = len(d.ax.collections)
    m = d.view(cut, bounds, scale, center=centre, weight=.55)
    for artist in list(d.ax.collections)[start:]:
        artist.set_clip_path(clip)
    material = union_all([area for area, _ in cut.hatches])
    for side in sides:
        boundary = LineString((side - [m.dx, m.dy]) / scale)
        for part in _paths(material.intersection(boundary)):
            d.line(part*scale + [m.dx, m.dy], width=.3)
    return m


def _assembly_cut(a, members, fasteners, frame, station):
    """Normal assembly convention: show a longitudinal screw WHOLE, not hatched.

    These screws are bodies of revolution with their axes in the cut plane.
    Their near half is in front of the retained assembly. Mask with their true
    projected material, then ink the uncut screw HLR, including the head rim.
    """
    cut = a.section(members, float(frame[2] @ station), frame)
    screws = a.derived('color', fasteners, frame)
    mask = union_all([shape for shape, _ in screws.fills])
    if mask.is_empty:
        raise ValueError('Empty fastener silhouette in axial section')

    def outside(paths):
        for path in paths:
            line = LineString(path)
            if line.intersects(mask):
                yield from _paths(line.difference(mask))
            else:
                yield path

    return SimpleNamespace(bounds=cut.bounds,
                           lines=[*outside(cut.lines), *screws.lines],
                           light=[*outside(cut.light), *screws.light],
                           hatches=[(shape.difference(mask), role) for shape, role in cut.hatches])


def _cap(cut, role, m, window=None):
    x, y, w, h = m.rect
    crop = box((x-m.dx)/m.scale, (y-m.dy)/m.scale,
               (x+w-m.dx)/m.scale, (y+h-m.dy)/m.scale)
    if window is not None:
        crop = crop.intersection(box(*window))
    area = union_all([p for p, key in cut.hatches if key == role]).intersection(crop)
    if area.is_empty or area.area <= 0:
        raise ValueError(f'No cut material for {role} in detail')
    pt = area.representative_point()
    return m.uv(pt.x, pt.y)


def _crown_window(crown, diffuser, panel):
    """Find the window IN a radial tongue wall of the crown; never a pseudo leaf."""
    up = flat_face_normal(diffuser)
    if up @ panel[1] < 0:
        up = -up
    centre = _centre(diffuser, camera(up, panel[0]))
    candidates = []
    for face in crown.shape.Faces:
        if len(face.Wires) != 2:
            continue
        plane = face.findPlane(1e-6)
        if plane is None:
            continue
        n = np.asarray(plane.Axis)
        delta = np.asarray(face.CenterOfMass) - centre
        radial = delta - up*(up @ delta)
        radius = np.linalg.norm(radial)
        if radius < 1e-5 or abs(n @ up) > 1e-5 or abs(n @ radial) < .98*radius:
            continue
        eye = n if n @ radial > 0 else -n
        hole = next(w for w in face.Wires if not w.isSame(face.OuterWire))
        candidates.append(((round(eye @ (panel[0]+panel[2]), 5), radius), eye, hole))
    if not candidates:
        raise ValueError('No integral crown tongue window found in the installed CAD')
    _, radial, hole = max(candidates, key=lambda row: row[0])
    return up, radial, hole


def _fascia(d, a, panel):
    sc = a.scene
    names = sc.named
    screws = [i for i in sc.by['Mounts'] if i.name.startswith('MechServiceScrew')]
    left, right = (names['MechServiceScrewTop' + side] for side in 'LR')
    ear, bed = names['MechPanelEarTopL'], names['MechKeyCarrier']
    film = [i for i in sc.by['Fascia'] if 'MechFrontFilm' in i.chain]
    if not film:
        raise ValueError('Fascia film missing: cannot mark the removed overlay on view Ж')
    face = a.line([i for i in sc.by['Fascia'] if i not in film] + screws + sc.by['DisplayPCB'], panel)
    _heading(d, 126, 281, 'Ж (1:1)', 'Кассета без накладки')
    mf = d.view(face, (103, 172, 46, 88), 1, weight=.45)
    p, q = _centre(left, panel), _centre(right, panel)
    pl, pr = mf.uv(*_uv(panel, p)), mf.uv(*_uv(panel, q))
    _spot(d, pl, 3.7)
    d.dim_h(pl[0], pr[0], (pl[1]+1.5, pr[1]+1.5), 261.5, _dim(abs(panel[0] @ (q-p))))
    cross = np.stack((panel[0], panel[2], -panel[1]))
    d.cutline(*_ends(mf, panel, face, p, cross[0], 10), _uv(panel, -cross[2]), 'И')

    # The installed section includes the continuous film in front of the head.
    cut = _assembly_cut(a, [*film, bed, ear], [left], cross, p)
    low, high = frame_box([ear, *film], cross)
    u = cross[0] @ p
    _heading(d, 83, 158, 'И–И (10:1)', 'Левая верхняя опора')
    mc = _detail(d, cut, (30, 79, 88, 60), 10, (u-.35, (low[1]+high[1])/2))
    v0, v1 = frame_box([left], cross)[:, 1]
    d.axis(mc.uv(u, v0-.8), mc.uv(u, v1+.7))
    # Seat and external screw are different installed positions. The point
    # inside the shank is on the real screw axis, below its head recess.
    d.leader(mc.uv(u, v0+.38*(v1-v0)), (121, 108), position_by_id('100', left.name))
    right_wall = (u+1, low[1]-.1, u+2, high[1]+.1)
    d.leader(_cap(cut, 'Housing', mc, right_wall), (120, 81), position_by_id('100', 'Housing'))
    d.leader(_cap(cut, 'Fascia', mc, right_wall), (120, 140), position_by_id('100', 'Fascia'))


def _ring(d, a, top, up, radial, hole):
    n = a.scene.named
    crown, rim = n['MechTopBridge'], n['MechLightRing']
    ring = a.line([crown, rim], top)
    _heading(d, 223, 281, 'К (1:1)', 'Обод отдельно')
    mt = d.view(ring, (185, 180, 76, 74), 1, weight=.45)
    # This radial section passes through the centre of the *hole*, not the
    # centre of the complete B-rep or an assumed fourfold angular pattern.
    p = np.asarray(hole.CenterOfMass)
    cross = np.stack((radial, up, np.cross(radial, up)))
    _spot(d, mt.uv(*_uv(top, p)), 4)
    d.cutline(*_ends(mt, top, ring, p, radial, 4), _uv(top, -cross[2]), 'Л')
    cut = a.section([crown, rim, n['MechUpperFairing']], float(cross[2] @ p), cross)
    u, v = _uv(cross, p)
    _heading(d, 207, 158, 'Л–Л (5:1)', 'Зацеп светового обода')
    mc = _detail(d, cut, (153, 78, 95, 65), 5, (u-.7, v+2))
    low, high = frame_box([replace(crown, shape=hole)], cross)
    x, y0 = mc.uv(u, low[1])
    _, y1 = mc.uv(u, high[1])
    d.dim_v(y0, y1, x, 253, _dim(high[1] - low[1]))
    # Position 3 lands on the tongue just below its window, not on the lens.
    tongue = _cap(cut, 'LightRing', mc, (u-1.2, low[1]-1.5, u+.2, low[1]-.1))
    d.leader(tongue, (157, 74), position_by_id('100', 'LightRing'), side='left')


def _base(d, a, bottom, up):
    sc = a.scene
    n = sc.named
    insert, seal, carrier = (n[k] for k in ('MechServiceBaseInsert', 'MechServiceBaseGasket', 'MechHeaterCarrier'))
    seal_screws = [i for i in sc.by['Housing'] if i.name.startswith('MechServiceBaseSealScrew')]
    inner_screws = [i for i in sc.by['Housing'] if i.name.startswith('MechServiceBaseInnerScrew')]
    first, second = n['MechServiceBaseSealScrewLeft'], n['MechServiceBaseInnerScrewFrontL']
    # Only the chosen central members of the upper service interface are in
    # view М. No lower consumer shell/latch, electrical leads or invented clip.
    face = a.line([insert, carrier, *seal_screws, *inner_screws], bottom)
    _heading(d, 346, 281, 'М (1:1)', 'Внутренняя вставка и обойма')
    d.text(346, 265, 'Уплотнение снято', h=3.5, ha='center', va='center')
    mb = d.view(face, (309, 179, 74, 74), 1, weight=.45)
    p, q = _centre(first, bottom), _centre(second, bottom)
    along = unit((q-p) - up*(up @ (q-p)))
    cross = np.stack((along, up, np.cross(along, up)))
    d.cutline(*_ends(mb, bottom, face, p, along, 10), _uv(bottom, -cross[2]), 'Н')
    for point in (p, q):
        _spot(d, mb.uv(*_uv(bottom, point)), 3)
    # Both differently directed screws are in this single straight plane.
    cut = _assembly_cut(a, [insert, carrier, seal], [first, second], cross, p)
    lo, hi = frame_box([insert, seal, carrier], cross)
    c = (_uv(cross, p)[0] + _uv(cross, q)[0])/2, (lo[1]+hi[1])/2
    _heading(d, 341, 158, 'Н–Н (4:1)', 'Два уровня крепления основания')
    mc = _detail(d, cut, (271, 83, 133, 57), 4, c)
    for item, point in ((first, p), (second, q)):
        u = cross[0] @ point
        z0, z1 = frame_box([item], cross)[:, 1]
        d.axis(mc.uv(u, z0-1.1), mc.uv(u, z1+1.1))
    us, ui = cross[0] @ p, cross[0] @ q
    z0 = frame_box([first], cross)[0, 1]
    z1 = frame_box([second], cross)[1, 1]
    d.callout(mc.uv(us, z0+.4), (283, 75), f'{len(seal_screws)} винта', side='left')
    d.callout(mc.uv(ui, z1-.4), (389, 142), f'{len(inner_screws)} винта')
    d.leader(_cap(cut, 'Heater', mc), (340, 73), position_by_id('100', 'Heater'))
    # Separation of THESE two axes in the marked section, not a screw pitch.
    xs, ys = mc.uv(us, z0-1.1)
    xi, yi = mc.uv(ui, frame_box([second], cross)[0, 1]-1.1)
    d.dim_h(xs, xi, (ys, yi), 64, _dim(ui-us))


def retention(a):
    """Return sheet 3/3 of the upper assembly; never save or alter the source."""
    sc = a.scene
    panel = sc.board_frame('DisplayPCB')
    n = sc.named
    up, radial, hole = _crown_window(n['MechTopBridge'], n['MechLightRing'], panel)
    side = camera(panel[0], up)
    top = np.stack((side[0], -side[2], up))
    bottom = np.stack((side[0], side[2], -up))
    d = Drawing('XKAH.43.100 СБ', 'Часть верхняя. Сборочный чертёж', '1:1',
                paper='A3', number=3, sheets=3, form='2a')
    main = a.line(sc.by_unit['UpperUnit'], side)
    d.text(60, 271, 'Верхний блок (1:2)', h=3.5, ha='center', va='center')
    ms = d.view(main, (30, 182, 65, 80), .5, weight=.5)
    x, y = ms.uv(*_uv(side, n['MechServiceScrewTopL'].center))
    _direction(d, (x-4, y), _uv(side, -panel[2]), 'Ж')
    x, _ = ms.uv(*_uv(side, hole.CenterOfMass))
    _direction(d, (x, ms.uv(0, main.bounds[3])[1]+2), (0, -1), 'К')
    base = n['MechServiceBaseInsert']
    x, _ = ms.uv(*_uv(side, base.center))
    _direction(d, (x, ms.uv(0, main.bounds[1])[1]-2), (0, 1), 'М')
    _fascia(d, a, panel)
    _ring(d, a, top, up, radial, hole)
    _base(d, a, bottom, up)
    d.tech(['Размеры для справок.',
            'Размеры модели оценены по фотографиям. Обмеры не проводились.',
            'На разрезах И–И и Н–Н накладка и уплотнение установлены.',
            'Язычок выполнен заодно с короной обода поз. 3.',
            'Н–Н: слева — винт под уплотнением, справа — винт внутренней вставки.',
            'Вставка и оба ряда винтов относятся к корпусу поз. 1.',
            'Резьба и профиль привода винтов не установлены.'], x=26, y=53, step=6.3)
    return d
