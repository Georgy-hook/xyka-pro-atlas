"""Purchased battery and the mating part of the upper housing. World B-reps only."""

from dataclasses import dataclass

import FreeCAD as App
import Part
import numpy as np
import shapely
from matplotlib.patches import Polygon as PaperPolygon
from matplotlib.transforms import Affine2D
from shapely.geometry import Polygon
from shapely.plotting import patch_from_polygon

from plates_eskd_geom import Drawing
from plates_eskd_positions import LEVELS, position_by_id
from plates_scene import FRONT, RIGHT, TOP, camera, combined_box
from plates_vector import Projection


_NOTES = ('Размеры для справок.', 'Размеры модели оценены по фотографиям.')
# .150 is laid on its side. -X is up in ALL its views, including the lettering.
_KEY = camera((0, 1, 0), (-1, 0, 0))
_MARK = camera((0, -1, 0), (-1, 0, 0))
_END = camera((0, 0, -1), (-1, 0, 0))
_CAP = camera((0, 0, 1), (-1, 0, 0))
_SEAT = ('MechPackWell', 'MechPackWellMouth', 'MechPackSeatCarrier', 'MechPackSeatSockets')
_PRINT = 'MechRetailBatteryRu'
# CAD paint is reproduced in positive monochrome; dark and light pigment are
# both black on paper, NOT two contours on either side of every letter stroke.
_FIELDS = ('Carrier', 'SpecPanel', 'WarningPanel', 'SpecInk', 'BrandInk', 'WarningInk',
           'CautionInk', 'OpticalPaper', 'OpticalInk')


def _mm(value):
    return f'{value:.1f}'.removesuffix('.0').replace('.', ',')


def _body(a):
    return [i for i in a.scene.by['Battery'] if not i.name.startswith(_PRINT)
            and i.name != 'MechPackEndInk']


def _leaf(a, name, root):
    item = a.scene.named[name]
    if item.root != root:
        raise ValueError(f'{name} must belong to {root}, not {item.root}')
    return item


def _four(item):
    solids = item.shape.Solids
    if len(solids) != 4:
        raise ValueError(f'{item.name}: expected four separate native bodies')
    return solids


def _centers(item):
    return np.array([tuple(s.CenterOfMass) for s in _four(item)])


def _land(solid, *, upper):
    """Witness within the exposed annular FACE, never at the empty centre."""
    z = solid.BoundBox.ZMax if upper else solid.BoundBox.ZMin
    for face in solid.Faces:
        if (len(face.Wires) != 2 or face.BoundBox.ZLength > 1e-5
                or abs(face.CenterOfMass.z-z) > 1e-5):
            continue
        outer = face.OuterWire
        inner = next(w for w in face.Wires if not w.isSame(outer))
        p = App.Vector(outer.BoundBox.Center.x, (outer.BoundBox.YMax+inner.BoundBox.YMax)/2,
                       face.CenterOfMass.z)
        if face.isInside(p, 1e-6, False):
            return np.array(p)
    raise ValueError('Visible annular land not found in contact B-rep')


def _view(d, proj, at, size, scale, *, center=None, weight=.5):
    w, h = size
    x, y = at
    rect = (x-w/2, y-h/2, w, h)
    m = d.view(proj, rect, scale, center=center, weight=weight)
    l, b = m.uv(*proj.bounds[:2])
    r, t = m.uv(*proj.bounds[2:])
    if l < rect[0] or b < rect[1] or r > rect[0]+w or t > rect[1]+h:
        raise ValueError('Battery projection exceeds its viewport')
    return m


def _view_arrow(d, tail, tip, letter):
    """Direction of sight, not direction from the model toward the observer."""
    u = np.asarray(tip) - tail
    u = u / np.linalg.norm(u)
    n = np.array((-u[1], u[0]))
    p = np.asarray(tip)
    d.line((tail, tip), width=.5)
    d.ax.add_patch(PaperPolygon([p, p-4*u+.7*n, p-4*u-.7*n],
                                facecolor='black', linewidth=0, zorder=9))
    d.text(tail[0], tail[1]+3.5, letter, h=5, ha='center', va='bottom')


