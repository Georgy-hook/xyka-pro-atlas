"""Removable carrier frame, actually visible rim bores, and closure mechanics.

The bracket holes in the side aperture are not the through-holes on either
printed circuit. In particular no bolt head is placed through the LCD lens.
The spring pin is shown as a mechanical pin only, never as a net assignment.
"""

import FreeCAD as App
import Part

from mech_profiles import cassette_frame, in_cassette
from mech_keyfaces import HINGE_PHOTO, REAR_PHOTO, UNLOCK_PHOTO, cushion, grip_key
from mech_shapes import (
    ALLOY, BACK_PHOTO, CASE, CY, EST, EXT, INK, MAN, MOLD, OBS, OPEN_PHOTO,
    PHOTO, SEAL, STEEL, V, WO1, WX, DY, HZ, Y, Z, bezier, body_pos, circle,
    moved, polygon, rounded_rect, scaled_part, trim, turned,
)


def depth_turn(shape):
    result = shape.copy()
    result.rotate(V(), V(1, 0, 0), -90)
    return result


def bent_button(width, height, y0, depth, x, y, z, pitch=0):
    s = Part.Face(rounded_rect(width, height, min(2.2, width/3), y0)).extrude(V(0, depth, 0))
    s.rotate(V(), V(1, 0, 0), pitch)
    return moved(s, x, y, z)


def rear_key(c, parent, ident, label, width, height, face_y, depth, y, z, pitch, source, note):
    # Same bore, back face and seated depth as bent_button. Only the outermost
    # 0.22 mm rounds into the silver-looking lip seen in XYKA 23/25.jpg.
    r = min(2.2, width / 3)
    blank = Part.makeLoft([rounded_rect(width - .32, height - .40, r - .16),
                           rounded_rect(width, height, r, .22),
                           rounded_rect(width, height, r, depth)], True, True)
    tilt = App.Rotation(V(1, 0, 0), pitch)
    face = V(0, y, z) + tilt.multVec(V(0, face_y, 0))
    pose = App.Placement(face, tilt.multiply(App.Rotation(Z, 180)))  # local -Y faces aft
    grip_key(c, parent, ident, label, blank, cushion(.76 * width, .66 * height),
             source, note, pose=pose)


def external_keys(c, upper, lower):
    ring = depth_turn(turned([(5.23, 0), (5.66, 0), (5.90, .36),
                              (5.90, 3.70), (5.23, 3.70)]))
    scaled_part(c, lower, 'FrontUnlockBezel', 'Обод кнопки разблокировки основания',
                moved(ring, 0, 6.05, 22.2), ALLOY, MAN+' g; '+OPEN_PHOTO, EXT)
    button = depth_turn(turned([(0, 0), (4.47, 0), (5.09, .50), (5.10, 2.72), (0, 2.72)]))
    disc = Part.Wire([Part.makeCircle(4.02, V(), Y)])
    grip_key(c, lower, 'FrontUnlockKey', 'Круглая клавиша разблокировки', button, disc,
             MAN+' g; '+OPEN_PHOTO+'; '+UNLOCK_PHOTO, 'На круглом поле видны грани, не знак. '
             'Скрытый привод и пружина неизвестны.',
             pose=App.Placement(V(0, 5.80, 22.2), App.Rotation()))
    rear_key(c, upper, 'PackReleaseKey', 'Задняя кнопка извлечения блока',
             7.67, 9.11, .61, 2.23, 79.12, 111.0, 0, MAN+' l; '+REAR_PHOTO,
             'На виде сзади — светлый обод и мелкая сетка без читаемого знака. '
             'Ход и скрытая защёлка не восстановлены.')


