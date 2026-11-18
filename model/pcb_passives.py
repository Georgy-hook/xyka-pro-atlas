"""Visible two-ended chips and plain discs on the component face (mask at z=0).

Each row is one fitted site, not a repeated footprint pattern: site ID, centre
in original pixels, end-to-end vector, transverse breadth in pixels, finish.
Descriptive IDs stand in for obscured designators. Colours and relief describe
appearance; these are neither electrical values nor production land patterns.
"""

from functools import lru_cache
from math import atan2, degrees, hypot

import FreeCAD as App
import Part


# IMG_8915: original 1152 x 2048, not the rotated inspection crops.
_SITES_15 = (
    # Along D26 / the two tabbed bodies. The separate D27 outline is vacant.
    ('C56', 855, 652, 4, -70, 30, 'honey'),
    ('C37', 823, 586, 38, 2, 16, 'buff'),
    ('BesideU7', 739, 570, 2, -64, 31, 'honey'),
    ('NextToC37', 770, 571, 1, -44, 16, 'buff'),
    ('DiodeSide', 772, 487, 1, -45, 17, 'honey'),
    ('C23', 528, 515, 39, 2, 17, 'buff'),
    ('C22', 525, 477, 65, 3, 29, 'honey'),
    # Two dark longitudinal chips and a transverse tan one at each station.
    ('R42', 261, 567, 0, -39, 15, 'dark'),
    ('R40', 233, 566, 0, -38, 15, 'dark'),
    ('C39', 250, 527, 38, 1, 16, 'tan'),
    ('R43', 262, 709, 1, -39, 15, 'dark'),
    ('R39', 234, 710, 1, -38, 15, 'dark'),
    ('C38', 250, 672, 38, 1, 16, 'honey'),
    # Neighbourhood of C24/C25, the three Y1 devices and the square IC.
    ('C25', 391, 756, 63, 0, 29, 'honey'),
    ('C24', 391, 801, 63, 0, 28, 'ochre'),
    ('R19', 453, 763, 1, -41, 17, 'dark'),
    ('AboveR19', 452, 817, 1, -42, 17, 'honey'),
    ('R35', 357, 863, 39, 2, 16, 'dark'),
    ('R37', 269, 864, 38, 2, 16, 'dark'),
    ('R30', 175, 864, 39, 2, 16, 'dark'),
    ('C18', 524, 863, 39, 0, 17, 'honey'),
    ('R27', 537, 723, 38, 0, 16, 'dark'),
    ('R16', 631, 791, 1, -38, 15, 'dark'),
    ('R14', 609, 791, 1, -37, 14, 'dark'),
    ('C20', 585, 791, 1, -37, 15, 'honey'),
    ('R34', 660, 717, 2, -37, 14, 'dark'),
    ('R13', 758, 814, 2, -55, 22, 'marked'),
    ('C30', 865, 758, 1, -36, 15, 'buff'),
    ('InnerTanByC30', 842, 758, 1, -35, 15, 'tan'),
    ('R18', 819, 758, 2, -35, 14, 'dark'),
    ('R10', 798, 758, 2, -35, 14, 'dark'),
    # By the four-way plug. The tan chip beside R45 is not part of R45.
    ('BesideR45', 347, 1209, 0, -39, 15, 'honey'),
    ('R45', 309, 1197, 36, 0, 14, 'dark'),
    ('R44', 309, 1155, 36, 0, 14, 'dark'),
    ('R36', 309, 1114, 36, 0, 14, 'dark'),
    ('R15', 309, 1069, 36, 0, 14, 'dark'),
    ('R46', 309, 1024, 37, 0, 14, 'dark'),
    ('C10', 349, 1038, 0, -38, 15, 'honey'),
    ('R49', 213, 1072, 1, -38, 14, 'dark'),
    ('R48', 188, 1072, 1, -37, 14, 'dark'),
    ('R47', 137, 1072, 1, -38, 14, 'dark'),
    ('R50', 200, 1026, 37, 1, 14, 'dark'),
    ('C26', 990, 852, 35, 1, 14, 'muted'),
    ('BesideC26', 1021, 874, 2, -40, 14, 'dark'),
    ('R23', 1113, 852, 35, 1, 13, 'dark'),
)

