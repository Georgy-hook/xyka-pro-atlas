"""Mechanical engineering sheets: true orthographic views, shell cuts, mount details."""

from dataclasses import replace
from textwrap import wrap

import numpy as np

from plates_graphics import Sheet, INK, LINE, MUTE, ORANGE, PALE, TEAL
from plates_graphics import est, fit_scale, nstr, ratio
from plates_scene import FRONT, REAR, LEFT, RIGHT, TOP, BOTTOM
from plates_scene import board_layers, camera, choose, distance_between_layers, flat_face_normal, frame_box, unique


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
              'Шесть независимых ортогональных видов закрытой сборки. Точки наблюдения указаны у каждого вида.',
              'Общий вид')
    views = [('А', 'Спереди', 'со стороны панели', FRONT), ('Б', 'Сзади', 'тыльная сторона', REAR),
             ('В', 'Слева', 'наблюдатель у −X', LEFT), ('Г', 'Справа', 'наблюдатель у +X', RIGHT),
             ('Д', 'Сверху', 'наблюдатель у +Z', TOP), ('Е', 'Снизу', 'наблюдатель у −Z', BOTTOM)]
    drawings = [a.line(a.scene.items, v[-1]) for v in views]
    boxes = [(x+13, y, 95, 80) for y in (149, 36) for x in (14, 148, 282)]
    mscale = min(fit_scale(p.bounds, b) for p, b in zip(drawings, boxes))
    for j, ((tag, title, side, frame), p, box) in enumerate(zip(views, drawings, boxes)):
        x, y = box[0]-13, (242 if j < 3 else 129)
        s.caption(x, y, tag, title, f'{side}   ·   {ratio(mscale)}')
        m = s.geometry(p, box, scale=mscale, weight=.29)
        lo, bot, hi, top = m.uvbox(p.bounds)
        w, h = p.bounds[2]-p.bounds[0], p.bounds[3]-p.bounds[1]
        if j == 0:
            s.dim_h(lo, hi, bot, bot-5.6, est(w))
            s.dim_v(bot, top, lo, lo-6.6, est(h))
        elif j == 2:
            s.dim_h(lo, hi, bot, bot-5.6, est(w))
    s.line([(14, 137.5), (406, 137.5)], lw=.17)
    for x in (141, 275):
        s.line([(x, 24), (x, 135)], lw=.17)
        s.line([(x, 139), (x, 247)], lw=.17)
    s.label(14, 22.2, 'Показаны видимые контуры. Мелкие внутренние элементы не проецируются сквозь непрозрачные оболочки.', 8.1, color=MUTE)
    s.bar(381, 23, mscale, 25)
    return s


def shell(a):
    s = Sheet(3, 'Разрез корпуса А–А',
              'Продольная вертикальная плоскость. Удалена ближняя половина; за сечением сохранены видимые кромки модели.',
              'Корпус')
    sc, cut = a.scene, a.cuts()
    front = a.line(sc.items, FRONT)
    sec = a.section(a.cut_items(), cut.x)
    s.caption(14, 241, 'А1', 'Положение секущей', 'Фронтальная проекция  /  XZ')
    m = s.geometry(front, (18, 101, 83, 101), cap=.8)
    section_marker(s, m, cut.x, [front.bounds[1], front.bounds[3]], 'А')
    s.bar(24, 87, m.scale, 25)
    s.label(16, 69, 'Мировая база: Y = 0\nВнутрь корпуса: +Y\nВысота от низа: +Z', 9.3, color=MUTE, valign='top')
    glass = choose(sc.by['DisplayPCB'], 'UiGlass', 'LCDGlass', 'стекло', required=False)
    if glass is not None:
        # Angle between the physical glass plane and the vertical direction,
        # independent of any assumption about parallelism with the PCB.
        nz = abs(flat_face_normal(glass)[2])
        angle = np.degrees(np.arcsin(np.clip(nz, 0., 1.)))
        s.label(16, 45, f'Плоскость стекла к вертикали:\n≈ {nstr(angle,1)}°  ·  EST',
                8.7, color=ORANGE, valign='top')
    s.line([(111, 28), (111, 245)], lw=.17)
    s.caption(120, 241, 'А2', 'Сечение и вид за ним', 'Наблюдатель у +X; вправо +Y, вверх +Z')
    msec = s.geometry(sec, (125, 47, 141, 175), cap=1.25, weight=.26)
    s.bar(122, 31, msec.scale, 30)
    s.label(263, 32, f'А–А  ·  {ratio(msec.scale)}', 9.5, bold=True, align='right')
    _cut_legend(s, 287, 231, sec)
    s.line([(280, 28), (280, 245)], lw=.18)
    s.small(287, 133, 'ЧТО ПОКАЗАНО')
    s.label(287, 123, 'Кожух, внутренние оболочки,\nпосадочные детали, подложки плат\nи пакет дисплея со стеклом.\nПроводка и корпуса SMD скрыты.', 9.6, valign='top')
    s.small(287, 84, 'ПРЕДЕЛ ДОСТОВЕРНОСТИ')
    s.label(287, 74, 'Форма скрытых полостей, батареи\nи нагревателя оценочная. Разрез\nпоказывает геометрию CAD, а не\nподтверждённое устройство изделия.', 9.6, valign='top')
    return s


