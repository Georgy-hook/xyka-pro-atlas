"""Assembly and electronics plates plus high-resolution, captioned CAD PNGs."""

from pathlib import Path

import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from plates_graphics import Sheet, W, H, MUTE, TEAL, PALE, LINE, STUDIO_BG, ORANGE, INK, nstr
from plates_scene import EXPLODED


GROUP_INFO = (
    ('Housing', 'Корпус', 'Неподвижная база разнесения.'),
    ('MainPCB', 'Основная плата', 'GYS005-S-088-A4.3, сторона пайки\nскрыта в собранном корпусе.'),
    ('DisplayPCB', 'Модуль дисплея', '20260305A, кнопки, стекло и FPC.'),
    ('Heater', 'Нагреватель', 'Скрытая форма концептуальная.'),
    ('Battery', 'Батарейный объём', 'Габарит EST; состав не задан.'),
    ('Harness', 'Жгут', 'Перемещён вместе с основной PCB.'),
    ('Mounts', 'Крепления', 'Опоры и крепёжные детали.'),
)


def cover(a):
    s = Sheet(1, 'XKAH PRO. Сборка и компоновка',
              'Альбом реконструкции по фотографиям владельца  /  электронная нагревательная чаша  /  ревизия основной платы A4.3.',
              'Сборка', foot='Параллельная проекция  ·  Не для производства')
    box = (14, 23, 219, 222)
    s.rect(*box, color=STUDIO_BG)
    s.image(a.raster('assembled'), box)
    s.small(20, 237, '01   /   ЗАКРЫТАЯ СБОРКА')
    s.label(21, 29, 'АКСОНОМЕТРИЯ  ·  СО СТОРОНЫ ПАНЕЛИ', 7.8, color=MUTE)
    s.small(246, 241, 'СОСТАВ АЛЬБОМА')
    rows = [('02', 'Наружные проекции', 'Шесть видов и оценочные габариты'),
            ('03–04', 'Корпус и посадка плат', 'Продольный разрез и узел монтажа'),
            ('05–06', 'Монтажные платы', 'Виды по нормали и увеличенные фрагменты'),
            ('07', 'Крепления', 'Торцы и профили физических деталей'),
            ('08–09', 'Разнесение и электроника', 'Компоновка групп и открытый жгут')]
    for i, (n, title, detail) in enumerate(rows):
        y = 223-24*i
        s.label(246, y, n, 9.3, color=TEAL, mono=True, bold=True)
        s.label(270, y+.5, title, 12.6, bold=True)
        s.label(270, y-7, detail, 8.8, color=MUTE)
        s.line([(246, y-13.2), (405, y-13.2)], lw=.16)
    s.small(246, 91, 'КАК ЧИТАТЬ РАЗМЕРЫ')
    s.label(246, 78.5, 'EST', 10.5, color=ORANGE, bold=True, mono=True)
    s.label(266, 79, 'Оценка формы или положения по фото и референсам.\nНет промеров корпуса и плат штангенциркулем.', 9.2, valign='top')
    s.label(246, 57.5, 'НОМ.', 10.1, color=TEAL, bold=True)
    s.label(266, 58, 'Номинал стандартного корпуса по документации.\nНе определяет точность сборки в целом.', 9.2, valign='top')
    s.label(246, 33, 'Плоскость панели: Y = 0.  +X вправо, +Y внутрь, +Z вверх.', 8.4, color=MUTE)
    return s


def exploded_anchors(a):
    import plates_render as studio
    sc = a.scene
    return studio.root_anchors(sc.items, EXPLODED, offsets=sc.offsets, width=880)


