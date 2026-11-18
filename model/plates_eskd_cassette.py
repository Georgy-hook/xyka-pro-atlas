"""XKAH.43.130 / .131: installed cartridge and its detachable two-zone facing.

All stations are in the actual display plane (u across, v up, w out), not in
world XZ. Read the aperture wires of the registered mask, not nominal switch
coordinates: the visible key centres and the axes of their feet differ.
"""

from dataclasses import dataclass

import FreeCAD as App
import numpy as np
from matplotlib.patches import Ellipse
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from plates_eskd_geom import Drawing, PT
from plates_scene import board_layers, frame_box
from plates_vector import Projection


_REFERENCE = ('Размеры для справок.', 'Размеры модели оценены по фотографиям.')


def _dim(value):
    return f'{value:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def _frame_shape(shape, frame):
    matrix = np.eye(4)
    matrix[:3, :3] = frame
    pose = App.Placement(App.Vector(), App.Rotation(App.Matrix(*matrix.ravel())))
    copied = shape.copy()
    copied.Placement = pose.multiply(copied.Placement)
    return copied


class _Rim:
    """Exact in-plane spans and actual extension-line witness points on a wire."""

    def __init__(self, wire):
        b = wire.optimalBoundingBox(False, False)
        self.l, self.b, self.r, self.t = b.XMin, b.YMin, b.XMax, b.YMax
        self.x, self.y = (self.l + self.r) / 2, (self.b + self.t) / 2
        self.width, self.height = self.r - self.l, self.t - self.b
        # Keep all arc/B-spline endpoints too (a junction can be an extremum).
        self.points = np.array([tuple(p)[:2] for e in wire.Edges
                                for p in e.discretize(Deflection=.002)])

    def witness(self, side, near):
        axis = 0 if side in ('l', 'r') else 1
        delta = np.abs(self.points[:, axis] - getattr(self, side))
        on_edge = self.points[delta <= delta.min() + 1e-5, 1 - axis]
        return (min if near in ('l', 'b') else max)(on_edge)


class _Front:
    def __init__(self, a):
        s = a.scene
        self.frame = s.board_frame('DisplayPCB')
        self.items = list(a.service.film)
        if {i.name for i in self.items} != {'MechServiceCover', 'MechCoverWindow'}:
            raise ValueError('Expected the two registered leaves of MechFrontFilm')
        mask = _frame_shape(s.named['MechServiceCover'].shape, self.frame)
        candidates = [f for f in mask.Faces if len(f.Wires) == 5]
        if not candidates:
            raise ValueError('No mask face with the optical aperture and three key apertures')
        face = max(candidates, key=lambda f: f.CenterOfMass.z)
        outer = face.OuterWire
        self.mask = _Rim(outer)
        self.outline = Polygon(np.array(outer.discretize(Deflection=.006))[:, :2])
        holes = [_Rim(w) for w in face.Wires if not w.isSame(outer)]
        pane_box = frame_box([s.named['MechCoverWindow']], self.frame)
        self.window = min(holes, key=lambda h: np.linalg.norm(
            [h.x - pane_box[:, 0].mean(), h.y - pane_box[:, 1].mean()]))
        w = self.window
        if not np.allclose((w.l, w.b, w.r, w.t), pane_box[:, :2].ravel(), atol=.005):
            raise ValueError('The selected pane is not registered in the optical aperture')
        self.keys = sorted((h for h in holes if h is not w), key=lambda h: h.x)
        self.row = self.keys[1].y
        if len(self.keys) != 3 or any(abs(h.y - self.row) > .01 for h in self.keys):
            raise ValueError('Key apertures do not share the indicated horizontal datum')


@dataclass(frozen=True)
class _CutItem:
    name: str
    shape: object
    root: str


def _section(a, items, frame, depth):
    """Pure section (not the view beyond the plane). All ink is a real OCC cap.

    Do not union distinct, adjoining members. Include the hatch role in the
    derived-cache identity, without editing Item.root or changing any B-rep.
    """
    bodies = []
    for item, role in items:
        low, high = frame_box([item], frame)[:, 2]
        if low < depth < high:
            bodies.append(_CutItem(f'{item.name}:{role}', item.shape, role))
    cut = a.section(bodies, depth, frame)
    lines = []
    for geometry, _ in cut.hatches:
        faces = geometry.geoms if geometry.geom_type == 'MultiPolygon' else (geometry,)
        for face in faces:
            lines.extend(np.asarray(ring.coords) for ring in (face.exterior, *face.interiors))
    if not lines:
        raise ValueError('Empty cut at the indicated station')
    pts = np.concatenate(lines)
    return Projection(lines=lines, hatches=cut.hatches,
                      bounds=(*pts.min(axis=0), *pts.max(axis=0)))


