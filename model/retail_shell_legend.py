"""Seated legend on the ordinary LOWER receiver, nominal world millimetres.

Not the removable pod, heater face, upper gasket or a flat warning decal.
The US Graphite and Blue replacement-base images show both arcs on the dark
insert. The latch hides the middle of IN…CTION. The regional XYKA cutaway
also shows lettering on the lower land beside the latch. Arc angles are read
clockwise from the hinge (+Y) looking down on the *open base*. On the 1600²
US image the far inner ellipse fits rx=275.8, ry=58.8, cy=592.4 pixels.
Lettering style, occluded strokes, material and depth are reconstructions.
"""

import math

import FreeCAD as App
import Part

from mech_shapes import CY, EXT, bezier, circle, moved, ring, scaled_part

V = App.Vector


SOURCE = ('XKAH US Replacement Base, Graphite/Blue, https://xkah.us/products/xkah-pro-replacement-base ; '
          'XYKA cutaway with pod raised, https://static.tildacdn.com/tild3366-6338-4633-b535-663165313031/1.jpg')
LOWER_DZ = -.28                 # actual inboard land, not the corrected external shell seam
RECESS_RADII = (26.62, 32.10)   # inner, outer
RING_RADII = (26.66, 32.02)
POCKET_DEPTH = .50             # vertical below LOWER_DZ
TOP_SETBACK = .10              # vertical below LOWER_DZ
INK_DEPTH = .050               # representational film; even its top is .05 below the ordinary land
KEEPOUT_MARGIN = .16           # running clearance outside even the reserved tab and pin apertures

# Angular extents of the visible words, not equal-pitch text on a circle.
# One continuous clockwise reading direction: the front text is upside-down
# to an observer at the release button, just as in the two lower-only views.
_WORDS = (('DO', -67.4, -56.7), ('NOT', -49.4, -33.2), ('TOUCH', -26.5, .2),
          ('WHEN', 7.4, 30.8), ('IN', 37.8, 45.), ('USE', 52.1, 66.9),
          ('REFER', 97., 128.), ('TO', 137., 149.), ('INSTRUCTION', 158., 216.5),
          ('MANUAL', 226., 263.5))

