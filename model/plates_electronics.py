"""Mounting-side PCB plans and enlarged, registered regions of the same vector view."""

from types import SimpleNamespace

import numpy as np

from plates_graphics import Sheet, LINE, MUTE, ORANGE, SCALES, TEAL, est, hatch_style, nstr, ratio
from plates_render import root_anchors
from plates_scene import camera, choose, frame_box, projected_box, substrate


def landmark(items, *names, avoid=()):
    return choose(items, *names, avoid=avoid)


def numbered_plan(s, points, margin):
    """Send callouts to nearest side; separate their badges vertically."""
    xmin, xmax = margin
    mid = (xmin+xmax)/2
    for side in (0, 1):
        pts = sorted([(v, u, n) for n, (u, v) in points if (u >= mid) == bool(side)])
        if not pts:
            continue
        heights = [pts[0][0]]
        for v, _, _ in pts[1:]:
            heights.append(max(v, heights[-1]+10))
        shift = max(0., heights[-1]-220)
        for (v, u, n), h in zip(pts, heights):
            s.leader((u, v), ((xmin, xmax)[side], h-shift), n)


def _detail(s, view, center, box, width, tag, name, cap=10):
    x, y, w, h = box
    cx, cy = center
    smax = min(cap, w/width)
    scale = next((s for s in SCALES if s <= smax + 1e-7), smax)
    width = w/scale
    hmodel = width*h/w
    bounds = (cx - width/2, cy - hmodel/2, cx + width/2, cy + hmodel/2)
    s.rect(x, y, w, h, edge=LINE, lw=.19)
    # Exact crop: draw the original projection, not a recreated package glyph.
    m = s.geometry(view, box, bounds=bounds, scale=w/width, weight=.10)
    s.label(x, y+h+5, f'{tag}   {name}', 9.6, bold=True)
    s.label(x, y-4.2, f'Фрагмент  ·  {ratio(m.scale)}', 7.9, color=MUTE)
    return m


def pcb(a):
    sc, root = a.scene, 'MainPCB'
    s = Sheet(5, 'Основная плата: монтажная сторона',
              'GYS005-S-088-A4.3  /  20260204. Вид перпендикулярно маске со стороны компонентов; жгут снят.',
              'Электроника')
    items, frame = sc.by[root], sc.board_frame(root)
    view = a.colors(root)
    sub = substrate(sc, root)
    u3 = landmark(items, 'PcU3_Body', 'MCUPackage', 'U3Body', 'MCUBody', 'AT32F421', 'MCU', 'QFN-28',
                  avoid=('mark', 'надпись', 'legend', 'thermal', 'land', 'pin1'))
    flash = landmark(items, 'PcFlash_Body', 'FlashBody', 'FlashPackage', 'FlashIC', 'HC25FQ', 'Flash',
                     avoid=('mark', 'надпись', 'pin1', 'legend', 'lead'))
    buz = landmark(items, 'PcBuzzer_Body', 'BuzzerBody', 'buzzer', 'зуммер', 'пищал')
    rgb = landmark(items, 'PcRGBShroud', 'PcRGBPlugBody', 'RGBHousing', 'RGBConnector', 'RgbSocket', 'Connector', 'разъём',
                   avoid=('pin', 'contact', 'wire', 'lead', 'контакт'))
    keys = [u3, flash, buz, rgb]
    centers = [np.asarray(projected_box([i], frame)).reshape(2, 2).mean(0) for i in keys]
    s.caption(14, 242, 'В1', 'Компоновка', 'Шелкография и площадки — тела из модели')
    box = (27, 49, 108, 172)
    m = s.geometry(view, box, cap=3, weight=.09)
    bounds = projected_box([sub], frame)
    lo, bot, hi, top = m.uvbox(bounds)
    s.dim_h(lo, hi, bot, bot-7.5, est(bounds[2]-bounds[0], 1))
    numbered_plan(s, [(n, m.uv(*v)) for n, v in a.plan_points(root, keys)], (18, 137))
    s.bar(18, 30, m.scale, 10)
    s.label(134, 30.5, ratio(m.scale), 8.4, color=MUTE, align='right')
    s.line([(148, 26), (148, 246)], lw=.18)
    s.small(157, 243, 'УВЕЛИЧЕННЫЕ ВИДЫ')
    # Centre the paired IC window on both bodies; retain all eight Flash contacts.
    p0, p1 = centers[:2]
    width = max(14.0, abs(p1[0]-p0[0])+10, (abs(p1[1]-p0[1])+9)*91/69)
    _detail(s, view, (p0+p1)/2, (158, 151, 92, 69), width, 'В2', 'U3 и Flash')
    _detail(s, view, centers[3], (158, 46, 92, 69), 15.0, 'В3', 'Разъём подсветки')
    s.line([(263, 26), (263, 246)], lw=.18)
    s.small(272, 242, 'ПО ФОТО И МАРКИРОВКЕ')
    entries = [('AT32F421G8U7', 'U3, QFN-28. Корпус 4 × 4 мм — номинал\nпо документации, не промер этой платы.'),
               ('HC25FQ128GSSIG', 'Flash; на корпусе HCT / 25FQ128GSSIG.\nВосемь выводов, 128 Мбит.'),
               ('Зуммер', 'Круглый корпус с центральным отверстием.\nГабарит и монтажная высота — EST.'),
               ('V / R / G / B', 'Четыре проводника к подсветке.\nПолярность и напряжение не проверены.')]
    for i, (name, note) in enumerate(entries):
        s.list_entry(272, 227-i*35, i+1, name, note)
    s.small(272, 84, 'НЕ ИНТЕРПРЕТИРОВАТЬ КАК СХЕМУ')
    s.label(272, 75, 'G / CLK / DIO / V и TX / RX — подписи площадок.\nНазначение GND / SDA / SCK / VDD не\nподтверждено электрически.', 9.0, valign='top')
    s.label(272, 41.5, f'Подложка: {nstr(bounds[2]-bounds[0],1)} × {nstr(bounds[3]-bounds[1],1)} мм  ·  EST',
            9.0, color=ORANGE, bold=True)
    s.label(272, 31.5, 'Источники: IMG_8913, 8914, 8915, 8921.', 8.3, color=MUTE)
    return s


