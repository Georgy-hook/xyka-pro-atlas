"""Pod-facing guard on the upper half of the *closed* Pro, not the pod lid.

Registration is exclusively to XKAH US, gallery view 3 (English face). Look
up at the closed guard: +X = image right, +Y = image foot/hinge; its outward
normal is -Z. All pixel coordinates use the same (710,423) crop of the 1920²
original. No font, image, network access or Python feature proxy at runtime.

HookahCat and the separate September teardown show a formed shield, warning
rim and three fixings. They are not evidence for the US centre geometry, US
screw construction, wording or the particular owner's revision. In particular
the XYKA view and September unit have different artwork. Section depths and
conversion to mm use the existing estimated heater envelope, not metrology.
"""

import Part

from mech_heat_face import perforated_face
from mech_shapes import (
    AXIS_Y, EST, EXT, MAN, SEAL, STEEL, V, WO1, circle, polygon, ring,
    scaled_part, trim, turned,
)
from retail_pod_guard_art import CAPTION, FIX_CROSS, RIM_LEGEND, WAVES


US = ('XKAH Pro, https://xkah.us/products/xkah-pro , gallery 3: '
      'https://cdn.shopify.com/s/files/1/0663/8865/6306/files/'
      '008-_2_30d05115-452e-451a-a09e-6bc29de4f65a.png?v=1779269809')
CAT = ('HookahCat, https://hookahcat.com.ua/image/catalog/Blog-images/blog/xkln/'
       'xkah-pro-3-gvynty-pid-prokladkoyu.jpg')
SEP = 'https://www.reddit.com/r/hookah/comments/1walb9l/ , September album, photos 6, 12, 16–17'
REGIONAL = 'https://static.tildacdn.com/tild3932-6164-4137-b763-376466326636/7.webp'

GUARD_Z = 'Parameters.BodyH * 0.2903'
D_RATIO = 'Parameters.HeatFaceD / 45.8 mm'
AXIS = (0, AXIS_Y, GUARD_Z)
RATIOS = (D_RATIO, D_RATIO, 1)
# Project the ~247 px outer radius of the bright rim into the existing carrier.
# The ~207 px disk/rim seam thus lands at R21.5, on the original shield bevel.
PX = 25.64 / 247
AXIS_PX = (250, 250)
RIM_FACE_Z = .08
MARK_T = .020  # selection relief towards the pod, not a measured coating
CHARCOAL = (.32, .32, .33)

# Centres measured on the dark cores, rounded to the source pixel. The small
# circular edges measure r≈9.9 px at mid contrast. Not complete polar arrays:
# in particular the three different, cross-in-circle positions are *solid*.
OPENINGS = (
    (192, 92), (307, 92), (142, 121), (358, 121), (220, 137), (280, 137),
    (104, 166), (395, 166), (167, 167), (333, 167), (250, 183),
    (198, 208), (302, 208), (137, 219), (363, 220), (84, 221), (415, 221),
    (185, 265), (315, 265), (84, 279), (415, 279), (137, 280), (363, 280),
    (221, 310), (279, 310), (167, 333), (333, 333), (220, 363), (280, 363),
    (131, 369), (369, 368), (179, 402), (321, 402),
)
BORE_PX = 9.9
FIXINGS = ((250.0, 78.7), (101.8, 335.4), (398.1, 335.4))
CENTER_PX = 23.7  # dark, rimmed US centre; no bore or sensor inferred


def _point(u, v, z=0):
    """One mapping for apertures, outlines, waves, text and fixing marks."""
    return V((u - AXIS_PX[0]) * PX, (v - AXIS_PX[1]) * PX, z)


def _ink(region, z=0, du=0, dv=0):
    """A solid stroke with its printed counters left open, extruded to -Z."""
    wires = []
    for contour in region.split('/'):
        vertices = []
        for pair in contour.split():
            u, v = map(float, pair.split(','))
            vertices.append(_point(u + du, v + dv, z))
        wires.append(polygon(vertices))
    return Part.makeFace(wires, 'Part::FaceMakerBullseye').extrude(V(0, 0, -MARK_T))


def _cutters():
    tools = []
    for u, v in OPENINGS:
        p = _point(u, v)
        tools.append(circle(BORE_PX * PX, 1.6, p.x, p.y, -.12))
    return tools


