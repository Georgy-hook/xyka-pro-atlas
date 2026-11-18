"""Outer moulds. The gently sloping part line is not a horizontal cylinder cut.

Digitising datum: manufacturer manual p.04 at 818 px raster: front envelope
(103,154)..(236,413), top plan centre (173,547), projected tip/rear y469/637.
Front seam reaches raster y354 on centre and y337 at either side; the raised
U-panel ends at y307, its faired shoulders near y337. IMG_AD206911 determines
the service pocket, not a guessed horizontal PCB shelf across the body.
"""

import math

import FreeCAD as App
import Part

from mech_keyfaces import panel_key
from mech_shapes import (
    ALLOY, BACK_PHOTO, CASE, CY, DY, EST, EXT, HZ, INK, MAN, MOLD, OBS, OPEN_PHOTO,
    PALE, PHOTO, RETAIL, SEAL, STEEL, US_FAMILY, V, WO1, WX, Y, Z, bezier, body_pos,
    circle, cut_native, hidden, moved, polygon, ring, rotated, rounded_rect, scaled,
    scaled_part, side_key, trim, turned, u_wire, z_box,
)


def seam_mask(dz=0):
    """Solid below the wave mould line. The rear edge is substantially level."""
    def p(y, z):
        return V(-75, y, z + dz)
    # Stations sample the cubic profile to <0.12 mm. Planar tooling faces are
    # deliberate: OCCT's general anisotropic transform otherwise reverses two
    # trimming p-curves on a single long extruded Bezier face after reopening.
    stations = []
    for i in range(9):
        t = i / 8
        u = 1 - t
        y = 36*u**3 + 3*21*u*u*t + 3*11.5*u*t*t + t**3
        z = 45.45*(u**3 + 3*u*u*t) + 34.65*(3*u*t*t + t**3)
        stations.append(p(y, z))
    loop = [p(-30, -5), p(128, -5), p(128, 45.45), *stations, p(-30, 34.65)]
    return Part.Face(polygon(loop)).extrude(V(150, 0, 0))


def barrel_solid():
    return turned([(0, 7.8), (38.75, 7.8), (39, 8.3), (38.96, 9.4),
                   (31.97, 145.55), (31.70, 146.60), (0, 146.60)], CY)


def transverse_cutter(x, y, z, radius, depth=25):
    return circle(radius, depth, x, y, z, Y)