def _oval(d, center, radius, *, visible):
    patch = Ellipse(center, 2 * radius[0], 2 * radius[1], transform=d.ax.transData,
                    facecolor='none', edgecolor='black' if visible else 'none',
                    linewidth=.28 * PT, zorder=6)
    if visible:
        d.ax.add_patch(patch)
    return patch


def _mark_detail(d, mapping, center, radii, letter, elbow, angle, side=1):
    x, y = mapping.uv(*center)
    rx, ry = (mapping.scale * r for r in radii)
    _oval(d, (x, y), (rx, ry), visible=True)
    angle = np.radians(angle)
    start = x + rx * np.cos(angle), y + ry * np.sin(angle)
    ex, ey = elbow
    d.line([start, elbow, (ex + side * 8, ey)], width=.3)
    d.text(ex + side * 4, ey + .9, letter, h=5, ha='center', va='bottom')


def _detail(d, projection, center, radii, location, scale, pen=.5):
    """Clip to the *same ellipse* picked on the parent, not to a guessed outline."""
    rx, ry = (scale * r for r in radii)
    x, y = location
    n = len(d.ax.collections)
    m = d.view(projection, (x - rx, y - ry, 2 * rx, 2 * ry), scale,
               center=center, weight=pen)
    clip = _oval(d, location, (rx, ry), visible=False)
    for artist in list(d.ax.collections)[n:]:
        artist.set_clip_path(clip)
    return m


def _width(d, m, rim, y):
    x0, x1 = (m.uv(x, rim.y)[0] for x in (rim.l, rim.r))
    near = 't' if y > m.uv(rim.x, rim.y)[1] else 'b'
    refs = [m.uv(rim.x, rim.witness(side, near))[1] for side in ('l', 'r')]
    d.dim_h(x0, x1, refs, y, _dim(rim.width))


def _height(d, m, rim, x):
    y0, y1 = (m.uv(rim.x, y)[1] for y in (rim.b, rim.t))
    near = 'r' if x > m.uv(rim.x, rim.y)[0] else 'l'
    refs = [m.uv(rim.witness(side, near), rim.y)[0] for side in ('b', 't')]
    d.dim_v(y0, y1, refs, x, _dim(rim.height))


def _heading(d, x, y, text):
    d.text(x, y, text, h=5, ha='center', va='center')


def _axes(d, m, rim, over=2.5):
    x, y = m.uv(rim.x, rim.y)
    l, b = m.uv(rim.l, rim.b)
    r, t = m.uv(rim.r, rim.t)
    d.axis((x, b - over), (x, t + over))
    d.axis((l - over, y), (r + over, y))