def _plate_and_rim(c, hot):
    def leaf(name, label, shape, color, sources, notes):
        return scaled_part(c, hot, name, label, shape, color, sources, EXT, notes,
                           ratios=RATIOS, origin=AXIS)

    # Preserve the formed guard envelope. The underside faces the removable
    # pod; the small return points back toward (but does not enter) the plate.
    guard = turned([(0, 0), (21.18, 0), (22.15, .28), (22.48, .76),
                    (22.20, 1.12), (20.85, 1.12), (20.55, .85), (0, .85)])
    bores = _cutters()
    leaf('HeatGuard', 'Щиток · перфорированный диск со стороны чаши',
         trim(guard, bores), STEEL, US + '; ' + CAT + '; ' + SEP,
         '33 малых отверстия по виду US. Центр и три метки крепления не просверлены. '
         'Положение по фото, не заводской шаблон; идентичность экземпляру A4.3 не установлена.')

    # Separate physical annulus, seen loose in September #16. Seat its inner
    # edge against the guard's .28→.76 bevel; the outer return rests against
    # the carrier's service-base rebate (-2 + 2.98 = .98). No floating ring.
    rim = turned([(21.55, RIM_FACE_Z), (25.54, RIM_FACE_Z), (25.64, .18),
                  (25.64, .98), (23.05, .98), (23.05, .82), (22.48, .82),
                  (22.48, .76), (22.15, .28)])
    leaf('HeatGuardRim', 'Щиток · отдельный обод с предупреждением', rim,
         (.76, .77, .77), US + '; ' + SEP,
         'Светлый обод вокруг щитка, не диск нагревателя. Раздельность видна на разборке; '
         'сечение кромки и ступень посадки оценочные.')

    # The three corners of the frame and the wave baseline meet real bores.
    # Trim the print itself too, not only its supporting steel.
    frame = _ink('249.4,167.4 343.2,349.2 155.4,349.2 / 249.4,194.6 176.2,336.5 322.6,336.5')
    waves = _ink(WAVES[0])
    center_mask = circle(CENTER_PX * PX, .16, z=-.1)
    symbol = trim(Part.makeCompound([frame, waves]), [*bores, center_mask])
    leaf('HeatGuardHotSymbol', 'Щиток · треугольник и три тепловые волны',
         symbol, (.45, .44, .45), US,
         'Только контрастная маркировка поверхности. Разрывы на отверстиях сохранены. '
         'Рельеф 0,020 мм условен для CAD, не проводник и не нагретая деталь.')

    caption = trim(Part.makeCompound([_ink(s) for s in CAPTION]), bores)
    leaf('HeatGuardCaption', 'Щиток · Caution Hot !', caption, (.45, .44, .45), US,
         'Обведены только видимые штрихи английской подписи под знаком, кромки букв у отверстий открыты.')
    legend = Part.makeCompound([_ink(s, RIM_FACE_Z) for s in RIM_LEGEND])
    leaf('HeatGuardRimLegend', 'Обод · две надписи и боковые знаки', legend, CHARCOAL,
         US + '; для сравнения: ' + REGIONAL,
         'Только вид US: DO NOT TOUCH WHEN IN USE / REFER TO INSTRUCTION MANUAL. '
         'Две малые треугольные метки по бокам. На региональном виде другие надписи; не совмещены.')

    # Visible ring + cross, not a drilled hole or a reconstructed screw.
    marks = []
    for u, v in FIXINGS:
        p = _point(u, v)
        marks.append(ring(17.7 * PX, 15.7 * PX, MARK_T, p.x, p.y, -MARK_T))
        marks.append(_ink(FIX_CROSS[0], du=u-FIXINGS[0][0], dv=v-FIXINGS[0][1]))
    leaf('HeatGuardFixingMarks', 'Щиток · три видимые метки крепления',
         Part.makeCompound(marks), CHARCOAL, US,
         'Показан вид торцов в галерее US, без отверстий, резьбы и хвостовиков. '
         'На разобранном сравнительном экземпляре видны гладкие торцы.')
    leaf('HeatGuardCenterMark', 'Щиток · тёмный круг в центре вида US',
         circle(CENTER_PX * PX, MARK_T, z=-MARK_T), (.17, .20, .20), US,
         'Круг заметно крупнее перфорации на этом виде. Только видимая поверхность; '
         'назначение и глубина не определены. Сквозное отверстие не предполагается.')


def heater(c):
    """Build only the upper guard, existing face layers, and their carrier."""
    import retail_clips_base

    hot = c.sub(c.groups['heater'], 'MechHeaterAssembly', 'Нижняя сторона верхней части · нагреватель')
    _plate_and_rim(c, hot)
    perforated_face(c, hot, GUARD_Z)

    # Unmodified carrier master. The shared service-base operation provides
    # the rim rebate as well as the service relief, in this axis-local frame.
    holder = turned([(22.60, -.06), (25.90, -.06), (26.3, .64), (26.4, 3.65),
                     (28.55, 4.15), (28.55, 5.4), (25.68, 6.1), (23.9, 13.7),
                     (22.95, 13.7), (22.95, 5.6), (23.02, 4.2), (23.02, 1.35),
                     (22.60, 1.25)])
    holder = retail_clips_base.cut_carrier_for_service_base(holder)
    scaled_part(c, hot, 'HeaterCarrier', 'Посадочная обойма щитка и пластины · EST',
                holder, SEAL, US + '; ' + MAN + ' k; ' + WO1 + ' Figs.11–14', EST,
                'Профиль и посадочные выборки оценочные. Внутренние слои, выводы и контакты не моделировались.',
                ratios=RATIOS, origin=AXIS)