def _paint_area(item, frame):
    """True orthographic footprint of a registered, faceted print layer.

    These leaves have polygonal caps on tangent stations and straight edges.
    Their walls are parallel to the viewing rays. Union the *outward* faces
    to suppress the construction seams, retaining counters and optical islands.
    No source photo, re-typesetting, font substitution or decoded payload.
    """
    def ring(wire):
        pts = np.array([tuple(v.Point) for v in wire.OrderedVertexes])
        return pts @ frame[:2].T

    faces = []
    for f in item.shape.Faces:
        if np.asarray(f.normalAt(0, 0)) @ frame[2] > 1e-7:
            outer = f.OuterWire
            faces.append(Polygon(ring(outer), [ring(w) for w in f.Wires if not w.isSame(outer)]))
    surface = shapely.union_all(faces, grid_size=1e-7)
    if surface.is_empty or not surface.is_valid or surface.area <= 0:
        raise ValueError(f'No front-facing native paint for {item.name}')
    return shapely.orient_polygons(surface)


def _paint(d, m, area, *, line=False):
    dx, dy = m.uv(0, 0)
    tr = Affine2D().scale(m.scale).translate(dx, dy) + d.ax.transData
    patch = patch_from_polygon(area, facecolor='white' if line else 'black',
                               edgecolor='black' if line else 'none',
                               linewidth=.25*72/25.4 if line else 0, transform=tr, zorder=6)
    d.ax.add_patch(patch)


def _marking(d, a):
    layers = {f: _leaf(a, _PRINT + f, 'Battery') for f in _FIELDS}
    # The native carrier HLR sets the view datum/extent. Repaint the optical
    # faces opaque so the folds of the substrate do not read as printed bars.
    m = _view(d, a.line([layers['Carrier']], _MARK), (291, 192), (238, 178), 4, weight=.25)
    carrier = _paint_area(layers['Carrier'], _MARK)
    limit = carrier.buffer(.002)
    for name, item in layers.items():
        area = carrier if name == 'Carrier' else _paint_area(item, _MARK)
        if not limit.covers(area):
            raise ValueError(f'{name} outside the native marking field')
        _paint(d, m, area, line=name in ('Carrier', 'SpecPanel', 'WarningPanel', 'OpticalPaper'))
    d.text(291, 285, 'А (4:1)', h=5, ha='center', va='center')


def _outer_points(proj, axis, side):
    p = np.vstack([*proj.lines, *proj.light])
    out = []
    for v in (p[:, axis].min(), p[:, axis].max()):
        edge = p[np.abs(p[:, axis]-v) < 1e-5]
        out.append(edge[np.argmax(side*edge[:, 1-axis])])
    return out


