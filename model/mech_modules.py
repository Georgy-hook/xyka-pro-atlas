"""Removable pack, provisional heater, pod, and recessed stem connection.

No electrochemical cells, wound conductor, contacts, sensor package or hidden
leads are inferred. The cylindrical body is the *entire removable pack*, not
a cell. The perforated plate visible from underneath is modelled separately
from the unobserved heat-producing layer.
"""

import math

import FreeCAD as App
import Part
import Sketcher

from mech_heat_face import perforated_face

from mech_shapes import (
    ALLOY, AXIS_Y, BACK_PHOTO, CASE, EST, EXT, HZ, INK, MAN, MOLD, OPEN_PHOTO,
    PACK_PHOTO, PALE, PODS, SEAL, STEEL, V, WO1, WO5, XYKA, Y, Z, at_ratio,
    circle, cut_native, feature, hidden, moved, ring, rotated, scaled, scaled_part,
    trim, turned,
)


def native_lathe(c, parent, name, label, stations, zbase):
    """Fully dimensioned, coincident closed sketch; every radius/axial station
    is editable. (nominal, expression) coordinates follow the spreadsheet.
    Local sketch X = radius, local Y = axial height; turn result upright.
    """
    def value(spec):
        return spec[0] if isinstance(spec, tuple) else spec
    sketch = feature(c, parent, 'Sketcher::SketchObject', name + 'Sketch', 'Профиль · ' + label)
    points = [V(value(r), value(z), 0) for r, z in stations]
    n = len(points)
    sketch.addGeometry([Part.LineSegment(points[i], points[(i+1) % n]) for i in range(n)], False)
    sketch.addConstraint([Sketcher.Constraint('Coincident', i, 2, (i+1) % n, 1) for i in range(n)])
    for i, rz in enumerate(stations):
        for axis, coordinate in zip(('DistanceX', 'DistanceY'), rz):
            idx = sketch.addConstraint(Sketcher.Constraint(axis, i, 1, float(value(coordinate))))
            if isinstance(coordinate, tuple):
                sketch.setExpression(f'Constraints[{idx}]', coordinate[1])
    rev = feature(c, parent, 'Part::Revolution', name, label)
    rev.Source = sketch
    rev.Axis = V(0, 1, 0)
    rev.Angle = 360
    rev.Solid = True
    rev.Placement = App.Placement(V(), App.Rotation(V(1, 0, 0), 90))
    c.at(rev, 0, AXIS_Y, zbase)
    hidden(sketch)
    return rev


def polar_holes(diameter, rings, h, z=-1):
    holes = []
    for r, number, phase in rings:
        for i in range(number):
            a = math.radians(i*360/number + phase)
            holes.append(circle(diameter/2, h, r*math.cos(a), r*math.sin(a), z))
    return holes


def battery(c, host):
    pack = c.sub(c.groups['battery'], 'MechPackAssembly', 'Съёмный блок · только наружный габарит')
    od = c.p['BatteryOD']
    length = c.p['BatteryL']
    def r(inset):
        return (od/2 + inset, f'Parameters.BatteryOD / 2 + ({inset:g} mm)')
    def l(offset):
        return (length + offset, f'Parameters.BatteryL + ({offset:g} mm)')
    cartridge = native_lathe(c, pack, 'BatteryEnvelope', 'Батарея · замкнутый внешний габарит UNKNOWN',
                             [(0., 0.), (r(-1.0), 0.), (r(-.18), 1.05),
                              (r(0), 2.8), (r(0), l(-9.4)), (r(-.4), l(-7.8)),
                              (r(-.4), l(-4.5)), (r(.2), l(-3.5)), (0., l(-3.5))],
                             'Parameters.BodyH - Parameters.BatteryL')
    c.register(cartridge, pack, MOLD, PACK_PHOTO+'; '+MAN+' iii; '+WO1+' Fig.8,9', EST,
               'Корпус единого съёмного блока, часть которого видна на изображении изделия. Химия, число и форма ячеек, напряжение и контакты UNKNOWN.')

    # Radial marks in design family Fig.7 and on the actual pack. Their lower
    # ends do not get connected to guessed vents or battery terminals.
    cap = turned([(0, 0), (22.88, 0), (23.10, .62), (24.18, 1.10),
                  (24.52, 1.58), (24.52, 3.08), (24.10, 3.5), (0, 3.5)])
    slot = Part.makeBox(.68, 5.4, 2.0, V(-.34, 13.50, 1.8))
    cuts = [rotated(slot, V(), i * 18) for i in range(20)]
    cuts.append(circle(1.65, .72, 0, 0, 2.9))
    cap = trim(cap, cuts)
    k = 'Parameters.BatteryOD / 45.4 mm'
    scaled_part(c, pack, 'PackCap', 'Головка съёмного блока · радиальные прорези', cap, INK,
                PACK_PHOTO+'; '+MAN+' a; CN309108835S 立体图1', EXT,
                'Заводское назначение радиальных прорезей, отверстия и их глубина не проверены.',
                ratios=(k, k, 1), origin=(0, AXIS_Y, 'Parameters.BodyH - 3.5 mm'))

    # Hollow sleeve, open at top. The open-face wire route is in front, not in
    # the well. No conjectural spring contacts are placed beneath the pack.
    sleeve = native_lathe(c, host, 'PackWell', 'Гнездо батареи · чашеобразная направляющая',
                          [(0., 0.), (r(.5), 0.), (r(1.3), 1.1), (r(1.3), l(-.6)),
                           (r(.55), l(-.6)), (r(.55), 2.05), (0., 2.05)],
                          'Parameters.BodyH - Parameters.BatteryL - 3.25 mm')
    # The well mouth continues only to the housing top deck. In the final few
    # millimetres the independently removable, wider pack head takes over.
    c.register(sleeve, host, SEAL, WO1+' Figs.8–12; '+PACK_PHOTO, EST,
               'Посадочная гильза, номинальный зазор 0.55 мм по радиусу. Дно упрощено; электрические контакты и защёлка внутри UNKNOWN.')