def shell_geometry():
    barrel = barrel_solid()
    # A front extrusion alone would yield slab-sided corners. The outer shoulder
    # widens and runs into the turned body while the U-tip sweeps down and back.
    outer_sections = [(0, 42.6, 61.65), (4.0, 44.15, 59.7),
                      (13.4, 48.7, 53.0), (23.0, 54.6, 47.1), (33, 55.3, 44.8)]
    nose = Part.makeLoft([u_wire(y, w, z, 146.60) for y, w, z in outer_sections], True, False)
    outer = barrel.fuse(nose).removeSplitter()
    inner_barrel = turned([(0, 7), (37.15, 7), (29.85, 148.2), (0, 148.2)], CY)
    inner_sections = [(-2, 40.6, 62.9), (1.0, 40.6, 62.9),
                      (9, 42.0, 59.55), (18, 45.1, 54.6), (32.4, 49.0, 49.1)]
    pocket = Part.makeLoft([u_wire(y, w, z, 148.3) for y, w, z in inner_sections], True, False)
    shell = outer.cut(inner_barrel.fuse(pocket)).removeSplitter()
    lower = shell.common(seam_mask(-.28))
    upper = shell.cut(seam_mask(.28))

    # Curved mating lands leave a large clear well for pod and heater. These are
    # estimated land sections and not implied hidden air guides or conductors.
    lower_land = barrel.common(seam_mask(-.28)).cut(seam_mask(-2.25))
    lower_land = lower_land.cut(circle(26.62, 64, 0, CY, 0))
    upper_land = barrel.common(seam_mask(2.25)).cut(seam_mask(.28))
    upper_land = upper_land.cut(circle(27.15, 64, 0, CY, 0))
    # A set-back step, not a fictitious rubber seal: in transmitted side view
    # the wave is a blind seam, not an air passage clear through the product.
    inner_step = turned([(35.15, 32), (36.65, 32), (35.95, 48), (34.45, 48)], CY)
    inner_step = inner_step.common(seam_mask(.276)).cut(seam_mask(-.35))
    lower = lower.fuse(lower_land).fuse(inner_step).removeSplitter()
    upper = upper.fuse(upper_land).removeSplitter()

    pin_bore = circle(2.03, 23, 9.0, 75.4, 35)
    tab_slot = Part.makeBox(10.2, 5.0, 17.5, V(-5.1, 12.1, 33.5))
    unlock_bore = transverse_cutter(0, -4, 22.2, 5.97)
    lower = trim(lower, [pin_bore, tab_slot, unlock_bore])
    # Five graduated apertures are clearly shown in a bank by the hinge. The
    # side cut ends at the skin; no internal ducts are asserted. Opposite bank
    # follows the bilateral bank in the manufacturer rear view, printed p.04.
    vents = []
    for sign in (-1, 1):
        for i, h in enumerate((8.0, 7.35, 6.55, 5.40, 4.45)):
            cut = Part.Face(rounded_rect(1.48, h, .68)).extrude(V(0, 8, 0))
            cut.translate(V(0, CY + 32.25, 47.1 + h / 2))
            vents.append(rotated(cut, V(0, CY, 0), sign * (24.5 + i * 5.15)))
    back_button = moved(Part.Face(rounded_rect(8.1, 9.55, 2.35)).extrude(V(0, 12, 0)),
                        0, CY + 29.5, 111.0)
    upper = trim(upper, vents + [pin_bore, tab_slot, back_button])

    # Collar around battery mouth. Open route below the front cap is visible in
    # AD206911: leave clearance for four wire jackets behind the transverse rail.
    deck = outer.common(z_box(145.12, 1.48)).cut(circle(24.8, 5.0, 0, CY, 143.0))
    portal = Part.makeBox(25.0, 15.8, 9, V(-12.5, 3.8, 142.0))
    front_rebate = Part.makeBox(40.7, 1.95, 8, V(-20.35, -1.0, 142))
    deck = deck.cut(portal).cut(front_rebate)
    upper = upper.fuse(deck).removeSplitter()

    # Take a real planar section for the crown, preserving the U nose at the
    # front rather than pretending it is just another concentric washer.
    section = max(outer.slice(Z, 146.1), key=lambda w: w.Length)
    face = Part.Face(section)
    crown = moved(face.extrude(V(0, 0, 2.7)), 0, 0, 150.83 - 146.1)
    crown = crown.cut(circle(25.10, 6.0, 0, CY, 149.5))
    return lower, upper, crown, outer


def base_skirt():
    # Some flutes have dark openings on the regional underside image. Their
    # repetition here is approximate. Other shallow grip marks are not ducts.
    body = turned([(32.2, .10), (33.1, .18), (38.75, 7.68), (38.71, 7.79),
                   (36.55, 7.79), (31.85, 1.57), (24.9, 1.57), (24.9, .10)], CY)
    flutes = []
    for i in range(32):
        a = i * 360.0 / 32
        # A facet follows the sloping skirt: about .48 mm deep, not a solid rib
        # through the lower air path. Rounded trapezoidal projection at its base.
        r0, r1 = 33.92, 37.45
        front = polygon([V(-2.12, CY+r0, 1.56), V(2.12, CY+r0, 1.56),
                         V(2.8, CY+r1, 6.28), V(-2.8, CY+r1, 6.28)])
        tool = Part.Face(front).extrude(V(0, 4.5, 0))
        flutes.append(rotated(tool, V(0, CY, 0), a))
        if i % 4 == 0:
            port = Part.makeBox(3.45, 7.5, .92, V(-1.725, CY+29.25, 1.65))
            flutes.append(rotated(port, V(0, CY, 0), a))
    # Adjacent cutter pairs touch: make two disjoint sets for the booleans.
    cuts = [s for i, s in enumerate(flutes) if i % 5 != 1]
    slots = [s for i, s in enumerate(flutes) if i % 5 == 1]
    return trim(trim(body, cuts), slots)