# IMG_8914: MCU/flash edge, then the B/F-end cluster between crossing wires.
# C15, C27, R31 etc. appear in both views; each is instantiated only once.
_SITES_14 = (
    ('C21', 379, 1099, 51, 8, 22, 'honey'),
    ('C15', 422, 942, 41, 7, 17, 'honey'),
    ('FlashOuter', 251, 1137, 12, -51, 21, 'honey'),
    ('C27', 227, 894, 8, -38, 15, 'buff'),
    ('R31', 665, 931, 38, 4, 15, 'dark'),
    ('WireUpper', 820, 918, 38, 4, 14, 'dark'),
    ('WireMiddle', 807, 892, 38, 4, 14, 'shadow'),
    ('R20', 760, 836, 37, 4, 14, 'shadow'),
    ('R32', 800, 1045, 62, 5, 22, 'shadow'),
    ('UnderWhitePair', 806, 1019, 61, 6, 22, 'tan'),
    ('R33', 963, 1012, 41, 3, 16, 'dark'),
    ('R28', 963, 992, 41, 3, 16, 'dark'),
    ('BelowTrio', 1022, 1017, 41, 4, 16, 'dark'),
    ('WireTrioA', 1036, 1055, 3, -44, 16, 'buff'),
    ('WireTrioB', 1007, 1054, 3, -43, 16, 'dark'),
    ('C35', 983, 1052, 1, -43, 16, 'tan'),
    ('BroadMarked', 938, 950, 77, 7, 35, 'marked'),
)

# Horizontal diametric chords in the source image, not drill diameters. The
# apparent ellipses rectify to nearly circular faces. No leads, hole or rim.
_DISCS = (
    ('PcDiscR45', 'R45', '8915', 231, 1184, 56, (0.61, 0.43, 0.30)),
    ('PcDiscC56', 'C56', '8915', 909, 622, 56, (0.81, 0.76, 0.77)),
    ('PcDiscQ12', 'Q12', '8909', 393, 216, 55, (0.78, 0.72, 0.56)),
    ('PcDiscMarked', 'B/F', '8914', 1020, 955, 55, (0.68, 0.64, 0.59)),
)

_COLOUR = {
    'buff': (0.79, 0.69, 0.50), 'honey': (0.74, 0.59, 0.37),
    'tan': (0.68, 0.54, 0.37), 'ochre': (0.65, 0.48, 0.29),
    'muted': (0.55, 0.49, 0.38), 'dark': (0.15, 0.145, 0.14),
    'shadow': (0.185, 0.175, 0.16), 'marked': (0.205, 0.195, 0.18),
}
_ENDS = (0.72, 0.72, 0.68)
_BASE = (0.62, 0.59, 0.54)
_EST = 'ФОТО / ESTIMATE'
_NOTE = 'Видимый габарит и посадка оценочны; номинал, материал и цепь не установлены.'
_V = App.Vector


def _chord(c, project, photo, x, y, dx, dy):
    """Rectify both ends; do not treat source pixels or normalized UV as mm."""
    a = project(photo, x - dx / 2, y - dy / 2)
    b = project(photo, x + dx / 2, y + dy / 2)
    return (b[0] - a[0]) * c.p['BoardW'], (b[1] - a[1]) * c.p['BoardL']


def _prism(points, sweep):
    return Part.Face(Part.makePolygon(points + [points[0]])).extrude(sweep)


