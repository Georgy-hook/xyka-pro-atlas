"""Embedded 20260305A land patterns. The project-local library is generated too."""

import math

from kicad_art import arc, circle, clip_left, custom_pad, field_polygons, line, native_pad, rect, ring_points


CONTACTS = ((-11.65, 3.67), (-4.37, 2.10), (-1.04, 2.06),
            (2.36, 2.05), (5.38, 2.07), (12.07, 3.51))
EDGE_PADS = ((11.88, 7.15), (11.77, 9.67), (11.76, 12.15), (11.69, 14.82))
SWITCHES = ((-8.9, 6.8), (0.3, 6.8), (9.4, 6.8))
HOLES = ((-7.90, 1.25), (8.25, 1.25))
FPC_CENTER = (4.465, 10.73)


def tact(key):
    parts = [rect((-1.51, -1.925), (1.51, 1.925), 'F.Fab', .08, key + '/case'),
             rect((-1.72, -2.48), (1.72, 2.48), 'F.CrtYd', .05, key + '/court')]
    # Local terminal names describe their positions on the front, NOT pin
    # numbers or a simulation model. No internal contact pairs given by image.
    for col, x in (('L', -.96), ('R', .96)):
        for row, y in (('D', -2.045), ('U', 2.045)):
            name = row + col
            parts.append(native_pad(name, (x, y), (.50, .55), key + '/' + name))
    return parts


def fpc(key):
    parts = [rect((-6.40, -1.28), (6.40, 1.28), 'F.CrtYd', .05, key + '/court')]
    for i in range(15):
        # 15 and 1 are optical end marks on the polyimide, not a verified
        # controller pinout. No plastic connector and no guessed paste stencil.
        parts.append(native_pad(str(15 - i), ((i - 7) * .845, 0), (.416, 2.16), key + f'/{i}'))
    return parts


def contact(i, key):
    u, v = CONTACTS[i]
    ro = 1.50 if i in (3, 4) else 1.58
    radius = 1.365
    silk_r = (ro + 1.41) / 2
    if i in (0, 5):
        # Locally crop the end metal to the visible chamfer; do not pull it
        # inward to satisfy a generic fabrication edge-clearance rule.
        a, b = (((-14.10, 4.35), (-10.60, 0)) if i == 0 else ((11.07, 0), (14.10, 4.09)))
        a = (a[0] - u, a[1] - v)
        b = (b[0] - u, b[1] - v)
        clipped = clip_left(ring_points(radius), a, b, .035)
        parts = [custom_pad('1', [clipped], key + '/face', anchor=.50)]
        # Inverse solution of the offset chamfer / ink-centreline circle
        # intersection. Save just one real circular arc, not a polygonal ring.
        dx, dy = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(dx, dy)
        n = (-dy / norm, dx / norm)
        offset = (a[0] * n[0] + a[1] * n[1] + .5 * (ro - 1.41) + .025) / silk_r
        offset = max(-1., min(1., offset))
        phi = math.atan2(n[1], n[0])
        half = math.acos(offset)

        def pt(t):
            return silk_r * math.cos(t), silk_r * math.sin(t)

        if half < math.pi - 1e-5:
            parts.append(arc(pt(phi - half), pt(phi), pt(phi + half), 'F.SilkS', ro - 1.41, key + '/ink'))
        else:
            parts.append(circle(0, 0, silk_r, 'F.SilkS', ro - 1.41, key + '/ink'))
    else:
        parts = [native_pad('1', (0, 0), (2 * radius, 2 * radius), key + '/face', 'circle'),
                 circle(0, 0, silk_r, 'F.SilkS', ro - 1.41, key + '/ink')]
    parts.append(circle(0, 0, .16, 'User.1', .035, key + '/central_witness'))
    return parts


def edge_pad(key):
    return [native_pad('1', (0, 0), (.81, .81), key + '/pad', 'circle'),
            circle(0, 0, .64, 'F.SilkS', .18, key + '/ink'),
            circle(0, 0, .155, 'User.1', .035, key + '/centre')]


