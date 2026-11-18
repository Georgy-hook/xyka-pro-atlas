"""20260305A folded polyimide tail, visible fingers and printed fan-out.

The same local group follows the lower glass tangent when UiL/UiGlassV change.
Nothing here is a guessed connector, pin assignment or through-board net.
"""

import Part

from display_interface import EST, FACE, LOW
from display_native import P, TIN, V, prism, round_slab, stroke, text_solid


AMBER = (0.87, 0.54, 0.105)
AMBER_LIGHT = (0.94, 0.65, 0.16)
TRACE_COLOR = (0.55, 0.31, 0.085)
FOIL_T = 0.086
PAD_T = 0.045
GLASS_V = 17.4
GLASS_U = 0.15


def _jogged_lead(u, y):
    """Raised silver contact at the film/board transition, in folded-tail frame."""
    yz = [(0, PAD_T), (0.16, PAD_T), (0.39, PAD_T + FOIL_T), (1.66, PAD_T + FOIL_T),
          (1.66, PAD_T + FOIL_T + 0.038), (0.38, PAD_T + FOIL_T + 0.038),
          (0.15, PAD_T + 0.039), (0, PAD_T + 0.039)]
    pts = [V(u - 0.203, y + v, w) for v, w in yz]
    return Part.Face(Part.makePolygon(pts + pts[:1])).extrude(V(0.406, 0, 0))


def _flat(c, group):
    # All geometry below is relative to the glass centreline and lower edge.
    u0, v0 = -2.47 - GLASS_U, 11.45 - GLASS_V
    film = round_slab(u0, v0, PAD_T, 13.90, 2.99, 0.22, FOIL_T)
    c.solid(group, 'UiFlexFoot', 'FPC · плоская янтарная контактная лента', film,
            AMBER_LIGHT, FACE, EST, 'Exposed termination observed. Film laminate thickness ESTIMATE.')
    for i in range(15):
        seq = f'{i + 1:02d}'
        u = -1.45 + i * 0.845 - GLASS_U
        land = round_slab(u - 0.208, 9.65 - GLASS_V, 0, 0.416, 2.16, 0.15, PAD_T)
        c.solid(group, 'UiFlexPad' + seq, f'FPC · площадка пайки {i + 1:02d} слева',
                land, TIN, FACE, EST, 'Observed index left-to-right, not a pin number.')
        lead = _jogged_lead(u, 11.06 - GLASS_V)
        c.solid(group, 'UiFlexFinger' + seq, f'FPC · облуженный палец {i + 1:02d} слева',
                lead, (0.80, 0.78, 0.67), FACE, EST)
        # The fan-out is a short visible printed motif for each finger; stop
        # before the code stripe, never assign a hidden electrical destination.
        y = 12.765 - GLASS_V
        drift = -0.24 if i > 3 else 0.20
        points = [(u, y), (u, y + 0.18), (u + drift * 0.4, y + 0.28),
                  (u + drift, y + 0.34), (u + drift, y + 0.61)]
        conductor = stroke(points, 0.088, 0.013, PAD_T + FOIL_T)
        c.solid(group, 'UiFlexTrace' + seq, f'FPC · фрагмент рисунка {i + 1:02d}',
                conductor, TRACE_COLOR, FACE, EST,
                'Visible copper-toned printed stub. Geometric trace, UNKNOWN pinout.')
    for name, value, u in (('UiFlexEndFifteen', '15', -2.32), ('UiFlexEndOne', '1', 10.97)):
        glyph = text_solid(value, 0.46, 0.012)
        glyph.translate(V(u - GLASS_U, 13.64 - GLASS_V, PAD_T + FOIL_T))
        c.solid(group, name, 'Печать на FPC: ' + value, glyph, TRACE_COLOR, FACE, EST,
                'End marking as seen 8917; obscured internal lot string not transcribed.')
    dots = []
    for base, count in ((-1.45, 5), (9.60, 4)):
        for col in range(count):
            for row in range(3):
                dots.append(Part.makeCylinder(0.05, 0.012,
                            V(base - GLASS_U + col * 0.21 + (row % 2) * 0.085,
                              13.59 - GLASS_V + row * 0.18, PAD_T + FOIL_T)))
    c.solid(group, 'UiFlexPrintDots', 'FPC · точечные метки у краёв',
            Part.makeCompound(dots), TRACE_COLOR, FACE, EST)