@lru_cache(maxsize=256)
def _chip(length, width, coated):
    """Local master: central body, two continuous cap/solder toes, optional top."""
    h = width * (0.49 if coated else 0.79)
    core = length * (0.58 if coated else 0.62)
    a, b, w = core / 2, length / 2, width / 2
    seat = 0.045
    relief = min(0.036, h * 0.13)
    crown = h - relief if coated else h
    bevel = min(0.045, width * 0.06)
    # One extrusion gives the ceramic its small longitudinal shoulder facets.
    section = [(-w, seat + bevel), (-w + bevel, seat), (w - bevel, seat),
               (w, seat + bevel), (w, crown - bevel), (w - bevel, crown),
               (-w + bevel, crown), (-w, crown - bevel)]
    body = _prism([_V(-a, y, z) for y, z in section], _V(core, 0, 0))
    # A low land and sloping toe rise into each plated end. One solid per end;
    # no hidden pad stack, through-board metal or inferred signal connection.
    toe = b + min(0.17, length * 0.10)
    cap = [(a, 0), (toe, 0), (toe, 0.035), (toe - 0.025, 0.050),
           (b + 0.025, h * 0.32), (b, h * 0.55), (b, h - bevel),
           (b - bevel, h), (a, h)]
    ends = Part.makeCompound([
        _prism([_V(sign * x, -w, z) for x, z in cap], _V(0, width, 0))
        for sign in (-1, 1)
    ])
    top = None
    if coated:
        top = Part.makeBox(core, width - 2 * bevel, relief,
                           _V(-a, -w + bevel, crown))
    return body, ends, top


def build_passives(c, root, project, locate, ink):
    """Register editable physical leaves directly below the supplied App::Part."""
    for photo, rows in (('8915', _SITES_15), ('8914', _SITES_14)):
        for site, x, y, dx, dy, breadth, finish in rows:
            uv = project(photo, x, y)
            lx, ly = _chord(c, project, photo, x, y, dx, dy)
            pixels = hypot(dx, dy)
            wx, wy = _chord(c, project, photo, x, y, -dy * breadth / pixels,
                            dx * breadth / pixels)
            length = hypot(lx, ly)
            width = abs(lx * wy - ly * wx) / length
            rotation = degrees(atan2(ly, lx))
            # Pool indistinguishable envelopes at 0.10 / 0.05 mm resolution.
            coated = finish in ('dark', 'shadow', 'marked')
            body, ends, face = _chip(round(length * 10) / 10,
                                     round(width * 20) / 20, coated)
            pieces = [('Body', 'корпус', body, _BASE if coated else _COLOUR[finish]),
                      ('Ends', 'два торца и посадка', ends, _ENDS)]
            if coated:
                pieces.append(('Face', 'тёмная поверхность', face, _COLOUR[finish]))
            source = f'IMG_{photo}.jpg · ({x}, {y}) px'
            for key, label, shape, colour in pieces:
                obj = c.solid(root, 'PcSm' + site + key, f'{site} · {label}',
                              shape, colour, source, _EST, _NOTE)
                locate(obj, *uv, 0, rotation)

    for name, neighbour, photo, x, y, chord, colour in _DISCS:
        diameter = hypot(*_chord(c, project, photo, x, y, chord, 0))
        shape = Part.makeCylinder(diameter / 2, 0.023)
        obj = c.solid(root, name, 'Открытый диск · ' + neighbour, shape, colour,
                      f'IMG_{photo}.jpg · ({x}, {y}) px', _EST,
                      'Сплошной видимый диск без ободка; назначение не определено.')
        locate(obj, *project(photo, x, y))

    # Only unambiguous local silk. Baseline is sampled in original image axes.
    for ref, photo, x, y, dx, dy in (
        ('R45', '8915', 265, 1219, -24, 0),
        ('C18', '8915', 527, 887, -24, 0),
        ('C21', '8914', 430, 1120, -25, -3),
    ):
        axis = _chord(c, project, photo, x, y, dx, dy)
        obj = c.solid(root, 'PcSmInk' + ref, 'Шелкография · ' + ref,
                      ink(ref, 0.45), (0.86, 0.86, 0.80),
                      f'IMG_{photo}.jpg · ({x}, {y}) px', _EST)
        locate(obj, *project(photo, x, y), 0.006, degrees(atan2(axis[1], axis[0])))
