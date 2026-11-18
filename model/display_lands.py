"""Registration landmarks, exposed metal field and actual silkscreen solids."""

import Part

from display_interface import CONTACTS, EDGE_PADS, EST, FACE, TRACE
from display_laminate import hole_placement
from display_native import (
    BRASS, SILK, TIN, V, move_uv, prism, ring, round_slab,
    stroke, text_solid,
)


def _trim_end_pad(shape, index, u, v):
    """The two end pads meet the chamfers; exposed finish stops at the edge."""
    if index not in (1, 6):
        return shape
    outline = [(-10.60, 0), (11.07, 0), (14.10, 4.09),
               (14.10, 10), (-14.10, 10), (-14.10, 4.35)]
    board_side = prism([(x - u, y - v) for x, y in outline], -0.1, 0.3)
    return shape.common(board_side)


def contacts(c, parent):
    for index, (u, v) in enumerate(CONTACTS, 1):
        suffix = f'{index:02d}'
        # Flat annular face with a shallow central eye — the photo does not
        # prove that these six contact centres are through holes.
        disc = _trim_end_pad(ring(1.365, 0.19, 0.057), index, u, v)
        item = c.solid(parent, 'UiContact' + suffix, f'Круглая площадка {index} / назначение UNKNOWN',
                       disc, TIN, TRACE, EST, 'Metal face with visible central witness; not an assigned signal.')
        move_uv(c, item, u, v)
        boss = Part.makeCone(0.19, 0.125, 0.046)
        center = c.solid(parent, 'UiContactEye' + suffix, f'Центр площадки {index}', boss,
                         BRASS, FACE, EST, 'Contrasting central witness; relief and finish estimated.')
        move_uv(c, center, u, v)
        # On the tight central pitch the white outlines nearly touch.  Keep
        # each as an independent printed solid, not overlapping plated discs.
        outer = 1.50 if index in (4, 5) else 1.58
        ink = c.solid(parent, 'UiContactInk' + suffix, f'Кольцо маркировки площадки {index}',
                      _trim_end_pad(ring(outer, 1.41, 0.015), index, u, v), SILK, FACE, EST)
        move_uv(c, ink, u, v)

    # Two visibly different bore mouths: only the left opening has a white halo.
    ink = c.solid(parent, 'UiLeftHoleInk', 'Шелкография у левого отверстия', ring(1.21, 1.09, 0.015),
                  SILK, FACE, EST)
    c.at(ink, *hole_placement('L'), 0)

    for index, (u, v) in enumerate(EDGE_PADS, 1):
        suffix = f'{index:02d}'
        land = c.solid(parent, 'UiEdgePad' + suffix, f'Краевая площадка {index} / UNKNOWN',
                       Part.makeCylinder(0.405, 0.043), TIN, TRACE, EST)
        move_uv(c, land, u, v)
        bump = c.solid(parent, 'UiEdgeEye' + suffix, f'Центр краевой площадки {index}',
                       Part.makeCone(0.19, 0.105, 0.06), BRASS, FACE, EST)
        move_uv(c, bump, u, v, 0.043)
        halo = c.solid(parent, 'UiEdgeInk' + suffix, f'Контур краевой площадки {index}',
                       ring(0.73, 0.55, 0.015), SILK, FACE, EST)
        move_uv(c, halo, u, v)

    eye = c.solid(parent, 'UiWitnessEye', 'Малая открытая площадка слева от FPC / UNKNOWN',
                  ring(0.58, 0.365, 0.043), TIN, TRACE, EST,
                  'Visible dark centre; through-connection and function not established.')
    move_uv(c, eye, -6.76, 14.31)
    for i, (u, v, r) in enumerate(((-10.98, 14.85, 0.58), (-4.59, 14.33, 0.40)), 1):
        # A shallow, slightly domed solder meniscus rather than a free silver ball.
        top = Part.makeSphere(r * 1.4, V(0, 0, -r * 1.03)).common(
            Part.makeCylinder(r, r * 0.52))
        witness = c.solid(parent, f'UiSolderWitness{i}', f'Паяная площадка слева {i} / UNKNOWN', top,
                          TIN, FACE, EST, 'No wire or termination inferred.')
        move_uv(c, witness, u, v)


