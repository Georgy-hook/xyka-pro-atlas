"""Editable routed profile, separate round drills and three native extrusions."""
import FreeCAD as App
import Part
import Sketcher

V = App.Vector
ROUTE_SOURCE = 'IMG_8908/8909/8914/8920/8921/AD206911; projected mask edges, not Gerber data'
EST = 'ФОТО / ОЦЕНКА'
CORE = (0.67, 0.58, 0.40)
MASK = (0.145, 0.139, 0.154)


def route_geometry():
    """Counter-clockwise walk, starting at the flat end between B− and B+.

    Circular scallops admit the panel posts on each long side. The small
    rounded crest is *in addition* to the shoulder carrying the four lands.
    Coordinates are the rectified nominal envelope, not a production DXF.
    """
    geometry = []
    p = V(-11.83, 0, 0)

    def line(x, y):
        nonlocal p
        q = V(x, y, 0)
        geometry.append(Part.LineSegment(p, q))
        p = q

    def arc(mx, my, x, y):
        nonlocal p
        q = V(x, y, 0)
        geometry.append(Part.Arc(p, V(mx, my, 0), q))
        p = q

    line(10.28, 0)
    line(14.65, 5.33)
    line(14.65, 12.09)
    arc(13.70, 14.25, 14.65, 16.41)
    line(14.65, 61.74)
    line(14.49, 61.90)
    line(4.25, 61.9)
    arc(3.88, 62.07, 3.74, 62.49)
    line(3.74, 63.70)
    arc(3.5935533906, 64.0535533906, 3.24, 64.2)
    line(-2.08, 64.2)
    arc(-2.4335533906, 64.0535533906, -2.58, 63.70)
    line(-2.58, 62.51)
    arc(-2.73, 62.09, -3.14, 61.90)
    line(-13.78, 61.90)
    # The very top of the left edge is partly finger-occluded in AD.
    line(-14.65, 40.02)
    line(-14.65, 16.24)
    arc(-13.85, 14.43, -14.65, 12.62)
    line(-14.65, 4.22)
    line(-11.83, 0)
    return geometry


def _new(c, parent, kind, name, label):
    obj = c.doc.addObject(kind, name)
    obj.Label = label
    parent.addObject(obj)
    return obj


def _circle(sketch, u, v, diameter, W, L, dia_alias=None):
    i = sketch.addGeometry(Part.Circle(V(u, v, 0), V(0, 0, 1), diameter / 2), False)
    C = Sketcher.Constraint
    for kind, value, expr in (
        ('DistanceX', u, f'Parameters.BoardW * ({u / W:.10f})'),
        ('DistanceY', v, f'Parameters.BoardL * ({v / L:.10f})'),
    ):
        idx = sketch.addConstraint(C(kind, i, 3, value))
        sketch.setExpression(f'Constraints[{idx}]', expr)
    idx = sketch.addConstraint(C('Diameter', i, diameter))
    if dia_alias:
        sketch.setExpression(f'Constraints[{idx}]', f'Parameters.{dia_alias}')


def _extrusion(c, parent, face, name, label, length, z, color, notes):
    obj = _new(c, parent, 'Part::Extrusion', name, label)
    obj.Base = face
    obj.DirMode = 'Custom'
    obj.Dir = V(0, 0, -1)
    obj.Solid = True
    if isinstance(length, str):
        obj.setExpression('LengthFwd', length)
    else:
        obj.LengthFwd = length
    c.at(obj, 0, 0, z)
    c.register(obj, parent, color, ROUTE_SOURCE, EST, notes)
    return obj


def build_profile(c, parent, mechanical, terminations, W, L):
    route = _new(c, parent, 'Sketcher::SketchObject', 'PcRouteMaster', 'Фрезерованный периметр · исходный эскиз 1:1')
    route.addGeometry(route_geometry(), False)
    # Fix each nominal edge; removing its Block in the sketch editor releases it.
    # Unlike a mesh, all scallops and crest corner radii are genuine OCC arcs.
    route.addConstraint([Sketcher.Constraint('Block', i) for i in range(route.GeometryCount)])
    scaled = _new(c, parent, 'Part::Scale', 'PcRouteScale', 'Периметр · масштаб X/Y по BoardW / BoardL')
    scaled.Base = route
    scaled.Uniform = False
    scaled.setExpression('XScale', f'Parameters.BoardW / ({W:g} mm)')
    scaled.setExpression('YScale', f'Parameters.BoardL / ({L:g} mm)')
    scaled.ZScale = 1.0
    holes = _new(c, parent, 'Sketcher::SketchObject', 'PcHoleLocations', '4 отверстия + 10 сверлений под пайку')
    barrels = _new(c, parent, 'Sketcher::SketchObject', 'PcBarrelLoops', '10 пар колец · условная металлизация')
    for u, v in mechanical.values():
        _circle(holes, u, v, c.p['BoardMountDia'], W, L, 'BoardMountDia')
    for u, v, diameter in terminations:
        _circle(holes, u, v, diameter, W, L)
        _circle(barrels, u, v, diameter, W, L)
        _circle(barrels, u, v, diameter - 0.065, W, L)
    outside = _new(c, parent, 'Part::Face', 'PcRoutedArea', 'Фрезерованный контур до сверления')
    outside.Sources = [scaled]
    cutters = _new(c, parent, 'Part::Face', 'PcDrillAreas', 'Сечения сверлений в плоскости маски')
    cutters.Sources = [holes]
    face = _new(c, parent, 'Part::Cut', 'PcBoardProfile', 'Контур с круглыми отверстиями · плоскость маски')
    face.Base = outside
    face.Tool = cutters
    # The *outer* envelope is rescaled before drilling. Bores stay round on edit.
    core = _extrusion(c, parent, face, 'PcLaminateCore', 'Стеклотекстолит · видимый торец',
                      'Parameters.BoardT - 0.04 mm', -.02, CORE,
                      'Светлый торец по фото; фактический материал и стек стеклотекстолита не измерены.')
    _extrusion(c, parent, face, 'PcMaskFace', 'Тёмная паяльная маска · сторона компонентов',
               .02, 0, MASK, 'Внешняя поверхность w=0; толщина покрытия условная.')
    _extrusion(c, parent, face, 'PcMaskRear', 'Обратная сторона · без реконструкции разводки',
               .02, '0.02 mm - Parameters.BoardT', MASK,
               'Обратная разводка не сфотографирована; толщина маски условная.')
    _extrusion(c, parent, barrels, 'PcPlatedWalls', 'Стенки 10 паяных проходов · гипотеза',
               'Parameters.BoardT', 0, (.52, .40, .23),
               'Паяные поверхности видны; внутренняя металлизация и её толщина не подтверждены.')
    c.doc.recompute()
    for work in (route, scaled, holes, barrels, outside, cutters, face):
        work.Visibility = False
    return core
