"""Fourteen observed wire jackets. The profiles remain editable in stock FreeCAD.

Frames follow the populated side of the main PCB. Bends are envelopes of a folded
service loop, not a hidden netlist. End planes denote where the image loses sight.
"""

import FreeCAD as App
from math import ceil, dist

from context import text_property, write_table


PARAMS = [
    ('PowerJacket', 2.05, 'IMG_8920/8921; OD relative to through-pad and tinned ends', 0.45),
    ('SignalJacket', 0.87, 'IMG_8914/8920; thin white, red and black jackets', 0.25),
    ('ClearJacket', 0.83, 'IMG_8921; pair next to the blue conductors, translucent', 0.23),
    ('LightJacket', 1.02, 'IMG_8913/8916/8919; four strands at lighting plug', 0.25),
    ('LoopDepth', 11.4, 'AD206911 / 8916 / 8920; service loop folded into side bay, not measured', 3.5),
    ('LowerExitHalfW', 10.8, 'AD206911; spread behind lower curved lip, not physical pin pitch', 3.0),
    ('LightBarDrop', 5.6, 'AD206911, manual overview; LED band below top rim, ESTIMATE', 2.3),
    ('LightBarDepth', 13.1, 'AD206911; depth of green edge in service bay, ESTIMATE', 2.5),
]

COLORS = {'red': (0.84, 0.065, 0.055), 'black': (0.115, 0.12, 0.135),
          'blue': (0.33, 0.49, 0.88), 'white': (0.91, 0.90, 0.86),
          'clear': (0.77, 0.80, 0.81), 'blue.rgb': (0.12, 0.21, 0.72)}

# ID, insulation, nominal OD alias, crest v/L, lateral return lane u/W, return depth / LoopDepth.
# The two blue wires follow adjacent but distinct paths. The two B wires are NOT part of a header.
LOWER = [
    ('B+', 'Bplus', 'red', 'PowerJacket', 0.183, 0.45, 0.98),
    ('B-', 'Bminus', 'black', 'PowerJacket', 0.315, -0.405, 1.01),
    ('F+', 'Fplus', 'blue', 'PowerJacket', 0.470, 0.265, 1.06),
    ('F-', 'Fminus', 'blue', 'PowerJacket', 0.470, 0.044, 1.06),
    ('Clear1', 'ClearOne', 'clear', 'ClearJacket', 0.407, -0.105, 1.01),
    ('Clear2', 'ClearTwo', 'clear', 'ClearJacket', 0.407, -0.058, 1.01),
    ('GND', 'GndWhite', 'white', 'SignalJacket', 0.445, -0.170, 1.00),
    ('KEY+', 'KeyWhite', 'white', 'SignalJacket', 0.474, -0.222, 1.01),
    ('S-', 'Sminus', 'black', 'SignalJacket', 0.508, -0.275, 1.015),
    ('S+', 'Splus', 'red', 'SignalJacket', 0.558, -0.324, 1.02),
]
SIDES = ['white', 'blue.rgb', 'black', 'red']
POWER_PHOTO = 'IMG_8921, IMG_8920, IMG_8914, IMG_AD206911'
LIGHT_PHOTO = 'IMG_8913, IMG_8916, IMG_8919, IMG_AD206911; уточнение владельца'


class Coordinate:
    """Linear dimensional expression plus evaluation at this assembly's nominal values."""

    def __init__(self, c, alias=None, factor=1.0, offset=0.0):
        self.value = offset if alias is None else c.p[alias] * factor + offset
        self.expr = offset if alias is None else f'Parameters.{alias} * {factor:.9f} + ({offset:.8f} mm)'

    @classmethod
    def combination(cls, c, terms, offset=0):
        dim = cls(c, offset=offset)
        dim.value += sum(c.p[alias] * weight for alias, weight in terms)
        dim.expr = ' + '.join([f'({weight:.9f}) * Parameters.{alias}' for alias, weight in terms]
                              + [f'({offset:.8f} mm)'])
        return dim

    @classmethod
    def tween(cls, a, b, weight):
        if a.expr == b.expr:
            return a
        dim = cls(None)
        dim.value = a.value + (b.value-a.value)*weight
        def term(x):
            return x.expr if isinstance(x.expr, str) else f'{x.expr:g} mm'
        dim.expr = f'({1-weight:.9f}) * ({term(a)}) + ({weight:.9f}) * ({term(b)})'
        return dim


def station(c, u, v, wf, wo=0.0):
    return (Coordinate(c, 'BoardW', u), Coordinate(c, 'BoardL', v), Coordinate(c, 'LoopDepth', wf, wo))


