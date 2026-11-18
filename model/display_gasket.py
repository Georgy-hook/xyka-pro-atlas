"""Removable silicone keypad membrane on PCB 20260305A. Local frame: u, v, w.

build(c) adds ONE registered solid to the display group; it does not change the
PCB, the switches or the external keys. w=0 is the front soldermask. The same
cassette transform therefore applies as the housing and PCB parameters change.
No proxy, material library, remote image or font is needed on reopen.
"""

from display_native import P, pad, rounded_loop, sketch


NAME = 'UiKeyMembrane'
IMAGE = 'https://hookahx.de/xkah-pro-innenaufbau-zerlegen/ (Displaymodul, dim_deui.jpg)'
SOURCE = ('Владелец: силиконовая прокладка на кнопках 20260305A; ' + IMAGE +
          '; dim_markings.jpg (нижняя вырезка того же фото); IMG_8917/8918 без прокладки.')
CONFIDENCE = 'Материал и место: подтверждены владельцем. Контур: фото. Размеры и скрытый профиль: ESTIMATE.'
REMOVED_IN = ('IMG_8917.jpg', 'IMG_8918.jpg')
CONTACTS = tuple('UiPlunger' + hand for hand in 'LCR')

# Nominals, mm. Installed reference (1024 × 1365, original orientation): the
# tops of the L, C, R islands are at approx. (797,725), (774,612), (752,505).
# Scale with the two outer switch centres (~18.3 mm apart), NOT body height.
# Image corners of the web are approx. (747,789), (859,773), (796,459),
# (687,471); parallax and perspective do not justify hundredth-mm geometry.
OVERHANG_L = 4.03
OVERHANG_R = 3.82
WEB_WIDTH = 7.55                 # across v, refined on the installed-view projection
WEB_OFFSET_V = -0.16             # derived from both long edges relative to the pad centres
WEB_RADIUS = 0.46
UNDERSIDE = 0.44                  # above terminals/witnesses; not a glued PCB pad
WEB_T = 0.49
FOOT_UV = (4.06, 4.55)           # drafted island at its junction with the web
SEAT_UV = (3.34, 4.16)           # simple clearance for each 3.02 × 3.85 tact body
CROWN_T = 0.65                   # roof over the extended cream plunger
TOP_W_EXPR = f'{P}UiPlungerTop + {CROWN_T:g} mm'
# Inward from the EXTERIOR face plane, along the inclined cassette normal.
OUTER_STEM_END_EXPR = f'{P}UiDepth - {P}UiPlungerTop - {CROWN_T:g} mm'


def _u(c, side):
    name = f'UiSw{side}U'
    return c.p[name] * c.p['UiW'] / 28.2, f'{P}{name} * {P}UiW / 28.2 mm'


def _three_profiles(c, body, name, label, size, radius, w):
    """Independent L/C/R centres: do not assume an equidistant three-key array."""
    sk = sketch(body, name, label)
    width, depth = size
    for side in 'LCR':
        u, ux = _u(c, side)
        bounds = (f'{ux} - {width / 2:g} mm', None, f'{ux} + {width / 2:g} mm', None)
        rounded_loop(sk, u - width / 2, -depth / 2, width, depth, radius, bounds, None)
    c.at(sk, 0, 0, w)
    return sk


