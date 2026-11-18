"""Removable retail Pro bowl in the INSTALLED orientation (not packing pose).

+Z faces the upper body. The stamped *fixed floor of the cup* is uppermost;
inside it is the removable square-wire sieve. The round-hole lid with four
turned-up ears faces the stem. None of these three is a heater component.
Coordinates and radii are nominal millimetres, not a manufacturing drawing.
"""

import math

import Part

from mech_shapes import (
    ALLOY, AXIS_Y, CY, EXT, MOLD, OPEN_PHOTO, PODS, STEEL, V, WO1, Z,
    circle, cut_native, rotated, scaled, scaled_part, trim, turned,
)
from retail_marks import POD_INK, POD_SOURCE, pod_mark

REGIONAL_CARE = 'https://xyka.pro/manual#clean'
MANUAL = 'XKAH Pro User Manual, https://www.animashop.cz/user/related_files/xkah_user_manual.pdf'
OPEN_SIDE = ('XKAH Pro, gallery 4, '
             'https://cdn.shopify.com/s/files/1/0663/8865/6306/files/'
             '007-_2_f38faec8-17df-42b8-868e-31dc00427d6c.png?v=1779269809')
BASE = 'https://xkah.us/products/xkah-pro-replacement-base'
POD_RATIOS = ('Parameters.PodOD / 42 mm', 'Parameters.PodOD / 42 mm',
              'Parameters.PodH / 23.3 mm')
POD_ORIGIN = (0, AXIS_Y, 'Parameters.BodyH * 0.2855 - Parameters.PodH')


def _cup():
    """Turn the wall and pressed floor together: no solid core and no false chimney.

    US gallery 4 and the XYKA exploded view: three concentric rows of holes
    in valleys separated by rounded/pressed lands, and a wider centre port.
    In the open side projection the angular repeats resolve as about 9°, 15°,
    22.5°. Pitch/radii, press depth and sheet section are not measurements.
    """
    # Outside wall, from the lid lip up to the edge of the heater-facing floor.
    wall = [(19.75, .58), (20.64, .58), (20.78, .75), (20.78, 1.04),
            (20.68, 1.30), (20.38, 1.58), (20.30, 2.40), (20.30, 20.80),
            (20.51, 21.10), (20.86, 21.29), (21., 21.62), (21., 22.04),
            (20.89, 22.27), (20.64, 22.48), (20.10, 22.48)]
    face = [(19.85, 22.40), (17.35, 22.40), (17.04, 22.53), (16.65, 23.12),
            (16.37, 23.30), (15.32, 23.30), (15.04, 23.15), (14.61, 22.57),
            (14.27, 22.40), (11.48, 22.40), (11.15, 22.53), (10.78, 23.08),
            (10.50, 23.24), (9.42, 23.24), (9.12, 23.09), (8.81, 22.56),
            (8.47, 22.40), (6.23, 22.40), (5.94, 22.52), (5.63, 22.97),
            (5.31, 23.10), (4.32, 23.10), (4.06, 22.97), (3.75, 22.65),
            (3.47, 22.58), (2.23, 22.58)]
    # Return along the INSIDE of the same thin stamping. The only centre detail
    # modelled is the open mouth visible in gallery 4, not the patent's tube.
    inside = [(r, z - .68) for r, z in reversed(face) if r <= 19.85]
    profile = wall + face + inside + [(19.62, 21.48), (19.48, 20.78),
                                      (19.48, 2.22), (19.75, 1.58)]
    bores = []
    for radius, count in ((7.40, 16), (13.05, 24), (18.18, 40)):
        for i in range(count):
            t = 2 * math.pi * i / count
            bores.append(circle(.55, 3., radius * math.cos(t), radius * math.sin(t), 21.))
    return trim(turned(profile), bores)


