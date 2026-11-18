"""Two registration sheets per PCB. Paper coordinates are mm, Y up.

Geometry, drill centres, plotted sides and the inspection crop share one map.
Neither a photograph nor a mechanical B-rep is a copper layer.
"""
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from math import ceil, cos, floor, hypot, radians, sin
from statistics import median

from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from matplotlib.patches import Circle, PathPatch, Polygon, Rectangle
from matplotlib.path import Path
from matplotlib.transforms import Affine2D
from plates_eskd_font import drawing_font


PT = 72 / 25.4
INK = '#101010'
THIN = 0.3
SIDES = ('F.Cu', 'B.Cu')


@dataclass(frozen=True)
class Edition:
    key: str
    designation: str
    title: str
    product: str
    photos: str
    limit: str


MAIN = Edition('main', 'XKAH.43.181', 'Плата печатная основная', 'GYS005-S-088-A4.3',
               'IMG_8909, 8914–8916, 8920/21; AD206911',
               'Видна лишь часть проводников наружной стороны. Продолжения под корпусами не восстановлены.')
DISPLAY = Edition('display', 'XKAH.43.191', 'Плата печатная дисплейная', '20260305A',
                  'IMG_8917, IMG_8918; положение в сборке — IMG_8919',
                  'Поле под дисплеем и дальний край скрыты. Геометрия замыкания контура — оценка.')


def num(value, places=3):
    # Coordinates reproduce the file; their decimals do not denote accuracy.
    s = f'{value:.{places}f}'.rstrip('0').rstrip('.') if places else f'{value:.0f}'
    return ('0' if s in ('', '-0') else s).replace('.', ',')


def ratio(scale):
    return f'{num(scale)}:1' if scale >= 1 else f'1:{num(1 / scale)}'


@lru_cache(maxsize=2048)
def width(value, h):
    return drawing_font().metrics(value)[0]*h


def wrap(value, w, h=2.5):
    lines = []
    for word in value.split():
        if lines and width(lines[-1] + ' ' + word, h) <= w:
            lines[-1] += ' ' + word
        else:
            lines.append(word)
    return lines


def text(ax, x, y, value, h=2.5, *, align='left', angle=0, maxw=None, clear=False):
    # Use the same embedded face and measured capital height as the title block.
    face = drawing_font()
    face.check_glyphs(value)
    if maxw is not None and width(value, h) > maxw:
        raise ValueError(f'Insufficient text cell ({maxw:g} mm): {value}')
    return ax.text(x, y, value, ha=align, va='center', fontproperties=face.properties(h),
                   parse_math=False, usetex=False,
                   color=INK, rotation=angle, zorder=12, clip_on=False,
                   bbox={'boxstyle':'square,pad=0.04', 'fc':'white', 'ec':'none'} if clear else None)


def line(ax, points, strong=THIN, *, style='-', z=4):
    xx, yy = zip(*points)
    ax.plot(xx, yy, color=INK, linewidth=strong*PT, linestyle=style,
            solid_capstyle='butt', dash_capstyle='butt', zorder=z)


def box(ax, x, y, w, h, strong=THIN, style='-'):
    ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=INK,
                           linewidth=strong*PT, linestyle=style, zorder=5))


def arrow(ax, x, y, dx, dy, length=2.6, half=0.42):
    # dx,dy is the inward direction from the point towards the base.
    base = x + length*dx, y + length*dy
    tip = [(x, y), (base[0]-dy*half, base[1]+dx*half), (base[0]+dy*half, base[1]-dx*half)]
    ax.add_patch(Polygon(tip, closed=True, facecolor=INK, edgecolor='none', zorder=8))


@dataclass(frozen=True)
class View:
    bounds: tuple
    scale: float
    cx: float
    cy: float
    reverse: bool = False

    @property
    def k(self):
        return -self.scale if self.reverse else self.scale

    def xy(self, x, y):
        x0, y0, x1, y1 = self.bounds
        return self.cx + self.k*(x - (x0 + x1)/2), self.cy - self.scale*(y - (y0 + y1)/2)

    @property
    def transform(self):
        bx, by = self.xy(0, 0)
        return Affine2D.from_values(self.k, 0, 0, -self.scale, bx, by)

    @property
    def paper_matrix(self):
        bx, by = self.xy(0, 0)
        # Native KiCad and SVG are both Y down; paper layout is Y up.
        return f'matrix({self.k:.12g} 0 0 {self.scale:.12g} {bx:.12g} {297-by:.12g})'

    @property
    def rect(self):
        x0, y0, x1, y1 = self.bounds
        a, b = self.xy(x0, y0), self.xy(x1, y1)
        return min(a[0], b[0]), b[1], max(a[0], b[0]), a[1]