def lower_stations(c, anchor, crest, lane, depth, key):
    u, v, z = anchor
    # A compact departure avoids a sharp corner at the solder joint. At the crown
    # the jacket turns into the bay; the return side runs *behind* the components.
    spread = {'S+': 0.02, 'S-': 0.035, 'GND': 0.06, 'KEY+': 0.045,
              'B+': 0.062, 'B-': -0.06}.get(key, 0.045)
    start = station(c, u, v, 0, z)
    terminal = (Coordinate(c, 'LowerExitHalfW', lane / 0.45),
                Coordinate.combination(c, [('BodyH', 0.414), ('PanelBase', -1)]),
                Coordinate(c, 'LoopDepth', depth))
    if key in ('F+', 'F-'):
        # Service loops lift together off the F pads, pass the left shoulder of
        # the buzzer and return on the cavity side, like the pair in IMG_8916.
        edge_drop = 0.15 if key == 'F-' else 0.0
        side_clearance = 0.019 if key == 'F-' else 0.0
        return [start, station(c, u-0.010, v+0.037, 0.39),
                station(c, u-0.011-side_clearance, v+0.117, 0.91-edge_drop),
                station(c, u-0.012-side_clearance, 0.335, 0.94-edge_drop),
                station(c, u, crest-0.049, 0.82-edge_drop),
                station(c, u+0.008, crest, 0.84),
                station(c, u+0.024, crest-0.053, 1.038),
                station(c, lane, 0.198, depth),
                station(c, lane, 0.092, depth), terminal]
    if key in ('GND', 'KEY+', 'S-', 'S+'):
        fan = {'GND': 0.55, 'KEY+': 0.19, 'S-': -0.12, 'S+': -0.47}[key]
        departure = [start]
        if key == 'S-':
            departure.append(station(c, u+0.029, v+0.008, 0.036, z))
        return departure + [station(c, u+0.085, v+0.045, 0.20, 0.4+fan),
                station(c, u*0.37+lane*0.63, v+(crest-v)*0.69, 0.44, fan),
                station(c, lane+spread, crest, 0.68, fan*0.5),
                station(c, lane+spread*0.48, crest-0.06, 0.90*depth),
                station(c, lane, 0.12, depth), terminal]
    return [start,
            station(c, 0.96*u + 0.04*lane, v + (crest-v)*0.22, 0.21, z*0.55),
            station(c, 0.84*u + 0.16*lane + spread/2, v + (crest-v)*0.75, 0.44),
            station(c, 0.53*u + 0.47*lane + spread, crest, 0.69),
            station(c, 0.15*u + 0.85*lane + spread/2, crest-0.045, 0.91*depth),
            station(c, lane, 0.12, depth),
            terminal]


def light_stations(c, anchor, i):
    u, v, w = anchor
    # The order of strand colours is read at the plug; it is not a verified
    # mapping of colour to signal at the other end. No invented hidden connector.
    lane = (i-1.5)*0.053
    def approach(k, x, depth):
        # Interpolate v to the actual top rail, NOT to the board's shorter crest.
        y = Coordinate.combination(c, [('BoardL', v*(1-k)), ('BodyH', k),
                                       ('LightBarDrop', -k), ('PanelBase', -k)])
        return Coordinate(c, 'BoardW', x), y, depth

    return [station(c, u, v, 0, w),
            station(c, u + 0.002+(i-1.5)*0.004, v+0.042, 0.03, w),
            station(c, u + 0.025+(i-1.5)*0.014, v+0.102, 0.13, w),
            approach(0.58, 0.055+lane, Coordinate(c, 'LoopDepth', 0.53 + i*0.018)),
            approach(0.86, 0.115+lane, Coordinate(c, 'LoopDepth', 0.50+i*0.018)),
            approach(1, 0.105+lane, Coordinate.combination(c, [('LightBarDepth', 1), ('MainDepth', -1)]))]


