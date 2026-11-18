"""Removable service base INSIDE the upper shell; nominal 78 × 98 × 154 mm EST.

Not the consumer pod chamber, hinge, display fixing or light-ring catches.
The gasket-side screws face down. The four screws revealed when the block is
lowered face up; their hollow posts belong to the heater-facing member.

The three site coordinates use the marked underside view (hinge at bottom).
The other four come from the differently oriented heater-side photo sep10:
register its two side holes and hinge hole to those three sites, correct the
oblique circular rim, then check the four wells against sep02 and oct06. This
is an inverse-camera estimate on other retail specimens, not metrology. No
thread, drive, full fastener length, release stroke or unseen catch is known.
"""

import Part

from mech_shapes import AXIS_Y, CY, INK, MOLD, V, Z, circle, moved, polygon, scaled_part, turned


GUARD_Z = 154.0 * .2903
GUARD_ORIGIN = (0, AXIS_Y, 'Parameters.BodyH * 0.2903')
HEAT_K = 'Parameters.HeatFaceD / 45.8 mm'
BASE_OD_R = 31.43
PASSAGE_R = 31.65
POST_TOP = 9.10
INNER_SEAT_Z = 11.95
SEAL_SEAT_Z = 2.55

# Axis-local XY in mm (X right from the display; positive Y toward the hinge).
# Individually registered, NOT copies rotated at equal pitch.
INNER_SITES = (('FrontL', -20.05, -17.70), ('FrontR', 18.60, -18.65),
               ('RearL', -21.05, 17.95), ('RearR', 21.75, 17.50))
SEAL_SITES = (('Left', -29.35, .55), ('Right', 29.10, -.45), ('Rear', .55, 29.35))

SEP = 'September teardown, https://www.reddit.com/r/hookah/comments/1walb9l/ , sep02/03/10'
OCT = ('oct04/05/06 (https://i.redd.it/rn3jrbuzpmwh1.jpeg ; '
       'https://i.redd.it/vxgzdcuzpmwh1.jpeg ; https://i.redd.it/hdf30duzpmwh1.jpeg)')
UA = 'HookahCat, https://hookahcat.com.ua/ru/xkah-pro-electronic-hookah-bowl-review'
UA_PHOTOS = 'https://hookahcat.com.ua/image/catalog/Blog-images/blog/xkln/'
GASKET_SOURCE = UA + '; ' + UA_PHOTOS + 'xkah-pro-3-gvynty-pid-prokladkoyu.jpg'
CATCH_SOURCE = UA + '; ' + UA_PHOTOS + 'xkah-pro-nyzhniy-blok-shleyf.jpg'
CONF = 'RETAIL TEARDOWN / COUNT OBSERVED; POSITION, SECTION AND REVISION EST'
HEAD_COLOR = (.19, .20, .215)


def _section(stations, width):
    """Partial lathe, centred at front (−Y). No replication around the rim."""
    face = Part.Face(polygon([V(r, 0, z) for r, z in stations]))
    solid = face.revolve(V(), Z, width)
    solid.rotate(V(), Z, -90 - width / 2)
    return solid


def _pin_keepout(radius):
    # This existing *consumer closure* guide must remain supported and clear.
    # The scallop opens out of the rim: it is not another hole or screw site.
    return circle(radius, 40, 9., 75.4 - CY, -15.)


def _bores(shape, sites, radius, z0, z1):
    tools = [circle(radius, z1 - z0, x, y, z0) for _, x, y in sites]
    return shape.cut(Part.makeCompound(tools))


def _catch():
    # One low shoulder on the FRONT peripheral band in dim_uaopen. The sloped
    # lead-in and depth of its hidden inverse surface are an estimated fit.
    return _section([(29.45, 6.75), (33.00, 6.75), (33.00, 7.52),
                     (31.15, 9.48), (29.45, 9.48)], 12.)


def _receiver():
    # One local backing inside the fairing. Its outer edge lands IN the wall
    # (r~34.8 here), well inside the exterior r>36. The pocket remains blind.
    block = _section([(31.85, 5.90), (35.23, 5.25), (35.23, 10.90),
                      (32.40, 10.42), (31.85, 9.78)], 17.)
    hollow = _section([(30.9, 6.60), (33.20, 6.60), (33.20, 9.52), (30.9, 9.52)], 13.5)
    return block.cut(hollow).removeSplitter()