def film(a):
    """Separate removable facing: two registered bodies, no keys, LCD or carrier."""
    from plates_eskd_positions import position_by_id

    f = _Front(a)
    mask, win = f.mask, f.window
    left, middle, right = f.keys
    d = Drawing('XKAH.43.131 СБ', 'Накладка лицевая\nСборочный чертёж', '2:1')
    front = a.line(f.items, f.frame)
    m = d.view(front, (72, 94, 106, 172), 2, center=(mask.x, mask.y), weight=.55)
    l, b = m.uv(mask.l, mask.b)
    r, t = m.uv(mask.r, mask.t)
    cx, row = m.uv(middle.x, f.row)
    _, wy = m.uv(win.x, win.y)
    win_top = m.uv(win.x, win.t)[1]
    # Leave a break at the window-width numeral rather than striking it out.
    d.axis((cx, b - 3), (cx, win_top + 3))
    d.axis((cx, win_top + 16), (cx, t + 3))
    d.axis((m.uv(left.l, f.row)[0] - 3, row), (r + 3, row))
    _width(d, m, mask, t + 12)
    _height(d, m, mask, 42)
    _width(d, m, win, m.uv(win.x, win.t)[1] + 8)
    _height(d, m, win, 62)
    d.dim_v(m.uv(win.x, win.t)[1], t,
            (m.uv(win.witness('t', 'l'), win.t)[0], l), 62, _dim(mask.t - win.t))
    d.dim_v(row, t, (r + 3, r), 187, _dim(mask.t - f.row))

    # А–А is a transverse section seen FROM THE TOP of the facing. The paper
    # horizontal (= u) and principal scale match the parent above exactly.
    u, v, w = f.frame
    transverse = np.stack((u, -w, v))
    members = [(i, 'FilmWindow' if i.name == 'MechCoverWindow' else 'Fascia') for i in f.items]
    cut = _section(a, members, transverse, win.y)
    d.cutline((l - 12, wy), (r + 12, wy), (0, -1), 'А')
    lo, hi = cut.bounds[1], cut.bounds[3]
    midw = (lo + hi) / 2
    sec = d.view(cut, (72, 65, 106, 12), 2, center=(mask.x, midw), weight=.25)
    _heading(d, cx, 84, 'А–А')

    # Enlarge the actual mask/pane butt joint: both faces finish in the same
    # planes. Never draw a stacked cover or scale up the thickness alone.
    seam = (win.r, midw)
    seam_radii = (3.0, 1.45)
    _mark_detail(d, sec, seam, seam_radii, 'В', (181, 81), 40)
    sm = _detail(d, cut, seam, seam_radii, (309, 235), 20, pen=.5)
    _heading(d, 309, 271, 'В (20:1)')
    d.leader(sm.uv(win.r + 1.5, midw), (347, 251), position_by_id('131', 'MechServiceCover', a))
    d.leader(sm.uv(win.r - 1.5, midw), (271, 251), position_by_id('131', 'MechCoverWindow', a),
             side='left')
    d.dim_v(sm.uv(win.r, lo)[1], sm.uv(win.r, hi)[1], 367, 383, _dim(hi - lo))

    # Locations are centres of the actual aperture envelopes, not stem axes
    # or wire centres of mass (the two side contours are asymmetric).
    station = (middle.x, f.row)
    radii = (max(middle.x - left.l, right.r - middle.x) + 2.5, middle.height / 2 + 3)
    _mark_detail(d, m, station, radii, 'Б', (181, 110), -33)
    km = _detail(d, front, station, radii, (309, 146), 4, pen=.55)
    _heading(d, 309, 202, 'Б (4:1)')
    for h in f.keys:
        _axes(d, km, h, 2)
    _width(d, km, left, 183)
    _width(d, km, middle, 190)
    _height(d, km, right, 389)
    _height(d, km, middle, 228)
    for first, second in zip(f.keys, f.keys[1:]):
        refs = [km.uv(k.x, k.b)[1] - 2 for k in (first, second)]
        d.dim_h(km.uv(first.x, f.row)[0], km.uv(second.x, f.row)[0], refs, 94,
                _dim(second.x - first.x))
    d.tech([*_REFERENCE, 'Базы отсчёта — верхняя кромка и продольная ось накладки.',
            'В элементе Б показаны проёмы под клавиши, а не сами клавиши.'])
    return d


def _key_role(i):
    if i.name.startswith('MechOuterKey'):
        return 'OuterKey'
    return {'MechServiceCover': 'FilmMask', 'MechCartridgeFrame': 'CartridgeFrame',
            'UiKeyMembrane': 'KeyMembrane'}.get(i.name, i.root)


def _intervals(region, at, vertical=False):
    """Material intervals, not a merged bbox bridging the bores in a section."""
    x0, y0, x1, y1 = region.bounds
    path = ((at, y0 - 1), (at, y1 + 1)) if vertical else ((x0 - 1, at), (x1 + 1, at))
    result = region.intersection(LineString(path))
    spans = []
    for piece in getattr(result, 'geoms', (result,)):
        if piece.geom_type == 'LineString' and not piece.is_empty and piece.length > 1e-6:
            j = 1 if vertical else 0
            spans.append((piece.bounds[j], piece.bounds[j + 2]))
    return sorted(spans)