def _cut_legend(s, x, y, sec):
    labels = {'Housing': 'Корпус', 'Mounts': 'Крепления', 'MainPCB': 'Основная плата',
              'DisplayPCB': 'Дисплейный модуль', 'Heater': 'Нагреватель · EST', 'Battery': 'Батарея · EST'}
    from matplotlib.patches import Rectangle
    marks = {'Housing': ('#e2eeea', '///'), 'Mounts': ('#ecdfca', '\\\\\\'),
             'MainPCB': ('#dbe6d5', 'xx'), 'DisplayPCB': ('#dbe6d5', 'xx'),
             'Heater': ('#ece5df', '\\\\\\'), 'Battery': ('#e3e3eb', '..')}
    seen = {root for _, root in sec.hatches}
    s.small(x, y, 'МАТЕРИАЛ В ПЛОСКОСТИ')
    y -= 11
    for key in labels:
        if key not in seen:
            continue
        color, hatch = marks[key]
        s.ax.add_patch(Rectangle((x, y-2.4), 8, 4.8, facecolor=color, hatch=hatch,
                                 edgecolor='#647975', linewidth=.45, zorder=9))
        s.label(x+12, y, labels[key], 9.4)
        y -= 9.1
    s.label(x, y-1, 'Кромки за плоскостью — без штриховки.', 8.2, color=MUTE)


def _param(scene, name):
    sheet = scene.doc.getObject('Parameters')
    if sheet and hasattr(sheet, name):
        q = getattr(sheet, name)
        return float(getattr(q, 'Value', q))
    return None


def seating(a):
    s = Sheet(4, 'Посадка плат в корпусе',
              'Физические подложки и опоры в сборочных координатах. Платы показаны без элементов, провода сняты с вида.',
              'Монтаж')
    sc, cut = a.scene, a.cuts()
    main = board_layers(sc, 'MainPCB')
    ui = board_layers(sc, 'DisplayPCB')
    carrier = [i for i in sc.by['Housing'] if any(k in i.name for k in ('CartridgeFrame', 'DisplaySeat', 'PanelEar'))]
    screws = [i for i in sc.by['Mounts'] if 'screw' in i.name.lower()]
    seat_items = unique([*main, *ui, *carrier, *screws, cut.mount])
    face = a.line(seat_items, sc.board_frame('DisplayPCB'))
    whole = a.section(a.cut_items(mounting=True), cut.seat_depth, cut.seat_frame)
    s.caption(14, 241, 'Б1', 'Подложки и крепления', 'По нормали к дисплейной PCB; ширина платы — вправо')
    mf = s.geometry(face, (22, 53, 106, 163), cap=2, weight=.28)
    section_marker(s, mf, cut.seat_depth, [face.bounds[1], face.bounds[3]], 'Б')
    s.bar(23, 33, mf.scale, 20)
    s.line([(139, 25), (139, 246)], lw=.17)
    s.caption(148, 241, 'Б2', 'Разрез Б–Б', 'Через опору, взгляд вдоль ширины дисплейной PCB')
    s.geometry(whole, (152, 50, 116, 173), cap=1.25, weight=.24)
    # Enlarged CAD section crop through the physical mounting leaf in the stack.
    p = cut.seat_frame[:2] @ cut.mount_point
    crop = (p[0]-10, p[1]-9, p[0]+10, p[1]+9)
    s.caption(282, 241, 'Б3', 'Фрагмент посадки', 'Тот же разрез; крепёж и стенка')
    box = (289, 135, 106, 83)
    s.rect(*box, edge=LINE, lw=.21)
    mc = s.geometry(whole, box, bounds=crop, cap=5, weight=.30)
    s.bar(290, 127, mc.scale, 5)
    s.label(393, 128, ratio(mc.scale), 8.5, color=MUTE, align='right')
    s.small(282, 112, 'БАЗЫ МОДЕЛИ')
    s.label(282, 101, 'Толщина каждой подложки — по нормали\nк её собственной плоскости. Указано\nкратчайшее расстояние между подложками,\nбез учёта стекла, рамки и компонентов.', 9.1, valign='top')
    for k, sub, root, name in [(0, main, 'MainPCB', 'Основная PCB'), (1, ui, 'DisplayPCB', 'Дисплейная PCB')]:
        envelope = frame_box(sub, sc.board_frame(root))
        d = envelope[1, 2] - envelope[0, 2]
        s.label(282, 60-k*9, name, 9.2, color=MUTE)
        s.label(401, 60-k*9, f't ≈ {nstr(d,2)} мм  EST', 9.2, color=ORANGE, align='right')
    between = distance_between_layers(main, ui)
    s.label(282, 42, 'Минимум между подложками', 9.2, color=MUTE)
    s.label(401, 42, f'≈ {nstr(between,1)} мм  EST', 9.2, color=ORANGE, align='right')
    s.label(148, 31, 'Сечения построены по телам CAD; штриховка обозначает материал.', 8.2, color=MUTE)
    return s


