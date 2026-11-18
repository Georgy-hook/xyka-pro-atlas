"""Paper-millimetre construction for orthographic drawings in the shared ESKD frame.

Geometry is visible OCC linework or a clipped B-rep section. This layer does not
resolve occlusion, estimate dimensions from pixels, or invent section material.
"""

from dataclasses import dataclass, replace
from math import cos, floor, radians, sin

import FreeCAD as App
import numpy as np
import shapely
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.transforms import Affine2D
from shapely.affinity import affine_transform
from shapely.geometry import LineString

from plates_eskd_frame import Sheet


PT = 72.0 / 25.4
# 0.25 mm is valid as s/3…s/2 both at a 0.50 and a 0.70 mm contour.
# Use a 0.70 mm section-trace stroke (s…1.5s for either weight). This is
# mechanical drawing ink; do not change the versioned KiCad/title-block master.
THIN = .25
SECTION_STROKE = .70
SECTION_MARK_LENGTH = 10.0
SECTION_ARROW_INSET = 2.5


@dataclass(frozen=True)
class Mapping:
    scale: float
    dx: float
    dy: float
    rect: tuple

    def uv(self, u, v):
        return self.dx + self.scale * u, self.dy + self.scale * v

    def uvbox(self, bounds):
        return (*self.uv(*bounds[:2]), *self.uv(*bounds[2:]))


def moved_items(items, offsets):
    """Displace copies of the located CAD shapes by their *saved total* global vectors."""
    moved = []
    for item in items:
        delta = np.asarray(offsets[item.name], dtype=float)
        if delta.shape != (3,) or not np.isfinite(delta).all():
            raise ValueError(f'Invalid native translation: {item.name}')
        shape = item.shape.copy()
        shape.translate(App.Vector(*delta))
        moved.append(replace(item, shape=shape))
    return moved


# Opposite or phase-shifted hatching on adjacent members. Glass is shown at a
# shallower angle. These are functional section keys, not material certifications.
_HATCHES = {
    'Housing': (45, 2.8), 'LowerBody': (-45, 2.8), 'Fascia': (-45, 2.0),
    'LightRing': (45, 1.6), 'Battery': (-45, 3.8), 'Pod': (-45, 2.4),
    'PodBody': (-45, 2.4), 'PodLid': (45, 2.0), 'PodScreen': (-45, 1.4),
    'Heater': (45, 2.0), 'HeatGuard': (-45, 1.7), 'MainPCB': (45, 1.6),
    'DisplayPCB': (-45, 1.6), 'Mounts': (-45, 2.3), 'KeyMembrane': (45, 1.6),
    'Glass': (18, 1.6), 'FilmWindow': (-18, 1.6), 'DisplaySeat': (-45, 2.2),
    'OuterKey': (45, 1.8),
}


