"""Removable U facing, optical zone and retained keys in cassette coordinates.

X right, n=Y inward, Z towards the header BEFORE the assembly's -7.5° rake.
XKAH US front 1 (1000²): inside trim y142..541, window y219..386, row y460;
XYKA silver 01 (1500²): y126..827, y256..549, row y683. Gallery 2 and 5
show flush optics and slightly proud keys. These are projected proportions,
not calibrated A4.3 dimensions or an active display specification.
"""

import Part

from display_interface import RETAIL_FRONT
from mech_keyfaces import cushion, panel_key, side_wedge
from mech_profiles import COVER_END, COVER_TIP
from mech_shapes import (
    EXT, HZ, V, WX, at_ratio, cut_native, moved, rounded_rect,
    scaled, scaled_part, u_wire,
)
from retail_clips import cut_rim_seats


OPEN_CASE = ('Owner A4.3/20260305A; https://www.reddit.com/r/hookah/comments/1walb9l/ '
             '(steps 1/4; images 1, 7, 8); detached trim: '
             'https://www.reddit.com/r/hookah/comments/1xat220/ (image 8)')
FACING = (.124, .123, .126)
SUPPORT = (.065, .068, .072)
FILM_FRONT, FILM_BACK = .07, .25
CARRIER_FRONT, KEY_LAND, CARRIER_BACK = .27, .43, .83
KEY_FRONT, KEY_BACK, KEY_Z = -.52, .30, 84.15
# Max cap width, height, and horizontal centre. Tactile axes are independent.
CAPS = {'L': (7.92, 9.48, -10.47), 'C': (10.88, 14.55, 0.), 'R': (7.92, 9.48, 10.47)}


def _window_datum():
    z = (at_ratio('BodyH', COVER_END, 154) + ' - Parameters.UiWindowDrop '
         '- Parameters.UiWindowL / 2')
    return (0, 0, z), ('Parameters.UiWindowW / 28 mm', 1, 'Parameters.UiWindowL / 33.8 mm')


def _window(c, owner, carrier):
    loc, ratios = _window_datum()
    # The film defines the sole visible contour. Relieve the rigid carrier
    # behind it, not the film itself. No opaque shelf at the old cell end;
    # the key lands and all five fastener seats remain at their former depths.
    # Leave a side stop: the nominal glass outline exceeds the film opening by
    # only 0.45 mm at the left tangent. With a 0.47 mm rear air gap, excessive
    # lateral relief would expose the PCB alongside the glass at three-quarter.
    width, height, radius = (28.10, 35.0, 7.10) if carrier else (28., 33.8, 7.05)
    outline = rounded_rect(width, height, radius, -1)
    return scaled(c, owner, 'CarrierSightTool' if carrier else 'LensAperture',
                  'Инструмент · оптическая зона', Part.Face(outline).extrude(V(0, 3, 0)), ratios, loc)


def _key_position(ident):
    return (at_ratio('BodyW', CAPS[ident][2], 78), 0, at_ratio('BodyH', KEY_Z, 154))


def _tail_position(ident):
    return (f'Parameters.UiSw{ident}U * Parameters.UiW / 28.2 mm',
            'Parameters.UiBase + Parameters.UiSwV * Parameters.UiL / 50.4 mm')


def _key_outline(ident, factor, n):
    width, height, _ = CAPS[ident]
    if ident == 'C':
        wire = cushion(width * factor, height * factor)
    else:
        wire = side_wedge(-1 if ident == 'L' else 1, width * factor, height * factor)
    return moved(wire, 0, n, 0)


def _punch(c, owner, blank, carrier=False):
    prefix = 'Carrier' if carrier else 'Panel'
    base = cut_native(c, owner, prefix+'WindowCut', 'Выборка окна', blank, _window(c, owner, carrier))
    for ident in CAPS:
        wire = _key_outline(ident, 1.015, -1.)
        height = 1. + KEY_LAND if carrier else 3.
        # Film through; in the rigid part the matching well STOPS above the
        # underside, leaving an opaque land under the entire running slit.
        tool = scaled(c, owner, prefix+'Opening'+ident, 'Инструмент · проём '+ident,
                      Part.Face(wire).extrude(V(0, height, 0)), (1, 1, 1), _key_position(ident))
        if carrier:
            base = cut_native(c, owner, 'KeyRebate'+ident, 'Посадочный уступ '+ident, base, tool)
            x, z = _tail_position(ident)
            throat = Part.makeBox(1.96, 2.4, 2.22, V(-.98, -.3, -1.11))
            tool = scaled(c, owner, 'KeyFootTool'+ident, 'Инструмент · проход пяты '+ident,
                          throat, (1, 1, 1), (x, 0, z))
        last = ident == 'R'
        name = ('KeyCarrier' if carrier else 'ServiceCover') if last else prefix+'Cut'+ident
        label = 'Жёсткая подложка · гнёзда и вырезы' if carrier else 'Лицевая плёнка · тёмная U-маска'
        base = cut_native(c, owner, name, label if last else 'Кассета · проём '+ident, base, tool)
    return base