def build(c, parent=None):
    """Return the removable PartDesign::Body; no new spreadsheet alias required."""
    parent = c.groups['display'] if parent is None else parent
    body = c.doc.addObject('PartDesign::Body', NAME)
    parent.addObject(body)
    body.Label = '20260305A · съёмная силиконовая прокладка трёх кнопок'
    # Local y=0 is the row of actuators; local z=0 is the lowest face of the web.
    c.at(body, 0, f'{P}UiSwV * {P}UiL / 50.4 mm', UNDERSIDE)
    ul, exl = _u(c, 'L')
    ur, exr = _u(c, 'R')
    x0 = ul - OVERHANG_L
    x1 = ur + OVERHANG_R
    outline = sketch(body, 'UiMembraneOutline', 'След по установленной накладке · наружный контур')
    bounds = (f'{exl} - {OVERHANG_L:g} mm', None, f'{exr} + {OVERHANG_R:g} mm', None)
    rounded_loop(outline, x0, WEB_OFFSET_V - WEB_WIDTH / 2, x1 - x0, WEB_WIDTH, WEB_RADIUS, bounds, None)
    web = pad(body, outline, 'UiMembraneWeb', 'Сплошное силиконовое полотно', WEB_T, None)

    islands = _three_profiles(c, body, 'UiMembranePadsSketch', 'Три основания выступов · оси UiSw',
                              FOOT_UV, 0.37, WEB_T)
    rise = c.p['UiPlungerTop'] + CROWN_T - UNDERSIDE - WEB_T
    pillars = pad(body, islands, 'UiMembranePads', 'Три выступа с небольшим уклоном', rise,
                  f'{TOP_W_EXPR} - {UNDERSIDE + WEB_T:g} mm')
    pillars.TaperAngle = -5.0
    web.Visibility = False
    # Soften only the outer lip of each top face. Preserve three pressure
    # flats for the exterior keys and keep the web-to-pad joint intact.
    c.doc.recompute([web, islands, pillars])
    top = c.p['UiPlungerTop'] + CROWN_T - UNDERSIDE
    edges = [f'Edge{i}' for i, edge in enumerate(pillars.Shape.Edges, 1)
             if abs(edge.BoundBox.ZMin - top) < 1e-5 and abs(edge.BoundBox.ZMax - top) < 1e-5]
    if not edges:
        raise ValueError('UiKeyMembrane: failed to locate the three drafted pad tops')
    rounded = body.newObject('PartDesign::Fillet', 'UiMembranePadLips')
    rounded.Label = 'Мягкая кромка пятачков'
    rounded.Base = (pillars, edges)
    rounded.Radius = 0.20
    pillars.Visibility = False

    # One minimal blind landing per mechanical switch. The pocket roof touches
    # the real plunger face; no conductive pill, carbon pad, secondary sensor,
    # broad contact chamber, pre-load, durometer or adhesive is inferred.
    seats = _three_profiles(c, body, 'UiMembraneSeatsSketch', 'Три посадки с обратной стороны',
                            SEAT_UV, 0.24, 0)
    pockets = body.newObject('PartDesign::Pocket', 'UiMembraneSeats')
    pockets.Label = 'Посадки трёх тактовиков · опора на вершины толкателей'
    pockets.Profile = seats
    pockets.Reversed = True
    pockets.Length = c.p['UiPlungerTop'] - UNDERSIDE
    pockets.setExpression('Length', f'{P}UiPlungerTop - {UNDERSIDE:g} mm')
    rounded.Visibility = False
    seats.Visibility = False
    c.register(body, parent, (0.125, 0.145, 0.15), SOURCE, CONFIDENCE,
               'Одна непрерывная деталь; скрытие открывает кремовые толкатели. '
               'L/C/R — только механические давления, не назначение электрических контактов. '
               'Верх = UiPlungerTop + 0.65 мм; степень обжатия и точный профиль изнанки UNKNOWN.')
    for key, value in (
        ('MaterialEvidence', 'Силикон — по уточнению владельца; цвет не является идентификацией.'),
        ('InstalledReference', IMAGE + '; три черных выступа на общей ленте. Это не наружные светлые клавиши.'),
        ('RemovedReference', 'IMG_8917.jpg: три открытых толкателя и снятая чёрная лента на столе внизу. '
                             'IMG_8918.jpg: все три кремовых толкателя также открыты.'),
        ('PlungerContacts', ', '.join(CONTACTS) + '; три отдельных площадки с внутренней стороны, в покое.'),
        ('EstimateBounds', 'Контур ±0.9 мм; размеры пятачков ±0.6 мм; толщина над толкателем ±0.30 мм. '
                           'Оценки по фото, не измерение, не допуски.'),
    ):
        body.addProperty('App::PropertyString', key, 'Evidence')
        setattr(body, key, value)
    c.doc.recompute()
    return body