def fill_stations(path, spacing=4.0):
    """Limit free loft spans in the return leg. Monotone cubic station interpolation
    prevents the smooth skin from ballooning into the battery well between profiles.
    Each new centre remains expressed in the same spreadsheet-driven end datums.
    """
    values = [tuple(axis.value for axis in point) for point in path]
    lengths = [dist(a, b) for a, b in zip(values, values[1:])]
    slopes = [tuple((b[k]-a[k])/length for k in range(3))
              for a, b, length in zip(values, values[1:], lengths)]
    tangents = [slopes[0]]
    for left, right in zip(slopes, slopes[1:]):
        tangents.append(tuple(0.0 if a*b <= 0 else 2*a*b/(a+b) for a, b in zip(left, right)))
    tangents.append(slopes[-1])
    dense = [path[0]]
    for i, length in enumerate(lengths):
        divisions = max(1, ceil(length / spacing))
        for j in range(1, divisions):
            t = j / divisions
            result = []
            for k in range(3):
                a, b = path[i][k], path[i+1][k]
                change = b.value - a.value
                if abs(change) < 1e-8:
                    fraction = t
                else:
                    fraction = (3-2*t)*t*t + (t*(1-t)**2 * tangents[i][k]
                                               - (1-t)*t*t * tangents[i+1][k]) * length/change
                result.append(Coordinate.tween(a, b, max(0.0, min(1.0, fraction))))
            dense.append(tuple(result))
        dense.append(path[i+1])
    return dense


def loft(c, parent, name, path, diameter):
    path = fill_stations(path)
    points = [App.Vector(*(dim.value for dim in p)) for p in path]
    directions = []
    for i, p in enumerate(points):
        left = (p - points[i-1]).normalize() if i else App.Vector()
        right = (points[i+1] - p).normalize() if i+1 < len(points) else App.Vector()
        directions.append((left + right).normalize())
    # Parallel transport fixes the circular seam as the sections turn the bight.
    orientation = App.Rotation(App.Vector(0, 0, 1), directions[0])
    sections = []
    for i, (center, direction) in enumerate(zip(points, directions)):
        if i:
            orientation = App.Rotation(directions[i-1], direction).multiply(orientation)
        ring = c.doc.addObject('Part::Circle', f'{name}Section{i:02d}')
        parent.addObject(ring)
        ring.Label = f'{name}  ·  сечение {i+1:02d}'
        ring.Placement = App.Placement(center, orientation)
        ring.setExpression('Radius', 'Parameters.' + diameter + ' / 2')
        c.at(ring, *(dim.expr for dim in path[i]))
        ring.Visibility = False
        sections.append(ring)
    jacket = c.doc.addObject('Part::Loft', 'Wire' + name)
    jacket.Sections = sections
    jacket.Solid = True
    jacket.Ruled = False
    jacket.MaxDegree = 3
    return jacket, sections


def build(c):
    from main_pcb import ANCHORS

    g = c.groups['wires']
    lower = c.sub(g, 'SolderedLoom', '10  •  Раздельная пайка по двум кромкам')
    upper = c.sub(g, 'LightingLoom', '04  •  Подсветка от белой колодки V/R/G/B')
    rows = []

    def make(parent, key, ident, color, diameter, path, source, end):
        obj, sections = loft(c, parent, ident, path, diameter)
        label = key.replace('Clear1', 'Прозрачная 1').replace('Clear2', 'Прозрачная 2')
        obj.Label = f'{label}  ·  {color.split(".")[0]}'
        c.register(obj, parent, COLORS[color], source,
                   'Наличие и цвет: фото + владелец. Объёмная укладка в закрытой кассете: ESTIMATE.', end)
        text_property(obj, 'Contact', key, 'Wire')
        text_property(obj, 'Insulation', color, 'Wire')
        text_property(obj, 'BeyondVisibility', end, 'Wire')
        if color == 'clear' and obj.ViewObject:
            obj.ViewObject.Transparency = 38
        for section in sections:
            section.Visibility = False
        rows.append(dict(contact_or_pin=key, object_id=obj.Name, insulation=color, diameter_parameter=diameter,
                         u_over_w=f'{ANCHORS[key][0]:.6f}', v_over_l=f'{ANCHORS[key][1]:.6f}',
                         w_at_exit_mm=ANCHORS[key][2], evidence=source, hidden_end=end))

    for key, ident, color, diameter, crest, lane, depth in LOWER:
        path = lower_stations(c, ANCHORS[key], crest, lane, depth, key)
        end = 'Трасса обрезана за нижней кромкой сервисного проёма. Скрытая оконцовка не установлена.'
        if key in ('Clear1', 'Clear2', 'S+', 'S-', 'KEY+', 'GND'):
            end += ' Назначение конечного устройства не установлено.'
        make(lower, key, ident, color, diameter, path, POWER_PHOTO, end)
    for i, color in enumerate(SIDES):
        key = f'RGB{i+1}'
        path = light_stations(c, ANCHORS[key], i)
        end = ('До видимой верхней планки подсветки. Порядок жил на скрытом конце, '
               'полярность и напряжение не определены.')
        make(upper, key, f'Light{i+1}', color, 'LightJacket', path, LIGHT_PHOTO, end)
    write_table(c.root / 'WIRE_REGISTER.csv', rows, rows[0].keys())
