"""XYKA PRO removable cartridge and fixed guide, reconstructed from retail views.

The photo master is Ø45.4 × 80 mm, not metrology. +Y is the keyed (USB)
side, -Y is the Russian label. Z=0 is the installed pack's lower end, not
the body datum. OD and length are independent native spreadsheet aliases.
The replacement pack, its crown surround and the heater are different parts.
"""

import FreeCAD  # Initialise the same OCCT runtime as the assembly before importing Part.
import Part

from context import text_property
from mech_shapes import (
    AXIS_Y, DY, EST, EXT, INK, MAN, MOLD, WX, V, Z, circle, cut_native,
    moved, rotated, rounded_rect, scaled, scaled_part, trim, turned,
)


SKU = 'https://xyka.pro/akkumulyator-xyka (SKU 700.954.29)'
FRONT = 'https://static.tildacdn.com/tild6231-3365-4234-a132-663431343461/1.webp'
REAR = 'https://static.tildacdn.com/tild3137-6631-4561-b431-366639646338/2.webp'
TOP = 'https://static.tildacdn.com/tild3237-6135-4633-b038-663765393039/3.webp'
RAISED = 'https://static.tildacdn.com/tild3238-3832-4039-b332-656661353561/6.webp'
WELL = 'https://i.redd.it/l3b6qbuzpmwh1.jpeg (u/Hot_Regret6391, album 1xat220, image 3)'
BOTTOM = ('https://kinescope.io/embed/mXNxchmGsU4nGGJsp5txz9, XYKA «Комплектация и распаковка», '
          '48.16–48.44 s (25 fps, исходный 3840×2160); https://xyka.pro/manual#unpack')

RADIAL = 'Parameters.BatteryOD / 45.4 mm'
AXIAL = 'Parameters.BatteryL / 80 mm'
Z0 = 'Parameters.BodyH - Parameters.BatteryL'
ORIGIN = (0, AXIS_Y, Z0)
RATIOS = (RADIAL, RADIAL, AXIAL)
RADIUS = 22.70
BACK_FLAT = 21.58
# The front of the device (bridge) points roughly left in the well image.
# The wider of the two spans consequently runs fore/aft in device coordinates.
# The ring centres, not pin assignments. Scale is conditional on BatteryOD.
# Ø reference: extended round outer arc on the *bottom*, not the top mouth
# or foreshortened deep well. 4K f1210: (1507,1116), (1583,1269),
# (1497,1220), (1591,1169). Deprojected diagonals ≈0.282D × 0.158D.
SEAT_XY = ((-3.59, 0.0), (3.59, 0.0), (0.0, -6.40), (0.0, 6.40))


BODY_COLOR = (.094, .097, .102)
CAP_COLOR = (.139, .143, .149)
SOCKET_COLOR = (.77, .70, .44)


def _pack_leaf(c, pack, name, label, shape, color, evidence, note):
    return scaled_part(c, pack, name, label, shape, color, evidence, EXT, note,
                       ratios=RATIOS, origin=ORIGIN)


def _clip_back(shape, y=BACK_FLAT):
    """Positive-Y chord, rather than a perfectly round generic can."""
    return shape.cut(Part.makeBox(80, 40, 100, V(-40, y, -10))).removeSplitter()


def _rear_slot(width, height, corner, z, start, depth):
    face = Part.Face(rounded_rect(width, height, corner))
    return moved(face.extrude(V(0, depth, 0)), 0, start, z)


def _slot_punch(z=79.07, thickness=1.2):
    # Closed racetrack, analytic semicircular ends. One blind recess per ray.
    ro, ri, w = 17.49, 13.10, .74
    a, b = ri + w / 2, ro - w / 2
    p, q = V(-w/2, a, z), V(-w/2, b, z)
    r, s = V(w/2, b, z), V(w/2, a, z)
    rim = Part.Wire([Part.makeLine(p, q), Part.Arc(q, V(0, ro, z), r).toShape(),
                     Part.makeLine(r, s), Part.Arc(s, V(0, ri, z), p).toShape()])
    return Part.Face(rim).extrude(V(0, 0, thickness))