def hinge(c, upper, lower, outer):
    # The rear protrusion gives the assembled body much more depth than width.
    # A shaped clevis, narrow revolving tongue, axle and rear eject pad account
    # for the unmistakable rear profile in the family design and the manual.
    def yz(x, y, z):
        return V(x, y, z)
    x = -15.1
    p = lambda y, z: yz(x, y, z)
    path = [Part.makeLine(p(73.5, 17.6), p(83.35, 17.6)),
            Part.makeLine(p(83.35, 17.6), p(97.0, 40.5)),
            bezier(p(97, 40.5), p(97.7, 41.9), p(98.0, 42.8), p(98.0, 45.15)),
            Part.makeLine(p(98.0, 45.15), p(98.0, 47.95)),
            bezier(p(98.0, 47.95), p(98, 55.3), p(90.8, 56.60), p(87.4, 50.0)),
            Part.makeLine(p(87.4, 50.0), p(84.4, 45.6)),
            Part.makeLine(p(84.4, 45.6), p(74.0, 45.6)),
            Part.makeLine(p(74.0, 45.6), p(73.5, 17.6))]
    bracket = Part.Face(Part.Wire(path)).extrude(V(30.2, 0, 0)).cut(outer)
    pinaxis = V(1, 0, 0)
    bore = circle(1.94, 35, -17.5, 92.45, 47.95, pinaxis)
    cavity = Part.makeBox(24.75, 32, 24, V(-12.375, 74, 42.67))
    rear_bore = bent_button(8.0, 8.72, -4, 9, 0, 90.18, 29.05, -30.8)
    bracket = trim(bracket.cut(cavity), [rear_bore, bore])
    scaled_part(c, lower, 'RearClevis', 'Основание шарнира · проушины и паз кнопки',
                bracket, CASE, MAN+' m,n; '+BACK_PHOTO+'; '+WO1+' Figs.3–7', EXT,
                'Наружная скоба подтверждена. Внутренний паз — приближение, не копия запатентованного механизма.')
    rear_key(c, lower, 'RearEjectKey', 'Задняя клавиша отделения основания',
             7.55, 8.22, .85, 2.45, 90.18, 29.05, -30.8, MAN+' m; '+REAR_PHOTO+'; '+HINGE_PHOTO,
             'Скошенная тыльная площадка с рядами граней, без обозначения и скрытого привода.')
    x = -12.0
    p = lambda y, z: yz(x, y, z)
    upper_path = [Part.makeLine(p(72, 80.3), p(76.95, 80.3)),
                  Part.makeLine(p(76.95, 80.3), p(79.55, 79.78)),
                  Part.makeLine(p(79.55, 79.78), p(81.83, 78.34)),
                  Part.makeLine(p(81.83, 78.34), p(83.78, 75.92)),
                  Part.makeLine(p(83.78, 75.92), p(85.55, 72.25)),
                  Part.makeLine(p(85.55, 72.25), p(96.32, 50.5)),
                  Part.Arc(p(96.32, 50.5), p(92.43, 43.35), p(88.33, 45.84)).toShape(),
                  Part.makeLine(p(88.33, 45.84), p(81.8, 46.05)),
                  Part.makeLine(p(81.8, 46.05), p(72.0, 47.7)),
                  Part.makeLine(p(72.0, 47.7), p(72.0, 80.3))]
    tongue = Part.Face(Part.Wire(upper_path)).extrude(V(24, 0, 0)).cut(outer).cut(bore).removeSplitter()
    scaled_part(c, upper, 'RearHingeLeaf', 'Наклонная спинка шарнира · верхняя часть', tongue, MOLD,
                MAN+' n; '+BACK_PHOTO+'; '+WO1+' Figs.3–6', EXT,
                'Верхняя половина геометрически отделена от скобы. Ось условная, рабочий угол не заявлен.')
    pivot = circle(1.80, 28.8, -14.4, 92.45, 47.95, pinaxis)
    scaled_part(c, c.groups['mounts'], 'HingeAxle', 'Поперечная ось шарнира · EST', pivot, ALLOY,
                WO1+' Figs.5,6,8; '+BACK_PHOTO, EST, 'Положение по силуэту; способ фиксации концов и профиль пальца UNKNOWN.')