def surface_mark(outer):
    # Hand traced four strokes from the A4.3 wordmark visible below the U-tip.
    # The unfitted master is intersected with a 0.075-mm outside skin only;
    # nothing is cut into the shroud. A presentation marking, not a boss.
    letters = [
        [(-12.5, -4.9), (-10.9, -4.7), (-6.1, .15), (-10.9, 5.0),
         (-12.4, 5.2), (-8.91, .14)],
        [(-8.1, 2.05), (-5.15, 2.1), (-3.6, .59), (-2.06, 2.10),
         (.46, 2.12), (-3.31, -2.24), (-5.9, -2.20), (-4.75, -.84)],
        [(.22, 2.12), (2.25, 2.14), (1.8, .2), (4.55, 2.14),
         (7.35, 2.18), (3.6, -.49), (5.72, -2.22), (2.96, -2.22),
         (1.48, -.89), (1.20, -2.22), (-.71, -2.22)],
        [(5.66, -2.23), (8.81, 2.19), (12.03, 2.16), (12.54, -2.20),
         (10.56, -2.2), (10.45, -1.05), (8.27, -1.05), (7.49, -2.23)],
    ]
    skin = moved(outer, 0, -.075, 0).cut(outer)
    marks = []
    for k, points in enumerate(letters):
        plate = Part.Face(polygon([V(x, -2, 50.5+z) for x, z in points])).extrude(V(0, 32, 0))
        if k == 3:
            counter = Part.Face(polygon([V(9.2, -3, 50.6), V(10.36, -3, 50.6),
                                         V(10.26, -3, 51.85)])).extrude(V(0, 35, 0))
            plate = plate.cut(counter)
        marks.append(skin.common(plate))
    return Part.makeCompound(marks)


def service_panel(c, cover):
    # Native aperture and three through-openings reference the other module's
    # alias values. Behind these is the real display assembly, not a texture.
    panel = Part.Face(u_wire(.07, 40.14, 63.13, 148.75)).extrude(V(0, .76, 0))
    support = scaled(c, cover, 'PanelBlank', 'Заготовка съёмной U-панели', panel)
    lens = Part.Face(rounded_rect(28.0, 31.8, 4.70, -2)).extrude(V(0, 8, 0))
    xf = 'Parameters.UiGlassU * Parameters.UiW / 28.2 mm'
    zf = ('Parameters.UiBase + Parameters.UiGlassV * Parameters.UiL / 50.4 mm '
          '+ Parameters.UiGlassL / 2')
    lens_tool = scaled(c, cover, 'LensAperture', 'Инструмент · окно с угловыми радиусами', lens,
                       ('(Parameters.UiGlassW - 1.2 mm) / 28 mm', 1,
                        '(Parameters.UiGlassL - 1.2 mm) / 31.8 mm'), (xf, 0, zf))
    support = cut_native(c, cover, 'PanelWindow', 'Кассета · выборка под стекло', support, lens_tool)
    for ident, polarity in [('L', -1), ('C', 0), ('R', 1)]:
        def key_outline(scale, y):
            if polarity == 0:
                return rounded_rect(8.55*scale, 11.15*scale, 2.65*scale, y)
            return side_key(polarity, scale, y)
        x = f'Parameters.UiSw{ident}U * Parameters.UiW / 28.2 mm'
        z = 'Parameters.UiBase + Parameters.UiSwV * Parameters.UiL / 50.4 mm'
        opening = Part.Face(key_outline(1.065, -2)).extrude(V(0, 8, 0))
        tool = scaled(c, cover, 'Opening'+ident, 'Инструмент · клавиша '+ident,
                      opening, (1, 1, 1), (x, 0, z))
        last = ident == 'R'
        support = cut_native(c, cover, 'ServiceCover' if last else 'PanelCut'+ident,
                             'Съёмная лицевая панель · окно и три проёма' if last
                             else 'Кассета · прорезь '+ident, support, tool)
        cap = Part.makeLoft([key_outline(.88, 0), key_outline(.995, .45),
                             key_outline(.995, 1.22)], True, True)
        stem = Part.makeBox(1.65, .75, 1.92, V(-.825, 1.20, -.96))
        cap = cap.fuse(stem).removeSplitter()
        panel_key(c, cover, ident, cap,
                  ratios=(1, '(Parameters.UiDepth - Parameters.UiPlungerTop + 0.45 mm) / 1.95 mm', 1),
                  origin=(x, -.45, z))
    c.register(support, cover, INK, PHOTO+'; '+MAN+' c,d,e; '+OPEN_PHOTO, OBS,
               'Маска: световой проём на 0.6 мм внутри края стекла по периметру. Видимая область не размер матрицы.')