def battery(a):
    """XKAH.43.150: the removable unit, with two separated, indicated views."""
    row = next(p for p in LEVELS['100'] if p.code == '150')
    d = Drawing('XKAH.43.150', row.name, '1:1', paper='A3')
    pack = _body(a)
    env = _leaf(a, 'MechBatteryEnvelope', 'Battery')
    rim = _leaf(a, 'MechPackUsbRim', 'Battery')
    ends = _leaf(a, 'MechPackEndContacts', 'Battery')
    windows = _leaf(a, 'MechPackEndWindows', 'Battery')
    eye_centers = _centers(ends)
    center = (env.box[0]+env.box[1])/2
    center[:2] = eye_centers.mean(axis=0)[:2]
    lo, hi = combined_box([env, _leaf(a, 'MechPackCap', 'Battery')])
    center[2] = (lo[2]+hi[2])/2

    # First angle: the cap is at the LEFT of the object, so its end view is
    # drawn on the RIGHT. Both views share the same projected -X centreline.
    rear = a.line(pack, _KEY)
    baseline = 77
    m = _view(d, rear, (104, baseline), (94, 55), 1, center=_KEY[:2] @ center)
    top = _view(d, a.line(pack, _CAP), (207, baseline), (55, 55), 1, center=_CAP[:2] @ center)
    x0, y0, x1, y1 = (*m.uv(*rear.bounds[:2]), *m.uv(*rear.bounds[2:]))
    d.axis((x0-4, baseline), (x1+2, baseline))
    _view_arrow(d, (171, baseline), (159, baseline), 'Б')

    p, q = [m.uv(*xy) for xy in _outer_points(rear, 0, 1)]
    d.dim_h(p[0], q[0], (p[1], q[1]), y1+11, _mm(hi[2]-lo[2]))
    # Dimension the CYLINDRICAL BODY, not the flat, the ink or the cap lip.
    p, q = [m.uv(*xy) for xy in _outer_points(a.line([env], _KEY), 1, -1)]
    d.dim_v(p[1], q[1], (p[0], q[0]), x0-11, '⌀'+_mm(env.box[1, 0]-env.box[0, 0]))
    usb = _KEY[:2] @ rim.center
    xu, yu = m.uv(*usb)
    d.dim_h(xu, x1, (yu, y0+1), y0-10, _mm(rim.center[2]-lo[2]))
    # Actual lip witness, displaced from the centreline of the aperture.
    lip = max(rim.shape.Vertexes, key=lambda v: (v.Point.x, v.Point.y)).Point
    d.callout(m.uv(*(_KEY[:2] @ np.array(lip))), (155, 59), 'USB-C')
    flat = top.uv(env.box[1, 1], -center[0])
    d.callout(flat, (239, 85), 'Лыска')

    # No housing sockets on the removable end. Paint on that end, where
    # present, is a separate optical skin, not another mechanical feature.
    endproj = a.line(pack, _END)
    end = _view(d, endproj, (92, 204), (126, 123), 2.5, center=_END[:2] @ center)
    end_ink = a.scene.named.get('MechPackEndInk')
    if end_ink is not None:
        _paint(d, end, _paint_area(_leaf(a, end_ink.name, 'Battery'), _END))
    d.text(98, 273, 'Б (2,5:1)', h=5, ha='center', va='center')
    # Anchor on the metal land of one real concentric contact; its centre is
    # recessed. The adjacent row of four small windows is on a separate arc.
    pin = min(_four(ends), key=lambda s: s.CenterOfMass.x)
    d.callout(end.uv(*(_END[:2] @ _land(pin, upper=False))), (58, 264), '4 контакта', side='left')
    win = min(_four(windows), key=lambda s: s.CenterOfMass.x)
    d.callout(end.uv(*(_END[:2] @ np.array(win.CenterOfMass))), (135, 258), '4 окна')
    _view_arrow(d, (167, 196), (154, 196), 'А')
    _marking(d, a)
    d.tech([*_NOTES, 'На виде А показана только наружная маркировка.',
            'Назначение контактов не установлено.'], x=28, y=35, step=7)
    return d


@dataclass(frozen=True)
class _Retained:
    name: str
    shape: object
    root: str
    obj: object
    color: str


def _installed_cut(a, fixed, pack, x):
    """Cut the sleeve, not the sealed purchased block. HLR solves occlusion
    between these retained solids and the *uncut* pack in one scene.
    """
    cut = a.section(fixed, x, RIGHT)
    if not cut.hatches or any(root != 'Housing' for _, root in cut.hatches):
        raise ValueError('No native section material for the fixed housing')
    lo, hi = combined_box(fixed)
    half = Part.makeBox(x-lo[0]+1, hi[1]-lo[1]+2, hi[2]-lo[2]+2, App.Vector(*(lo-1)))
    kept = []
    for item in fixed:
        shape = item.shape.common(half)
        if not shape.isNull() and shape.Solids:
            # Distinct names: Assets caches by names, frame and operation, so
            # a half-sleeve must not share an HLR cache entry with the full one.
            kept.append(_Retained(f'{item.name}:x<={x:.9f}', Part.makeCompound(shape.Solids),
                                  item.root, item.obj, item.color))
    hlr = a.line([*kept, *pack], RIGHT)
    return Projection(lines=hlr.lines, light=hlr.light, hatches=cut.hatches, bounds=hlr.bounds)