def _install_key(c, owner, ident):
    levels = [(.917, 0), (1., .375), (1., .76), (.985, KEY_BACK - KEY_FRONT)]
    cap = Part.makeLoft([_key_outline(ident, k, n) for k, n in levels], True, True)
    x, _, z = _key_position(ident)
    panel_key(c, owner, ident, cap, ratios=(1, 1, 1), origin=(x, KEY_FRONT, z))
    # The effective tail end, NOT the entire broad cap back, bears on the
    # unloaded silicone pad. Centre it on the original 20260305A tactile axis.
    x, z = _tail_position(ident)
    depth = (f'(Parameters.UiDepth - Parameters.UiPlungerTop - Parameters.UiMembraneOver '
             f'- {KEY_BACK:g} mm) / 1 mm')
    tail = Part.makeBox(1.62, 1., 1.86, V(-.81, 0, -.93))
    scaled_part(c, owner, 'OuterKey'+ident+'Foot', 'Пята наружной клавиши '+ident,
                tail, SUPPORT, OPEN_CASE+'; IMG_8917/8918', EXT,
                'Пята на оси UiSw; задняя поверхность касается верхнего пятачка силикона без '
                'сжатия. Скрытая форма условна. Не кремовый толкатель и не вторая прокладка.',
                ratios=(1, depth, 1), origin=(x, KEY_BACK, z))


def build_front(c, owner):
    film = c.sub(owner, 'MechFrontFilm', 'Съёмная U-накладка · маска и оптическое окно')
    skin = Part.Face(u_wire(FILM_FRONT, 40.14, COVER_TIP, COVER_END)).extrude(V(0, FILM_BACK-FILM_FRONT, 0))
    blank = scaled(c, film, 'PanelBlank', 'Тёмная область накладки до вырезов', skin, (WX, 1, HZ))
    mask = _punch(c, film, blank)
    c.register(mask, film, FACING, OPEN_CASE+'; '+RETAIL_FRONT, EXT,
               'Одна съёмная облицовка. Три отверстия под клавиши; светопропускающее окно — '
               'смежная часть этой же плёнки, не ещё одна наклейка. Снимать группу MechFrontFilm '
               'наружу по локальной −Y. Толщина 0,18 мм оценочна.')
    # Same boundary as the cut: no doubled sheet, open slit, or overlapping
    # display polygons. The bare PCB's UiGlass and its folded tail stay put.
    pane_shape = Part.Face(rounded_rect(28., 33.8, 7.05, FILM_FRONT)).extrude(V(0, FILM_BACK-FILM_FRONT, 0))
    loc, ratios = _window_datum()
    pane = scaled_part(c, film, 'CoverWindow', 'Лицевая плёнка · тонированное окно',
                       pane_shape, (.047, .050, .056), OPEN_CASE+'; '+RETAIL_FRONT, EXT,
                       'Окно заподлицо с маской. Степень прозрачности условна; химсостав не '
                       'установлен. Контур окна НЕ контур активных пикселей.', ratios=ratios, origin=loc)
    pane.addProperty('App::PropertyPercent', 'OpticalTransparency', 'Presentation')
    pane.OpticalTransparency = 76
    if pane.ViewObject:
        pane.ViewObject.Transparency = 76
        pane.ViewObject.DisplayMode = 'Shaded'

    slab = Part.Face(u_wire(CARRIER_FRONT, 40., COVER_TIP+.12, COVER_END-.12)).extrude(V(0, CARRIER_BACK-CARRIER_FRONT, 0))
    stock = scaled(c, owner, 'KeyCarrierBlank', 'Каркас · ступенчатые выборки к креплениям',
                   cut_rim_seats(slab, add_pads=True), (WX, 1, HZ))
    support = _punch(c, owner, stock, carrier=True)
    c.register(support, owner, SUPPORT, OPEN_CASE, EXT, 'Отдельная жёсткая подложка под плёнкой: '
               'ступенчатые углубления под крепёж. За клавишами — непрозрачные '
               'буртики, открытые только для пяты. Оптический проём носителя раскрыт под плёнкой '
               'на 0,60 мм сверху/снизу и 0,05 мм по бокам (оценка). Боковые стенки отсекают '
               'косой луч мимо стекла; верхнего уступа в поле нет. Силикон UiKeyMembrane на плате.')
    for ident in CAPS:
        _install_key(c, owner, ident)