# Local redraw of the observed capitals, not a system font. A point is a line
# endpoint; Q takes a control and endpoint, C two controls and endpoint. Each
# contour closes; subsequent contours in a glyph are actual negative space.
# Width is relative to a cap height of 100 before fitting each observed word.
_GLYPHS = {
    'A': (89, '0,0 41,100 59,100 100,0 82,0 72,26 28,26 18,0',
          '34,41 66,41 50,82'),
    'C': (83, '100,75 84,69 Q76,85 55,85 47,85 C25,85 17,75 17,55 17,45 '
          'C17,23 26,15 47,15 56,15 Q78,15 85,32 100,26 Q90,0 57,0 44,0 '
          'C15,0 0,14 0,44 0,56 C0,86 15,100 45,100 57,100 Q89,100 100,75'),
    'D': (85, '0,0 0,100 49,100 C83,100 100,85 100,56 100,44 C100,15 83,0 49,0',
          '17,15 48,15 C72,15 83,24 83,45 83,55 C83,76 72,85 48,85 17,85'),
    'E': (76, '0,0 0,100 100,100 100,85 19,85 19,58 90,58 90,43 19,43 19,15 100,15 100,0'),
    'F': (74, '0,0 0,100 100,100 100,85 20,85 20,56 89,56 89,41 20,41 20,0'),
    'H': (84, '0,0 0,100 18,100 18,58 82,58 82,100 100,100 100,0 82,0 82,43 18,43 18,0'),
    'I': (16, '0,0 0,100 100,100 100,0'),
    'L': (70, '0,100 21,100 21,15 100,15 100,0 0,0'),
    'M': (104, '0,0 0,100 18,100 50,39 82,100 100,100 100,0 85,0 85,73 55,20 45,20 15,73 15,0'),
    'N': (86, '0,0 0,100 17,100 83,24 83,100 100,100 100,0 83,0 17,76 17,0'),
    'O': (91, '46,0 C16,0 0,15 0,44 0,56 C0,85 16,100 46,100 54,100 C84,100 100,85 100,56 '
          '100,44 C100,15 84,0 54,0',
          '46,15 54,15 C74,15 83,24 83,44 83,56 C83,76 74,85 54,85 46,85 '
          'C26,85 17,76 17,56 17,44 C17,24 26,15 46,15'),
    'R': (84, '0,0 0,100 57,100 C84,100 98,90 98,70 C98,54 90,44 73,40 100,0 79,0 '
          '54,37 18,37 18,0',
          '18,52 55,52 Q80,52 80,69 Q80,85 55,85 18,85'),
    'S': (80, '97,76 80,72 Q74,86 50,86 Q21,86 21,72 Q21,62 40,59 62,55 '
          'C87,51 100,43 100,28 C100,9 82,0 51,0 Q11,0 0,25 17,30 Q26,14 51,14 '
          'Q82,14 82,28 Q82,37 63,41 39,45 C15,49 3,56 3,71 C3,89 20,100 50,100 Q86,100 97,76'),
    'T': (84, '0,100 100,100 100,85 59,85 59,0 41,0 41,85 0,85'),
    'U': (84, '0,100 18,100 18,40 Q18,15 49,15 51,15 Q82,15 82,40 82,100 100,100 100,39 '
          'Q100,0 52,0 48,0 Q0,0 0,39'),
    'W': (124, '0,100 14,100 28,23 44,100 56,100 72,23 86,100 100,100 80,0 65,0 '
          '50,72 35,0 20,0'),
}
_TRIANGLE = ('3,5 Q0,5 2,10 47,95 Q50,101 53,95 98,10 Q100,5 97,5',
             '24,20 76,20 50,69')


def _cap(radii, relief):
    """Annular stock with its real sloping top and both existing keep-outs."""
    from retail_shell import parting_mask

    ri, ro = radii
    blank = ring(ro, ri, 24, 0, CY, 30)
    tab = Part.makeBox(10.2 + 2*relief, 5.0 + 2*relief, 26, V(-5.1-relief, 12.1-relief, 29))
    pin = circle(2.03 + relief, 26, 9., 75.4, 29)
    return blank.common(parting_mask(LOWER_DZ)).cut(Part.makeCompound([tab, pin])).removeSplitter()


def _single(shape, label):
    solids = shape.Solids
    if len(solids) != 1 or not solids[0].isValid() or solids[0].Volume <= 0:
        raise ValueError(f'{label}: expected one valid native solid')
    return solids[0]


def receiver_recess():
    """Nominal world cutting solid for the LOWER master, before scaled_part()."""
    cap = _cap(RECESS_RADII, 0.)
    return _single(cap.cut(moved(cap, 0, 0, -POCKET_DEPTH)).removeSplitter(), 'Receiver pocket')


def _relief(distance, full, end):
    t = min(1., max(0., (end - distance) / (end - full)))
    return t*t*(3 - 2*t)


def _outline(data, point):
    tokens = iter(data.replace('Q', 'Q ').replace('C', 'C ').split())

    def vertex(pair):
        x, y = pair.split(',')
        return point(float(x), float(y))

    first = last = vertex(next(tokens))
    edges = []
    for token in tokens:
        if token in ('Q', 'C'):
            controls = [vertex(next(tokens)) for _ in range(2 if token == 'Q' else 3)]
            edges.append(bezier(last, *controls))
            last = controls[-1]
        else:
            end = vertex(token)
            edges.append(Part.makeLine(last, end))
            last = end
    if (last - first).Length > 1e-8:
        edges.append(Part.makeLine(last, first))
    return Part.Wire(edges)