def seat(a):
    """XKAH.43.100 СБ, sheet 2: local installed interface, plus the empty well."""
    d = Drawing('XKAH.43.100 СБ', 'Верхний блок. Гнездо аккумулятора', '2:1',
                paper='A3', number=2, sheets=3, form='2a')
    fixed = [_leaf(a, n, 'Housing') for n in _SEAT]
    sockets = _centers(fixed[-1])
    pins = _centers(_leaf(a, 'MechPackEndContacts', 'Battery'))
    # The two pairs for which x is nearest the axis lie IN the cutting plane.
    # Do not substitute the corresponding removable features into the empty well.
    xy = sockets[:, :2].mean(0)
    distances = np.linalg.norm(pins[:, None, :2] - sockets[None, :, :2], axis=2)
    if (distances.min(axis=1).max() > .001 or len(set(distances.argmin(axis=1))) != 4
            or np.count_nonzero(abs(sockets[:, 0]-xy[0]) < .001) != 2):
        raise ValueError('Mating pattern or cut plane does not match the saved battery')
    pack = _body(a)
    lo, hi = combined_box(pack + fixed)
    center = np.r_[xy, (lo[2]+hi[2])/2]
    # Local views of the seat alone, not the outside silhouette of the upper
    # unit. The parent and the first-angle right-hand section share Z and scale.
    front = a.line(fixed+pack, FRONT)
    mf = _view(d, front, (209, 163), (106, 183), 2, center=FRONT[:2] @ center)
    section = _installed_cut(a, fixed, pack, xy[0])
    ms = _view(d, section, (85, 163), (106, 183), 2, center=RIGHT[:2] @ center)
    trace, low = mf.uv(xy[0], lo[2])
    _, high = mf.uv(xy[0], hi[2])
    d.axis((trace, low-2), (trace, high+2))
    d.cutline((trace, low-12), (trace, high+12), (-1, 0), 'В')
    d.text(85, 269, 'В–В (2:1)', h=5, ha='center', va='center')
    d.text(209, 283, 'Посадка аккумулятора (2:1)', h=3.5, ha='center', va='center')
    _view_arrow(d, (238, 270), (238, 255), 'Г')

    # Real material on the left wall; a centroid of the hollow sleeve itself
    # would fall inside pos. 4. Target the hatch between guide bottom and rim.
    area = shapely.union_all([g for g, _ in section.hatches])
    box = fixed[0].box
    mid_z = box[:, 2].mean()
    strip = area.intersection(shapely.box(box[0, 1]-1, mid_z-1, xy[1], mid_z+1))
    if strip.is_empty:
        raise ValueError('No cut guide wall for position 1')
    p = strip.representative_point()
    d.leader(ms.uv(p.x, p.y), (34, 154), position_by_id('100', fixed[0]), side='left')
    env = _leaf(a, 'MechBatteryEnvelope', 'Battery')
    # A point on the opaque projection of the bought-in block, not a cell.
    target = ms.uv(xy[1], env.box[:, 2].mean()+5)
    d.leader(target, (34, 218), position_by_id('100', env), side='left')

    # Sight Г along -Z; +Y is up on paper. Only the physical Housing leaves
    # remain. The four little windows on the *pack's arc* cannot appear here.
    plan = a.line(fixed, TOP)
    mg = _view(d, plan, (341, 165), (130, 130), 2.5, center=xy)
    d.text(341, 260, 'Г (2,5:1)', h=5, ha='center', va='center')
    d.text(341, 250, 'Аккумулятор снят', h=3.5, ha='center', va='center')
    left, right = sockets[sockets[:, 0].argmin()], sockets[sockets[:, 0].argmax()]
    bottom, top = sockets[sockets[:, 1].argmin()], sockets[sockets[:, 1].argmax()]
    lx, ly = mg.uv(*left[:2])
    rx, ry = mg.uv(*right[:2])
    bx, by = mg.uv(*bottom[:2])
    tx, ty = mg.uv(*top[:2])
    for x, y, _ in sockets:
        px, py = mg.uv(x, y)
        d.axis((px-5.2, py), (px+5.2, py))
        d.axis((px, py-5.2), (px, py+5.2))
    d.dim_h(lx, rx, (ly, ry), 124, _mm(right[0]-left[0]))
    d.dim_v(by, ty, (bx, tx), 381, _mm(top[1]-bottom[1]))
    fixed_eye = max(_four(fixed[-1]), key=lambda s: s.CenterOfMass.y)
    d.callout(mg.uv(*_land(fixed_eye, upper=True)[:2]), (321, 232),
              '4 гнездовых контакта', side='left')
    d.tech([*_NOTES, 'Показана посадочная часть верхнего корпуса.',
            'На разрезе аккумулятор показан нерассечённым.'], x=28, y=46, step=7)
    return d
