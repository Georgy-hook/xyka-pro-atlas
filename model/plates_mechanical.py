"""Mechanical sheets from the installed, registered B-reps; dimensions are CAD estimates."""

from dataclasses import replace

import numpy as np

from plates_graphics import Sheet, MUTE, ORANGE, TEAL
from plates_graphics import est, fit_scale, hatch_style, nstr, ratio
from plates_scene import FRONT, REAR, LEFT, RIGHT, TOP, BOTTOM
from plates_scene import board_layers, camera, distance_between_layers, flat_face_normal, frame_box, unique
from plates_section import cap_point, crop_view, section, window


def section_marker(s, m, cut_u, v_range, letter):
    """Edge-on trace. Locator horizontal = cut normal; arrows point from +u to −u."""
    x, lo = m.uv(cut_u, v_range[0])
    _, hi = m.uv(cut_u, v_range[1])
    lo -= 2
    hi += 2
    s.line([(x, lo), (x, hi)], color=TEAL, lw=.20, style=(0, (8, 3, 1.2, 3)))
    for y in (lo, hi):
        s.line([(x+5, y), (x, y)], color=TEAL, lw=.33)
        s.arrow((x, y), (1, 0), TEAL, length=1.85)
        s.label(x+6.1, y, letter, 8.1, bold=True, color=TEAL, bg='white')


def ortho(a):
    s = Sheet(2, 'Наружные проекции',
              'Закрытая сборка. Шесть видов в одном масштабе; габариты даны по видимому контуру CAD.', 'Общий вид')
    views = [('А', 'Спереди', 'со стороны панели', FRONT), ('Б', 'Сзади', 'тыльная сторона', REAR),
             ('В', 'Слева', 'наблюдатель у −X', LEFT), ('Г', 'Справа', 'наблюдатель у +X', RIGHT),
             ('Д', 'Сверху', 'наблюдатель у +Z', TOP), ('Е', 'Снизу', 'наблюдатель у −Z', BOTTOM)]
    drawings = [a.line(a.scene.items, frame) for _, _, _, frame in views]
    boxes = [(x+13, y, 95, 80) for y in (149, 36) for x in (14, 148, 282)]
    scale = min(fit_scale(p.bounds, b) for p, b in zip(drawings, boxes))
    for j, ((tag, title, side, _), p, box) in enumerate(zip(views, drawings, boxes)):
        s.caption(box[0]-13, 242 if j < 3 else 129, tag, title, f'{side}   ·   {ratio(scale)}')
        m = s.geometry(p, box, scale=scale, weight=.27)
        lo, bot, hi, top = m.uvbox(p.bounds)
        if j in (0, 2):
            s.dim_h(lo, hi, bot, bot-5.6, est(p.bounds[2]-p.bounds[0], 1))
        if j == 0:
            s.dim_v(bot, top, lo, lo-6.6, est(p.bounds[3]-p.bounds[1], 1))
    s.line([(14, 137.5), (406, 137.5)], lw=.17)
    for x in (141, 275):
        s.line([(x, 24), (x, 135)], lw=.17)
        s.line([(x, 139), (x, 247)], lw=.17)
    state = 'UpperUnit и LowerUnit состыкованы.' if a.scene.structured else 'Сборка в установленном положении.'
    s.label(14, 22.2, state+' Внутренние детали за непрозрачными оболочками не показаны.', 8.2, color=MUTE)
    s.bar(381, 23, scale, 25)
    return s


def _swatch(s, x, y, key):
    face, pattern = hatch_style(key)
    patch = s.rect(x, y-2.3, 8, 4.6, color=face, edge='#647975', lw=.15, z=9)
    patch.set_hatch(pattern)


def _cut_legend(s, caps):
    rows = [('Housing', 'Верхний кожух и его опоры'), ('LowerBody', 'Нижний корпус и его детали'),
            ('Fascia', 'Лицевая кассета'), ('LightRing', 'Световое кольцо'),
            ('Pod', 'Съёмная табачная чаша'), ('Heater', 'Нагревательный узел'),
            ('Battery', 'Съёмный аккумуляторный блок'), ('Mounts', 'Крепления'),
            ('MainPCB', 'Подложка основной платы'), ('DisplayPCB', 'Дисплейная плата и пакет LCD')]
    keys = set(caps)
    if keys & {'PodBody', 'PodLid', 'PodScreen'}:
        keys.add('Pod')
    if 'HeatGuard' in keys:
        keys.add('Heater')
    s.small(285, 241, 'УЗЛЫ, ПЕРЕСЕЧЁННЫЕ ПЛОСКОСТЬЮ А–А')
    y = 231
    for key, label in rows:
        if key in keys:
            _swatch(s, 285, y, key)
            s.label(297, y, label, 9.2)
            y -= 8.0
    s.label(285, y-1, 'Без штриховки — видимые кромки за плоскостью.', 8.0, color=MUTE)