def _return_fold(c, group):
    # Two opposed half-cylindrical turns and their tangent flats form an S in
    # v/w section. Analytic concentric arcs retain uniform foil thickness.
    # A generic smooth loft can self-cross on such a tight double return.
    t = FOIL_T / 2
    start, back = 16.51, 16.06              # v coordinates, board frame
    r1, r2 = 0.260, 0.4635
    middle, end = 2 * r1, 2 * (r1 + r2)     # w relative to foil neutral plane
    left, right = -5.68, 7.04

    def point(v, w):
        return V(left - GLASS_U, v - GLASS_V, w)

    def line(a, b):
        return Part.makeLine(point(*a), point(*b))

    def arc(a, through, b):
        return Part.Arc(point(*a), point(*through), point(*b)).toShape()

    path = [
        arc((start, -t), (start + r1 + t, r1), (start, middle + t)),
        line((start, middle + t), (back, middle + t)),
        arc((back, middle + t), (back - r2 + t, middle + r2), (back, end - t)),
        line((back, end - t), (17.50, end - t)),
        line((17.50, end - t), (17.50, end + t)),
        line((17.50, end + t), (back, end + t)),
        arc((back, end + t), (back - r2 - t, middle + r2), (back, middle - t)),
        line((back, middle - t), (start, middle - t)),
        arc((start, middle - t), (start + r1 - t, r1), (start, t)),
        line((start, t), (start, -t)),
    ]
    formed = Part.Face(Part.Wire(path)).extrude(V(right - left, 0, 0))
    shoulder_uv = [(-2.18, 14.44), (10.97, 14.44), (10.97, 14.85),
                   (right, start), (left, start), (left, 16.11), (-2.18, 14.80)]
    shoulder = prism([(u - GLASS_U, v - GLASS_V) for u, v in shoulder_uv], -t, FOIL_T)

    blank = c.doc.addObject('Part::Feature', 'UiFormedFlexBlank')
    group.addObject(blank)
    blank.Label = 'Развёрнутое плечо и два касательных полукруглых гиба'
    blank.Shape = shoulder.fuse(formed).removeSplitter()
    notch = c.doc.addObject('Part::Box', 'UiFlexNotchTool')
    group.addObject(notch)
    notch.Label = 'Инструмент видимой высечки у переднего перегиба'
    notch.Length, notch.Width, notch.Height = 1.62, 0.83, 0.74
    c.at(notch, -2.2 - GLASS_U, 15.21 - GLASS_V, 0.70)
    stamped = c.doc.addObject('Part::Cut', 'UiCutFlex')
    group.addObject(stamped)
    stamped.Label = 'Сформованная лента с высечкой'
    stamped.Base, stamped.Tool = blank, notch

    # Scaling only w keeps both glass and board tangencies in v. Datum is the
    # flat foot's neutral plane, not the board underside or the global origin.
    final = c.doc.addObject('Part::Scale', 'UiFlexReturn')
    final.Label = 'FPC · смещённое плечо и обратный сгиб с высечкой'
    final.Base = stamped
    final.Uniform = False
    z0 = PAD_T + t
    final.setExpression('ZScale', f'({P}UiGlassTop - {z0:g} mm) / {2.2 - z0:g} mm')
    c.at(final, 0, 0, z0)
    c.register(final, group, AMBER, FACE, LOW,
               'Observed folded tongue, traced off-centre wing and notch. Hidden bend radii approximate. '
               'Continuous to the front rim; unseen final LCD bond and pin assignment UNKNOWN.')
    for obj in (blank, notch, stamped):
        obj.Visibility = False


def flex(c, parent):
    group = c.sub(parent, 'UiFoldedFPC', 'FPC · 15 видимых пальцев / сгиб на экран')
    c.at(group, f'{P}UiGlassU * {P}UiW / 28.2 mm', f'{P}UiGlassV * {P}UiL / 50.4 mm', 0)
    _flat(c, group)
    _return_fold(c, group)