def _cap():
    # Shallow concave waist below the uninterrupted narrow outer lip.
    a, b = V(0, 0, 72.24), V(RADIUS, 0, 72.24)
    top = V(22.69, 0, 78.83)
    vtx = [top, V(22.72, 0, 79.55), V(22.59, 0, 79.86), V(22.40, 0, 80),
           V(0, 0, 80), a]
    edges = [Part.makeLine(a, b), Part.Arc(b, V(22.02, 0, 75.73), top).toShape()]
    edges.extend(Part.makeLine(p, q) for p, q in zip(vtx, vtx[1:]))
    cap = _clip_back(Part.Face(Part.Wire(edges)).revolve(V(), Z, 360))
    pocket = _slot_punch()
    cuts = [rotated(pocket, V(), i * 18) for i in range(20)]
    # Image 3: dimple Ø≈0.113D. Spherical, not an open centre bore or USB.
    cuts.append(Part.makeSphere(3.45, V(0, 0, 82.31)))
    return trim(cap, cuts)


def _face_sector(inner, outer, angle, thickness, z):
    sector = Part.makeCylinder(outer, thickness, V(0, 0, z), Z, angle)
    sector = sector.cut(circle(inner, thickness + .2, z=z - .1))
    return rotated(sector, V(), -90 - angle / 2)


def _face_window(width, length, z, thickness, angle):
    # Small radial capsule in XY, not a vent through the cartridge.
    slot = Part.Face(rounded_rect(width, length, width * .42)).extrude(V(0, thickness, 0))
    slot.rotate(V(), V(1, 0, 0), 90)
    return rotated(moved(slot, 0, -16.97, z), V(), angle)


