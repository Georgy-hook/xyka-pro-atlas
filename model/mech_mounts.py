"""Removable carrier frame, actually visible rim bores, and closure mechanics.

The bracket holes in the side aperture are not the through-holes on either
printed circuit. In particular no bolt head is placed through the LCD lens.
The spring pin is shown as a mechanical pin only, never as a net assignment.
"""

import FreeCAD as App
import Part

from mech_keyfaces import UNLOCK_PHOTO, grip_key
from retail_shell import UNLOCK_Z
from retail_shell_rear import PACK_KEY, REAR, hinge, retail_key
from mech_shapes import (
    ALLOY, EST, EXT, MAN, MOLD, OPEN_PHOTO, PHOTO, STEEL, V, WO1, Y,
    circle, moved, polygon, rounded_rect, scaled_part, trim, turned,
)


def depth_turn(shape):
    result = shape.copy()
    result.rotate(V(), V(1, 0, 0), -90)
    return result


def external_keys(c, upper, lower):
    # The lower button is not a straight-through annular peephole. A shallow
    # retaining shoulder behind its original cap backs the narrow dark reveal.
    ring = depth_turn(turned([(5.23, 0), (5.66, 0), (5.90, .36),
                              (5.90, 4.21), (6.16, 4.21), (6.16, 4.52),
                              (4.72, 4.52), (4.72, 2.61), (5.23, 2.61)]))
    scaled_part(c, lower, 'FrontUnlockBezel', 'Обод кнопки разблокировки основания',
                moved(ring, 0, 6.05, UNLOCK_Z), ALLOY, MAN+' g; '+OPEN_PHOTO, EXT)
    button = depth_turn(turned([(0, 0), (4.47, 0), (5.09, .50), (5.10, 2.72), (0, 2.72)]))
    disc = Part.Wire([Part.makeCircle(4.02, V(), Y)])
    grip_key(c, lower, 'FrontUnlockKey', 'Круглая клавиша разблокировки', button, disc,
             MAN+' g; '+OPEN_PHOTO+'; '+UNLOCK_PHOTO, 'На круглом поле видны грани, не знак. '
             'Скрытый привод и пружина неизвестны.',
             pose=App.Placement(V(0, 5.80, UNLOCK_Z), App.Rotation()))
    retail_key(c, upper, 'PackReleaseKey', 'Задняя кнопка извлечения блока', PACK_KEY,
               REAR + '; ' + MAN + ' l')


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