def _rep(item):
    if len(item.shape.Solids) < 2:
        return item
    # MultiSolid mounting leaves are common; show one real solid and say so.
    chosen = max(item.shape.Solids, key=lambda s: s.Volume)
    return replace(item, shape=chosen)


def _axis(item):
    ranked = []
    for f in item.shape.Faces:
        surf = f.Surface
        if surf.TypeId in ('Part::GeomCylinder', 'Part::GeomCone'):
            ranked.append((f.Area, tuple(surf.Axis)))
    if not ranked:
        # Non-uniform Part::Scale turns circles into NURBS. The cap of the
        # turned sleeve is still planar, including after arbitrary rotation.
        axis = flat_face_normal(item)
    else:
        axis = np.array(max(ranked, key=lambda p: p[0])[1])
    if axis[np.argmax(np.abs(axis))] < 0:
        axis = -axis
    return axis


def hardware(a):
    s = Sheet(7, 'Крепления и механические детали',
              'Изолированные физические детали сборки. Профиль и торец каждой позиции показаны в одном масштабе.',
              'Детали')
    sc = a.scene
    pool = [*sc.by['Mounts'], *sc.by['Housing']]
    picks = []
    for terms in [('ServiceScrewTopL', 'screw', 'винт', 'шуруп'),
                  ('DisplaySeatL', 'boss', 'стойк', 'опор', 'standoff'),
                  ('latchpin', 'closurepin', 'штыр', 'толкател', 'штифт', 'pin')]:
        part = choose([p for p in pool if p not in picks], *terms, required=False)
        if part:
            picks.append(part)
    for part in sc.by['Mounts']:
        if len(picks) >= 3:
            break
        if part not in picks:
            picks.append(part)
    for j, item in enumerate(picks[:3]):
        x = (14, 149, 284)[j]
        if j:
            s.line([(x-8, 27), (x-8, 245)], lw=.18)
        part = _rep(item)
        axis = _axis(part)
        up = np.eye(3)[int(np.argmin(np.abs(axis)))]
        head = camera(axis, up)
        side = camera(head[0], axis)
        plan = a.line([part], head)
        elevation = a.line([part], side)
        b1, b2 = (x+7, 146, 103, 60), (x+7, 66, 103, 61)
        scale = min(fit_scale(plan.bounds, b1, cap=10), fit_scale(elevation.bounds, b2, cap=10))
        s.small(x, 241, f'ДЕТАЛЬ  {j+1:02d}')
        label = item.label.split(' · ')[0].split(' / ')[0].strip()
        s.label(x, 232, '\n'.join(wrap(label, 35)[:2]), 10.8, bold=True, valign='top')
        s.label(x, 214, 'Торец', 8.4, color=MUTE)
        s.geometry(plan, b1, scale=scale)
        s.label(x, 138, 'Профиль', 8.4, color=MUTE)
        m = s.geometry(elevation, b2, scale=scale)
        lo, bot, hi, top = m.uvbox(elevation.bounds)
        h = elevation.bounds[3]-elevation.bounds[1]
        s.dim_v(bot, top, hi, hi+5.6, est(h, 1))
        s.bar(x+3, 53, scale, 1 if scale >= 4 else 5)
        s.label(x+111, 54, ratio(scale), 8.9, color=MUTE, align='right')
        multi = len(item.shape.Solids)
        desc = f'1 из {multi} тел позиции' if multi > 1 else 'Отдельное тело CAD'
        s.label(x, 40, desc, 8.7, color=MUTE)
        s.label(x, 32, item.name, 7.5, color=TEAL, mono=True)
    s.label(14, 21.8, 'Резьба, материал и класс точности не устанавливаются по изображениям. EST — размер оценочной геометрии, не спецификация крепежа.', 8.0, color=MUTE)
    return s
