"""Photo-based outer face of the heater support, not a circuit reconstruction.

The intact A4.3 handoff does not show this face. The other documented Pro
shows three bands of openings and a blue/silver face. The coordinates below
are visible hole centres in a close-up crop, normalized by the apparent rim.
Do not complete the pattern behind the tabs or infer terminals from it.
"""

import Part

from mech_shapes import AXIS_Y, EXT, V, Z, circle, scaled_part, trim


PHOTO = 'https://hookahx.de/wp-content/uploads/xkah-innenaufbau-heizspiralen-platte-v1.jpg'
ARTICLE = 'https://hookahx.de/en/xkah-pro-innenaufbau-zerlegen/'
# Image 1024 x 1365; crop (184,437)..(901,1092), resized uniformly to height 680.
# Edge estimate in the resulting image: centre (343,284), Rx 247, Ry 243 px.
# The silver centre fixing is NOT represented as a through-hole.
OPENINGS = (
    (257, 255), (301, 195), (374, 191), (428, 241), (421, 314), (355, 354), (281, 326),
    (204, 209), (253, 150), (401, 137), (463, 181), (499, 250), (489, 324),
    (446, 391), (370, 421), (286, 411), (220, 364), (191, 286),
    (120, 236), (150, 168), (199, 115), (262, 78), (406, 77), (476, 102),
    (514, 145), (553, 203), (540, 387), (491, 444), (441, 480), (360, 493),
    (277, 483), (206, 450), (152, 389), (122, 314),
)


def perforated_face(c, parent, guard_z):
    radius = 22.9
    holes = [circle(1.28, 2.5, (x-343)*radius/247, (284-y)*radius/243, -.2)
             for x, y in OPENINGS]
    kd = 'Parameters.HeatFaceD / 45.8 mm'
    thick = 'Parameters.HeatPlateT / 1.5 mm'
    height = guard_z + ' + 1.62 mm'
    substrate = trim(circle(radius, 1.5), holes)
    scaled_part(c, parent, 'HeaterPlate', 'Подложка нагревательного узла · открытая сторона',
                substrate, (0.12, 0.26, 0.48), PHOTO+'; '+ARTICLE, EXT,
                'Синий перфорированный диск виден на разборке другого Pro с основной PCB A4.3. '
                'Показаны различимые отверстия, не повторён узор за клеммами. Диаметр, толщина, '
                'положение по углу и состав не измерены; электрические соединения UNKNOWN.',
                ratios=(kd, kd, thick), origin=(0, AXIS_Y, height))

    # Only the visible contrasting bands. Small gaps deliberately interrupt
    # them: this is not a continuous heater trace, nor a cross-section of one.
    bands = []
    for outer, inner, start, sweep in ((5.2, 3.05, 17, 322), (12.1, 10.6, 12, 328),
                                        (18.95, 17.35, 22, 315)):
        segment = Part.makeCylinder(outer, .025, V(), Z, sweep).cut(circle(inner, .3, z=-.1))
        segment.rotate(V(), Z, start)
        bands.append(trim(segment, holes))
    scaled_part(c, parent, 'HeaterFaceBands', 'Контрастный рисунок открытой стороны · внешний вид',
                Part.makeCompound(bands), (0.37, 0.63, 0.78), PHOTO, EXT,
                'Только видимые дуги контраста. Не электрическая дорожка; высота 0,025 мм '
                'условна для раздельного выбора поверхности в CAD. Без перемычек и контактов.',
                ratios=(kd, kd, 1), origin=(0, AXIS_Y, height+' + Parameters.HeatPlateT'))