def _bottom(c, pack, body):
    """Observed service face WITHOUT the silicone shipping plug in the video."""
    # The distinct moulded rim is lower than the inner face. Only the relief,
    # not the wall thickness, follows the video. It is not an extra loose lid.
    medallion = _clip_back(circle(20.03, 1.25, z=-.50), 18.23)
    body = body.cut(medallion)
    plate = _clip_back(circle(19.98, .33, z=.42), 18.18)
    pocket = _face_sector(14.80, 20.03, 45, .60, .30)
    body = body.cut(pocket).removeSplitter()
    _pack_leaf(c, pack, 'PackEndPlate', 'Торцевая плашка · вырез под четыре окна',
               plate.cut(pocket), (.094, .112, .121), BOTTOM,
               'Видна тёмная внутренняя плашка (~0.88D) и краевой шов. Плоская сторона '
               'на Y≈+0.40D, окна напротив. Способ крепления и толщина неизвестны.')
    plaque = _face_sector(14.88, 19.98, 44.7, .43, .47)
    angles = (-15.5, -5.15, 5.15, 15.5)
    windows = [_face_window(1.25, 2.08, .38, .60, angle) for angle in angles]
    _pack_leaf(c, pack, 'PackEndArc', 'Нижний торец батареи · дуга с четырьмя окнами',
               trim(plaque, windows), (.160, .169, .177), BOTTOM,
               'Дугообразная зона напротив задней лыски. Четыре малых тёмных прямоугольника '
               'различимы на кадре. Изображение не доказывает устройство под ними.')
    masks = [_face_window(1.17, 1.98, .54, .36, angle) for angle in angles]
    _pack_leaf(c, pack, 'PackEndWindows', 'Нижний торец батареи · четыре тёмные вставки',
               Part.makeCompound(masks), (.210, .236, .256), BOTTOM,
               'Показаны в неактивном состоянии; это не четыре контакта. Материал и '
               'функция непосредственно не определены.')
    contacts = []
    dark_floors = []
    pale_floors = []
    for x, y in SEAT_XY:
        # Two brighter centres in the fore/aft pair, two darker wells across.
        # An optical distinction, not a claim concerning terminal material or gender.
        r = 1.53
        core = .18 if y else .31
        eye = turned([(0, .42), (r - .11, .42), (r, .31), (r, .06), (r - .06, 0),
                      (1.13, 0), (.89, core * .67), (.55, core), (0, core)])
        contacts.append(moved(eye, x, y, 0))
        # Two photographs of the same 4K sequence distinguish those finish
        # pairs even when the hand turns. Colour the recessed faces, never
        # the common mating plane; a finish is not an invented spring/pin.
        edge_z = core * .67 * (1.13 - 1.08) / (1.13 - .89)
        skin = turned([(0, core), (.55, core), (.89, core * .67), (1.08, edge_z),
                       (1.08, edge_z - .015), (.89, core * .67 - .015),
                       (.55, core - .015), (0, core - .015)])
        (pale_floors if y else dark_floors).append(moved(skin, x, y, 0))
    for suffix, title, pieces, color in [
        ('Pale', 'Два светлых центра вдоль Y', pale_floors, (.68, .57, .48)),
        ('Dark', 'Два тёмных центра вдоль X', dark_floors, (.31, .205, .118)),
    ]:
        _pack_leaf(c, pack, 'PackContact' + suffix + 'Faces', title + ' · видимое покрытие',
                   Part.makeCompound(pieces), color, BOTTOM,
                   'Контраст центров контактов на фото; визуальная поверхность, а не отдельные '
                   'электроды сверх четырёх основных. Состав покрытия и функция пары неизвестны.')
    ends = _pack_leaf(c, pack, 'PackEndContacts', 'Съёмная батарея · четыре торцевых контакта',
                      Part.makeCompound(contacts), (.76, .55, .34), BOTTOM + '; ' + WELL,
                      'Четыре золотистых круга с бортиками расположены ромбом, два центра светлее. '
                      'Им соответствует отдельный ромб в колодце корпуса. Наружный вид; форма центра, '
                      'глубина, сила поджима и принадлежность электрическим цепям не определены.')
    text_property(ends, 'PhotoWitness', 'XYKA 4K unboxing: f1210, 48.40 s. Symmetrised pattern, no pin 1. '
                  'Only the visible faces are modelled. Shipping cap omitted in installed state.')
    return body