def _pod_detail(s, sec, caps, parent):
    body = caps.get('PodBody')
    if body is None:
        return
    roles = {'PodBody': 'Корпус\nчаши', 'PodLid': 'Перфорированная\nкрышка чаши',
             'PodScreen': 'Донная сетка\nчаши', 'HeatGuard': 'Щиток\nнагревателя'}
    # A single wall, from the actual lid/screen to the guard. Preserve the
    # installed orientation, even when the cup is inverted relative to a prior CAD.
    ext = np.array([caps[k].bounds for k in roles if k in caps])
    left, _, right, _ = body.bounds
    crop = (left-2, ext[:, 1].min()-1.8, (left+right)/2+.4, ext[:, 3].max()+1.8)
    window(s, parent, crop, 'А3')
    s.caption(284, 134, 'А3', 'Край съёмной чаши', 'Увеличение отмеченной части А–А')
    m = crop_view(s, sec, crop, (283, 41, 72, 77), cap=5, weight=.20)
    targets = []
    for k, label in roles.items():
        point = cap_point(caps.get(k), crop)
        if point is not None:
            targets.append((m.uv(*point), label))
    for n, (target, label) in enumerate(sorted(targets, key=lambda t: -t[0][1]), 1):
        y = 107 - 14*(n-1)
        s.leader(target, (362, y), n)
        s.label(368, y, label, 8.6)
    s.bar(286, 29, m.scale, 5)
    s.label(405, 31, f'А3   /   {ratio(m.scale)}', 8.5, color=MUTE, align='right')


def shell(a):
    s = Sheet(3, 'Разрез корпуса А–А',
              'Полный продольный разрез. Штриховка различает узлы в плоскости, а не марки материалов.', 'Корпус')
    sc, cut = a.scene, a.cuts()
    front = a.line(sc.items, FRONT)
    sec = section(a, a.cut_items(), cut.x)
    caps = {key: area for area, key in sec.hatches}
    s.caption(14, 241, 'А1', 'Положение секущей', 'Фронтальная проекция  /  XZ')
    m = s.geometry(front, (18, 119, 82, 105), cap=.8)
    section_marker(s, m, cut.x, [front.bounds[1], front.bounds[3]], 'А')
    s.bar(23, 106, m.scale, 25)
    s.small(15, 91, 'БАЗА РАЗРЕЗА')
    s.label(15, 81, f'Плоскость X = {nstr(cut.x, 2)} мм.\nВправо — внутрь от панели (+Y),\nвверх — от основания (+Z).', 8.9, valign='top')
    glass = sc.named.get('UiGlass')
    if glass is not None:
        nz = abs(flat_face_normal(glass)[2])
        angle = np.degrees(np.arcsin(np.clip(nz, 0., 1.)))
        s.label(15, 57, f'Стекло LCD к вертикали:\n{nstr(angle, 1)}° по CAD  ·  EST', 9.0, color=ORANGE, valign='top')
    s.label(15, 37, 'Жгут и SMD не показаны. Скрытые\nпрофили оценочны; устройство АКБ\nи нагревателя не установлено.', 8.3, color=MUTE, valign='top')
    s.line([(108, 24), (108, 246)], lw=.17)
    s.line([(278, 24), (278, 246)], lw=.17)
    s.caption(116, 241, 'А2', 'Вся сборка в разрезе', 'Взгляд от +X; ближняя половина удалена')
    ms = s.geometry(sec, (114, 33, 158, 194), cap=1.25, weight=.23)
    s.bar(117, 22.8, ms.scale, 25)
    s.label(271, 24.5, f'А–А   /   {ratio(ms.scale)}', 8.7, color=MUTE, align='right')
    _cut_legend(s, caps)
    _pod_detail(s, sec, caps, ms)
    return s


def _seat_items(scene, cut, main, ui):
    # Locator without opaque covers/glass. In particular, *not* every screw in
    # Mounts belongs to the cassette: guard and internal-base screws stay out.
    prefixes = ('MechCartridgeFrame', 'MechDisplaySeat', 'MechPanelEar', 'MechServiceScrew',
                'UiDisplaySeat', 'MechUiSeat', 'DisplaySeat')
    local = [i for root in ('Fascia', 'Mounts', 'Housing') for i in scene.by.get(root, ())
             if i.name.startswith(prefixes)]
    return unique([*main, *ui, *local, cut.mount])