def cut_upper_for_service_base(shape):
    """Nominal WORLD upper master → same shell with insert passage + one pocket.

    Removing the consumer lower half exposes the photographed service insert.
    The old unmeasured Ø54.3 inner edge otherwise traps this ~Ø63 insert even
    after all fasteners are out. Relieve only its axial passage in the upper
    wave land. Keep the outer closure land, skin and existing pin seat; there
    is no lower-shell operation and no exterior aperture.
    """
    z0 = 31. - GUARD_Z
    # The two independent blind vent returns start at r31.66. Do not clip
    # them with a general circular cutter enlarged to cover the flat heel.
    passage = circle(PASSAGE_R, 17., z=z0)
    heel_passage = Part.makeBox(12.38, 4.0, 17., V(-6.19, 27.38, z0))
    passage = passage.fuse(heel_passage).cut(_pin_keepout(2.48))
    result = shape.cut(moved(passage, 0, CY, GUARD_Z))
    return result.fuse(moved(_receiver(), 0, CY, GUARD_Z)).removeSplitter()


def cut_carrier_for_service_base(shape):
    """Existing unscaled axis-local holder → SAME MechHeaterCarrier, not a copy.

    The old central seat remains. Its heater-facing lip receives the widened
    warning surround and carries the observed outer flange and four posts.
    All stations here and below are relative to the original guard datum.
    """
    flange = turned([(25.65, 1.45), (31.30, 1.45), (BASE_OD_R, 1.78),
                     (BASE_OD_R, 3.73), (31.30, 4.02), (25.65, 4.02)])
    # Small flat hinge-side heel around the marked third hole (sep03/10).
    heel = Part.makeBox(12., 3.8, 2.57, V(-6., 27.39, 1.45))
    lower = shape.fuse(flange).fuse(heel)
    for _, x, y in INNER_SITES:
        tower = turned([(0, 3.96), (1.95, 3.96), (1.70, 4.40),
                        (1.62, POST_TOP - .19), (1.54, POST_TOP), (0, POST_TOP)])
        lower = lower.fuse(moved(tower, x, y, 0))
    lower = _bores(lower, INNER_SITES, .97, -.25, POST_TOP + .15)
    lower = _bores(lower, INNER_SITES, 1.52, -.25, 1.98)
    # At the right site the shank also grazes the original holder's raised
    # r28.55 flange; carry the same witness bore through that flange.
    lower = _bores(lower, SEAL_SITES, 1.02, -.25, 6.12)
    lower = _bores(lower, SEAL_SITES, 1.77, -.25, SEAL_SEAT_Z)
    # Open-ended rebate for the revised warning rim (r<=25.64; z+.08…+.82).
    # Cut the carrier ONLY. The guard, its markings and the plate stay intact.
    return lower.cut(circle(25.80, 2.98, z=-2.)).cut(_pin_keepout(2.72)).removeSplitter()


def _insert():
    # Model the observable load-bearing annulus, not an opaque disk standing
    # in for hidden contacts or heater internals. Stepped rims frame the wells.
    # Straight lower od belt at the pin scallop. An EST conical bevel here
    # produced an unorientable trimmed face after native XY-only scaling.
    web = turned([(23.95, 4.46), (BASE_OD_R, 4.46),
                  (BASE_OD_R, 8.40), (31.14, 8.87), (26.54, 8.87),
                  (26.16, 9.30), (25.96, 12.58), (25.63, 12.86), (23.95, 12.86)])
    for _, x, y in INNER_SITES:
        ear = turned([(0, 8.73), (3.01, 8.73), (2.66, 9.23),
                      (2.61, 12.91), (2.45, 13.12), (0, 13.12)])
        web = web.fuse(moved(ear, x, y, 0))
    web = web.fuse(_catch())
    # Follow the EXISTING central holder's outer flange with running clearance.
    # This also leaves the lower edges of the counterbores true to that flange.
    center = turned([(0, 4.11), (28.76, 4.11), (28.76, 5.53),
                     (25.90, 6.26), (24.10, 13.85), (0, 13.85)])
    web = web.cut(center).cut(_pin_keepout(2.72))
    web = _bores(web, INNER_SITES, 1.03, 4.1, 13.35)
    web = _bores(web, INNER_SITES, 1.84, 4.1, POST_TOP)
    web = _bores(web, INNER_SITES, 1.79, INNER_SEAT_Z, 13.35)
    return _bores(web, SEAL_SITES, 1.13, 4.1, 13.35).removeSplitter()


