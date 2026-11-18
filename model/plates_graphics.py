"""A3 millimetre-space layout, searchable type and vector drawing primitives."""

from dataclasses import dataclass

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, PathPatch, Polygon as MplPolygon, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Affine2D
import numpy as np
from shapely.geometry.polygon import orient

matplotlib.rcParams.update({
    'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'pdf.compression': 8,
    'svg.fonttype': 'none', 'svg.hashsalt': 'xkah-a43-v1',
    'hatch.linewidth': 0.46, 'path.simplify': False,
})

W, H = 420, 297
INK, MUTE, TEAL, ORANGE = '#172e35', '#496168', '#006b69', '#924719'
LINE, PALE, STUDIO_BG = '#a8b8b5', '#f2f6f3', '#f1f4f1'
MM = 72 / 25.4  # points per physical mm
SCALES = (35, 30, 25, 20, 16, 12.5, 10, 8, 6, 5, 4, 3, 2.5, 2, 1.5, 1.25,
          1, .8, 2/3, .5, .4, 1/3, .25, .2, .1, .05)


def nstr(v, digits=1):
    return (f'{v:.{digits}f}'.rstrip('0').rstrip('.') if digits else f'{v:.0f}').replace('.', ',')


def est(v, digits=0):
    return f'{nstr(v, digits)} EST'


def ratio(s):
    return f'{nstr(s, 2)}:1' if s >= 1 else f'1:{nstr(1/s, 2)}'


def fit_scale(bounds, box, pad=0, cap=None):
    x0, y0, x1, y1 = bounds
    w, h = box[2:]
    natural = min((w - 2*pad) / max(x1 - x0, .001),
                  (h - 2*pad) / max(y1 - y0, .001))
    if cap:
        natural = min(natural, cap)
    return next((s for s in SCALES if s <= natural + 1e-7), natural)


@dataclass
class Mapping:
    scale: float
    dx: float
    dy: float
    rect: tuple

    def uv(self, u, v):
        return self.dx + self.scale*u, self.dy + self.scale*v

    def uvbox(self, bounds):
        return (*self.uv(*bounds[:2]), *self.uv(*bounds[2:]))


def placement(bounds, box, scale=None, cap=None):
    x, y, w, h = box
    cx, cy = (np.asarray(bounds[:2]) + np.asarray(bounds[2:])) / 2
    s = scale or fit_scale(bounds, box, cap=cap)
    return Mapping(s, x + .5*w - s*cx, y + .5*h - s*cy, box)


def polygons(geometry):
    if geometry.geom_type == 'Polygon':
        yield geometry
    elif hasattr(geometry, 'geoms'):
        for g in geometry.geoms:
            yield from polygons(g)


def polygon_path(geom):
    verts, codes = [], []
    for poly in polygons(geom):
        if poly.is_empty:
            continue
        poly = orient(poly, sign=1)
        for ring in [poly.exterior, *poly.interiors]:
            xy = np.asarray(ring.coords)[:, :2]
            if len(xy) < 4:
                continue
            verts.append(xy)
            code = np.full(len(xy), MplPath.LINETO, dtype=np.uint8)
            code[0], code[-1] = MplPath.MOVETO, MplPath.CLOSEPOLY
            codes.append(code)
    return MplPath(np.vstack(verts), np.concatenate(codes)) if verts else None