def _board_data(s, sc, main, ui):
    s.small(14, 78, 'ПОДЛОЖКИ   /   Ш × Д × t, мм   /   EST')
    for y, layers, root, title in ((66, main, 'MainPCB', 'Основная PCB'), (55, ui, 'DisplayPCB', 'Дисплейная PCB')):
        lo, hi = frame_box(layers, sc.board_frame(root))
        s.label(14, y, title, 8.9)
        s.label(130, y, ' × '.join(nstr(d, 2) for d in hi-lo), 9.4, color=ORANGE, align='right')
    gap = distance_between_layers(main, ui)
    s.label(14, 41, 'Между подложками, минимум', 8.7)
    s.label(130, 41, f'{nstr(gap, 2)} мм  ·  EST', 8.8, color=ORANGE, align='right')
    s.label(14, 32, 'Габарит — в плоскости своей платы; t — по нормали.\nМинимум — между телами, не зазор до корпуса.', 8.0, color=MUTE, valign='top')


def seating(a):
    s = Sheet(4, 'Посадка плат в корпусе',
              'Б–Б проходит через опору дисплейной платы. На разрезе показана установленная кассета; жгут и SMD не показаны.', 'Монтаж')
    sc, cut = a.scene, a.cuts()
    main, ui = (board_layers(sc, root) for root in ('MainPCB', 'DisplayPCB'))
    face = a.line(_seat_items(sc, cut, main, ui), sc.board_frame('DisplayPCB'))
    items = a.cut_items(mounting=True)
    whole = section(a, items, cut.seat_depth, cut.seat_frame, cut.mount)
    caps = {key: area for area, key in whole.hatches}
    if 'DisplaySeat' not in caps:
        raise ValueError(f'Б–Б does not cut material of the selected display seat: {cut.mount.name}')

    s.caption(14, 241, 'Б1', 'Платы и опоры кассеты', 'Выборка опор и подложек; по нормали дисплейной PCB')
    mf = s.geometry(face, (19, 98, 106, 123), cap=2, weight=.26)
    section_marker(s, mf, cut.seat_depth, [face.bounds[1], face.bounds[3]], 'Б')
    s.bar(19, 85, mf.scale, 15)
    _board_data(s, sc, main, ui)
    s.line([(138, 24), (138, 246)], lw=.17)
    s.line([(272, 24), (272, 246)], lw=.17)

    s.caption(145, 241, 'Б2', 'Разрез Б–Б по кассете', 'Взгляд вдоль ширины дисплейной платы')
    x, y = cut.seat_frame[:2] @ cut.mount_point
    detail = (x-5.5, y-4.5, x+7.5, y+10.5)
    local = [i for i in items if i.name in ('UiGlass', 'UiKeyMembrane') or i.name.startswith('MechOuterKey')]
    lo, hi = frame_box([*main, *ui, *local, cut.mount], cut.seat_frame)
    bounds = (*np.minimum(lo[:2]-2, detail[:2]), *np.maximum(hi[:2]+2, detail[2:]))
    ms = crop_view(s, whole, bounds, (155, 53, 105, 170), cap=2.5, weight=.21)
    window(s, ms, detail, 'Б3')
    s.bar(149, 33, ms.scale, 10)
    s.label(265, 35, ratio(ms.scale), 8.6, color=MUTE, align='right')

    s.caption(281, 241, 'Б3', 'Фрагмент у опоры', 'Увеличение отмеченного окна Б–Б')
    mc = crop_view(s, whole, detail, (283, 130, 118, 92), cap=8, weight=.23)
    s.bar(284, 120, mc.scale, 3)
    s.label(404, 122, f'Б3   /   {ratio(mc.scale)}', 8.6, color=MUTE, align='right')
    roles = [('FilmWindow', 'Тонированное окно лицевой плёнки'), ('Glass', 'Покровное стекло LCD'),
             ('OuterKey', 'Наружная клавиша кассеты'),
             ('KeyMembrane', 'Силиконовая прокладка клавиш'), ('DisplaySeat', 'Опора дисплейной PCB')]
    s.small(282, 105, 'НА РАЗРЕЗЕ Б–Б')
    targets = []
    for key, title in roles:
        pt = cap_point(caps.get(key), bounds)
        if pt is None:
            continue
        n = len(targets)+1
        target = ms.uv(*pt)
        targets.append((target, n))
        ly = 104 - 10*n
        s.badge(285.5, ly, n)
        _swatch(s, 292, ly, key)
        s.label(304, ly, title, 8.9)
        if key == 'DisplaySeat':
            seat = cap_point(caps[key], detail)
            if seat is not None:
                s.leader(mc.uv(*seat), (399, 142), n)
    # Stack close callouts instead of pointing labels at guessed board centres.
    ceiling = 215
    for j, (target, n) in enumerate(sorted(targets, key=lambda t: -t[0][1])):
        ly = min(ceiling, max(56+10*(len(targets)-j-1), target[1]))
        s.leader(target, (150, ly), n)
        ceiling = ly-10
    s.label(282, 44.5, cut.mount.name, 8.6, color=TEAL, mono=True)
    s.label(282, 35, 'Секущая проходит через опору у отверстия платы.\nНаличие втулки в модели не означает винт в отверстии.', 8.3, color=MUTE, valign='top')
    return s