def _cut_ticks(s, box, y):
    """Mark the section on the registered detail, without drawing over the switches."""
    for edge, side in ((box[0], -1), (box[0] + box[2], 1)):
        x = edge + side * 3.4
        s.line([(edge + side * .6, y), (edge + side * 5.2, y)], color=TEAL, lw=.32)
        s.line([(x, y - 5), (x, y)], color=TEAL, lw=.23)
        s.arrow((x, y), (0, -1), TEAL)
        s.label(x, y - 7.2, 'К', 8.2, color=TEAL, bold=True, align='center')


def _key_views(s, a, frame, sub, switches, membrane, station_v):
    """Isolate the actual silicone and section the installed row, not an offset diagram."""
    s.line([(157, 133), (406, 133)], lw=.18)
    s.caption(157, 122, 'Г3', 'Силиконовая мембрана', 'Отдельная деталь, вид со стороны клавиш')
    oblique = camera((.30, -.94, 1.24), (0, 1, 0)) @ frame
    m = s.geometry(a.line(membrane, oblique), (159, 66, 105, 42), cap=5, weight=.24)
    s.bar(159, 58, m.scale, 5)
    s.label(263, 58.5, ratio(m.scale), 8.3, color=MUTE, align='right')
    s.label(159, 47, 'Одно полотно, три выступа над толкателями.\nСкрытый профиль и толщины оценочные.',
            8.6, color=MUTE, valign='top')

    fascia = a.scene.by.get('Fascia', ())
    caps = [i for i in fascia if i.name.startswith(('MechOuterKeyL', 'MechOuterKeyC', 'MechOuterKeyR'))]
    # The cut projector unions exposed material by root. Keep the silicone
    # distinct from the PCB; qualify the cache name, not the native object.
    def layer(items, role):
        return [SimpleNamespace(name=f'{i.name}:{role}', shape=i.shape, root=role) for i in items]

    # With +u across and +w up, the eye is at -v. station_v and the plane
    # depth are projected WORLD mm; do not subtract the board origin again.
    cross = np.stack((frame[0], frame[2], -frame[1]))
    cut_items = [sub, *switches, *layer(membrane, 'KeyMembrane'), *layer(caps, 'OuterKey')]
    section = a.section(cut_items, -station_v, cross)
    s.caption(277, 122, 'Г4', 'Разрез К–К', 'Через средний толкатель, взгляд в сторону дисплея')
    m = s.geometry(section, (279, 66, 125, 42), cap=5, weight=.21)
    s.bar(279, 58, m.scale, 5)
    s.label(404, 58.5, ratio(m.scale), 8.3, color=MUTE, align='right')
    present = {role for _, role in section.hatches}
    for x, role, name in ((279, 'DisplayPCB', 'Плата и кнопки'), (326, 'KeyMembrane', 'Силикон'),
                          (360, 'OuterKey', 'Наружные клавиши')):
        if role in present:
            color, hatch = hatch_style(role)
            s.rect(x, 45, 5.5, 3.4, color=color, edge='#647975', lw=.22, z=8).set_hatch(hatch)
            s.label(x + 7, 46.7, name, 8.1, color=MUTE)
    s.label(279, 37, 'Кромки за плоскостью К–К — без штриховки.', 8.3, color=MUTE)