def _overlap(caps, middle):
    """Locate the moving slit and the return behind it at the actual cut station."""
    mask = caps['FilmMask']
    carrier = caps['Fascia']
    cap = caps['OuterKey']
    w = (mask.bounds[1] + mask.bounds[3]) / 2
    lip = next(lo for lo, hi in _intervals(mask, w) if lo > middle.x)
    edge = next(hi for lo, hi in _intervals(cap, w) if lo <= middle.x < hi)
    if not edge < lip:
        raise ValueError('No running gap between central key and facing')
    slit = (edge + lip) / 2
    lo, hi = max(_intervals(carrier, slit, vertical=True))
    shelf = (lo + hi) / 2
    throat = next(lo for lo, hi in _intervals(carrier, shelf) if lo <= slit < hi)
    if not middle.x < throat < edge < lip or not shelf < w:
        raise ValueError('Cannot identify the carrier return under the running gap')
    return throat, lip, slit, shelf


def _paths(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == 'LineString':
        if geometry.length > 1e-5:
            yield np.asarray(geometry.coords)
    else:
        for g in getattr(geometry, 'geoms', ()):
            yield from _paths(g)


def _installed_opening(a, front, components, installed):
    """Outline the adjacent opening in thin line, WITH its actual occlusion.

    The locators/weights do not create geometry. Every output stroke is clipped
    FROM the combined installed HLR (including the two finished substrates).
    Never superimpose a part drawn through the fairing. Show only the immediate
    surroundings of the U, not a distracting half-drawn device behind it.
    """
    own = a.line(components, front.frame)
    whole = a.line(installed, front.frame)
    heavy = unary_union([LineString(p) for p in own.lines]).buffer(.016)
    envelope = front.outline.buffer(1.6)
    sharp, thin = [], []
    for p in whole.lines:
        visible = LineString(p).intersection(envelope)
        sharp.extend(_paths(visible.intersection(heavy)))
        thin.extend(_paths(visible.difference(heavy)))
    for p in whole.light:
        thin.extend(_paths(LineString(p).intersection(envelope)))
    pts = np.concatenate([*sharp, *thin])
    return Projection(lines=sharp, light=thin, bounds=(*pts.min(0), *pts.max(0)))


def _profile_dimension(d, m, projection, span, y):
    points = np.concatenate([*projection.lines, *projection.light])
    x0, _, x1, _ = projection.bounds
    refs = [m.uv(x, points[np.abs(points[:, 0] - x) < 1e-4, 1].min())[1] for x in (x0, x1)]
    d.dim_h(m.uv(x0, 0)[0], m.uv(x1, 0)[0], refs, y, _dim(span))


def fascia(a):
    """Installed .130 assembly, not the service state under the removed film."""
    from plates_eskd_positions import position_by_id
    from plates_render import root_anchors

    s = a.scene
    f = _Front(a)
    mask = f.mask
    middle = f.keys[1]
    items = s.by['Fascia']
    u, v, w = f.frame
    side = np.stack((w, v, -u))  # left view at the right of the front view
    across = np.stack((u, w, -v))  # from below; outwards is UP on the section
    bounds = frame_box(items, f.frame)
    center = bounds.mean(axis=0)
    d = Drawing('XKAH.43.130 СБ', 'Кассета лицевая\nСборочный чертёж', '2:1')

    # The relieved ornamental fields are CAD subdivisions of the caps, not
    # openings. Omit only the microfacets on the front; keep their blind seats,
    # the marks and the complete moving caps. The section uses the full solids.
    faced = [i for i in items if not i.name.endswith('Field')]
    adjacent = [s.named[n] for n in ('MechUpperFairing', 'MechNoseBridge', 'MechTopBridge',
                                     'MechLightRing', 'UiBacking', 'UiCell', 'UiRim', 'UiGlass')]
    adjacent.extend(i for root in ('MainPCB', 'DisplayPCB') for i in board_layers(s, root))
    exterior = [*faced, *adjacent]
    front = _installed_opening(a, f, faced, exterior)
    left = a.line(items, side)
    mf = d.view(front, (55, 92, 106, 174), 2, center=center[:2], weight=.55)
    ms = d.view(left, (183, 92, 42, 174), 2, center=(center[2], center[1]), weight=.5)
    l, _ = mf.uv(mask.l, mask.b)
    r, top = mf.uv(mask.r, mask.t)
    _, row = mf.uv(middle.x, f.row)
    d.cutline((l - 13, row), (r + 13, row), (0, 1), 'А')
    _width(d, mf, mask, top + 11)
    # Height and depth of .130 itself, not of the glass behind its window.
    sidepts = np.concatenate([*left.lines, *left.light])
    low, high = left.bounds[1], left.bounds[3]
    witnesses = [sidepts[np.abs(sidepts[:, 1] - val) < 1e-4, 0].min() for val in (low, high)]
    d.dim_v(ms.uv(0, low)[1], ms.uv(0, high)[1],
            [ms.uv(x, y)[0] for x, y in zip(witnesses, (low, high))], 181,
            _dim(bounds[1, 1] - bounds[0, 1]))
    _profile_dimension(d, ms, left, bounds[1, 2] - bounds[0, 2], 80)

    def position(name):
        return position_by_id('130', name, a)

    # Leave the front in its installed state; the .130 balloons follow its
    # own specification, never that of the upper-unit fasteners or bare PCB.
    af = root_anchors(exterior, f.frame, width=620, name_mode=True)
    aside = root_anchors(items, side, width=320, name_mode=True)
    targets = [('MechServiceCover', (149, 238), 'right'),
               ('MechOuterKeyL', (61, 103), 'left'),
               ('MechOuterKeyC', (104, 83), 'right'),
               ('MechOuterKeyR', (152, 104), 'right')]
    for name, elbow, direction in targets:
        d.leader(mf.uv(*af[name]), elbow, position(name), side=direction)
    for name, elbow in (('MechCartridgeFrame', (220, 176)), ('MechDisplaySeatL', (220, 107))):
        d.leader(ms.uv(*aside[name]), elbow, position(name))

    # Adjacent board and silicone are installation *context*. Section the
    # actual substrate, silicone and tactile switch members at this locator;
    # no imaginary electronics, no rear optical path made by omitting the land.
    context = [i for i in s.by['DisplayPCB'] if i.name == 'UiSubstrate'
               or 'UiKeyMembrane' in (i.name, *i.chain) or i.name.startswith(('UiSwitch', 'UiPlunger'))]
    section = _section(a, [(i, _key_role(i)) for i in [*items, *context]], across, -f.row)
    caps = {role: g for g, role in section.hatches}
    throat, lip, slit, land = _overlap(caps, middle)
    x0, w0, x1, w1 = section.bounds
    msec = d.view(section, (236, 77, 174, 43), 4,
                  center=((x0 + x1) / 2, (w0 + w1) / 2), weight=.4)
    _heading(d, 323, 136, 'А–А (4:1)')

    # A true local enlargement of THIS section, including the opaque material
    # under the seam. Locate both ends of the overlap on cut material, not on
    # the ornamental outer edge of a key or a guessed pocket width.
    board = s.named['UiSubstrate']
    board_lo, board_hi = frame_box([board], f.frame)[:, 2]
    zmid = (w1 + board_lo) / 2
    centre = (throat + .51 * (lip - throat), zmid)
    radii = (3.4, (w1 - board_lo) / 2 + .65)
    _mark_detail(d, msec, centre, radii, 'Б', (358, 123), 46)
    detail = _detail(d, section, centre, radii, (323, 208), 20, pen=.5)
    _heading(d, 323, 280, 'Б (20:1)')
    # Dimension on the projected line joining the lip with the actual throat.
    x_throat, y_land = detail.uv(throat, land)
    mask_w = caps['FilmMask'].bounds[3]
    x_lip, y_mask = detail.uv(lip, mask_w)
    d.dim_h(x_throat, x_lip, (y_land, y_mask), 264, _dim(lip - throat))
    target = detail.uv(slit, land)
    d.leader(target, (382, 216), position('MechKeyCarrier'))
    ub, vb = detail.uv(centre[0], (board_lo + board_hi) / 2)
    d.callout((ub, vb), (283, 154), 'Плата', side='left')

    d.tech([*_REFERENCE,
            'Обвод проёма корпуса на главном виде показан тонкими линиями.',
            'Дисплей, плата и кнопочный узел платы показаны для пояснения установки.',
            'В элементе Б уступ подложки перекрывает зазор у клавиши.',
            'В зазорах трёх клавиш по нормали к накладке плата не видна.',
            'Мелкая фактура лицевых поверхностей клавиш не показана.'])
    return d