def closure(c, upper, lower):
    loc = c.sub(c.groups['mounts'], 'MechClosureGroup', 'Механика стыка · без электрической схемы')
    # WO381 figs.24–25 put the closure sensing pin next to the hinge. Only its
    # existence is attested by the A4.3 owner; its exact offset/travel is not.
    sleeve = turned([(1.22, 0), (1.95, 0), (1.95, 2.65), (2.25, 2.8),
                     (2.25, 3.33), (1.22, 3.33)])
    scaled_part(c, upper, 'ClosurePinGuide', 'Втулка нажимного штырька · EST',
                moved(sleeve, 9.0, 75.4, 45.25), ALLOY, WO1+' Figs.24,25; описание владельца §4', EST,
                'Закрытое положение. Направляющая, ход и положение относительно шарнира не измерены.')
    pin = turned([(0, 0), (.79, 0), (1.11, .31), (1.11, 4.86), (.86, 5.17), (0, 5.17)])
    scaled_part(c, loc, 'ClosurePin', 'Металлический штырёк закрытия · цепь UNKNOWN',
                moved(pin, 9.0, 75.4, 43.94), STEEL, '00_START_HERE §4, владелец; '+WO1+' Figs.24–25',
                'OWNER-REPORTED / POSITION ESTIMATE', 'Назначение контактов KEY/GND и S± не установлено; ни к одной паре не привязан.')
    sec = [(12.30, 35.4), (16.72, 35.4), (16.72, 42.26), (15.78, 43.65),
           (13.18, 44.45), (13.20, 42.94), (12.30, 42.48)]
    lug = Part.Face(polygon([V(-4.65, y, z) for y, z in sec])).extrude(V(9.30, 0, 0))
    scaled_part(c, lower, 'FrontHook', 'Передний ответный выступ крышки · EST', lug, MOLD,
                OPEN_PHOTO+'; '+WO1+' Figs.3–7, 9', EST,
                'Один видимый выступ на стороне, противоположной петле. Скрытый кинематический привод неизвестен.')


def board_carrier(c, cover):
    bw, bl = 29.3, 64.2
    perimeter = [(-10.9, -.5), (10.9, -.5), (16.05, 5.75), (16.05, 60.7),
                 (13.8, 62.15), (4.10, 62.15), (3.55, 64.68), (-3.55, 64.68),
                 (-4.1, 62.15), (-13.8, 62.15), (-16.05, 60.7), (-16.05, 5.75)]
    frame = Part.Face(polygon([V(x, 0, z) for x, z in perimeter])).extrude(Y)
    opening = moved(Part.Face(rounded_rect(27.55, 54.65, 2.15, -.5)).extrude(V(0, 2, 0)),
                    0, 0, 31.80)
    frame = frame.cut(opening)
    hp = [( .01911, .97539), (-.30717, .02305), (.25529, .02305), (.43003, .16573)]
    centers = [(-u * bw, v * bl) for u, v in hp]  # main PCB u = -global X
    for x, z in centers:
        frame = frame.fuse(circle(2.02, 1, x, 0, z, Y))
    frame = trim(frame, [circle(1.02, 2, x, -.5, z, Y) for x, z in centers])
    front = 'Parameters.UiDepth + Parameters.UiT + 0.42 mm'
    ratio_y = '(Parameters.MainDepth - Parameters.BoardT - Parameters.UiDepth - Parameters.UiT - 0.44 mm) / 1 mm'
    scaled_part(c, cover, 'CartridgeFrame', 'Открытая рамка платы · четыре совмещённых отверстия',
                frame, MOLD, PHOTO+'; IMG_8908/8919/8921; pcb_registration.json', EST,
                'Рамка лежит между обратными сторонами плат. Четыре канала привязаны к отверстиям основной PCB; винт в каждом не предполагается.',
                ratios=('Parameters.BoardW / 29.3 mm', ratio_y, 'Parameters.BoardL / 64.2 mm'),
                origin=(0, front, 'Parameters.PanelBase'))
    for side in ('L', 'R'):
        x = f'Parameters.UiHole{side}U * Parameters.UiW / 28.2 mm'
        z = 'Parameters.UiBase + Parameters.UiHoleV * Parameters.UiL / 50.4 mm'
        boss = circle(1.26, 1, 0, 0, 0, Y).cut(circle(.64, 2, 0, -.5, 0, Y))
        k = 'Parameters.UiHoleD / 1.25 mm'
        scaled_part(c, cover, 'DisplaySeat'+side, 'Опора 20260305A '+side+' · EST',
                    boss, MOLD, 'IMG_8917, IMG_8918 (два сквозных отверстия); '+PHOTO, EST,
                    'Втулка у поверхности маски, не винт в припое. Глубина и реальность отдельной втулки UNKNOWN.',
                    ratios=(k, '(Parameters.UiDepth - 0.94 mm) / 1 mm', k), origin=(x, .84, z))


