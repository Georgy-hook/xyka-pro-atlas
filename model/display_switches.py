"""Three four-terminal tactile envelopes with independent moving plungers."""

import Part

from display_interface import EST, FACE, SCALE
from display_laminate import body
from display_native import NICKEL, P, TIN, V, pad, round_slab, rounded_loop, sketch


CREAM = (0.90, 0.78, 0.45)
CAN = (0.71, 0.69, 0.57)


def _terminals():
    pads = []
    feet = []
    for side in (-1, 1):
        for u in (-0.96, 0.96):
            y0 = -2.32 if side < 0 else 1.77
            pads.append(round_slab(u - 0.25, y0, 0, 0.50, 0.55, 0.085, 0.046))
            # Stamped, bent terminal in local v/w section, touching the molded case.
            yz = [(1.745, 0.09), (2.00, 0.046), (2.24, 0.046), (2.24, 0.118),
                  (2.04, 0.118), (1.83, 0.152), (1.81, 0.37), (1.745, 0.37)]
            path = [V(u - 0.195, side * v, w) for v, w in yz]
            feet.append(Part.Face(Part.makePolygon(path + path[:1])).extrude(V(0.39, 0, 0)))
    return Part.makeCompound(pads), Part.makeCompound(feet)


def switches(c, parent):
    p = c.p
    for side, position in (('L', 'левая'), ('C', 'средняя'), ('R', 'правая')):
        sw = c.sub(parent, 'UiSwitch' + side, 'Тактовая кнопка · ' + position)
        c.at(sw, f'{P}UiSw{side}U * {P}UiW / 28.2 mm', f'{P}UiSwV * {P}UiL / 50.4 mm', 0)
        lands, terminals = _terminals()
        c.solid(sw, 'UiSwitchPads' + side, 'Четыре паяльных площадки ' + side, lands, TIN, FACE, EST)
        c.solid(sw, 'UiSwitchLeads' + side, 'Загнутые лапки ' + side, terminals, NICKEL, FACE, EST,
                'Local visible terminal envelope, not a contact assignment.')
        lower = round_slab(-1.455, -1.745, 0.070, 2.91, 3.49, 0.17, 0.44)
        c.solid(sw, 'UiSwitchBase' + side, 'Основание контактного блока ' + side, lower,
                (0.28, 0.27, 0.22), SCALE, EST, 'Part number and actuator travel UNKNOWN.')
        # The punched retainer stays clear of the moving button. A separate
        # top lip uses four light corner tabs rather than a second solid cube.
        can = round_slab(-1.51, -1.925, 0.51, 3.02, 3.85, 0.15, 0.55)
        opening = round_slab(-1.19, -1.41, 0.49, 2.38, 2.82, 0.87, 0.60)
        c.solid(sw, 'UiSwitchCan' + side, 'Штампованная рамка с окном ' + side,
                can.cut(opening), CAN, FACE, EST)
        tabs = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0 = sx * 1.245 - 0.18
                y0 = sy * 1.61 - 0.215
                tabs.append(round_slab(x0, y0, 1.06, 0.36, 0.43, 0.075, 0.095))
        c.solid(sw, 'UiSwitchClips' + side, 'Четыре прижимных язычка ' + side,
                Part.makeCompound(tabs), (0.81, 0.79, 0.67), FACE, EST)
        cap = body(c, sw, 'UiPlunger' + side, 'Кремовый толкатель · ' + position)
        profile = sketch(cap, 'UiPlungerProfile' + side, 'Скруглённый профиль подвижного толкателя')
        w, l = p['UiCapW'], p['UiCapL']
        rounded_loop(profile, -w / 2, -l / 2, w, l, 0.415 * w,
                     (f'-{P}UiCapW / 2', f'-{P}UiCapL / 2', f'{P}UiCapW / 2', f'{P}UiCapL / 2'),
                     f'{P}UiCapW * 0.415')
        part = pad(cap, profile, 'UiPlungerShaft' + side, 'Ходовая часть и шляпка',
                   p['UiPlungerTop'] - 0.51, P + 'UiPlungerTop - 0.51 mm')
        # The visible cream face rounds into the plunger, unlike a bare pad.
        c.doc.recompute([profile, part])
        top = p['UiPlungerTop'] - 0.51
        top_edges = [f'Edge{i}' for i, e in enumerate(part.Shape.Edges, 1)
                     if abs(e.BoundBox.ZMin - top) < 1e-5 and abs(e.BoundBox.ZMax - top) < 1e-5]
        finish = cap.newObject('PartDesign::Fillet', 'UiPlungerCrown' + side)
        finish.Label = 'Скругление рабочей поверхности'
        finish.Base = (part, top_edges)
        finish.Radius = 0.19
        part.Visibility = False
        c.at(cap, 0.0, 0.0, 0.51)
        c.register(cap, sw, CREAM, FACE, EST,
                   'Cream PCB actuator only; no exterior keycap. Top referenced to w=0 via UiPlungerTop.')