def visible_ring(key):
    # A real exposed annulus on the FRONT plane. No NPTH or barrel asserted.
    ro, ri = .58, .365
    n = 48
    pieces = []
    for start, stop in ((0, 24), (24, 48)):
        ang = [math.tau * i / n for i in range(start, stop + 1)]
        poly = [(r * math.cos(t), r * math.sin(t)) for r, angles in ((ro, ang), (ri, ang[::-1])) for t in angles]
        pieces.append([(x - .48, y) for x, y in poly])
    # The custom copper anchor must lie on the annulus rather than inside its
    # dark centre. Footprint origin remains the optical centre of the eye.
    pad = custom_pad('1', pieces, key + '/face', anchor=.03).replace('(at 0 0)', '(at 0.48 0)', 1)
    return [pad]


def bore(side, key):
    parts = [native_pad('', (0, 0), (1.25, 1.25), key + '/bore', 'circle', 1.25),
             circle(0, 0, .72, 'User.1', .04, key + '/light_wall')]
    if side == 'L':
        parts.append(circle(0, 0, 1.15, 'F.SilkS', .12, key + '/ink'))
    return parts


def perforated(key):
    # Bright sites interrupt the otherwise regular upper-left lattice; bottom
    # row of four is separated. These are NOT 64 new board drills or vias.
    filled = {(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (5, 4)}
    rows = {}
    for row in range(10):
        yy = 5.17 - .451 * row
        rows[yy] = [.23 + .478 * col for col in range(8 if row < 3 else 6) if (row, col) not in filled]
    rows[.22] = [1.27 + .57 * i for i in range(4)]
    polys = field_polygons(rows)
    parts = [custom_pad('1', polys, key + '/perforated')]
    for row, col in sorted(filled):
        parts.append(circle(.23 + .478 * col - 2.16, 5.17 - row * .451 - 3.05,
                            .105, 'User.1', .03, key + f'/bright{row}_{col}'))
    return parts


def devices():
    """ref, pattern id, optical origin, source/limits, function(pattern)"""
    result = []
    for i, uv in enumerate(SWITCHES, 1):
        result.append((f'SW{i}', 'FourTab_Tact_Photo', uv,
                       'IMG_8917/18. Four mechanical terminals; geographic names UL/UR/DL/DR. '
                       'No polarity marking or internal switch pairing established. Courtyard is a photo-based envelope.', tact))
    result.append(('FPC1', 'FlexTail_15Lands', FPC_CENTER,
                   'IMG_8917/18. Solder lands at the flexible-to-rigid bond; printed ends 15/1, functional mapping UNKNOWN.', fpc))
    for i, uv in enumerate(CONTACTS):
        kind = ('LeftEdge' if i == 0 else 'RightEdge' if i == 5 else 'TightInk' if i in (3, 4) else 'Round')
        result.append((f'CT{i+1}', 'Contact_' + kind, uv,
                       'IMG_8917/18. Exposed circular face and central witness; no drilled through-connection inferred.',
                       lambda key, i=i: contact(i, key)))
    for i, uv in enumerate(EDGE_PADS, 1):
        result.append((f'TP{i}', 'EdgeLand_Small', uv,
                       'IMG_8917/18. Four separate small faces; finish and electrical role UNKNOWN.', edge_pad))
    for i, (uv, diameter) in enumerate([((-10.98, 14.85), 1.16), ((-4.59, 14.33), .8)], 1):
        result.append((f'TS{i}', f'SolderWitness_{i}', uv, 'IMG_8917/18. Raised solder; only footprint estimated.',
                       lambda key, d=diameter: [native_pad('1', (0, 0), (d, d), key + '/pad', 'circle')]))
    result.append(('TP5', 'Witness_Annulus', (-6.76, 14.31),
                   'IMG_8917/18. Open-looking centre; backside and drill depth UNKNOWN. Front annulus only.', visible_ring))
    result.append(('MP1', 'Exposed_PerforatedField', (-6.89 + 2.16, 4.12 + 3.05),
                   'IMG_8917/18. Perforated exposed metallic field; placed on F.Cu as a surface proxy. '
                   '64 negative spaces in top foil; plating, composition and penetration UNKNOWN.', perforated))
    for side, uv in zip('LR', HOLES):
        result.append((f'H{1 if side == "L" else 2}', 'Observed_Bore_' + side, uv,
                       'IMG_8917/18. Visible clear bore. NPTH is a mechanical-only drill encoding, not proof of an '
                       'unplated wall. Diam. 1.25 mm estimated; no backside annulus or electrical net invented.',
                       lambda key, s=side: bore(s, key)))
    return result