def rim_hardware(c, upper, shell):
    mounts = c.sub(c.groups['mounts'], 'MechPanelFixings', 'Лицевая кассета · пример установки крепежа')
    rim = c.sub(upper, 'MechRimEars', 'Проушины в наклонной плоскости кассеты')
    cassette_frame(c, rim)
    cassette_frame(c, mounts)
    shell = in_cassette(shell, inverse=True)
    # Four direct sightings, not a fictitious regularly spaced bolt circle.
    # No fifth screw is silently mirrored into the area occluded by the board.
    fixtures = [('TopL', -15.25, 142.9), ('TopR', 15.25, 142.9),
                ('SideR', 18.63, 82.9), ('Foot', -1.9, 69.02)]
    for ident, x, z in fixtures:
        rr = 1.98 if ident.startswith('Top') else 1.90
        depth = 3.05 if ident == 'Foot' else 3.44
        ear = circle(rr, depth, x, 1.50, z, Y)
        if ident.startswith('Top'):
            strap = Part.makeBox(rr*2, 3.44, 2.23, V(x-rr, 1.5, z))
        elif ident == 'SideR':
            strap = Part.makeBox(2.0, 3.44, 2*rr, V(x, 1.5, z-rr))
        else:
            strap = Part.makeBox(2*rr, depth, 1.85, V(x-rr, 1.5, z-1.85))
        ear = ear.fuse(strap).cut(circle(.90, 5.0, x, 1.1, z, Y)).removeSplitter()
        # The curved cheek can sever a corner outside the case. Only the
        # mounting lug connected to the web around its bore is physical.
        web = V(x - 1.40, 1.50 + depth / 2, z)
        pieces = ear.cut(shell).removeSplitter().Solids
        seated = [piece for piece in pieces if piece.isInside(web, 1e-6, False)]
        if len(seated) != 1:
            raise ValueError(f'{ident}: no unique rim ear at its bore')
        ear = seated[0]
        scaled_part(c, rim, 'PanelEar'+ident, 'Проушина кассеты '+ident, ear, MOLD,
                    PHOTO, OBS, 'Координата оценена по косому AD206911; сквозной канал сохранён.')
        if ident.startswith('Top'):
            screw = depth_turn(turned([(0, 0), (1.12, 0), (1.53, .20), (1.62, .40),
                                       (1.58, .60), (.77, .60), (.77, 4.0),
                                       (.59, 4.18), (0, 4.18)]))
            scaled_part(c, mounts, 'ServiceScrew'+ident, 'Винт крепления кассеты '+ident+' · EST',
                        moved(screw, x, .895, z), ALLOY,
                        'IMG_8917/8919/8921 (свободный крепёж); '+PHOTO+' (отверстия)', EST,
                        'Два условно установленных крепежа в существующих верхних проушинах. Не заявлены тип шлица, шаг, резьба, длина или полный заводской комплект.')