def choose_scale(board):
    x0, y0, x1, y1 = board.bounds
    for s in (2.5, 2, 1, 0.5):
        if s*(x1-x0) <= 82 and s*(y1-y0) <= 161.5:
            return s
    raise ValueError('Board exceeds the A3 registration layout')


def mpl_path(d):
    pen = RecordingPen()
    parse_path(d, pen)
    verts, codes = [], []
    for op, points in pen.value:
        if op == 'closePath':
            verts.append((0, 0))
            codes.append(Path.CLOSEPOLY)
        elif op != 'endPath':
            code = {'moveTo': Path.MOVETO, 'lineTo': Path.LINETO,
                    'curveTo': Path.CURVE4, 'qCurveTo': Path.CURVE3}[op]
            verts.extend(points)
            codes.extend([code]*len(points))
    return Path(verts, codes)


def contour(ax, board, view, strong):
    p = PathPatch(mpl_path(board.edge_path), transform=view.transform + ax.transData,
                  facecolor='none', edgecolor=INK, linewidth=strong*PT,
                  capstyle='round', joinstyle='round', zorder=6)
    ax.add_patch(p)


def grid(ax, view):
    """2.5-mm perimeter marks; common front datum retained on reverse."""
    x0, y0, x1, y1 = view.bounds
    ox, oy = view.xy(x0, y1)
    sign = -1 if view.reverse else 1
    tx, ty = view.xy(x1, y0)
    style = (0, (5, 1.5, 0.8, 1.5))
    line(ax, [(ox-1*sign, oy), (tx+5*sign, oy)], 0.25, style=style, z=2)
    line(ax, [(ox, oy-1), (ox, ty+5)], 0.25, style=style, z=2)
    arrow(ax, tx+5*sign, oy, -sign, 0, 2, 0.35)
    arrow(ax, ox, ty+5, 0, -1, 2, 0.35)
    text(ax, tx+7*sign, oy, 'X', align='center')
    text(ax, ox-2.5*sign, ty+5.5, 'Y', align='center')
    text(ax, ox-2.8*sign, oy-3.9, 'O', align='center')
    for j in range(1, floor((x1-x0)/2.5+1e-7)+1):
        x = ox+view.k*j*2.5
        length = 2 if j % 4 == 0 else 1.2
        line(ax, [(x, oy), (x, oy-length)], 0.25)
        if j % 4 == 0:
            text(ax, x, oy-4.6, str(j*5//2), align='center')
    for j in range(1, floor((y1-y0)/2.5+1e-7)+1):
        y = oy+view.scale*j*2.5
        length = 2 if j % 4 == 0 else 1.2
        line(ax, [(ox, y), (ox-sign*length, y)], 0.25)
        if j % 4 == 0:
            text(ax, ox-3*sign, y, str(j*5//2), align='left' if view.reverse else 'right', clear=True)


def dimensions(ax, board, view):
    x0, y0, x1, y1 = view.rect
    xmin, ymin, xmax, ymax = view.bounds
    # Start extensions at the actual native extrema (crest, flank, etc.),
    # not at a fictitious corner of a bounding rectangle. In the display
    # path a circular arc is a cubic; use its extrema as well as endpoints.
    pts = []
    for segment, code in mpl_path(board.edge_path).iter_bezier():
        if code == Path.MOVETO:
            continue
        _, t = segment.axis_aligned_extrema()
        pts.extend(view.xy(*segment(at)) for at in (0, *t, 1))
    def support(axis, edge, other, select):
        err = min(abs(p[axis]-edge) for p in pts)
        return select(p[other] for p in pts if abs(p[axis]-edge) <= err+0.001)
    by, rx = y0-13.5, x1+28
    for x in (x0, x1):
        line(ax, [(x, support(0, x, 1, min)-0.7), (x, by-1.7)], z=2)
    line(ax, [(x0, by), (x1, by)])
    arrow(ax, x0, by, 1, 0)
    arrow(ax, x1, by, -1, 0)
    text(ax, (x0+x1)/2, by+2.6, num(xmax-xmin), 3.5, align='center')
    for y in (y0, y1):
        line(ax, [(support(1, y, 0, max)+0.7, y), (rx+1.7, y)], z=2)
    line(ax, [(rx, y0), (rx, y1)])
    arrow(ax, rx, y0, 0, 1)
    arrow(ax, rx, y1, 0, -1)
    text(ax, rx-3.1, (y0+y1)/2, num(ymax-ymin), 3.5, angle=90, align='center')


def header(ax, title, product):
    # Field 26 (the inverted designation) occupies x=20..90, y=278..292.
    text(ax, 100, 283, title, 5)
    text(ax, 407, 282, product+'    /    NON PRODUCTION', 3.5, align='right')
    line(ax, [(28, 275), (407, 275)], 0.35)


def table(ax, x, top, columns, labels, rows, row_h=6.0):
    edges = [x]
    for w in columns:
        edges.append(edges[-1]+w)
    data = [labels, *rows]
    bottom = top-row_h*len(data)
    box(ax, x, bottom, sum(columns), top-bottom, 0.5)
    for xx in edges[1:-1]:
        line(ax, [(xx, top), (xx, bottom)], 0.25)
    for j, row in enumerate(data):
        if j:
            y = top-j*row_h
            line(ax, [(x, y), (edges[-1], y)], 0.35 if j == 1 else 0.25)
        for i, value in enumerate(row):
            text(ax, (edges[i]+edges[i+1])/2, top-(j+0.5)*row_h,
                 str(value), 2.5, align='center', maxw=columns[i]-1.5)
    return bottom


def requirements(ax, x, bottom, w, items):
    rows = []
    for i, statement in enumerate(items, 1):
        rows.extend(wrap(f'{i}. {statement}', w))
    top = bottom+4.8*len(rows)+2
    text(ax, x, top, 'Технические требования', 3.5)
    for j, row in enumerate(rows):
        text(ax, x, top-6.8-j*4.8, row)
    return top


def marks(board):
    groups = defaultdict(list)
    for hole in board.holes:
        key = (hole.kind, hole.dx, hole.dy, hole.pad_shape or '', tuple(hole.pad_size or ()))
        groups[key].append(hole)
    group_rows, holes = [], []
    letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    for i, (key, family) in enumerate(sorted(groups.items(), key=lambda item: (-max(item[0][1:3]), item[0]))):
        if i >= len(letters):
            raise ValueError('Too many distinct drill families for this sheet')
        kind, dx, dy, shape, size = key
        letter = letters[i]
        circular = abs(dx-dy) < 1e-6
        drill = '⌀'+num(dx) if circular else num(dx)+' × '+num(dy)
        if not size:
            land = '—'
        elif shape == 'circle':
            land = '⌀'+num(size[0])
        else:
            label = {'oval':'ов.', 'rect':'пр.', 'roundrect':'скр.'}.get(shape, shape)
            land = f'{label} {num(size[0])} × {num(size[1])}'
        group_rows.append([letter, drill, land, kind, 'не установлена', len(family)])
        for n, hole in enumerate(sorted(family, key=lambda h: (-h.y, h.x)), 1):
            holes.append((f'{letter}{n}', hole))
    return group_rows, holes


def hole_symbol(ax, hole, view, *, small_via=False):
    x, y = view.xy(hole.x, hole.y)
    a, b = hole.dx*view.scale, hole.dy*view.scale
    # GOST 2.417 §20: close round bores have the same symbol; the table
    # specifies the actual file diameter. Oblongs retain their axis/angle.
    if abs(a-b) < 1e-6:
        r = 1.25 if hole.kind != 'VIA' else 0.52
        # On the main registration map use the same fine symbol throughout
        # the via family. This is not a change to the file drill or land.
        r, pen = (0.25, 0.20) if small_via else (r, 0.28)
        ax.add_patch(Circle((x, y), r, facecolor='white', edgecolor=INK,
                            linewidth=pen*PT, zorder=7))
    else:
        angle = radians(hole.angle + (90 if b > a else 0))
        dx = (max(a,b)-min(a,b))*cos(angle)/2
        dy = (max(a,b)-min(a,b))*sin(angle)/2
        for color, width_mm in [(INK, min(a,b)+0.28), ('white', max(0.01, min(a,b)-0.28))]:
            ax.plot([x-dx, x+dx], [y-dy, y+dy], color=color, linewidth=width_mm*PT,
                    solid_capstyle='round', zorder=7.2 if color == 'white' else 7)
        r = max(a,b)/2
    if hole.kind != 'VIA':
        line(ax, [(x-r-0.6, y), (x+r+0.6, y)], 0.2, z=8)
        line(ax, [(x, y-r-0.6), (x, y+r+0.6)], 0.2, z=8)


def label_holes(ax, items, view):
    x0, y0, x1, y1 = view.rect
    by_side = {False: [], True: []}
    split = median(h.x for _, h in items) if len(items) > 16 else (view.bounds[0]+view.bounds[2])/2
    for name, hole in items:
        x, y = view.xy(hole.x, hole.y)
        radius = 0.52 if hole.kind == 'VIA' else 1.25
        by_side[hole.x >= split].append((y, x, name, radius))
    for right, group in by_side.items():
        group.sort()
        if not group:
            continue
        s = 1 if right else -1
        # Order-preserving rail (one ID per actual hole). Leave space for
        # ordinate ticks on the left and the overall dimension on the right.
        elbow = x1+10 if right else x0-13
        anchor = elbow+3*s
        lo, hi = max(89, y0+4), min(251, y1-4)
        gap = 4.5
        if (len(group)-1)*gap > hi-lo:
            lo, hi = 88, 249
        if (len(group)-1)*gap > hi-lo:
            raise ValueError('Too many hole leaders on one rail')
        ys = []
        for y, x, name, radius in group:
            ys.append(max(lo, y, ys[-1]+gap if ys else lo))
        ys[-1] = min(ys[-1], hi)
        for i in range(len(ys)-2, -1, -1):
            ys[i] = min(ys[i], ys[i+1]-gap)
        for (y, x, name, radius), end in zip(group, ys):
            vx, vy = elbow-x, end-y
            distance = hypot(vx, vy)
            start = x+radius*vx/distance, y+radius*vy/distance
            line(ax, [start, (elbow, end), (anchor, end)], 0.25, z=3)
            text(ax, anchor+0.8*s, end, name, 2.5, align='left' if right else 'right')


def _shelf(ax, name, center, radius, dx, dy, side, length):
    """Start on the ring, then a straight lead and a labelled horizontal shelf."""
    x, y = center
    distance = hypot(dx, dy)
    rim = x + radius*dx/distance, y + radius*dy/distance
    knee = x + dx, y + dy
    end = knee[0] + length*side, knee[1]
    line(ax, [rim, knee, end], 0.3)
    text(ax, (knee[0]+end[0])/2, knee[1]+3.3, name, align='center')


# Main registration view only. Each tuple specifies a label's elbow offset
# in *paper* mm and the side of its shelf. These are annotation positions,
# not PCB coordinates. Short approaches avoid both the adjacent marks and
# the opaque text masks along the coordinate axes.
_MAIN_SHELVES = {
    'A1': (-1.3, 4.8, -1), 'A2': (2.5, 4.3, 1),
    'A3': (-3.5, 3.5, -1), 'A4': (2.8, -10.6, 1),
    'B1': (-2.5, 4.3, -1), 'B2': (3.5, 3.5, 1),
    'C1': (-1.7, 6.3, -1), 'C2': (2.8, 10.6, 1),
    'D1': (1.7, 6.3, 1), 'D2': (1.7, 6.3, 1),
    'D3': (1.7, 6.3, 1), 'D4': (1.7, 6.3, 1),
    'E1': (-2.5, 4.3, -1), 'E2': (-2.5, 4.3, -1),
    'F1': (0, -11, -1), 'F2': (0, -8.5, 1),
    'F3': (-9.5, -5.5, -1), 'F4': (-2.5, 4.3, -1),
    'F5': (-6.3, 1.7, -1), 'F6': (-2.8, 10.6, -1),
    'F7': (0, -8.5, 1), 'F8': (-2.2, -8.2, -1),
    'F9': (-3.5, 3.5, -1), 'F10': (5.6, -3.3, 1),
    'F11': (0, 5, 1), 'F12': (5.6, 3.2, 1), 'F13': (0, 11, -1),
    'F21': (5.6, -3.3, 1), 'F22': (-13.5, -3.6, -1),
    'F23': (5.6, 3.2, 1), 'F24': (-6.3, -1.7, -1),
}


def dense_via_detail(ax, items, view, edition):
    """Main sheet 1: detail Б. Only label directions are authored here;
    centres, orientation and drill diameters are read from the board.
    """
    # Distribute the shelves out of, not through, the two crowded banks.
    outward = {'F14': (1, -1), 'F15': (-1, -1), 'F16': (-1, -1),
               'F17': (1, -1), 'F18': (1, 1), 'F19': (-1, 1), 'F20': (-1, 1)}
    holes = {n: h for n, h in items if n in outward and h.kind == 'VIA'}
    if edition.key != 'main' or set(holes) != set(outward):
        return set()
    xs, ys = zip(*((h.x, h.y) for h in holes.values()))
    bounds = min(xs), min(ys), max(xs), max(ys)
    detail = View(bounds, 20, 107, 35)  # free field to the left of the stamp
    x0, y0, x1, y1 = detail.rect
    if x0 < 49 or x1 > 167 or y0 < 25 or y1 > 44:
        raise ValueError('Re-layout the drill detail for the changed source cluster')

    # On the parent view mark the region once, not seven almost coincident tips.
    left, top = view.xy(min(xs), min(ys))
    right, bottom = view.xy(max(xs), max(ys))
    pad = 1.5
    box(ax, left-pad, bottom-pad, right-left+2*pad, top-bottom+2*pad, 0.3,
        style=(0, (4, 1.2, 0.8, 1.2)))
    line(ax, [(left-pad, top+pad), (left-6, top+5), (left-12, top+5)])
    text(ax, left-9, top+8, 'Б', 3.5, align='center')

    text(ax, 28, 62, 'Б (20:1)', 3.5)
    text(ax, 54, 62, 'Отверстия F14–F20. Вид со стороны компонентов.')
    for n, h in holes.items():
        x, y = detail.xy(h.x, h.y)
        radius = detail.scale * h.dx / 2
        sx, sy = outward[n]
        _shelf(ax, n, (x, y), radius, 7.5*sx, 7.5*sy, sx, 8)
        ax.add_patch(Circle((x, y), radius, facecolor='white', edgecolor=INK,
                            linewidth=0.3*PT, zorder=7))
    text(ax, 28, 13, 'В элементе Б показан диаметр сверления по файлу KiCad, не по обмеру.')
    return set(holes)


def coordinate_tables(ax, board, items, top, bottom):
    x0, _, _, y1 = board.bounds
    slots = any(abs(h.dx-h.dy)>1e-6 for _, h in items)
    rows = [[n, num(h.x-x0, 2), num(y1-h.y, 2)] + ([num(h.angle)+'°' if abs(h.dx-h.dy)>1e-6 else '—'] if slots else [])
            for n, h in items]
    capacity = floor((top-bottom)/5.4)-1
    if capacity < 1:
        raise ValueError('No space remains for coordinate rows')
    blocks = max(1, ceil(len(rows)/capacity))
    if blocks > (3 if slots else 4):
        raise ValueError(f'{len(rows)} coordinate rows do not fit A3')
    per_block = max(1, ceil(len(rows)/blocks))
    w = (210-(blocks-1)*3)/blocks
    columns = [0.22*w, 0.39*w, 0.39*w] if not slots else [0.20*w, 0.29*w, 0.29*w, 0.22*w]
    # Compact sparse tables; do not stretch three values over half a sheet.
    if blocks == 1:
        columns = [min(a, b) for a, b in zip(columns, (23, 38, 38, 29))]
    labels = ['Поз.', 'X', 'Y']+(['α'] if slots else [])
    for j in range(blocks):
        table(ax, 197+j*(w+3), top, columns, labels,
              rows[j*per_block:(j+1)*per_block], 5.4)


def mechanical(sheet, board, edition, scale):
    ax = sheet.ax
    header(ax, 'Контур и отверстия', edition.product)
    text(ax, 28, 267, 'Вид со стороны компонентов', 3.5)
    text(ax, 28, 260, 'Проводники не показаны. Контур — Edge.Cuts.')
    view = View(board.bounds, scale, 106, 171)
    grid(ax, view)
    contour(ax, board, view, 0.7)
    dimensions(ax, board, view)
    groups, items = marks(board)
    in_detail = dense_via_detail(ax, items, view, edition)
    if in_detail and {n for n, _ in items} != set(_MAIN_SHELVES) | in_detail:
        raise ValueError('Re-layout the main drill labels for the changed source inventory')
    for n, hole in items:
        compact = bool(in_detail) and hole.kind == 'VIA'
        hole_symbol(ax, hole, view, small_via=compact)
        if in_detail and n not in in_detail:
            _shelf(ax, n, view.xy(hole.x, hole.y), 0.25 if compact else 1.25,
                   *_MAIN_SHELVES[n], length=6)
    if not in_detail:
        label_holes(ax, items, view)
    text(ax, 197, 267, 'Таблица отверстий', 3.5)
    bottom = table(ax, 197, 261, [18, 38, 50, 27, 54, 23],
                   ['Знак', 'Отверстие, мм', 'Площадка, мм', 'KiCad', 'Металлизация', 'Кол.'], groups)
    text(ax, 197, bottom-6.5, 'Координаты центров от O, мм', 3.5)
    x0, _, _, y1 = board.bounds
    thick = f' Толщина модели {num(board.thickness)} мм.' if board.thickness is not None else ''
    tech = requirements(ax, 197, 67, 210, [
        f'Размеры для справок. Фотореконструкция ({edition.photos}), без обмера.'+thick,
        f'O — пересечение левой и нижней габаритных линий вида. В мм: X = xKiCad - ({num(x0)}); Y = ({num(y1)}) - yKiCad.',
        'Риски сетки через 2,5 мм, числа через 10 мм. Буквы — группы; знаки круглых отверстий условны. На плату не наносить.',
        'Тип в файле не подтверждает покрытие стенок. Материал и допуски не установлены. Для изготовления не применять.'
    ])
    coordinate_tables(ax, board, items, bottom-11.5, tech+4.5)
    return {'groups': groups, 'scale': scale, 'centers':[
        {'id':n, 'ref':h.ref, 'type_in_file':h.kind, 'plating':'unknown', 'kicad_mm':[h.x, h.y],
         'drawing_xy_mm':[h.x-x0, y1-h.y], 'drill_axes_mm':[h.dx, h.dy], 'axis_deg':h.angle,
         'land_shape':h.pad_shape, 'land_size_mm':h.pad_size} for n, h in items]}


def label_range(bounds, axis, board):
    if bounds is None:
        return '—'
    lo, hi = ((bounds[0]-board.bounds[0], bounds[2]-board.bounds[0]) if axis == 'X'
              else (board.bounds[3]-bounds[3], board.bounds[3]-bounds[1]))
    return f'{num(lo, 2)}...{num(hi, 2)}'


def pattern(sheet, board, plots, edition, scale, filename):
    ax = sheet.ax
    header(ax, 'Проводящий рисунок', edition.product)
    locations = []
    views = {side: View(board.bounds, scale, cx, 177, side == 'B.Cu')
             for side, cx in zip(SIDES, (84, 201))}
    for side, view in views.items():
        caption = 'Сторона компонентов' if not view.reverse else 'Обратная сторона'
        text(ax, view.cx, 267.5, f'{side}   {caption} ({ratio(scale)})', 3.5, align='center')
        grid(ax, view)
        contour(ax, board, view, 0.7)
        if plots[side].ink_count:
            locations.append({'id': 'CuFront' if not view.reverse else 'CuBack',
                              'group': plots[side].svg_group, 'transform': view.paper_matrix, 'clip': None})
        elif board.routes[side] is not None:
            raise ValueError(f'{side}: native track geometry but empty plot')
    # Crop the actual plotted layer a second time, not a drawn imitation. The
    # same KiCad coordinates define the reference frame on the parent view.
    side = next((s for s in SIDES if board.inspection[s] and board.routes[s] and plots[s].ink_count), None)
    side = side or next((s for s in SIDES if board.inspection[s] and plots[s].ink_count), None)
    if not side:
        raise ValueError('No real copper feature available for an inspection crop')
    fx, fy = board.inspection[side]
    detail_scale, uw, vh = 10, 9.6, 6.4
    bounds = fx-uw/2, fy-vh/2, fx+uw/2, fy+vh/2
    detail = View(bounds, detail_scale, 341.5, 223, side == 'B.Cu')
    x0, y0, x1, y1 = detail.rect
    text(ax, x0, 267.5, f'А ({ratio(detail_scale)})    {side}', 3.5)
    box(ax, x0, y0, x1-x0, y1-y0, 0.35)
    native = views[side]
    p, q = native.xy(*bounds[:2]), native.xy(*bounds[2:])
    lx, rx = sorted((p[0], q[0]))
    ly, uy = sorted((p[1], q[1]))
    box(ax, lx, ly, rx-lx, uy-ly, 0.3, style=(0, (4, 1.2, 0.8, 1.2)))
    nx = native.rect[2] + 9
    line(ax, [(rx, uy), (nx-2, uy+3), (nx+3, uy+3)], 0.3)
    text(ax, nx+0.5, uy+5.8, 'А', 3.5, align='center')
    locations.append({'id':'CuInspection', 'group':plots[side].svg_group, 'transform':detail.paper_matrix,
                      'clip':(x0, 297-y1, x1-x0, y1-y0)})
    tx = num(fx-board.bounds[0], 2)
    ty = num(board.bounds[3]-fy, 2)
    text(ax, 275, 185.5, f'Центр фрагмента: X = {tx}; Y = {ty} мм.')
    text(ax, 275, 175, 'Содержимое файла по слоям', 3.5)
    rows = []
    for key, label in (('pads','Площадки'), ('vias','Переходы'), ('segments','Отрезки'),
                       ('arcs','Дуги'), ('zones','Зоны меди')):
        rows.append([label, *[board.counts[s][key] for s in SIDES]])
    for axis in ('X', 'Y'):
        rows.append([f'{axis} трасс, мм', *[label_range(board.routes[s], axis, board) for s in SIDES]])
    end = table(ax, 275, 170, [52, 40, 40], ['Объект', *SIDES], rows, 6)
    text(ax, 275, end-7, 'Ширины участков (файл), мм', 3.5)
    y = end-14
    for s in SIDES:
        values = '; '.join(num(w) for w in board.widths[s]) or 'нет участков'
        for row in wrap(f'{s}: {values}', 132):
            text(ax, 275, y, row)
            y -= 4.8
    y -= 3
    for sentence in [
        'Границы трасс в таблице относятся к отрезкам и дугам с учётом их ширины, но не к площадкам.',
        ('Кольца на B.Cu — геометрия сквозных объектов файла, не наблюдение обратной стороны.'
         if plots['B.Cu'].ink_count and not board.routes['B.Cu'] else
         ('В файле B.Cu пуст. Это не подтверждает отсутствие меди на обороте образца.'
          if not plots['B.Cu'].ink_count else 'Пустые поля не подтверждают отсутствие меди.')),
        f'Файл: {filename}  /  SHA-256: {board.sha256[:16]}...']:
        for row in wrap(sentence, 132):
            text(ax, 275, y, row)
            y -= 4.8
    if y < 61:
        raise ValueError('Evidence notes do not fit on sheet')
    notes = [
        f'Источник: {edition.photos}. {edition.limit}',
        'Площадки и проводники — объекты KiCad в их размерах, не проверенные электрические связи. Оборот показан снаружи: отражён X, база O та же.',
        'Размеры для справок. Риски через 2,5 мм. Неизвестны закрытые участки, число внутренних слоёв и покрытия. Для изготовления не применять.'
    ]
    y = requirements(ax, 28, 67, 229, notes)
    if y > min(v.rect[1] for v in views.values())-7:
        # Keep the full-scale copper clear. The continuation sheet has a short
        # title block; the frame below this left-hand area is blank.
        raise ValueError('Pattern notes would overlap the plotted boards')
    return locations, {'side':side, 'center_kicad_mm':[fx, fy], 'roi_kicad_mm':bounds,
                       'scale':detail_scale, 'direction':'outside, same as corresponding parent view'}
