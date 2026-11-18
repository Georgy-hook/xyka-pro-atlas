"""Outer moulds. The gently sloping part line is not a horizontal cylinder cut.

Digitising datum: manufacturer manual p.04 at 818 px raster: front envelope
(103,154)..(236,413), top plan centre (173,547), projected tip/rear y469/637.
Front seam reaches raster y354 on centre and y337 at either side; the raised
U-panel ends at y307, its faired shoulders near y337. IMG_AD206911 determines
the service pocket, not a guessed horizontal PCB shelf across the body.
"""

import Part

from mech_profiles import (BODY_TOP, SIDE_SOURCE, cassette_frame, crown_and_bridge,
                           fairing_master, in_cassette, pocket_master, retail_diffuser)
from mech_shapes import (
    BACK_PHOTO, CASE, CY, EXT, INK, MAN, MOLD, OBS, OPEN_PHOTO, PALE, PHOTO,
    US_FAMILY, V, Y, circle, scaled_part, trim, turned, z_box,
)
from retail_clips import crown_with_light_clips, cut_upper_for_light
from retail_clips_base import cut_upper_for_service_base
from retail_front import build_front
from retail_marks import BODY_INK, BODY_SOURCE, surface_mark
from retail_shell import UNLOCK_Z, bevel_grip as base_skirt, parting_mask as seam_mask, rear_features
from retail_shell_legend import legend, receiver_recess


def barrel_solid():
    return turned([(0, 7.8), (38.75, 7.8), (39, 8.3), (38.96, 9.4),
                   (31.97, 145.55), (31.70, 146.60), (0, 146.60)], CY)


def transverse_cutter(x, y, z, radius, depth=25):
    return circle(radius, depth, x, y, z, Y)


def shell_geometry():
    barrel = barrel_solid()
    nose = fairing_master()
    outer = barrel.fuse(nose.common(z_box(35, BODY_TOP-35))).removeSplitter()
    inner_barrel = turned([(0, 7), (37.15, 7), (29.85, 148.2), (0, 148.2)], CY)
    pocket = pocket_master()
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
    unlock_bore = transverse_cutter(0, -4, UNLOCK_Z, 5.97)
    lower = trim(lower, [pin_bore, tab_slot, unlock_bore])
    upper = rear_features(trim(upper, [pin_bore, tab_slot]))

    # Collar around battery mouth. Open route below the front cap is visible in
    # AD206911: leave clearance for four wire jackets behind the transverse rail.
    deck = outer.common(z_box(145.12, 1.48)).cut(circle(24.8, 5.0, 0, CY, 143.0))
    portal = in_cassette(Part.makeBox(25.0, 15.8, 18, V(-12.5, 3.8, 138.0)))
    front_rebate = in_cassette(Part.makeBox(40.7, 1.95, 18, V(-20.35, -1.0, 139)))
    deck = deck.cut(portal).cut(front_rebate)
    upper = upper.fuse(deck).removeSplitter()

    crown, bridge = crown_and_bridge(nose)
    return lower, upper, crown, outer, bridge


def service_panel(c, cover):
    build_front(c, cover)


def housing(c):
    group = c.groups['housing']
    upper = c.sub(group, 'MechUpperShellGroup', 'Верхняя часть · кожух и корона')
    lower = c.sub(c.groups['lower'], 'MechLowerShellGroup', 'Основание · паз чаши и патрубок')
    cover = c.sub(c.groups['fascia'], 'MechServicePanelGroup', 'Лицевая кассета · наклонная система')
    cassette_frame(c, cover)
    lo_shape, up_shape, crown_shape, outer, bridge = shell_geometry()
    lo_shape = lo_shape.cut(receiver_recess()).removeSplitter()
    legend(c, lower)
    up_shape = cut_upper_for_light(cut_upper_for_service_base(up_shape))
    crown_shape = crown_with_light_clips(crown_shape)
    scaled_part(c, upper, 'UpperFairing', 'Верхний кожух · U-проём, боковые плечи и задние щели',
                up_shape, CASE, PHOTO+'; '+SIDE_SOURCE+'; '+MAN+' f,n; '+US_FAMILY, OBS,
                'Наклон панели 7.5° и кривизна EST: тонкая U-кромка плавно переходит в конус. Глубина полости и стенка оценочны.')
    scaled_part(c, lower, 'LowerShroud', 'Корпус основания · неплоский стык и посадочный пояс',
                lo_shape, CASE, MAN+' f,h,i; '+OPEN_PHOTO+'; '+US_FAMILY, EXT,
                'Нижняя половина съёмная. Неподтверждённая внутренняя полка оставляет свободное место для чаши.')
    scaled_part(c, c.groups['light'], 'TopBridge', 'Корона · перемычка панели и буртик гнезда батареи',
                crown_shape, INK, SIDE_SOURCE+'; '+MAN+' a,b; '+US_FAMILY, EXT,
                'Буртик не является частью батарейного блока; сверху оставлено открытое гнездо.')
    scaled_part(c, c.groups['light'], 'LightRing', 'Кольцо индикации · светорассеиватель',
                retail_diffuser(), PALE, MAN+' b; '+PHOTO,
                EXT, 'Видимый пояс, не предполагаемая LED-плата. Выводы светодиодов не установлены.')
    scaled_part(c, upper, 'NoseBridge', 'Верхняя перекладина сервисного окна',
                bridge, MOLD, PHOTO+'; '+SIDE_SOURCE,
                OBS, 'Четыре провода исчезают позади перекладины, а не в контактах дисплея.')
    scaled_part(c, lower, 'BevelGrip', 'Нижний скос · утопленные грани и прерывистые окна',
                base_skirt(), MOLD, MAN+' j; '+BACK_PHOTO, EXT,
                'Ряды рельефа не все вырезаны насквозь; период повторения и глубина предполагаются. Внутреннее продолжение неизвестно.')
    scaled_part(c, upper, 'BrandMark', 'XYKA · наружная маркировка владельца', surface_mark(outer),
                BODY_INK, BODY_SOURCE, OBS,
                'Печатный знак на верхнем кожухе, между кончиком U и швом; не часть плёнки.')
    service_panel(c, cover)
    return upper, lower, cover, outer, up_shape, lo_shape