def _badge_points(s, m, anchors):
    # Distribute labels along the two side margins; monotone ordering avoids crossings.
    x0, y0, w, h = m.rect
    uv = {root: m.uv(*point) for root, point in anchors.items()}
    for side in (0, 1):
        selected = sorted((uv[root][1], i+1, root) for i, (root, _, _) in enumerate(GROUP_INFO)
                          if root in uv and (uv[root][0] >= x0+w*.5) == bool(side))
        if not selected:
            continue
        levels = [np.clip(q[0], y0+12, y0+h-12) for q in selected]
        for i in range(1, len(levels)):
            levels[i] = max(levels[i], levels[i-1]+13)
        excess = max(0, levels[-1]-(y0+h-7))
        for (_, number, root), level in zip(selected, levels):
            s.leader(uv[root], ((x0+6, x0+w-6)[side], level-excess), number)


def exploded(a):
    s = Sheet(8, 'Разнесённый вид сборки',
              'Перенос групп без поворота деталей. Жгут остаётся при основной плате; направления разнесения не задают порядок разборки.',
              'Сборка', foot='Разнос условный  ·  Межгрупповые расстояния не размерять')
    box = (14, 24, 263, 218)
    s.rect(*box, color=STUDIO_BG)
    m = s.image(a.raster('exploded'), box)
    _badge_points(s, m, exploded_anchors(a))
    s.label(20, 30, 'АКСОНОМЕТРИЯ  /  СМЕЩЕНИЯ КАК В СЛОЕ EXPLODED', 7.7, color=MUTE, bg=STUDIO_BG)
    s.small(288, 241, 'ФИЗИЧЕСКИЕ ГРУППЫ')
    for j, (_, title, note) in enumerate(GROUP_INFO):
        s.list_entry(288, 226-27.6*j, j+1, title, note)
    s.label(288, 27, 'Невидимые окончания проводов не дорисованы.', 8.2, color=MUTE)
    return s


def electronics(a):
    s = Sheet(9, 'Электроника в сборочных координатах',
              'Корпус, крепёж, аккумуляторный и нагревательный узлы скрыты. Взаимное положение плат и жил не изменено.',
              'Электроника', foot='Геометрическая реконструкция  ·  Не является схемой подключения')
    groups = [('Д1', 'Сторона основной платы', 'Со стороны +Y; видны жгут и компоненты.', 'electronics'),
              ('Д2', 'Сторона дисплея', 'Со стороны −Y; видны экран и кнопки.', 'electronics-front')]
    for j, (tag, title, caption, key) in enumerate(groups):
        x = 14+j*133
        s.caption(x, 241, tag, title)
        box = (x, 44, 126, 182)
        s.rect(*box, color=STUDIO_BG)
        s.image(a.raster(key), box)
        s.label(x, 34, caption, 8.4, color=MUTE)
    s.line([(279, 26), (279, 245)], lw=.18)
    s.small(287, 241, 'ГРУППЫ ВИДИМЫХ ЖИЛ')
    s.label(287, 218, '10', 27, bold=True, color=TEAL)
    s.label(306, 220, 'Припаяны к PCB', 12.0, bold=True)
    s.label(287, 199, 'B+ / B−', 9.1, bold=True)
    s.label(315, 199, 'толстые красная и чёрная', 8.7)
    s.label(287, 187, 'F+ / F−', 9.1, bold=True)
    s.label(315, 187, 'две толстые синие', 8.7)
    s.label(287, 175, 'без метки', 9.1, bold=True)
    s.label(315, 175, 'две тонкие прозрачные', 8.7)
    s.label(287, 163, 'GND / KEY+', 9.1, bold=True)
    s.label(315, 163, 'две тонкие белые', 8.7)
    s.label(287, 151, 'S− / S+', 9.1, bold=True)
    s.label(315, 151, 'тонкие чёрная и красная', 8.7)
    s.line([(287, 138), (404, 138)], lw=.2)
    s.label(287, 122, '4', 27, bold=True, color=TEAL)
    s.label(306, 124, 'Разъём подсветки', 12.0, bold=True)
    s.label(287, 106, 'Буквы на плате: V / R / G / B.\nНе разъём дисплея. По фото нельзя\nустановить напряжение на выводах.', 9.3, valign='top')
    s.small(287, 71, 'ЧТО ОСТАЛОСЬ НЕИЗВЕСТНЫМ')
    s.label(287, 61, 'Принадлежность KEY+ и S± датчикам,\nназначение прозрачной пары и дальние\nконцы жил не подтверждены.', 9.3, valign='top')
    s.label(287, 32, 'Прозрачная изоляция показана светло-серой.', 8.0, color=MUTE)
    return s