class Sheet:
    def __init__(self, number, title, subtitle, section, foot='Размеры в мм  ·  Оценки не являются допусками'):
        self.fig = plt.figure(figsize=(W/25.4, H/25.4), facecolor='white')
        self.ax = self.fig.add_axes([0, 0, 1, 1], xlim=(0, W), ylim=(0, H), aspect='equal')
        self.ax.set_axis_off()
        self.label(14, 287, 'КОНСТРУКТОРСКИЙ АТЛАС', 8.4, color=TEAL, bold=True)
        self.label(75, 287, f'/    {section.upper()}', 8.4, color=MUTE)
        self.label(406, 287, 'XKAH PRO     /     PCB A4.3', 8.4, bold=True, align='right')
        self.label(14, 271.5, title, 24, bold=True)
        self.label(14, 260.5, subtitle, 10.1, color=MUTE)
        self.line([(14, 254.2), (406, 254.2)], lw=.29, color=INK)
        self.line([(14, 16), (406, 16)], lw=.25, color=INK)
        self.label(14, 9.3, 'XKAH  /  PRO', 8.8, bold=True)
        self.label(48, 9.3, 'A4.3   •   ФОТОРЕКОНСТРУКЦИЯ', 7.7, color=MUTE)
        self.label(209, 9.3, foot, 7.8, color=MUTE, align='center')
        self.label(406, 9.3, f'ЛИСТ  {number:02d} / 09', 8.4, bold=True, align='right')

    def label(self, x, y, s, size=9, *, color=INK, bold=False, align='left',
              valign='center', rot=0, mono=False, bg=None, z=11):
        props = dict(ha=align, va=valign, fontsize=size, color=color, zorder=z,
                     rotation=rot, linespacing=1.32,
                     fontfamily='DejaVu Sans Mono' if mono else 'DejaVu Sans',
                     fontweight='bold' if bold else 'normal')
        if bg is not None:
            props['bbox'] = dict(facecolor=bg, edgecolor='none', pad=1.5)
        return self.ax.text(x, y, s, **props)

    def line(self, pts, *, color=LINE, lw=.23, style='solid', z=9):
        xy = np.asarray(pts)
        self.ax.plot(xy[:, 0], xy[:, 1], color=color, lw=lw*MM, ls=style,
                     solid_capstyle='butt', zorder=z)

    def rect(self, x, y, w, h, *, color='none', edge='none', lw=.2, z=0, style='solid'):
        patch = Rectangle((x, y), w, h, facecolor=color, edgecolor=edge,
                          linewidth=lw*MM, linestyle=style, zorder=z)
        self.ax.add_patch(patch)
        return patch

    def caption(self, x, y, id_, name, meta=None):
        self.label(x, y, id_, 8.6, color=TEAL, bold=True, mono=True)
        self.label(x + 12, y, name, 11.6, bold=True)
        if meta:
            self.label(x + 12, y - 6.0, meta, 8.0, color=MUTE)

    def small(self, x, y, s):
        self.label(x, y, s, 8.1, color=TEAL, bold=True)

    def list_entry(self, x, y, num, name, detail=None):
        self.badge(x + 3.5, y, num)
        self.label(x + 12, y, name, 10.5, bold=True)
        if detail:
            self.label(x + 12, y - 6.7, detail, 8.55, color=MUTE, valign='top')

    def badge(self, x, y, text):
        self.ax.add_patch(Circle((x, y), 3.4, facecolor='white', edgecolor=TEAL,
                                 lw=.29*MM, zorder=12))
        self.label(x, y, str(text), 7.5, color=TEAL, bold=True, align='center', mono=True, z=13)

    def leader(self, target, textpos, number):
        tx, ty = target
        x, y = textpos
        k = 1 if tx >= x else -1
        pts = [(x + 3.3*k, y), (x + 6.2*k, y), (tx, ty)]
        self.line(pts, color='white', lw=.55, z=9)
        self.line(pts, color=TEAL, lw=.25, z=10)
        self.ax.add_patch(Circle((tx, ty), .65, facecolor=TEAL, edgecolor='white', lw=.3, zorder=11))
        self.badge(x, y, number)

    def arrow(self, tip, direction, color, length=2.35, half=.65):
        t, d = np.asarray(tip), np.asarray(direction, dtype=float)
        d /= np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        tri = [t, t + d*length + n*half, t + d*length - n*half]
        self.ax.add_patch(MplPolygon(tri, closed=True, facecolor=color, edgecolor='none', zorder=10))

    def dim_h(self, x0, x1, yref, y, text):
        k = 1 if y > yref else -1
        for x in (x0, x1):
            self.line([(x, yref+k), (x, y+k*1.3)], color=ORANGE, lw=.18)
        self.line([(x0, y), (x1, y)], lw=.22, color=ORANGE)
        self.arrow((x0, y), (1, 0), ORANGE)
        self.arrow((x1, y), (-1, 0), ORANGE)
        self.label((x0+x1)/2, y + 2, text, 8.1, color=ORANGE, align='center', valign='bottom', bg='white')

    def dim_v(self, y0, y1, xref, x, text):
        k = 1 if x > xref else -1
        for y in (y0, y1):
            self.line([(xref+k, y), (x+k*1.3, y)], color=ORANGE, lw=.18)
        self.line([(x, y0), (x, y1)], lw=.22, color=ORANGE)
        self.arrow((x, y0), (0, 1), ORANGE)
        self.arrow((x, y1), (0, -1), ORANGE)
        self.label(x - 1.8, (y0+y1)/2, text, 8.1, color=ORANGE, align='center', rot=90, valign='bottom', bg='white')

    def bar(self, x, y, scale, model_mm, color=MUTE):
        width = scale*model_mm
        self.line([(x, y+1.5), (x, y), (x+width, y), (x+width, y+1.5)], color=color, lw=.35)
        self.label(x + width/2, y+2, f'{nstr(model_mm)} мм', 7.2, align='center', color=color, valign='bottom')

    def geometry(self, proj, box, *, bounds=None, scale=None, cap=None, weight=.29, material=False):
        """Draw in model mm; text always remains in paper space. Clip crops, not the native CAD."""
        m = placement(bounds if bounds is not None else proj.bounds, box, scale, cap)
        tra = Affine2D().scale(m.scale).translate(m.dx, m.dy) + self.ax.transData
        clip = Rectangle(box[:2], box[2], box[3], transform=self.ax.transData)
        for geom, color in proj.fills:
            path = polygon_path(geom)
            if path is not None:
                p = PathPatch(path, transform=tra, facecolor=color, linewidth=0, edgecolor='none', zorder=4)
                self.ax.add_patch(p)
                p.set_clip_path(clip)
        hatches = {'Housing': ('#e2eeea', '///'), 'Mounts': ('#ecdfca', '\\\\\\'),
                   'MainPCB': ('#dbe6d5', 'xx'), 'DisplayPCB': ('#dbe6d5', 'xx'),
                   'Heater': ('#ece5df', '\\\\\\'), 'Battery': ('#e3e3eb', '..')}
        for geom, root in proj.hatches:
            path = polygon_path(geom)
            if path is None:
                continue
            face, pattern = hatches.get(root, ('#e3e7e4', '//'))
            p = PathPatch(path, transform=tra, facecolor=face, edgecolor='#647975',
                          linewidth=.22*MM, hatch=pattern, zorder=5)
            self.ax.add_patch(p)
            p.set_clip_path(clip)
        for group, color, stroke, z in [(proj.light, '#788b8b', weight*.53, 6),
                                        (proj.lines, '#263a3f', weight, 7)]:
            if not group:
                continue
            coll = LineCollection(group, colors=color, linewidths=stroke*MM,
                                  capstyle='round', joinstyle='round', transform=tra, zorder=z)
            self.ax.add_collection(coll)
            coll.set_clip_path(clip)
        return m

    def image(self, rendered, box):
        u0, v0, u1, v1 = rendered.extent
        x, y, w, h = box
        s = min(w/(u1-u0), h/(v1-v0))
        ww, hh = (u1-u0)*s, (v1-v0)*s
        x += (w-ww)/2
        y += (h-hh)/2
        self.ax.imshow(np.asarray(rendered.image), extent=(x, x+ww, y, y+hh),
                       origin='upper', interpolation='none', zorder=2, aspect='equal')
        return Mapping(s, x-u0*s, y-v0*s, (x, y, ww, hh))

    def finish(self):
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(0, H)
