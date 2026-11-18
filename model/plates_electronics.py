"""Mounting-side PCB plans and enlarged, registered regions of the same vector view."""

import numpy as np

from plates_graphics import Sheet, LINE, MUTE, ORANGE, SCALES, TEAL, est, nstr, ratio
from plates_scene import choose, projected_box, substrate


def landmark(items, *names, avoid=()):
    return choose(items, *names, avoid=avoid)


def numbered_plan(s, mapping, points, margin):
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
    centers = [frame[:2] @ i.center for i in keys]
    s.caption(14, 242, 'В1', 'Компоновка', 'Шелкография и площадки — тела из модели')
    box = (27, 49, 108, 172)
    m = s.geometry(view, box, cap=3, weight=.09)
    bounds = projected_box([sub], frame)
    lo, bot, hi, top = m.uvbox(bounds)
    s.dim_h(lo, hi, bot, bot-7.5, est(bounds[2]-bounds[0], 1))
    numbered_plan(s, m, [(j+1, m.uv(*v)) for j, v in enumerate(centers)], (18, 137))
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


def ui(a):
    sc, root = a.scene, 'DisplayPCB'
    s = Sheet(6, 'Плата панели: дисплей, кнопки и FPC',
              '20260305A. Вид снаружи со стороны экрана; положение стекла и гибкого шлейфа соответствует CAD-сборке.',
              'Электроника')
    items, frame = sc.by[root], sc.board_frame(root)
    p = a.colors(root)
    sub = substrate(sc, root)
    glass = landmark(items, 'UiGlass', 'LCDGlass', 'glass', 'стекло', 'LCD')
    button = landmark(items, 'UiPlungerC', 'UiSwitchC', 'button', 'кнопк')
    fpc = landmark(items, 'UiFPC', 'flex', 'FPC', 'шлейф', avoid=('pin', 'площадки'))
    shield = landmark(items, 'UiPerforated', 'perfor', 'перфор', 'щит', 'screen', 'mesh', 'metal')
    keys = [glass, button, fpc, shield]
    cps = [frame[:2] @ i.center for i in keys]
    s.caption(14, 242, 'Г1', 'Лицевая сторона', 'Нормаль к плоскости PCB  /  −Y')
    m = s.geometry(p, (23, 51, 113, 166), cap=3, weight=.085)
    bounds = projected_box([sub], frame)
    lo, bot, hi, top = m.uvbox(bounds)
    s.dim_h(lo, hi, bot, bot-7.4, est(bounds[2]-bounds[0], 1))
    numbered_plan(s, m, [(j+1, m.uv(*v)) for j, v in enumerate(cps)], (17, 140))
    s.bar(18, 30, m.scale, 10)
    s.label(134, 30.5, ratio(m.scale), 8.4, color=MUTE, align='right')
    s.line([(150, 26), (150, 246)], lw=.18)
    s.small(159, 243, 'ДЕТАЛИ ПАКЕТА')
    # Locate the photographed perforated zone and adjacent button rather than
    # assuming that the unseen portion of the flex is routed in a known way.
    uv = .50*cps[1] + .50*cps[3]
    _detail(s, p, uv, (159, 142, 96, 74), 15, 'Г2', 'Кнопки и перфорация')
    # Look along local +u. Longitudinal +v is horizontal; +w (towards the
    # user) is upwards. This also works on an unplaced display subassembly.
    profile = a.line(items, np.stack((frame[1], frame[2], frame[0])))
    s.label(159, 122, 'Г3   Боковой профиль', 9.6, bold=True)
    mp = s.geometry(profile, (159, 67, 96, 38), cap=2, weight=.24)
    s.bar(159, 63, mp.scale, 10)
    s.label(159, 46, 'Вправо +Z; к пользователю вверх (−Y).', 7.9, color=MUTE)
    s.line([(265, 26), (265, 246)], lw=.18)
    s.small(274, 242, 'ВИДИМЫЕ УЗЛЫ')
    entries = [('Дисплейная панель', 'Стекло закрывает часть PCB.\nТип контроллера дисплея — UNKNOWN.'),
               ('Три тактовые кнопки', 'Отдельные механические корпуса\nи нажимные поверхности.'),
               ('Гибкий шлейф', 'Янтарная лента и открытые контакты.\nРаспиновка не установлена.'),
               ('Перфорированный участок', 'Расположение по макрофотографии.\nНазначение металлической зоны неизвестно.')]
    for j, (name, note) in enumerate(entries):
        s.list_entry(274, 227-38*j, j+1, name, note)
    s.label(274, 56, 'Круглые площадки на кромке показаны по фото;\nконтактное назначение не назначено.', 9.0, color=MUTE, valign='top')
    s.label(274, 40, f'Подложка: {nstr(bounds[2]-bounds[0],1)} × {nstr(bounds[3]-bounds[1],1)} мм  ·  EST',
            9.0, color=ORANGE, bold=True)
    s.label(274, 31, 'Источники: IMG_8917, 8918.', 8.3, color=MUTE)
    return s