def _gasket():
    # Independent peelable seal hiding all three lower heads. Its flat back
    # meets the lower flange, not the consumer chamber. Section/material EST.
    lip = turned([(26.53, .87), (27.05, .60), (30.88, .60), (31.31, .79),
                  (31.40, 1.07), (31.18, 1.45), (26.76, 1.45), (26.53, 1.20)])
    return lip.cut(_pin_keepout(2.72)).removeSplitter()


def _inner_screw():
    # Smooth observed envelope, short seated shank. No invented drive/thread.
    return turned([(0, 7.20), (.69, 7.20), (.83, 7.37), (.83, INNER_SEAT_Z),
                   (1.59, INNER_SEAT_Z), (1.63, 12.12), (1.61, 12.69),
                   (1.39, 12.85), (0, 12.85)])


def _seal_screw():
    return turned([(0, 1.57), (1.40, 1.57), (1.60, 1.76), (1.61, 2.37),
                   (1.55, SEAL_SEAT_Z), (.82, SEAL_SEAT_Z), (.82, 5.77),
                   (.65, 5.95), (0, 5.95)])


def add_service_base(c, parent):
    """Register installed leaves in an unrotated upper parent. No case rebuild."""
    first = c.sub(parent, 'MechServiceBaseSealStage', 'Основа верха · 01 / уплотнитель и 3 винта снизу')
    second = c.sub(parent, 'MechServiceBaseInnerStage', 'Основа верха · 02 / вставка и 4 внутренних винта сверху')

    def part(group, name, label, shape, color, source, note):
        return scaled_part(c, group, 'ServiceBase' + name, label, shape, color, source, CONF, note,
                           ratios=(HEAT_K, HEAT_K, 1), origin=GUARD_ORIGIN)

    part(first, 'Gasket', 'Съёмный уплотнитель нагревателя · закрывает 3 головки',
         _gasket(), INK, GASKET_SOURCE + ' (ua_gasket, три стрелки); ' + SEP,
         'Только уплотнитель сервисной основы сверху от нижней чаши. Сечение, материал и глубина EST.')
    part(second, 'Insert', 'Сервисная вставка · 4 колодца и один видимый зацеп',
         _insert(), MOLD, SEP + '; ' + OCT + '; ' + CATCH_SOURCE + ' (dim_uaopen, выступ под передней кромкой)',
         'Сопряжение с четырьмя стойками MechHeaterCarrier. Один передний зацеп входит в глухой карман '
         'MechUpperFairing. Его сечение/азимут EST, полное число защёлок UNKNOWN. Центр не заполнен '
         'гипотетическим механизмом. Не нижняя чаша, не экран, не кольцо подсветки.')
    for group, family, sites, screw, count, direction, source in (
            (first, 'Seal', SEAL_SITES, _seal_screw(), 3, 'под уплотнителем, головка вниз', GASKET_SOURCE + '; ' + SEP),
            (second, 'Inner', INNER_SITES, _inner_screw(), 4, 'на выдвинутой основе, головка вверх', SEP + '; ' + OCT)):
        for index, (key, x, y) in enumerate(sites, 1):
            name = family + 'Screw' + key
            label = f'Винт {index}/{count} · {direction} · {key} EST'
            part(group, name, label, moved(screw, x, y, 0), HEAD_COLOR, source,
                 'Число креплений подтверждено разборкой. XY из косого/перевёрнутого снимка; Z, диаметр '
                 'и длина видимого контура EST. Показан короткий гладкий стержень, не тип резьбы или шлица.')
    return first, second