def perforated_field(c, parent):
    # Measured on the paired rectifications. The upper three rows span more
    # columns; the narrow body ends in a SEPARATE row of four. A bright filled
    # site is not represented as a hole just because it fits the lattice.
    width, length = 4.32, 6.10
    metal = round_slab(0, 0, 0, width, length, 0.075, 0.060)
    # Centre coordinates of the field in its own frame (positive y towards LCD).
    holes = []
    for row in range(10):
        cols = range(8) if row < 3 else range(6)
        for col in cols:
            if (row, col) in {(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (5, 4)}:
                continue
            holes.append((0.23 + 0.478 * col, 5.17 - 0.451 * row))
    holes += [(1.27 + 0.57 * i, 0.22) for i in range(4)]
    tools = [Part.makeCylinder(0.116, 0.10, V(x, y, -0.02)) for x, y in holes]
    metal = metal.cut(Part.makeCompound(tools))
    patch = c.solid(parent, 'UiPerforatedLand', 'Прямоугольная металлическая область · поле отверстий',
                    metal, (0.69, 0.70, 0.66), FACE, EST,
                    f'{len(holes)} resolved open/contrast pits in the irregular row pattern. '
                    'Apertures pass through this visible metal layer ONLY. Board penetration, plating stack and purpose UNKNOWN.')
    move_uv(c, patch, -6.89, 4.12)
    # The uncovered pads in the sparse array are visibly brighter than the empty pits.
    caps = [Part.makeCylinder(0.11, 0.016, V(0.23 + 0.478 * col, 5.17 - 0.451 * row, 0))
            for row, col in ((0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (5, 4))]
    filled = c.solid(parent, 'UiFieldBrightSites', 'Светлые точки в поле перфорации',
                     Part.makeCompound(caps), TIN, FACE, EST,
                     'Bright/filled appearance on 8917/18; electrical path UNKNOWN.')
    move_uv(c, filled, -6.89, 4.12, 0.060)


def via_witnesses(c, parent):
    # Small repeatable, dark-centred sites on 8917. Model the visible masked
    # rims only, not a guessed via stack or a circuit on the reverse.
    arrays = [
        (3.90, 4.83, (0.00, 0.48, 0.94), (0.00, 0.48)),
        (7.82, 3.08, (0.00, 0.47, 0.96), (0.00, 0.39)),
        (13.00, 7.77, (0.00, 0.53), (0.00, 0.42, 0.83)),
        (0.48, 3.12, (0.00, 0.50), (0.00, 0.36)),
        (11.19, 5.99, (0.00, 0.59, 1.10, 1.91, 2.39), (0.00,)),
    ]
    for n, (u, v, cols, rows) in enumerate(arrays, 1):
        eyes = [ring(0.071, 0.037, 0.012, V(x, y, 0)) for x in cols for y in rows]
        field = c.solid(parent, f'UiViaGroup{n:02d}', f'Малые металлизированные контуры {n} / UNKNOWN',
                        Part.makeCompound(eyes), (0.25, 0.23, 0.19), FACE, EST,
                        'Only resolved face witnesses, not implied through-drills, nets or components.')
        move_uv(c, field, u, v)


def silkscreen(c, parent):
    words = text_solid('20260305A', 1.02, 0.016)
    words.rotate(V(), V(0, 0, 1), -90)
    stamp = c.solid(parent, 'UiDateMark', 'Маркировка PCB: 20260305A', words, SILK, FACE,
                    'CONFIRMED inscription / placement ESTIMATE',
                    'Read directly; the string is not proof of date of manufacture.')
    move_uv(c, stamp, -12.54, 13.66)
    # Left boundary witness and sparse corner register for the flex foot. Not a net map.
    ticks = [
        ('UiPadRegistration', 'Штрих у центральных площадок', -6.09, 0.18,
         [(0, 0), (0, 2.63), (0.18, 3.02)]),
        ('UiFlexCornerMark', 'Угловая метка у шлейфа', -2.55, 11.56,
         [(0.63, 0), (0.1, 0), (0, 0.1), (0, 0.65)]),
        ('UiWitnessMark', 'Штрих у паяной площадки', -4.04, 13.88,
         [(0, 0), (0.34, -0.08), (1.32, -0.53)]),
    ]
    for name, label, u, v, pts in ticks:
        mark = c.solid(parent, name, label, stroke(pts, 0.064, 0.013), SILK, FACE, EST)
        move_uv(c, mark, u, v)
    marker = c.solid(parent, 'UiPanelTriangle', 'Белая метка у левого угла LCD',
                     prism([(0, 0), (0.75, 0.17), (0.64, 0.92), (0.38, 0.67)], 0, 0.016),
                     SILK, FACE, EST, 'Fragment of exposed silkscreen; symbol interpretation UNKNOWN.')
    move_uv(c, marker, -13.75, 17.14)