def header_return():
    """Dark U-shaped return behind the crown. The wire channel remains open inboard."""
    ledge = Part.makeBox(40.30, 3.81, 2.05, V(-20.15, 0, 148.78))
    band = circle(31.0, 6.0, 0, CY, 145.5)
    for x in (-20.38, 18.95):
        side = Part.makeBox(1.43, 22.9, 4.22, V(x, 1.02, 146.61)).cut(band)
        ledge = ledge.fuse(side)
    return ledge.removeSplitter()


def housing(c):
    group = c.groups['housing']
    upper = c.sub(group, 'MechUpperShellGroup', 'Верхняя часть · кожух и корона')
    lower = c.sub(group, 'MechLowerShellGroup', 'Основание · паз чаши и патрубок')
    cover = c.sub(group, 'MechServicePanelGroup', 'Съёмная лицевая панель · крепление с обратной стороны')
    lo_shape, up_shape, crown_shape, outer = shell_geometry()
    scaled_part(c, upper, 'UpperFairing', 'Верхний кожух · U-проём, боковые плечи и задние щели',
                up_shape, CASE, PHOTO+'; '+MAN+' f,n; '+BACK_PHOTO+'; '+US_FAMILY, OBS,
                'Плавный вынос панели; волнообразная плоскость стыка по видами производителя; глубина полости и толщина стенки оценены. Скрытые воздуховоды не восстановлены.')
    scaled_part(c, lower, 'LowerShroud', 'Корпус основания · неплоский стык и посадочный пояс',
                lo_shape, CASE, MAN+' f,h,i; '+OPEN_PHOTO+'; '+US_FAMILY, EXT,
                'Нижняя половина съёмная. Неподтверждённая внутренняя полка оставляет свободное место для чаши.')
    scaled_part(c, upper, 'TopBridge', 'Корона · перемычка панели и буртик гнезда батареи',
                crown_shape, INK, MAN+' a,b; '+US_FAMILY, EXT,
                'Буртик не является частью батарейного блока; сверху оставлено открытое гнездо.')
    scaled_part(c, upper, 'LightRing', 'Кольцо индикации · светорассеиватель',
                ring(30.95, 28.85, 3.70, 0, CY, 146.95), PALE, MAN+' b; '+PHOTO,
                EXT, 'Видимый пояс, не предполагаемая LED-плата. Выводы светодиодов не установлены.')
    scaled_part(c, upper, 'NoseBridge', 'Верхняя перекладина сервисного окна',
                header_return(), MOLD, PHOTO,
                OBS, 'Четыре провода исчезают позади перекладины, а не в контактах дисплея.')
    scaled_part(c, lower, 'BevelGrip', 'Нижний скос · утопленные грани и прерывистые окна',
                base_skirt(), MOLD, MAN+' j; '+BACK_PHOTO, EXT,
                'Ряды рельефа не все вырезаны насквозь; период повторения и глубина предполагаются. Внутреннее продолжение неизвестно.')
    scaled_part(c, upper, 'BrandMark', 'XYKA · наружная маркировка владельца', surface_mark(outer),
                ALLOY, PHOTO, OBS, 'Графика по фотографии на наружной поверхности; не элемент крепления.')
    service_panel(c, cover)
    return upper, lower, cover, outer, up_shape, lo_shape