def _crown_tongue(crown, diffuser):
    """Locate a window in a radial blade of the actual one-piece crown.

    Do not invent a clip body or import its design master. The plain legacy
    crown has no such face. Both views below use the entire unmodified leaf.
    """
    if crown is None or diffuser is None or crown.root != 'LightRing':
        return None
    axis = flat_face_normal(diffuser)
    if axis[2] < 0:
        axis = -axis
    candidates = []
    for face in crown.shape.Faces:
        if len(face.Wires) != 2:
            continue
        plane = face.findPlane(1e-6)
        if plane is None:
            continue
        normal = np.array(plane.Axis)
        if abs(normal @ axis) > 1e-5:
            continue
        radial = np.array(face.CenterOfMass) - diffuser.center
        radial -= axis * (radial @ axis)
        r = np.linalg.norm(radial)
        if r < 1e-6 or abs(normal @ radial) < .98*r:
            continue
        eye = normal if normal @ radial > 0 else -normal
        hole = next(w for w in face.Wires if not w.isSame(face.OuterWire))
        # Prefer a front-facing station, then its outer rather than inner wall.
        candidates.append(((round(eye[0]-eye[1], 5), r), face, hole, eye))
    if not candidates:
        return None
    _, face, hole, eye = max(candidates, key=lambda row: row[0])
    return face, hole, camera(-axis, -eye), camera(eye, axis)


def _fixations(scene):
    def first(*prefixes):
        return next((i for p in prefixes for i in scene.items if i.name.startswith(p)), None)

    screw = first('MechServiceScrewTopL', 'MechServiceScrew')
    base = first('MechServiceBaseInnerScrewFrontL', 'MechServiceBaseInnerScrew', 'MechInternalBaseScrew',
                 'MechServiceBaseScrew', 'MechCarrierFloorScrew', 'MechBaseCatch', 'MechCarrierCatch')
    parts = [(screw, 'Винт лицевой кассеты', 'screw', None)]
    crown = scene.named.get('MechTopBridge')
    tab = _crown_tongue(crown, scene.named.get('MechLightRing'))
    ring = next((i for i in scene.by.get('LightRing', ()) if i.name.startswith(
        ('MechLightRingClip', 'MechRingClip', 'MechLightClip', 'MechLightRingLatch'))), None)
    if ring is not None:
        parts.append((ring, 'Фиксатор светового кольца', 'ring', None))
    elif tab is not None:
        parts.append((crown, 'Корона с зацепом кольца', 'crown', tab))
    else:
        parts.append((first('MechDisplaySeatL', 'MechDisplaySeatR'), 'Опора дисплейной платы', 'flat', None))
    if base is not None:
        is_screw = 'Screw' in base.name
        title = ('Винт' if is_screw else 'Зацеп') + ' внутреннего основания'
        parts.append((base, title, 'screw' if is_screw else 'flat', None))
    else:
        parts.append((first('MechFrontHook'), 'Ответный выступ нижней части', 'flat', None))
    return [part for part in parts if part[0] is not None]