def _pack(c, pack):
    # One sealed external envelope, NOT the material volume of cells / case.
    body = _clip_back(turned([(0, 0), (22.38, 0), (22.58, .15), (22.70, .47),
                              (22.70, 72.24), (0, 72.24)]))
    # Rounded USB mouth and separate rectangular recess both lie on the flat.
    # Neither a board nor any unseen connector contacts are represented here.
    usb_z = 6.42
    mouth = _rear_slot(9.20, 3.57, 1.52, usb_z, BACK_FLAT - 2.32, 4.20)
    notch = _rear_slot(11.80, 3.39, .19, 16.23, BACK_FLAT - 1.10, 2.50)
    body = trim(body, [notch, mouth])
    body = _bottom(c, pack, body)
    shell = _pack_leaf(c, pack, 'BatteryEnvelope', 'Съёмная батарея XYKA PRO · корпус с задней лыской',
                       body, BODY_COLOR, SKU + '; ' + FRONT + '; ' + REAR + '; ' + MAN + ' p.05 a',
                       'Корпус единого блока, не отдельная ячейка. Наружная форма и расположение '
                       'двух проёмов — по RU карточке; скрытые слои, состав и защёлка не восстановлены.')
    _pack_leaf(c, pack, 'PackCap', 'Верх батареи · лыска, 20 щелей и центральная лунка', _cap(), CAP_COLOR,
               TOP + '; ' + RAISED, 'Видна сплошная головка с 20 радиальными метками через 18°. '
               'Лунка и метки глухие в модели: глубина и назначение не измерены.')
    # In a direct plan view an unlit recess would otherwise tessellate as a
    # coplanar-looking disk of the same colour as the lid. These thin, fully
    # backed surfaces represent its visible dark floors, not separate ports.
    floor = _slot_punch(79.07, .036)
    wells = Part.makeCompound([rotated(floor, V(), i * 18) for i in range(20)])
    _pack_leaf(c, pack, 'PackSlotWells', 'Затемнённые донья двадцати щелей · внешний вид',
               wells, (.026, .027, .030), TOP + '; ' + RAISED,
               'Тонкие слои передают тёмный вид углублений и в прямой проекции. Это не '
               'дополнительные узлы и не предположение о сквозной вентиляции.')
    dark_notch = _rear_slot(11.76, 3.35, .18, 16.23, BACK_FLAT - 1.10, .036)
    _pack_leaf(c, pack, 'PackRearRecess', 'Задняя выемка над USB-C · тёмное основание',
               dark_notch, (.028, .029, .031), REAR,
               'Видимое дно прямоугольной выемки; роль внутреннего зацепа не установлена.')
    # Shallow dark reveal, rolled metal-looking border, backed-off central tongue.
    rim = _rear_slot(9.14, 3.52, 1.50, usb_z, BACK_FLAT - 2.32, 2.22)
    core = _rear_slot(8.35, 2.68, 1.13, usb_z, BACK_FLAT - 2.45, 3.20)
    _pack_leaf(c, pack, 'PackUsbRim', 'USB-C · кромка утопленного разъёма', rim.cut(core),
               (.147, .151, .157), SKU + '; ' + REAR, 'Видимый ободок бокового разъёма, не электрическая модель. '
               'Материал и внутренние размеры не подтверждены.')
    tongue = _rear_slot(6.55, .55, .18, usb_z, BACK_FLAT - 2.32, 1.72)
    _pack_leaf(c, pack, 'PackUsbTongue', 'USB-C · видимая центральная пластина', tongue,
               (.118, .122, .125), REAR, 'Лишь видимая пластина в глубине разъёма; никаких распиновок и проводки.')
    return shell


def _fixed_mouth(c, seat):
    # OD follows the HOUSING labyrinth; the keyed bore follows the PACK OD.
    # As a result editing the battery diameter doesn't resize the body hole.
    z = 'Parameters.BodyH - 3.85 mm'
    blank = scaled(c, seat, 'PackMouthOutside', 'Внешняя кромка горловины',
                   # The shadow return is narrower (r24.18) below z150.50
                   # than at its visible throat (r24.65 at z150.92). Follow
                   # that ramp, without widening the crown or losing the
                   # 0.42 mm radial optical underlap in a straight top view.
                   turned([(0, 0), (24.0, 0), (24.04, .35), (24.49, .77),
                           (24.60, 1.28), (24.60, 3.19), (24.48, 3.33), (0, 3.33)]),
                   ratios=(WX, DY, 1), origin=(0, AXIS_Y, z))
    bore = _clip_back(circle(RADIUS + .50, 4.5, z=-.3), BACK_FLAT + .50)
    tool = scaled(c, seat, 'PackMouthBore', 'Д-образный инструмент · по съёмному блоку', bore,
                  ratios=(RADIAL, RADIAL, 1), origin=(0, AXIS_Y, z))
    rim = cut_native(c, seat, 'PackWellMouth', 'Неподвижная шейка · ориентированная горловина', blank, tool)
    c.register(rim, seat, INK, RAISED + '; ' + WELL + '; ' + REAR, EST,
               'Отдельно от головки батареи. Лыска ориентирована к тылу, как и USB. Наружный радиус '
               '24.60 при номинале. Посадка — оценка, не заводской зазор.')