def _line_parts(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == 'LineString':
        yield np.asarray(geometry.coords)[:, :2]
    elif hasattr(geometry, 'geoms'):
        for child in geometry.geoms:
            yield from _line_parts(child)


def _hatch_segments(area, angle, spacing):
    """Clip real vector lines in *paper space*: spacing independent of detail scale."""
    angle = radians(angle)
    u = np.array((cos(angle), sin(angle)))
    v = np.array((-u[1], u[0]))
    x0, y0, x1, y1 = area.bounds
    corners = np.array(((x0, y0), (x0, y1), (x1, y0), (x1, y1)))
    along = corners @ u
    across = corners @ v
    first = floor(across.min() / spacing) * spacing
    seeds = np.arange(first, across.max() + spacing, spacing)
    rays = [LineString((u * (along.min() - 1) + v * h, u * (along.max() + 1) + v * h))
            for h in seeds]
    for fragment in shapely.intersection(rays, area):
        yield from _line_parts(fragment)


class Drawing(Sheet):
    def view(self, proj, box, scale, *, center=None, weight=.7):
        """Map model (u,v) to paper without scaling to fit. Box clips a detail, not its CAD."""
        x, y, w, h = box
        if w <= 0 or h <= 0 or not np.isfinite(scale) or scale <= 0:
            raise ValueError('Invalid paper viewport or scale')
        if center is None:
            center = (np.array(proj.bounds[:2]) + np.array(proj.bounds[2:])) / 2
        m = Mapping(scale, x + w / 2 - scale * center[0], y + h / 2 - scale * center[1], tuple(box))
        clip = Rectangle((x, y), w, h, transform=self.ax.transData)
        tra = Affine2D().scale(scale).translate(m.dx, m.dy) + self.ax.transData
        for geom, role in proj.hatches:
            area = affine_transform(geom, [scale, 0, 0, scale, m.dx, m.dy])
            if area.is_empty:
                continue
            angle, spacing = _HATCHES.get(role, (45, 2.5))
            hatch = LineCollection(list(_hatch_segments(area, angle, spacing)),
                                   colors='black', linewidths=.25 * PT, zorder=3)
            self.ax.add_collection(hatch)
            hatch.set_clip_path(clip)
        # HLR never supplies hidden edges here. Tangency isn't a heavy contour.
        for paths, thickness, level in ((proj.light, min(weight / 2, .35), 4),
                                        (proj.lines, weight, 5)):
            if paths:
                coll = LineCollection(paths, colors='black', linewidths=thickness * PT,
                                      capstyle='round', joinstyle='round', transform=tra, zorder=level)
                self.ax.add_collection(coll)
                coll.set_clip_path(clip)
        return m

    def _arrow(self, tip, toward_shank, *, length=3.4, half=.54):
        vector = np.array(toward_shank, dtype=float)
        length_v = np.linalg.norm(vector)
        if length_v < 1e-9:
            raise ValueError('Arrow must have a direction')
        vector /= length_v
        n = np.array((-vector[1], vector[0]))
        tip = np.array(tip)
        shape = (tip, tip + length * vector + half * n, tip + length * vector - half * n)
        self.ax.add_patch(Polygon(shape, facecolor='black', linewidth=0, zorder=9))

    def dim_h(self, x0, x1, yref, y, text):
        refs = np.broadcast_to(yref, (2,))
        for x, ref in zip((x0, x1), refs):
            k = 1 if y >= ref else -1
            self.line(((x, ref), (x, y + 1.8 * k)), width=THIN)
        lo, hi = sorted((x0, x1))
        inside = hi - lo >= 8 + 2.4 * len(str(text))
        extra = 0 if inside else 6
        self.line(((lo - extra, y), (hi + extra, y)), width=THIN)
        self._arrow((lo, y), ((1 if inside else -1), 0))
        self._arrow((hi, y), ((-1 if inside else 1), 0))
        if inside:
            self.text((lo + hi) / 2, y + .9, text, h=3.5, ha='center', va='bottom')
        else:
            self.text(hi + 4, y + .9, text, h=3.5, ha='left', va='bottom')

    def dim_v(self, y0, y1, xref, x, text):
        refs = np.broadcast_to(xref, (2,))
        for y, ref in zip((y0, y1), refs):
            k = 1 if x >= ref else -1
            self.line(((ref, y), (x + 1.8 * k, y)), width=THIN)
        lo, hi = sorted((y0, y1))
        inside = hi - lo >= 8 + 2.4 * len(str(text))
        extra = 0 if inside else 6
        self.line(((x, lo - extra), (x, hi + extra)), width=THIN)
        self._arrow((x, lo), (0, (1 if inside else -1)))
        self._arrow((x, hi), (0, (-1 if inside else 1)))
        self.text(x - .8, (lo + hi) / 2 if inside else hi + 4, text, h=3.5, rotation=90,
                  ha='right', va='center' if inside else 'bottom')

    def _shelf(self, target, elbow, text, side, height, dot):
        sign = 1 if side == 'right' else -1
        x, y = elbow
        width = max(8.0, len(str(text)) * height * .75 + 1.5)
        end = x + sign * width
        self.line((target, (x, y), (end, y)), width=THIN)
        if dot:
            self.ax.add_patch(Circle(target, .65, facecolor='black', linewidth=0, zorder=9))
        else:
            self._arrow(target, np.asarray(elbow) - target, length=3.0, half=.45)
        self.text((x + end) / 2, y + .85, str(text), h=height, ha='center', va='bottom')

    def leader(self, target, elbow, number, side='right'):
        self._shelf(target, elbow, number, side, 5.0, True)

    def callout(self, target, elbow, text, side='right'):
        self._shelf(target, elbow, text, side, 3.5, False)

    def axis(self, p, q):
        # Matplotlib path-dash sequence is scaled by linewidth. Specify dashes
        # in final paper mm; use the same phase and width on all sheets.
        self.line((p, q), width=.25, style=(0, (32, 6, 2, 6)))

    def cutline(self, p, q, direction, letter):
        """Two 10 mm open marks; retain the cut locus and the original view clearance.

        p/q locate each end station on the projected cutting plane. The inward
        tip is 7 mm from that station. Lengthen OUTWARD, never into the part.
        Positions are in paper millimetres, independent of the view scale.
        """
        p, q, direction = (np.asarray(v, dtype=float) for v in (p, q, direction))
        tangent = q - p
        tangent /= np.linalg.norm(tangent)
        direction /= np.linalg.norm(direction)
        for point, sign in ((p, 1), (q, -1)):
            inner = point + sign * tangent * 7.0
            outer = inner - sign * tangent * SECTION_MARK_LENGTH
            self.line((outer, inner), width=SECTION_STROKE,
                      gid=f'cut-{ord(letter):04x}-{1 if sign > 0 else 2}')
            at = outer + sign * tangent * SECTION_ARROW_INSET
            tail = at - direction * 9
            self.line((tail, at), width=THIN)
            self._arrow(at, -direction, length=4.0, half=.7)
            self.text(*(tail - sign * tangent * 3), letter, h=5.0, va='center', ha='center')

    def tech(self, lines, x=26, y=49, h=3.5, step=6):
        for j, text in enumerate(lines):
            self.text(x, y - step * j, text, h=h, va='center')