def _lid():
    """Manual p.04 o, corrected for the apparent ellipse: 61 in staggered rows.

    Vector plate: ellipse 31.801 x 12.625 pts, individual bores 1.590 x .632
    pts, stagger pitches 3.245 x 1.10 pts. Four small edge turns (not extra
    fasteners). They cap the rolled lip; do not confuse them with the single
    large base-unlock catch on the front of the lower housing.
    """
    radius = 20.95
    blank = turned([(0., 0.), (20.64, 0.), (radius, .22), (radius, .41),
                    (20.80, .58), (0., .58)])
    holes = []
    for row in range(-4, 5):
        count = 9 - abs(row)
        for col in range(count):
            x = (col - (count - 1) / 2) * (2 * radius * 3.245 / 31.801)
            y = row * (2 * radius * 1.10 / 12.625)
            holes.append(circle(.025 * 2 * radius, 2., x, y, -.4))
    lid = trim(blank, holes)
    # A narrow fold of the disk at four positions, curling over the cup lip.
    # Undercut, spring load, shutoff and angular registration on A4.3 unknown.
    section = [(20.59, .36), (20.94, .36), (20.96, .84), (20.96, 1.23),
               (20.77, 1.51), (20.57, 1.67), (20.40, 1.63), (20.46, 1.52),
               (20.83, 1.22), (20.83, .65), (20.73, .58)]
    pts = [V(r, 0, z) for r, z in section]
    arc = Part.Face(Part.makePolygon(pts + pts[:1])).revolve(V(), Z, 8.)
    ears = [rotated(arc, V(), i * 90 - 4) for i in range(4)]
    return lid.multiFuse(ears).removeSplitter()


def _strand(offset):
    """One continuous round strand. Bent tips follow the same dished envelope."""
    radius, flat, rise = 18.45, 15.10, 2.34
    end = math.sqrt(radius**2 - offset**2)
    start = math.sqrt(max(flat**2 - offset**2, 0.))

    def point(x):
        r = math.hypot(x, offset)
        t = max(0., (r - flat) / (radius - flat))
        return V(x, offset, 18.99 + rise * t * t)

    def tangent(x):
        r = math.hypot(x, offset)
        return V(1, 0, 2 * rise * max(0., r - flat) * x / (r * (radius - flat)**2))

    def bend(a, b):
        curve = Part.BSplineCurve()
        curve.interpolate(Points=[point(a + (b - a) * i / 5) for i in range(6)],
                          InitialTangent=tangent(a), FinalTangent=tangent(b))
        return curve.toShape()

    edges = [bend(-end, -start)]
    if start > 0:
        edges.append(Part.makeLine(point(-start), point(start)))
    edges.append(bend(start, end))
    profile = Part.Wire([Part.makeCircle(.195, point(-end), tangent(-end))])
    return Part.Wire(edges).makePipeShell([profile], True, False)


def _screen():
    """Free, dished 2-way mesh; true open cells, no fictitious peripheral ring.

    At 800 px in XYKA 2.jpg the insert spans approximately 175 px against
    the cup's 205 px, with about 11 px between wires. The 2.25-mm pitch and
    bent ends follow this projection. Strand diameter, depth and crossings
    are estimates; a joined B-rep does not assert a weld or weave process.
    """
    wires = []
    for i in range(-8, 8):
        across = _strand((i + .5) * 2.25)
        crosswise = rotated(across, V(), 90)
        crosswise.translate(V(0, 0, .23))
        wires.extend((across, crosswise))
    mesh = wires[0].multiFuse(wires[1:]).removeSplitter()
    # Seat the highest tilted wire end against the inside of the stamped floor.
    # The two directions are offset, so a guessed common Z for every end would
    # either penetrate the sheet or leave the entire screen floating.
    top = mesh.optimalBoundingBox(False, False).ZMax
    mesh.translate(V(0, 0, 22.40 - .68 - top))
    return mesh