def _font(n, bold=False):
    return ImageFont.truetype(font_manager.findfont(font_manager.FontProperties(
        family='DejaVu Sans', weight='bold' if bold else 'normal')), n)


def save_posters(a, dest):
    """Standalone images retain native raster detail, independent of A3 page sampling."""
    render_specs = [('assembled', 'assembly_assembled', 'Сборка в корпусе', '01',
                     'Закрытая сборка  ·  со стороны панели  ·  оценочная реконструкция'),
                    ('exploded', 'assembly_exploded', 'Разнесённая сборка', '02',
                     'Те же детали, что в сборке  ·  разнос условный, не порядок разборки'),
                    ('electronics', 'electronics', 'Электроника и жгут', '03',
                     'Монтажная сторона  ·  корпус скрыт  ·  положение плат и проводов сохранено')]
    for key, fname, title, n, detail in render_specs:
        r = a.raster(key)
        w, h = r.image.size
        z = w/1550
        margin = round(44*z)
        upper, lower = round(150*z), round((115 if key == 'exploded' else 75)*z)
        final = Image.new('RGB', (w, h+upper+lower), STUDIO_BG)
        final.paste(r.image, (0, upper))
        d = ImageDraw.Draw(final)
        d.text((margin, round(30*z)), f'XKAH PRO   /   CAD   /   A4.3', fill=TEAL, font=_font(round(22*z), True))
        d.text((margin, round(72*z)), title, fill=INK, font=_font(round(48*z), True))
        d.text((w-margin, round(90*z)), f'ВИД   {n} / 03', fill=MUTE, anchor='ra', font=_font(round(22*z)))
        d.line((margin, upper-2, w-margin, upper-2), fill='#b4c1bd', width=max(1, round(1.6*z)))
        d.line((margin, h+upper+1, w-margin, h+upper+1), fill='#b4c1bd', width=max(1, round(1.6*z)))
        if key == 'exploded':
            u0, v0, u1, v1 = r.extent
            anchors = exploded_anchors(a)
            rad = round(15*z)
            for i, (root, _, _) in enumerate(GROUP_INFO):
                if root not in anchors:
                    continue
                u, v = anchors[root]
                x, y = round((u-u0)*w/(u1-u0)), round((v1-v)*h/(v1-v0))+upper
                d.ellipse((x-rad, y-rad, x+rad, y+rad), fill='#ffffff', outline=TEAL, width=max(1, round(2*z)))
                d.text((x,y), str(i+1), font=_font(round(17*z), True), fill=TEAL, anchor='mm')
            d.text((margin, h+upper+round(13*z)),
                   '1  Корпус     2  Основная PCB     3  Дисплей     4  Нагреватель¹     5  Батарейный объём¹     6  Жгут     7  Крепления',
                   fill=INK, font=_font(round(19*z), True))
            detail += '  ·  ¹ Концептуальная форма.'
        d.text((margin, h+upper+lower-round(24*z)), detail, fill=MUTE, font=_font(round(21*z)), anchor='ls')
        provenance = PngInfo()
        provenance.add_text('CADSource', a.scene.src.name)
        provenance.add_text('CADSourceSHA256', a.fingerprint)
        final.save(Path(dest)/f'XKAH_PRO_A43_{fname}.png', optimize=True, dpi=(160, 160),
                   pnginfo=provenance)