def base_interface(c, lower):
    # The published dimensions concern the female bore in this regional family,
    # not a male projection, not a production tolerance, and not a measurement
    # of this owner's A4.3 unit. A separate grommet (manual p.03 ii) is omitted.
    d0 = (c.p['StemMouthD']/2, 'Parameters.StemMouthD / 2')
    d1 = (c.p['StemThroatD']/2, 'Parameters.StemThroatD / 2')
    h = (c.p['StemSocketL'], 'Parameters.StemSocketL')
    stem = native_lathe(c, lower, 'StemSocket', 'Патрубок · внутренний конус со стороны дна',
                        [(d0, .0), (13.45, .0), (14.20, .44), (14.20, 2.20),
                         (13.05, 3.05), (11.15, h), (d1, h)], 0)
    c.register(stem, lower, STEEL, XYKA+' FAQ; '+MAN+' j; '+WO1+' Figs.8,9,23', EXT,
               'Утопленное гнездо под конус шахты. Диаметры из FAQ семейства XYKA, владелец не измерял. Угол и длина не паспортные.')
    foot = ring(21.90, 14.27, 1.88)
    pockets = [rotated(Part.makeBox(3.65, 2.08, 2.6, V(-1.825, 16.75, -.1)), V(), 90*i)
               for i in range(4)]
    scaled_part(c, lower, 'StemFacePlate', 'Нижнее кольцо · четыре окна вокруг конуса',
                trim(foot, pockets), ALLOY, BACK_PHOTO+'; '+MAN+' j', EXT,
                'Четыре видимые прорези; зацепы и внутреннее продолжение неизвестны.',
                ratios=(1, 1, 1), origin=(0, AXIS_Y, .17))
    scaled_part(c, lower, 'FootWelt', 'Тёмный опорный кант', ring(24.88, 21.98, 1.38),
                INK, BACK_PHOTO, EXT, 'Материал уплотнения неизвестен.', ratios=(1, 1, 1),
                origin=(0, AXIS_Y, .035))
    # An internal annular return closes the ground-facing annulus without
    # duplicating the stem cylinder. Its thickness is explicitly provisional.
    base = turned([(14.25, 2.18), (31.40, 2.18), (36.50, 8.10), (37.00, 8.10),
                   (37.00, 9.9), (35, 9.90), (30.6, 3.62), (14.25, 3.62)])
    scaled_part(c, lower, 'BaseReturn', 'Внутренняя отбортовка донного узла', base,
                MOLD, BACK_PHOTO+'; '+WO1+' Figs.8–10,23', EST,
                'Внутренний несущий пояс: форма оценочная. Не является предполагаемым воздушным коллектором.',
                ratios=('Parameters.BodyW / 78 mm', 'Parameters.BodyW / 78 mm', HZ),
                origin=(0, AXIS_Y, 0))


