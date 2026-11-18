"""Lower stem socket, rear face and mounting interface on the removable base."""

import FreeCAD as App
import Part
import Sketcher

from mech_shapes import (
    AXIS_Y, BACK_PHOTO, EST, EXT, HZ, INK, MAN, MOLD, STEEL, V, WO1, XYKA,
    cut_native, feature, hidden, rotated, scaled, scaled_part, trim, turned,
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




def base_interface(c, lower):
    # The FAQ concerns the internal taper, not a male spigot. The outside face
    # is read independently on the oblique underside, using the visible drum
    # width rather than the foreshortened height of the ellipse.
    source = (BACK_PHOTO + '; XYKA Graphite '
              'https://static.tildacdn.com/tild6266-3464-4239-a239-646538633937/4.webp; '
              'XKAH US gallery 6, https://xkah.us/products/xkah-pro')
    d0 = (c.p['StemMouthD']/2, 'Parameters.StemMouthD / 2')
    d1 = (c.p['StemThroatD']/2, 'Parameters.StemThroatD / 2')
    mouth = (d0[0] + .69, d0[1] + ' + 0.69 mm')
    short_lip = (d0[0] + .48, d0[1] + ' + 0.48 mm')
    h = (c.p['StemSocketL'], 'Parameters.StemSocketL')
    stem = native_lathe(c, lower, 'StemSocket', 'Патрубок · внутренний конус со стороны дна',
                        [(d0, .15), (short_lip, .05), (mouth, .12), (mouth, 1.48),
                         (d0, 2.40), (11.10, h), (d1, h)], 0)
    c.register(stem, lower, STEEL, XYKA + ' FAQ; ' + MAN + ' j; ' + source, EXT,
               'Узкая светлая отбортовка устья. Диаметры внутреннего конуса — сведения для семейства, '
               'не промер конкретной чаши. Тёмные участки не обозначают винты.')
    ratio = 'Parameters.BodyW / 78 mm'
    # Preserve the nominal StemMouth +/- fit without uniformly resizing the
    # retail plate: an independent subtractive cylinder follows the socket OD.
    face = turned([(0., .18), (19.55, .18), (19.74, .31), (19.74, .63), (0., .63)])
    # Four dark tangential sectors in the product photo. A shallow pocket may
    # look black while the bottom is seated; do not draw cross-head screws.
    pts = [(-2.28, 12.94), (2.28, 12.94), (2.28, 15.60), (-2.28, 15.60)]
    seat = Part.Face(Part.makePolygon([V(x, y, 0) for x, y in pts + pts[:1]])).extrude(V(0, 0, 1.8))
    blanks = [rotated(seat, V(), 90*j) for j in range(4)]
    body = scaled(c, lower, 'StemFaceBlank', 'Донный фланец · заготовка с четырьмя окнами',
                  trim(face, blanks), (ratio, ratio, 1), (0, AXIS_Y, 0))
    tool = feature(c, lower, 'Part::Cylinder', 'StemFaceClearance', 'Проход узкой кромки конуса')
    tool.Height = 3.0
    tool.setExpression('Radius', 'Parameters.StemMouthD / 2 + 0.79 mm')
    c.at(tool, 0, AXIS_Y, -1.)
    plate = cut_native(c, lower, 'StemFacePlate', 'Донный светлый фланец · четыре тёмные прорези', body, tool)
    c.register(plate, lower, STEEL, source + '; ' + MAN + ' j', EXT,
               'Виден плоский светлый фланец Ø39.5 с четырьмя тёмными тангенциальными прорезями. '
               'Тип крепления и внутреннее назначение проёмов снаружи не определяются.')
    # An annular lap backs all four face slots and the small circular joint. It
    # does not plug the central stem bore. No individual fastener is visible.
    welt = turned([(19.9, .42), (20.26, .30), (20.84, .04), (27.37, .04),
                   (27.78, .22), (27.84, .63), (27.84, 1.90), (12.18, 1.90),
                   (12.18, .72), (19.90, .72)])
    scaled_part(c, lower, 'FootWelt', 'Тёмный опорный пояс и глухой подхват прорезей',
                welt, INK, source, EXT,
                'Широкий чёрный пояс Ø55.7; под прорезями видна тёмная поверхность, а не случайная полость. '
                'Тип материала по снимкам не определён.', ratios=(ratio, ratio, 1), origin=(0, AXIS_Y, 0))
    # Behind the intermittent skirt ports there is space; the source does
    # not show a straight translucent opening or any specific duct topology.
    base = turned([(12.20, 2.18), (29.85, 2.18), (29.85, 1.76), (30.52, 1.76),
                   (31.40, 2.18), (36.50, 8.10), (37.00, 8.10),
                   (37.00, 9.9), (35, 9.90), (30.6, 3.62), (12.20, 3.62)])
    scaled_part(c, lower, 'BaseReturn', 'Внутренняя отбортовка донного узла', base,
                MOLD, source + '; ' + WO1 + ' Figs.8–10,23', EST,
                'Внутренний несущий пояс: форма оценочная. Не является предполагаемым воздушным коллектором.',
                ratios=(ratio, ratio, HZ), origin=(0, AXIS_Y, 0))