def _hardware_views(item, kind, scene):
    if kind == 'screw':
        axes = [(f.Area, np.array(f.Surface.Axis)) for f in item.shape.Faces
                if f.Surface.TypeId in ('Part::GeomCylinder', 'Part::GeomCone')]
        axis = max(axes, key=lambda row: row[0])[1] if axes else flat_face_normal(item)
        # Face the broad head when a coaxial circular rim survives the native scale.
        rings = [e.Curve for e in item.shape.Edges if e.Curve.TypeId == 'Part::GeomCircle'
                 and abs(np.array(e.Curve.Axis) @ axis) > .999]
        if rings and (np.array(max(rings, key=lambda c: c.Radius).Center) - item.center) @ axis < 0:
            axis = -axis
        front = camera(axis, np.eye(3)[np.argmin(np.abs(axis))])
        return front, camera(front[0], axis), 'Вдоль оси винта', 'Поперёк оси'
    diffuser = scene.named.get('MechLightRing')
    if kind == 'ring' and diffuser is not None:
        axis = flat_face_normal(diffuser)
        if axis[2] < 0:
            axis = -axis
        delta = item.center - diffuser.center
        radial = delta - axis*(delta @ axis)
        if np.linalg.norm(radial) > 1e-5:
            front = camera(radial, axis)
            return front, camera(front[0], axis), 'По радиусу кольца', 'По касательной к кольцу'
    try:
        normal = flat_face_normal(item)
    except ValueError:
        return FRONT, RIGHT, 'Спереди', 'Справа'
    front = camera(normal, (0, 0, 1) if abs(normal[2]) < .95 else (0, 1, 0))
    return front, camera(front[0], front[1]), 'По нормали к плоской грани', 'Сбоку'


def _crown_detail(s, a, item, tab, x):
    face, hole, bottom, radial = tab
    plan, side = a.line([item], bottom), a.line([item], radial)
    mb = s.geometry(plan, (x+6, 145, 105, 62), cap=2, weight=.23)
    lo, hi = frame_box([replace(item, shape=face)], bottom)
    window(s, mb, (*(lo[:2]-1.4), *(hi[:2]+1.4)), 'К')
    s.label(x, 215, f'Снизу  /  корона целиком  /  {ratio(mb.scale)}', 8.6, color=MUTE)
    # Zoom the projected silhouette, not a clipped-off free-standing solid.
    lo, hi = frame_box([replace(item, shape=face)], radial)
    crop = (*(lo[:2] - [1.8, .7]), *(hi[:2] + [1.8, .7]))
    mc = crop_view(s, side, crop, (x+7, 66, 101, 61), cap=10, weight=.23)
    s.label(x, 137, 'К  /  по радиусу, окно зацепа короны', 8.6, color=MUTE)
    lo, hi = frame_box([replace(item, shape=hole)], radial)
    _, bot, right, top = mc.uvbox((*lo[:2], *hi[:2]))
    s.dim_v(bot, top, right, mc.rect[0]+mc.rect[2]+5, est(hi[1]-lo[1], 2))
    s.bar(x+3, 52, mc.scale, 2)
    s.label(x+115, 54, f'К   /   {ratio(mc.scale)}', 8.9, color=MUTE, align='right')


def hardware(a):
    s = Sheet(7, 'Крепления и механические детали',
              'Два взаимно перпендикулярных вида каждой позиции. Размеры сняты с реальных контуров модели.', 'Детали')
    for j, (item, title, kind, tab) in enumerate(_fixations(a.scene)):
        x = (14, 149, 284)[j]
        if j:
            s.line([(x-8, 27), (x-8, 245)], lw=.18)
        s.small(x, 241, f'ДЕТАЛЬ  {j+1:02d}')
        s.label(x, 231, title, 10.5, bold=True)
        s.label(x, 41, item.name, 8.6, color=TEAL, mono=True)
        location = f'{item.unit}  /  {item.root}' if item.unit else item.root
        if kind == 'crown':
            s.label(x, 33, location+'  ·  Язычок — часть короны', 8.2, color=MUTE)
            _crown_detail(s, a, item, tab, x)
            continue
        s.label(x, 33, location, 8.2, color=MUTE)
        f1, f2, label1, label2 = _hardware_views(item, kind, a.scene)
        first, second = a.line([item], f1), a.line([item], f2)
        b1, b2 = (x+7, 146, 101, 60), (x+7, 66, 101, 61)
        scale = min(fit_scale(first.bounds, b1, cap=16), fit_scale(second.bounds, b2, cap=16))
        s.label(x, 215, label1, 8.6, color=MUTE)
        s.geometry(first, b1, scale=scale, weight=.27)
        s.label(x, 137, label2, 8.6, color=MUTE)
        m = s.geometry(second, b2, scale=scale, weight=.27)
        _, bot, hi, top = m.uvbox(second.bounds)
        s.dim_v(bot, top, hi, hi+5.4, est(second.bounds[3]-second.bounds[1], 2))
        s.bar(x+3, 52, scale, 1 if scale >= 4 else 5)
        s.label(x+115, 54, ratio(scale), 8.9, color=MUTE, align='right')
    s.label(14, 21.8, 'EST — габарит геометрии CAD, не спецификация крепежа. Резьба, материал и допуски не устанавливаются по этим видам.', 8.1, color=MUTE)
    return s