def _fixed_seat(c, host):
    from mech_modules import native_lathe  # common sketch constructor, not the old battery implementation

    seat = c.sub(host, 'MechPackSeatAssembly', 'Неподвижная посадка батареи · принадлежит верхнему корпусу')

    def radius(delta):
        return c.p['BatteryOD'] / 2 + delta, f'Parameters.BatteryOD / 2 + ({delta:g} mm)'

    height = c.p['BatteryL'] - .6, 'Parameters.BatteryL - 0.6 mm'
    guide = native_lathe(c, seat, 'PackWell', 'Гильза корпуса · гнездо для съёмной батареи',
                         [(0., 0.), (radius(.5), 0.), (radius(1.30), 1.10), (radius(1.30), height),
                          (radius(.55), height), (radius(.55), 2.05), (0., 2.05)], Z0 + ' - 3.25 mm')
    c.register(guide, seat, MOLD, RAISED + '; ' + WELL + '; ' + MAN + ' pp.04–05', EST,
               'Ось вертикальна. Сохранён исходный радиальный номинальный зазор 0.55 мм к телу '
               'без печати, прежние наружная стенка и дно. Не часть съёмного блока.')
    _fixed_mouth(c, seat)
    # Distinct dark circular boss at the BOTTOM of the well: not the white
    # hand-drawn annotation around the four metallic eyes in the source.
    carrier = turned([(0, -1.20), (21.75, -1.20), (21.75, -.89), (21.55, -.75),
                      (12.10, -.75), (12.10, -.41), (11.90, -.22), (0, -.22)])
    seats = [circle(1.60, 1.50, x, y, -.91) for x, y in SEAT_XY]
    fixed = dict(ratios=(RADIAL, RADIAL, 1), origin=ORIGIN)
    scaled_part(c, seat, 'PackSeatCarrier', 'Держатель четырёх контактов · дно гнезда',
                trim(carrier, seats), (.122, .124, .129), WELL, EXT,
                'Тёмная площадка в центре дна гнезда; видна на другом Pro. Диаметры, ступени и '
                'установочные высоты оценочные. Белая обводка на фото — аннотация автора.', **fixed)
    # Gold-coloured annular faces have a dark centre; contact internals and
    # material are unknown. Do not interpret a highlight as a spring or net.
    eye = turned([(.51, -.88), (1.51, -.88), (1.58, -.73), (1.58, -.11),
                  (1.49, 0), (.73, 0), (.51, -.16)])
    sockets = Part.makeCompound([moved(eye, x, y, 0) for x, y in SEAT_XY])
    out = scaled_part(c, seat, 'PackSeatSockets', 'Четыре золотистых гнездовых контакта · неподвижные',
                      sockets, SOCKET_COLOR, WELL, EXT,
                      'Четыре отдельных круглых золотистых торца с тёмными центрами. Длинная ось '
                      'ромба направлена примерно от панели к тылу; координаты/Ø/глубина оценочные. '
                      'Не назначены ни полярность, ни материал покрытия, ни тип внутренней пружины.', **fixed)
    text_property(out, 'RegistrationPixels', 'Oct03 1400×1867 px: centres ~ (708,1080), (816,1077), '
                  '(761,1049), (762,1109); non-orthographic. No direct metric calibration.')


def battery(c, host):
    """Register removable parts under Battery; guide and eyelets stay with host."""
    from retail_battery_endprint import add_end_print
    from retail_battery_print import add_print

    pack = c.sub(c.groups['battery'], 'MechPackAssembly', 'XYKA PRO · съёмная батарея с русской этикеткой')
    shell = _pack(c, pack)
    add_print(c, pack, RATIOS, ORIGIN)
    add_end_print(c, pack, RATIOS, ORIGIN)
    _fixed_seat(c, host)
    text_property(shell, 'InterfaceLimit', 'Четыре лицевых торца на батарее и четыре в гнезде подтверждены раздельными '
                  'изображениями. В CAD встречаются при z=BodyH−BatteryL. Физический ход, усилие, '
                  'глубина смыкания, номера и функции контактов НЕ установлены.')