def ui(a):
    sc, root = a.scene, 'DisplayPCB'
    items, frame = sc.by[root], sc.board_frame(root)
    # Internal feature / App::Part ID, never a colour or a translated label.
    membrane = [i for i in items if i.name == 'UiKeyMembrane' or 'UiKeyMembrane' in i.chain]
    plan = [i for i in items if i not in membrane]
    p = a.derived('color', plan, frame)
    anchors = root_anchors(plan, frame, width=1300, name_mode=True)
    sub = substrate(sc, root)
    glass = landmark(plan, 'UiGlass', 'LCDGlass', 'glass', 'стекло', 'LCD')
    button = landmark(plan, 'UiPlungerC', 'UiSwitchC', 'button', 'кнопк')
    fpc = landmark(plan, 'UiFlexFoot', 'UiFlexReturn', 'UiFPC', 'flex', 'FPC', 'шлейф', avoid=('pin', 'площадки'))
    field = landmark(plan, 'UiPerforatedLand', 'perfor', 'перфор', 'metal')
    keys = [glass, button, fpc, field]
    s = Sheet(6, 'Плата панели: дисплей, кнопки и FPC',
              '20260305A. Дисплей показан выключенным. Ширина и длина — в плоскости подложки, толщина — по её нормали.',
              'Электроника')
    convention = ('Условность Г1 и Г2: силиконовая мембрана скрыта' if membrane
                  else 'По нормали к плате, со стороны кнопок')
    s.caption(14, 242, 'Г1', 'Монтажная сторона', convention)
    m = s.geometry(p, (23, 51, 113, 166), cap=3, weight=.085)
    low, high = frame_box([sub], frame)
    width, length, thick = high - low
    lo, bot, hi, _ = m.uvbox((*low[:2], *high[:2]))
    s.dim_h(lo, hi, bot, bot-7.4, est(width, 1))
    points = [(n, m.uv(*anchors[i.name])) for n, i in enumerate(keys, 1) if i.name in anchors]
    numbered_plan(s, points, (17, 140))
    s.bar(18, 34, m.scale, 10)
    s.label(137, 34.5, ratio(m.scale), 8.4, color=MUTE, align='right')
    s.label(17, 24, f'Подложка W × L × t:  {nstr(width)} × {nstr(length)} × {nstr(thick,2)} мм  ·  EST',
            8.7, color=ORANGE, bold=True)
    s.line([(150, 24), (150, 246)], lw=.18)
    s.small(159, 243, 'ДЕТАЛИ ПАКЕТА')
    if membrane:
        switches = [i for i in plan if 'UiTactiles' in i.chain or i.name.startswith(('UiSwitch', 'UiPlunger'))]
        # Frame all three switch bodies AND the flex termination. This is a crop
        # of G1, not a second assembly or inferred circuitry behind the panel.
        box = (159, 151, 103, 71)
        uv = np.asarray(projected_box([*switches, fpc, field], frame)).reshape(2, 2)
        du, dv = uv[1] - uv[0]
        needed = max(du + 2, (dv + 2) * box[2] / box[3])
        detail = _detail(s, p, uv.mean(0), box, needed, 'Г2', 'Ряд кнопок и контакты FPC')
        station_v = frame_box([button], frame)[:, 1].mean()
        _cut_ticks(s, box, detail.uv(0, station_v)[1])
        _key_views(s, a, frame, sub, switches, membrane, station_v)
    else:
        # The older file has no membrane to suppress, section or describe.
        uv = [np.asarray(projected_box([i], frame)).reshape(2, 2).mean(0) for i in (button, field)]
        _detail(s, p, np.mean(uv, axis=0), (159, 142, 96, 74), 15, 'Г2', 'Кнопки и перфорация')
        profile = a.line(plan, np.stack((frame[1], frame[2], frame[0])))
        s.label(159, 122, 'Г3   Боковой профиль', 9.6, bold=True)
        mp = s.geometry(profile, (159, 67, 96, 38), cap=2, weight=.24)
        s.bar(159, 63, mp.scale, 10)
        s.label(159, 46, 'Вправо — от кнопок к стеклу; вверх — от лицевой маски.', 7.9, color=MUTE)

    s.line([(270, 138 if membrane else 26), (270, 246)], lw=.18)
    s.small(279, 242, 'ПОЗИЦИИ НА ПЛАТЕ')
    entries = [('Стекло дисплея', 'Показано стекло, а не граница активных пикселей.\nТип контроллера не установлен.'),
               ('Три тактовые кнопки', 'У каждой — корпус и собственный толкатель.'),
               ('Гибкий шлейф', 'Видны лента и контакты. Распиновка неизвестна.'),
               ('Перфорированный участок', 'Назначение металлической зоны не установлено.')]
    for j, (name, note) in enumerate(entries):
        s.list_entry(279, 228 - (23 if membrane else 37)*j, j+1, name, note)
    if not membrane:
        s.label(279, 56, 'Круглые площадки на кромке показаны по фото;\nих назначение не подтверждено.',
                9.0, color=MUTE, valign='top')
    if any(i.name == 'MechCoverWindow' and 'MechFrontFilm' in i.chain for i in sc.by.get('Fascia', ())):
        s.label(279, 31 if membrane else 38,
                'Съёмная лицевая плёнка кассеты не показана.\nЕё прозрачное окно и стекло LCD — разные детали.',
                8.3, color=MUTE, valign='top')
    source = 'Плата: IMG_8917, IMG_8918.'
    if membrane:
        source += '   Мембрана: владелец; фото HookahX.'
    s.label(159 if membrane else 279, 24, source, 8.3, color=MUTE)
    return s