def _receiver(c, lower):
    """The fixed silicone receiver lives on the LOWER housing, not on the pod.

    Fixed exterior touches the case's actual annular land. The interior
    follows the pod datums: the cap edge rests on an annular shelf at z=0
    in its own frame. The space below the hole field remains open to the
    existing stem; unobserved air ducts and latch drive are not inferred.
    """
    from retail_shell import parting_mask

    outer = turned([(0., 18.70), (12.15, 18.70), (15.35, 17.60), (20.70, 17.60),
                    (22.94, 19.10), (23.65, 20.78), (24.62, 34.10), (25.65, 35.15),
                    (27.40, 36.90), (27.40, 47.0), (0., 47.0)], CY)
    # R=26.62 is the shroud's inboard land aperture. A stock cylinder simply
    # scaled with PodOD would either float inside it or cut into the case.
    outer = outer.common(parting_mask(-2.25)).removeSplitter()
    stock = scaled(c, lower, 'ReceiverExterior', 'Заготовка нижнего ложемента', outer)
    cavity = turned([(0., -35.), (10.60, -35.), (10.60, -1.82), (12.38, -1.22),
                     (17.70, -.77), (18.73, 0.), (21.43, 0.), (21.43, 14.20),
                     (22.05, 16.60), (24.28, 19.15), (25.25, 21.42),
                     (25.31, 22.64), (25.31, 50.), (0., 50.)])
    void = scaled(c, lower, 'ReceiverCavity', 'Выборка и кольцевое дно под перевёрнутую чашу',
                  cavity, POD_RATIOS, POD_ORIGIN)
    receiver = cut_native(c, lower, 'ChamberInsert', 'Ложемент чаши · посадка в нижнем основании',
                          stock, void)
    return c.register(receiver, lower, MOLD, REGIONAL_CARE + '; ' + MANUAL + ' pp.04–05 i; ' + BASE,
                      EXT, 'Силиконовый ложемент нижней части, не вторая табачная чаша. '
                      'Кольцевая опора оставляет свободным перфорированное поле крышки. '
                      'Скрытый профиль и зазоры оценочные, не размеры пресс-формы.')


def chamber(c, lower):
    """Single installed pod. A spare from the box is inventory, not assembly."""
    parent = c.groups['pod']
    _receiver(c, lower)
    cup = _cup()
    pose = dict(ratios=POD_RATIOS, origin=POD_ORIGIN)
    scaled_part(c, parent, 'RemovablePod', 'Съёмная чаша · стенка и штампованное дно',
                cup, STEEL, OPEN_SIDE + '; ' + OPEN_PHOTO + '; ' + PODS, EXT,
                'Нержавеющая сталь по XYKA; марка неизвестна. Ø42 × 23,3 мм — габарит '
                'сменной чаши по продавцу. В установленном виде дно с тремя рядами отверстий '
                'и центральным окном направлено вверх, к щитку. Скрытая трубка не утверждается.', **pose)
    scaled_part(c, parent, 'PodLid', 'Крышка чаши · шахматная перфорация и четыре загиба',
                _lid(), STEEL, MANUAL + ' p.04 o, p.05 c,d; ' + OPEN_PHOTO, EXT,
                '61 сквозное отверстие по рисунку o: по рядам, не по окружностям. '
                'Крышка снизу; четыре малых загиба принадлежат ей, не защёлке основания. '
                'Толщина и посадка кромки приблизительны.', **pose)
    scaled_part(c, parent, 'PodScreen', 'Вынимаемая сетка · внутри у несъёмного дна чаши',
                _screen(), ALLOY, REGIONAL_CARE + '; ' + OPEN_PHOTO + '; ' + WO1 + ' Figs.19–22', EXT,
                'Квадратная сетка видна отдельно от перфорированной крышки; XYKA описывает '
                'её извлечение. В рабочей перевёрнутой чаше сетка у верхнего гофрированного '
                'дна, а не снаружи у нагревателя. Изгиб, калибр проволоки и способ '
                'переплетения не измерены.', **pose)
    mark = pod_mark(cup, width=20.5, center_z=9.8)
    scaled_part(c, parent, 'PodWallMark', 'XYKA · маркировка на стенке съёмной чаши',
                mark, POD_INK, POD_SOURCE + '; https://static.tildacdn.com/'
                'tild3366-6338-4633-b535-663165313031/1.jpg', EXT,
                'Штрихи повторяют поверхность чаши и уезжают вместе с ней. Номинальная '
                'ориентация для показа: азимут не фиксирован; иные слова или номера не добавлены.',
                **pose)


def heater(c):
    """Independent upper heating head. Never register its guard under Pod."""
    from retail_pod_guard import heater as build_upper_head

    return build_upper_head(c)