def _stencil(contours, angle, radius, width, height):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)

    def point(x, y):
        u = (x/100 - .5)*width
        r = radius + (y/100 - .5)*height
        return V(u*c + r*s, CY - u*s + r*c, 30)

    wires = [_outline(path, point) for path in contours]
    return Part.makeFace(wires, 'Part::FaceMakerBullseye').Faces[0]


def _stencils():
    radius, height, tracking = 29.35, 2.46, 27.
    for word, start, finish in _WORDS:
        letters = [_GLYPHS[ch] for ch in word]
        length = sum(g[0] for g in letters) + tracking*(len(letters)-1)
        scale = (finish - start) / length  # degrees per artwork unit
        cursor = start
        for advance, *loops in letters:
            angle = cursor + .5*advance*scale
            cursor += (advance + tracking)*scale
            # The unmeasured A4.3 pin guide is offset from the photo. Tuck
            # WHEN inboard locally. At the front keep the complete hidden
            # letters on the narrow supported lip BEHIND the actual tab.
            pin = _relief(abs(angle - 16.65), 4., 11.)
            tab = _relief(abs(angle - 180.), 11., 21.)
            r = radius - 1.26*pin - 1.93*tab
            h = height - .28*pin - 1.32*tab
            w = radius * math.radians(advance * scale) * (1 - .36*tab)
            yield _stencil(loops, angle, r, w, h)
    # Visible opposed pointed outlines, not the central heater warning. The
    # small interior detail is not resolved reliably on the lower-only views.
    for angle in (-81.6, 82.1):
        yield _stencil(_TRIANGLE, angle, radius, 3.72, 3.72)


def _ink(cap):
    skin = moved(cap, 0, 0, INK_DEPTH).cut(cap).removeSplitter()
    faces = list(_stencils())
    punches = Part.makeCompound([f.extrude(V(0, 0, 24)) for f in faces])
    ink = skin.common(punches).removeSplitter()
    # For vertical film on a sloped surface, volume = XY area × Z thickness.
    # This also catches characters getting clipped by the front or rear relief.
    expected = sum(f.Area for f in faces)*INK_DEPTH
    if (len(ink.Solids) != len(faces) or not ink.isValid() or
            abs(ink.Volume - expected) > max(.001, expected*.0005)):
        raise ValueError('Receiver legend lost ink, a counter, or its seating surface')
    return ink


def legend(c, lower):
    """Register (ring, ink) with the lower-shell group; both follow BodyW/D/H.

    Cut receiver_recess() from the nominal LOWER shape before registering it.
    Scaled leaves use baked Part::Feature masters. No font, SVG, raster,
    projection support or Python proxy is needed to recompute/reopen the CAD.
    """
    cap = _cap(RING_RADII, KEEPOUT_MARGIN)
    top = moved(cap, 0, 0, -TOP_SETBACK)
    seat = _single(top.cut(moved(cap, 0, 0, -POCKET_DEPTH)).removeSplitter(), 'Receiver ring')
    film = _ink(top)
    band = scaled_part(c, lower, 'ReceiverLegendRing', 'Тёмное кольцо нижнего гнезда чаши', seat,
                       (.255, .265, .275), SOURCE, EXT,
                       'Нижнее штатное основание. Кольцо утоплено в волнистый посадочный пояс; '
                       'передний зацеп и отверстие штырька свободны. Материал и сечение EST.')
    marks = scaled_part(c, lower, 'ReceiverLegendInk', 'Надписи и боковые треугольники нижнего гнезда', film,
                        (.060, .064, .071), SOURCE, EXT,
                        'DO NOT TOUCH WHEN IN USE / REFER TO INSTRUCTION MANUAL. По часовой от петли, '
                        'вершины двух треугольников наружу. Середина IN…CTION закрыта зацепом на фото. '
                        'Тонкий условный слой; способ нанесения, профиль и глубина не измерены.')
    return band, marks
