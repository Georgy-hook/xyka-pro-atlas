"""XKAH.43.171. Перфорированный щиток со стороны чаши, без отдельного обода."""

import numpy as np
from matplotlib.patches import Ellipse

from plates_eskd_geom import Drawing
from plates_scene import BOTTOM, FRONT
import Part  # FreeCAD is initialized by plates_eskd_geom.


_EPS = 1e-6  # Только для сравнения координат BRep, не допуск детали.


def _dim(value):
    return f'{value:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def _bores(solid):
    """Оба торца одной цилиндрической стенки — внутренние петли плоских граней."""
    mouths = []
    for face in solid.Faces:
        if not isinstance(face.Surface, Part.Plane) or abs(face.Surface.Axis.z) < 1 - _EPS:
            continue
        for wire in face.Wires:
            if wire.isSame(face.OuterWire) or not wire.isClosed():
                continue
            edges = wire.Edges
            if len(edges) == 1 and isinstance(edges[0].Curve, Part.Circle):
                mouths.append(edges[0])

    holes = []
    for face in solid.Faces:
        wall = face.Surface
        if not isinstance(wall, Part.Cylinder) or abs(wall.Axis.z) < 1 - _EPS:
            continue
        ends = [e.Curve.Center for e in face.Edges if any(e.isSame(m) for m in mouths)]
        if len(ends) == 2:
            lo, hi = sorted(ends, key=lambda p: p.z)
            holes.append((lo.x, lo.y, lo.z, hi.z, wall.Radius))
    holes = np.asarray(holes)
    if not len(holes) or not np.allclose(holes[:, 2:], holes[0, 2:], rtol=0, atol=_EPS):
        raise ValueError('Не подтверждены одинаковые сквозные отверстия в дне щитка')
    return holes


def _frames(offsets, radii):
    # Провести диаметральную плоскость по наибольшему числу действительных осей.
    def rank(u):
        distance = abs(offsets @ (u[1], -u[0]))
        return np.count_nonzero(distance < _EPS), np.count_nonzero(distance < radii)

    rays = (p / np.linalg.norm(p) for p in offsets if np.linalg.norm(p) > _EPS)
    u = max(rays, key=rank)
    if rank(u)[0] < 2:
        raise ValueError('Не найден диаметральный ряд отверстий для разреза')
    u = np.r_[u if u[0] >= 0 else -u, 0.]
    eye = np.cross(u, FRONT[1])
    return np.stack((u, eye, BOTTOM[2])), np.stack((u, FRONT[1], eye))


def _edge_detail(d, cut, parent, floor, deck, top):
    """Вынести крайний участок материала до настоящей стенки отверстия."""
    (area, _), = cut.hatches
    islands = sorted(area.geoms, key=lambda g: g.bounds[0])
    edge = islands[-1]
    inner, _, outer, _ = edge.bounds
    # Левая граница овала лежит в просвете последнего рассечённого отверстия.
    uc, zc = (inner + outer) / 2, (floor + top) / 2
    rx = uc - (inner + islands[-2].bounds[2]) / 2
    ry = max(rx / 2, 2 * (top - floor))
    angle = np.linspace(0, 2 * np.pi, 121)
    d.line([parent.uv(uc + rx*np.cos(t), zc + ry*np.sin(t)) for t in angle], width=.3, zorder=7)
    anchor = parent.uv(uc + rx / np.sqrt(2), zc + ry / np.sqrt(2))
    d.line((anchor, (175, 149), (186, 149)), width=.35, zorder=7)
    d.text(180.5, 150, 'Б', h=5, ha='center', va='bottom')

    cx, cy, k = 110, 105, 10
    dx, dy = k * rx, k * ry
    start = len(d.ax.collections)
    m = d.view(cut, (cx-dx, cy-dy, 2*dx, 2*dy), k, center=(uc, zc), weight=.5)
    clip = Ellipse((cx, cy), 2*dx, 2*dy, transform=d.ax.transData)
    for collection in d.ax.collections[start:]:
        collection.set_clip_path(clip)
    d.text(cx, 120, 'Б (10:1)', h=5, ha='center', va='center')

    # Свидетели — вершины заштрихованной грани, а не углы габаритного бокса.
    vertices = np.asarray(edge.exterior.coords)
    def witness(z, extremum):
        return m.uv(extremum(vertices[abs(vertices[:, 1] - z) < _EPS, 0]), z)

    p, q = witness(floor, min), witness(deck, min)
    d.dim_v(p[1], q[1], (p[0], q[0]), cx - dx - 9, _dim(deck - floor))
    p, q = witness(floor, max), witness(top, max)
    d.dim_v(p[1], q[1], (p[0], q[0]), cx + dx + 9, _dim(top - floor))


def guard(a) -> Drawing:
    i = a.scene.named['MechHeatGuard']
    if (i.unit, i.root) != ('UpperUnit', 'Heater'):
        raise ValueError('Щиток должен принадлежать нагревателю верхней части')
    solid, = i.shape.Solids
    holes = _bores(solid)
    rim = max((e.Curve for e in solid.Edges if isinstance(e.Curve, Part.Circle)
               and e.isClosed() and abs(e.Curve.Axis.z) > 1 - _EPS), key=lambda c: c.Radius)
    center, r = np.array(rim.Center), rim.Radius
    if not np.allclose(i.box[:, :2], [center[:2]-r, center[:2]+r], rtol=0, atol=_EPS):
        raise ValueError('Наружная окружность не совпадает с габаритом щитка')
    face, side = _frames(holes[:, :2] - center[:2], holes[:, 4])
    u, depth = face[:2] @ center  # Одна абсцисса для обоих видов; face.v = side.eye.
    plan = a.line([i], face)
    cut = a.section([i], depth, side)
    floor, deck = holes[0, 2:4]
    top = i.box[1, 2]

    d = Drawing('XKAH.43.171', 'Щиток теплозащитный', '2,5:1', paper='A4')
    m = d.view(plan, (35, 155, 148, 122), 2.5, center=(u, depth), weight=.5)
    ms = d.view(cut, (35, 132, 148, 14), m.scale, center=(u, (floor + top) / 2), weight=.5)
    x, y = m.uv(u, depth)
    radius = m.scale * r
    d.axis((x, y-radius-3), (x, y+radius+3))
    d.axis((x-radius-2, y), (x+radius+2, y))
    d.dim_v(y-radius, y+radius, x, 34, '⌀' + _dim(2*r))
    d.cutline((x-radius-10, y), (x+radius+10, y), face[:2] @ -side[2], 'А')
    d.text(x, 149, 'А–А', h=5, ha='center', va='center')

    # Ближайшая к полке реальная окружность: наконечник лежит на её контуре.
    centers = [m.uv(*p) for p in holes[:, :3] @ face[:2].T]
    elbow = np.array((138., 269.))
    hole = np.array(min(centers, key=lambda p: np.linalg.norm(elbow - p)))
    tip = hole + m.scale * holes[0, 4] * (elbow - hole) / np.linalg.norm(elbow - hole)
    d.callout(tip, elbow, f'{len(holes)} сквозных отв. ⌀{_dim(2*holes[0, 4])}')
    _edge_detail(d, cut, ms, floor, deck, top)
    d.tech(['Размеры для справок.',
            'Размеры модели оценены по фотографиям; обмеры не выполнялись.'],
           x=25, y=75, step=6)
    return d