def chamber(c, lower):
    pot = c.sub(c.groups['heater'], 'MechPodAssembly', 'Съёмная чаша · контейнер и крышка')
    k = 'Parameters.PodOD / 42 mm'
    q = 'Parameters.PodH / 23.3 mm'
    # Rolled edges and a hollow interior: the pod is not a single filled puck.
    cup = turned([(0, 0), (18.7, 0), (19.65, .34), (20.43, 1.2),
                  (20.52, 20.9), (20.9, 21.48), (21., 21.83), (20.99, 22.78),
                  (20.54, 23.30), (19.75, 23.30), (19.72, 22.3), (19.82, 21.75),
                  (19.45, 20.82), (19.38, 1.70), (18.45, .82), (0, .82)])
    cup = trim(cup, polar_holes(1.4, [(0, 1, 0), (5.1, 7, 0), (10.25, 12, 15),
                                       (15.4, 18, 3)], 1.9))
    pod_top = 'Parameters.BodyH * 0.2855'
    pod_base = pod_top+' - Parameters.PodH'
    scaled_part(c, pot, 'RemovablePod', 'Сменная чаша · перфорированное дно и завальцовка',
                cup, STEEL, OPEN_PHOTO+'; '+MAN+' p; '+PODS+'; '+WO1+' Figs.18–22', EXT,
                '23.3 × Ø42 — габарит сменного изделия по продавцу, а не промер оригинала. Шаг и число отверстий приблизительны.',
                ratios=(k, k, q), origin=(0, AXIS_Y, pod_base))
    lid = turned([(0, 0), (18.77, 0), (19.64, .18), (19.63, .74), (18.78, .95), (0, .95)])
    holes = polar_holes(1.48, [(0, 1, 0), (4.2, 6, 0), (8.45, 12, 15),
                               (12.65, 18, 4), (16.5, 24, 8)], 3)
    scaled_part(c, pot, 'PodLid', 'Съёмный перфорированный диск чаши', trim(lid, holes),
                ALLOY, MAN+' o,p; '+OPEN_PHOTO+'; '+WO1+' Figs.18–22', EXT,
                'Крышка отдельная; рисунок отверстий представительный, не шаблон для изготовления.',
                ratios=(k, k, 1), origin=(0, AXIS_Y, pod_top+' - 1.05 mm'))
    liner = turned([(10.6, 0), (12.05, 0), (17.8, .75), (22.54, .95),
                    (23.5, 2.2), (24.35, 22.4), (24.9, 23.26), (24.88, 24.13),
                    (21.45, 24.13), (21.43, 2.86), (19.9, 1.92), (12.20, 1.92)])
    scaled_part(c, lower, 'ChamberInsert', 'Гнездо сменной чаши · полая вставка', liner,
                MOLD, MAN+' i; '+OPEN_PHOTO+'; '+WO1+' Figs.7–10', EST,
                'Полость со свободным местом для съёмной чаши: скрытый профиль приёмника оценочный.',
                ratios=(k, k, q), origin=(0, AXIS_Y, pod_base+' - Parameters.PodH * 0.0841'))


def heater(c):
    hot = c.sub(c.groups['heater'], 'MechHeaterAssembly', 'Нижняя сторона верхней части · нагреватель')
    kd = 'Parameters.HeatFaceD / 45.8 mm'
    guard_z = 'Parameters.BodyH * 0.2903'
    guard = turned([(0, 0), (21.18, 0), (22.15, .28), (22.48, .76),
                    (22.20, 1.12), (20.85, 1.12), (20.55, .85), (0, .85)])
    bores = polar_holes(1.48, [(0, 1, 0), (4.45, 6, 0), (9.45, 10, 18),
                               (13.8, 12, 0), (18.25, 16, 11)], 3)
    scaled_part(c, hot, 'HeatGuard', 'Перфорированный щиток · лицом к чаше', trim(guard, bores),
                STEEL, OPEN_PHOTO+'; '+MAN+' k; '+WO5+' Figs.4–8', EXT,
                'Перфорация видна на продуктовых видах, а не на фотографиях A4.3. Диаметр, рисунок и идентичность ревизии не подтверждены.',
                ratios=(kd, kd, 1), origin=(0, AXIS_Y, guard_z))
    perforated_face(c, hot, guard_z)
    holder = turned([(22.60, -.06), (25.90, -.06), (26.3, .64), (26.4, 3.65),
                     (28.55, 4.15), (28.55, 5.4), (25.68, 6.1), (23.9, 13.7),
                     (22.95, 13.7), (22.95, 5.6), (23.02, 4.2), (23.02, 1.35),
                     (22.60, 1.25)])
    scaled_part(c, hot, 'HeaterCarrier', 'Посадочная обойма щитка и пластины · EST', holder,
                SEAL, OPEN_PHOTO+'; '+WO1+' Figs.11–14; '+WO5+' Figs.3–5', EST,
                'Представительный профиль вокруг двух раздельных деталей. Теплоизоляционный пакет и контакт датчика не реконструированы.',
                ratios=(kd, kd, 1), origin=(0, AXIS_Y, guard_z))
