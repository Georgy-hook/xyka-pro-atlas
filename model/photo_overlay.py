#!/usr/bin/env python3
"""Compare a saved FreeCAD assembly with two unrotated owner photographs.

Run with FreeCAD's Python, e.g.:
    R=/Applications/FreeCAD.app/Contents/Resources
    PYTHONPATH="$R/lib" "$R/bin/python" model/photo_overlay.py \
        --photos /path/to/XKAH_PRO_CAD_REBUILD_HANDOFF/photos/original

The JSON records manual observations in original, top-left-origin photo pixels.
There are NO traced CAD outlines or alternative board geometry in the JSON.
The board frame and all model-side landmark positions come from the supplied
FCStd. This is a planar registration, not a calibrated perspective camera.
"""

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import FreeCAD as App
import Part
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, PngImagePlugin

ROOT = Path(__file__).resolve().parent.parent
REGISTRATION = Path(__file__).with_name('photo_registration.json')
STEM = 'XKAH_PRO_A43_overlay_reference'
AA = 2  # Subpixel coverage for native-resolution printed edges.
DEFLECTION_MM = 0.035


def mapping(h, xy):
    """Apply a planar projectivity to an N×2 array in one coordinate system."""
    xy = np.atleast_2d(np.asarray(xy, dtype=float))
    hom = np.column_stack((xy, np.ones(len(xy)))) @ h.T
    if np.any(np.abs(hom[:, 2]) < 1e-10):
        raise ValueError('Registration projects a landmark to infinity')
    return hom[:, :2] / hom[:, 2, None]


def normalise(xy):
    center = xy.mean(axis=0)
    spread = np.linalg.norm(xy - center, axis=1).mean()
    if spread <= 1e-9:
        raise ValueError('Coincident registration points')
    s = np.sqrt(2) / spread
    mat = np.array([[s, 0, -s * center[0]], [0, s, -s * center[1]], [0, 0, 1]])
    return mapping(mat, xy), mat


def fit_homography(uv, pixels):
    """Overdetermined normalised DLT, then minimise *pixel* transfer errors.

    Every declared fit observation is retained with equal weight. Held-out
    checks and elevated bodies never enter this function, even as outliers.
    """
    if len(uv) < 6:
        raise ValueError('Need at least six distributed fit observations')
    src, t = normalise(uv)
    tgt, n = normalise(pixels)
    a = []
    for (u, v), (x, y) in zip(src, tgt):
        a.append([-u, -v, -1, 0, 0, 0, u * x, v * x, x])
        a.append([0, 0, 0, -u, -v, -1, u * y, v * y, y])
    _, sv, vt = np.linalg.svd(a, full_matrices=False)
    if sv[-2] < sv[0] * 1e-6:
        raise ValueError('Degenerate planar landmark pattern')
    h = vt[-1].reshape(3, 3)
    h /= h[2, 2]
    points = np.column_stack((src, np.ones(len(src))))
    for _ in range(25):
        pred = mapping(h, src)
        err = tgt - pred
        denom = points @ h[2]
        m = points / denom[:, None]
        zero = np.zeros_like(m)
        jac = np.vstack((np.hstack((m, zero, -pred[:, 0, None] * m[:, :2])),
                         np.hstack((zero, m, -pred[:, 1, None] * m[:, :2]))))
        step = np.linalg.lstsq(jac, err.T.ravel(), rcond=None)[0]
        trial = h + np.r_[step, 0].reshape(3, 3)
        if np.linalg.norm(tgt - mapping(trial, src)) >= np.linalg.norm(err):
            break
        h = trial
        if np.linalg.norm(step) < 1e-11:
            break
    result = np.linalg.inv(n) @ h @ t
    return result / result[2, 2]


def check_orientation(h, center, expected):
    """A wrong mirrored/quarter-turned correspondence must not pass on RMS alone."""
    xy = mapping(h, [center, center + [1, 0], center + [0, 1]])
    dirs = xy[1:] - xy[0]
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    expected = np.array(expected, dtype=float)
    if np.linalg.det(dirs) >= 0 or np.any(np.sum(dirs * expected, axis=1) < 0.60):
        raise ValueError(f'Inconsistent orientation on populated face: {dirs}')


def board_shapes(doc, group_name):
    """Collect registered physical leaves only; omit boolean tools and links.

    Shape.Placement contains the leaf's own Placement. Only its ancestry is
    still missing: remove the local transform before applying the global one.
    Finally invert the board frame, so closed/exploded scene orientation is
    not confused with the side seen in the dismantling photographs.
    """
    board = doc.getObject(group_name)
    if board is None or board.TypeId != 'App::Part':
        raise ValueError(f'Missing native board group: {group_name}')
    inv = board.getGlobalPlacement().inverse()
    shapes = {}
    stack = list(board.Group)
    while stack:
        obj = stack.pop()
        if obj.TypeId == 'App::Part':
            stack.extend(obj.Group)
        elif 'EvidenceSource' in obj.PropertiesList and hasattr(obj, 'Shape'):
            shape = obj.Shape.copy()
            if shape.isNull():
                raise ValueError(f'Null registered shape: {obj.Name}')
            parent = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
            shape.Placement = inv.multiply(parent).multiply(shape.Placement)
            shapes[obj.Name] = shape
    if not shapes:
        raise ValueError(f'No physical solids under {group_name}')
    return shapes


def ref_xy(shapes, ref):
    """Resolve IDs to actual B-rep centres or measured hole axes, in board mm."""
    shape = shapes[ref['object']]
    if 'solid' in ref:
        # Ordered repeated pad bodies, not an assumed CAD pitch/analytic grid.
        axis, index = ref['solid']
        solids = sorted(shape.Solids, key=lambda s: getattr(s.BoundBox.Center, axis))
        shape = solids[index]
    if 'hole_near_mm' in ref:
        # A seed merely disambiguates real circular edges in the substrate.
        # It is never returned as a reference position, even if no hole exists.
        u, v, tolerance = ref['hole_near_mm']
        axes = set()
        for edge in shape.Edges:
            curve = edge.Curve
            if isinstance(curve, Part.Circle) and abs(curve.Axis.z) > 0.999:
                axes.add((round(curve.Center.x, 5), round(curve.Center.y, 5)))
        hits = [p for p in axes if np.linalg.norm(np.subtract(p, [u, v])) < tolerance]
        if len(hits) != 1:
            raise ValueError(f'Expected exactly one hole axis for {ref}; found {hits}')
        return np.array(hits[0])
    p = shape.BoundBox.Center
    return np.array([p.x, p.y])


@dataclass
class Observation:
    tag: str
    role: str
    name: str
    ref: dict
    uv: np.ndarray
    pick: np.ndarray
    label_offset: tuple


def observations(points, shapes):
    obs = [Observation(p['id'], p['role'], p['name'], p['ref'], ref_xy(shapes, p['ref']),
                       np.array(p['pixel'], dtype=float), tuple(p.get('label_offset', (13, -29))))
           for p in points]
    if len({p.tag for p in obs}) != len(obs) or len({tuple(p.uv) for p in obs}) != len(obs):
        raise ValueError('Repeated landmark ID or duplicated physical reference')
    return obs


def raster_triangle(xy, zw, face_id, depth, face_ids):
    """Z-buffer one tessellated B-rep face triangle in warped photo space.

    z is distance toward the camera in the *board* top view. Interpolation
    after H is perspective-correct; a planar H does NOT model z parallax.
    """
    height, width = depth.shape
    x0, y0 = np.maximum(np.ceil(xy.min(axis=0)).astype(int), 0)
    x1, y1 = np.minimum(np.floor(xy.max(axis=0)).astype(int), [width - 1, height - 1])
    if x0 > x1 or y0 > y1:
        return
    a, b, c = xy
    ab = b - a
    ac = c - a
    area = ab[0] * ac[1] - ac[0] * ab[1]
    if abs(area) < 1e-7:
        return
    strip = np.s_[y0:y1 + 1, x0:x1 + 1]
    dx = np.arange(x0, x1 + 1) - a[0]
    dy = np.arange(y0, y1 + 1)[:, None] - a[1]
    f1 = (dx * ac[1] - dy * ac[0]) / area
    f2 = (dy * ab[0] - dx * ab[1]) / area
    f0 = 1.0 - f1 - f2
    inside = (f0 >= -1e-6) & (f1 >= -1e-6) & (f2 >= -1e-6)
    if np.ptp(zw[:, 0]) < 1e-8:
        z = zw[0, 0]
    else:
        inv_w = 1. / zw[:, 1]
        k0, k1, k2 = f0 * inv_w[0], f1 * inv_w[1], f2 * inv_w[2]
        z = (k0 * zw[0, 0] + k1 * zw[1, 0] + k2 * zw[2, 0]) / (k0 + k1 + k2)
    update = inside & (z >= depth[strip] - 1e-6)
    np.copyto(depth[strip], z, where=update, casting='unsafe')
    face_ids[strip][update] = face_id


def rendered_projection(shapes, h, cfg, crop_photo):
    """Rasterise real OCC faces with semantic colours at their visible boundaries.

    Face IDs, not triangle IDs, generate lines. This keeps screw holes and
    package/lead outlines without painting a triangulation over the photograph.
    Camera-side occluders are manually outlined only in the separate photo mask.
    """
    x0, y0, x1, y1 = cfg['crop']
    width, height = crop_photo.size
    if (width, height) != (x1 - x0, y1 - y0):
        raise ValueError('Bad image crop')
    local = np.array([[AA, 0, -AA * x0], [0, AA, -AA * y0], [0, 0, 1.]]) @ h
    depth = np.full((height * AA, width * AA), -np.inf, np.float32)
    ids = np.zeros(depth.shape, dtype=np.int32)
    # 0 = background; 1 = package/lead, 2 = substrate, 3 = LCD envelope.
    classes = [0]
    faces = 0
    for name, shape in shapes.items():
        if name in cfg.get('omit', []) or name.endswith(tuple(cfg.get('omit_suffixes', []))):
            continue
        kind = 2 if name == cfg['substrate'] else 3 if name in cfg.get('glass', []) else 1
        box = shape.BoundBox
        corners = np.array([[u, v] for u in (box.XMin, box.XMax) for v in (box.YMin, box.YMax)])
        pix = mapping(local, corners)
        if np.max(pix[:, 0]) < 0 or np.min(pix[:, 0]) >= width * AA:
            continue
        if np.max(pix[:, 1]) < 0 or np.min(pix[:, 1]) >= height * AA:
            continue
        for face in shape.Faces:
            pts, tri = face.tessellate(DEFLECTION_MM)
            if not tri:
                continue
            vertices = np.array([[p.x, p.y, p.z] for p in pts])
            vh = np.column_stack((vertices[:, :2], np.ones(len(vertices)))) @ local.T
            if np.any(vh[:, 2] <= 0):
                raise ValueError(f'{name}: homography horizon crosses visible board')
            xy = vh[:, :2] / vh[:, 2, None]
            zw = np.column_stack((vertices[:, 2], vh[:, 2]))
            faces += 1
            classes.append(kind)
            for triangle in np.asarray(tri):
                raster_triangle(xy[triangle], zw[triangle], faces, depth, ids)
    layer = np.array(classes, dtype=np.uint8)[ids]
    # Boundaries of *visible faces* (incl. relief details), not hidden back edges.
    edges = np.zeros_like(layer)
    for axis in (0, 1):
        before, after = ((np.s_[:-1, :], np.s_[1:, :]) if axis == 0
                         else (np.s_[:, :-1], np.s_[:, 1:]))
        a, b = layer[before], layer[after]
        # A land against the laminate is a component outline, NOT an exterior
        # board edge. Only true background/board and glass boundaries are mint.
        kind = np.where((a == 3) | (b == 3), 3, np.where((a == 1) | (b == 1), 1, 2))
        mark = np.where(ids[before] != ids[after], kind, 0).astype(np.uint8)
        np.maximum(edges[before], mark, out=edges[before])
        np.maximum(edges[after], mark, out=edges[after])
    del depth, ids
    out = crop_photo.convert('RGB')
    def strokes(selection, radius, alpha):
        mask = Image.fromarray((edges == selection).astype('uint8') * alpha)
        if radius:
            mask = mask.filter(ImageFilter.MaxFilter(2 * radius + 1))
        return mask.resize(out.size, Image.Resampling.LANCZOS)

    # A coarse camera-side mask must never clip a board-edge mismatch just
    # because it is outside a traced PCB outline. Only real occluders are used.
    total = np.zeros((height, width), bool)
    glass = np.zeros_like(total)
    for region in cfg['occlusion']:
        m = Image.new('L', out.size)
        poly = [(x - x0, y - y0) for x, y in region['polygon']]
        ImageDraw.Draw(m).polygon(poly, fill=255)
        if region['type'] == 'glass':
            glass |= np.asarray(m) > 0
        else:
            total |= np.asarray(m) > 0
    for kind, color, radius, alpha in [(1, '#A1DFFF', 1, 208), (2, '#4EF8CF', 3, 255),
                                       (3, '#4EF8CF', 2, 250)]:
        mask = strokes(kind, radius, alpha)
        hide = total if kind == 3 else (total | glass)
        mask = Image.fromarray(np.where(hide, 0, np.asarray(mask)).astype(np.uint8))
        if kind in (2, 3):
            shadow = mask.filter(ImageFilter.MaxFilter(3)).point(lambda v: v * 0.5)
            out.paste('#133E42', (0, 0, width, height), shadow)
        out.paste(color, (0, 0, width, height), mask)
    yy, xx = np.ogrid[:height, :width]
    hatch = ((xx + yy) % 22 < 2) & (total | glass)
    out.paste('#FBD394', (0, 0, width, height), Image.fromarray(hatch.astype(np.uint8) * 65))
    if np.count_nonzero(layer) < 1000:
        raise ValueError('No substantial projected board geometry inside the photo')
    return out, faces


PAPER = '#F4F2E9'
INK = '#132B35'
MUTED = '#45616A'
TEAL = '#076A67'
AMBER = '#A85112'
RULE = '#AEBDB9'
PICK = {'fit': '#FCE5A1', 'check': '#FF97AB', 'height': '#F7C697'}
PAGE_W = 2464
MARGIN = 64
GAP = 32
PHOTO_Y = 185


@lru_cache(maxsize=None)
def font(pt, bold=False):
    """Require a real Cyrillic font; fail visibly instead of emitting tofu."""
    override = os.environ.get('XKAH_FONT_BOLD' if bold else 'XKAH_FONT')
    options = [override, '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else
               '/System/Library/Fonts/Supplemental/Arial.ttf',
               'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf']
    for option in filter(None, options):
        try:
            return ImageFont.truetype(option, pt)
        except OSError:
            continue
    raise RuntimeError('A Cyrillic TrueType font is needed; set XKAH_FONT and XKAH_FONT_BOLD')


def text(d, x, y, value, pt, color=INK, bold=False, anchor='lt'):
    d.text((x, y), value, font=font(pt, bold), fill=color, anchor=anchor)


def wrap(d, x, y, value, pt, width, color=INK, line_gap=8):
    """Width-aware typesetting for proof notes in print and at screen zoom."""
    f = font(pt)
    line = ''
    for word in value.split():
        test = (line + ' ' + word).strip()
        if line and d.textlength(test, font=f) > width:
            text(d, x, y, line, pt, color)
            y += pt + line_gap
            line = word
        else:
            line = test
    if line:
        text(d, x, y, line, pt, color)
        y += pt + line_gap
    return y


def photo_marks(im, obs, predicted, crop):
    """Photo pick (ring/box) vs projected CAD centre (+), true displacement."""
    draw = ImageDraw.Draw(im)
    start = np.array(crop[:2])
    for p, cad in zip(obs, predicted):
        x, y = (p.pick - start).tolist()
        a, b = (cad - start).tolist()
        col = PICK[p.role]
        draw.line((x, y, a, b), fill='#152936', width=5)
        draw.line((x, y, a, b), fill=col, width=2)
        box = (x - 6, y - 6, x + 6, y + 6)
        symbol = draw.rectangle if p.role == 'fit' else draw.ellipse
        symbol((x - 7, y - 7, x + 7, y + 7), outline='#27363B', width=3)
        symbol(box, outline=col, width=2)
        for x2, y2, x3, y3 in ((a - 4, b, a + 4, b), (a, b - 4, a, b + 4)):
            draw.line((x2, y2, x3, y3), fill='#20323B', width=4)
            draw.line((x2, y2, x3, y3), fill=col, width=2)
        tx = int(np.clip(x + p.label_offset[0], 2, im.width - 39))
        ty = int(np.clip(y + p.label_offset[1], 2, im.height - 21))
        w = draw.textlength(p.tag, font=font(15, True))
        draw.rounded_rectangle((tx - 3, ty - 2, tx + w + 4, ty + 16), 3, fill='#19323A')
        text(draw, tx, ty, p.tag, 15, col, True)


def physical_axes(im, h, center):
    """Orientation key computed from the local Jacobian of H, never hard-coded."""
    xy = mapping(h, np.array([center, center + [1, 0], center + [0, 1]]))
    directions = xy[1:] - xy[0]
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    d = ImageDraw.Draw(im)
    # Fixed page key (not a scale bar). Each arm points in the local photo direction.
    x, y = 61, im.height - 60
    d.rounded_rectangle((5, im.height - 117, 119, im.height - 5), radius=15, fill='#17343E')
    for label, (dx, dy) in zip(('+u', '+v'), directions):
        ex, ey = x + 30 * dx, y + 30 * dy
        d.line((x, y, ex, ey), fill='#E5FDF0', width=3)
        tip = np.array([ex, ey])
        inv = np.array([-dx, -dy]) * 9
        perp = np.array([-dy, dx]) * 4
        d.polygon([tuple(tip), tuple(tip + inv + perp), tuple(tip + inv - perp)], fill='#E5FDF0')
        text(d, x + 42 * dx, y + 42 * dy, label, 15, '#E5FDF0', True, 'mm')
    d.ellipse((x - 3, y - 3, x + 3, y + 3), fill='#E5FDF0')


def summary(obs, predicted):
    err = np.linalg.norm(predicted - np.array([p.pick for p in obs]), axis=1)
    groups = {}
    for role in ('fit', 'check', 'height'):
        ind = [i for i, p in enumerate(obs) if p.role == role]
        if not ind:
            raise ValueError(f'Missing {role} observations')
        values = err[ind]
        groups[role] = dict(n=len(ind), rms=float(np.sqrt(np.mean(values ** 2))),
                            max=float(values.max()))
    return err, groups


def plate(cfg, original, overlay, obs, predicted, metrics, errors, model_name, digest):
    x0, y0, x1, y1 = cfg['crop']
    crop = original.crop((x0, y0, x1, y1))
    x_a = MARGIN
    x_b = MARGIN + crop.width + GAP
    below = PHOTO_Y + crop.height
    page = Image.new('RGB', (PAGE_W, below + 428), PAPER)
    d = ImageDraw.Draw(page)
    d.rectangle((0, 0, PAGE_W, 7), fill=TEAL)
    text(d, x_a, 25, 'XKAH PRO   /   ПРОВЕРКА ПО ФОТОГРАФИЯМ ВЛАДЕЛЬЦА', 21, TEAL, True)
    text(d, PAGE_W - MARGIN, 25, f"ЭЛЕКТРОНИКА     •     ЛИСТ {cfg['plate']} / 02", 21, MUTED, True, 'rt')
    text(d, x_a, 61, cfg['title'], 49, INK, True)
    text(d, PAGE_W - MARGIN, 75, cfg['photo'], 30, MUTED, False, 'rt')
    d.line((MARGIN, 126, PAGE_W - MARGIN, 126), fill=RULE, width=2)
    text(d, x_a, 147, 'A   /   ОРИГИНАЛ', 23, INK, True)
    text(d, x_a + crop.width, 149, 'неповёрнутый фрагмент, 1 : 1 в пикселях', 19, MUTED, False, 'rt')
    text(d, x_b, 147, 'B   /   ТОТ ЖЕ ФРАГМЕНТ + CAD', 23, INK, True)
    text(d, PAGE_W - MARGIN, 149, 'контуры из сохранённых B-rep', 19, MUTED, False, 'rt')
    page.paste(crop, (x_a, PHOTO_Y))
    page.paste(overlay, (x_b, PHOTO_Y))

    # Full-image locator prevents a cropped macro from being mistaken for a
    # photograph of the entire board. The actual source pixels remain untouched in A.
    thumb_w = 112
    thumb_h = round(thumb_w * original.height / original.width)
    thumb = original.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
    td = ImageDraw.Draw(thumb)
    td.rectangle(tuple(round(v * thumb_w / original.width) for v in cfg['crop']),
                 outline='#70FFE2', width=2)
    top = below + 30
    page.paste(thumb, (x_a, top + 38))
    text(d, x_a, top, 'ПОЛЕ КАДРА', 17, MUTED, True)

    x = 202
    text(d, x, top, '01   /   РЕГИСТРАЦИЯ В ПЛОСКОСТИ ПЛАТЫ', 18, TEAL, True)
    fit = metrics['fit']
    check = metrics['check']
    text(d, x, top + 37, f"{fit['rms']:.1f} px", 40, INK, True)
    text(d, x + 246, top + 37, f"{check['rms']:.1f} px", 40, INK, True)
    text(d, x, top + 89, f"RMS опор F · n={fit['n']}", 20, MUTED)
    text(d, x + 246, top + 89, f"RMS контроля K · n={check['n']}", 20, MUTED)
    labels = '; '.join(p.name for p in obs if p.role == 'fit')
    y = wrap(d, x, top + 132, 'Опоры F: ' + labels + '.', 21, 526)
    wrap(d, x, y + 5, 'K и H не входят в расчёт гомографии. Смещения показаны без увеличения; ручной выбор центра — несколько px.',
         20, 526, MUTED)

    x = 785
    text(d, x, top, '02   /   ОТЛОЖЕННЫЕ ТОЧКИ', 18, TEAL, True)
    y = top + 38
    for p, e in zip(obs, errors):
        if p.role == 'fit':
            continue
        text(d, x, y, p.tag, 19, TEAL if p.role == 'check' else AMBER, True)
        text(d, x + 50, y, p.name, 20)
        text(d, x + 534, y, f'{e:.1f} px', 20, INK, False, 'rt')
        y += 31
    text(d, x, y + 5, 'H — над платой; отдельно от RMS контроля.', 19, MUTED)

    x = 1380
    text(d, x, top, '03   /   КАК ЧИТАТЬ НАЛОЖЕНИЕ', 18, TEAL, True)
    y = top + 38
    notes = [
        'Мятный контур — плата или стекло; голубой — границы видимых граней остальных тел. '
        'Рамка F или кольцо K/H — точка на фото; крест — центр из CAD.',
        cfg['limit'],
        'Косая штриховка — перекрытие на фото. Из геометрии не выводятся высота, '
        'посадка и допуск в мм: гомография меняет перспективу и масштаб.',
    ]
    for note in notes:
        y = wrap(d, x, y, note, 21, PAGE_W - MARGIN - x, INK)
        y += 8

    foot = page.height - 64
    d.line((MARGIN, foot - 15, PAGE_W - MARGIN, foot - 15), fill=RULE, width=2)
    text(d, MARGIN, foot, f"Метод: плоская проекция B-rep → гомография   •   источник CAD: {model_name}",
         19, MUTED)
    text(d, PAGE_W - MARGIN, foot,
         f"SHA-256 CAD: {digest[:16]}…   /   кадр: {cfg['sha256'][:16]}…", 18, MUTED, False, 'rt')
    return page


def file_hash(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_png(im, path, report):
    # Each sheet carries its registration, observed & predicted pixels and
    # both source hashes. Ordinary image viewers do not need a sidecar.
    info = PngImagePlugin.PngInfo()
    info.add_itxt('Registration', json.dumps(report, ensure_ascii=False))
    tmp = path.with_suffix('.tmp.png')
    im.save(tmp, pnginfo=info, compress_level=7, dpi=(180, 180))
    os.replace(tmp, path)


def run(model, photos, out, individual=False):
    configs = json.loads(REGISTRATION.read_text(encoding='utf-8'))['views']
    model_digest = file_hash(model)
    doc = App.openDocument(str(model.resolve()))
    sheets = []
    reports = []
    try:
        for cfg in configs:
            photo_path = photos / cfg['photo']
            if file_hash(photo_path) != cfg['sha256']:
                raise ValueError(f'Wrong input photo for native pixel picks: {photo_path}')
            with Image.open(photo_path) as inp:
                original = inp.convert('RGB')
            if original.size != (1152, 2048):
                raise ValueError(f'Wrong photo resolution: {original.size}')
            shapes = board_shapes(doc, cfg['group'])
            removed = []
            if cfg['photo'] == 'IMG_8917.jpg' and 'UiKeyMembrane' in shapes:
                # The original shows the loose black strip on the table below
                # the board and three exposed cream actuators, not a fitted pad.
                del shapes['UiKeyMembrane']
                removed.append('UiKeyMembrane')
                cfg = dict(cfg, limit=cfg['limit'] + ' На исходном кадре силиконовая накладка снята.')
            if cfg['substrate'] not in shapes:
                raise KeyError(cfg['substrate'])
            obs = observations(cfg['points'], shapes)
            fitting = [p for p in obs if p.role == 'fit']
            uv = np.array([p.uv for p in fitting])
            h = fit_homography(uv, np.array([p.pick for p in fitting]))
            check_orientation(h, uv.mean(axis=0), cfg['axis_directions'])
            predicted = mapping(h, [p.uv for p in obs])
            errors, metrics = summary(obs, predicted)
            print(f"=== {cfg['photo']}  /  {len(shapes)} registered physical leaves", flush=True)
            print('   ' + '  '.join(f'{k}: n={m["n"]}, RMS {m["rms"]:.2f} px' for k, m in metrics.items()), flush=True)
            img, n_faces = rendered_projection(shapes, h, cfg, original.crop(cfg['crop']))
            photo_marks(img, obs, predicted, cfg['crop'])
            physical_axes(img, h, uv.mean(axis=0))
            sheets.append(plate(cfg, original, img, obs, predicted, metrics, errors,
                                model.name, model_digest))
            reports.append(dict(projection='Orthographic into local UV, z-buffered, then H onto the JPEG; no height parallax correction.',
                                photo=cfg['photo'], photo_sha256=cfg['sha256'],
                                model=model.name, model_sha256=model_digest, crop=cfg['crop'],
                                board=cfg['group'], H_board_mm_to_photo_px=h.tolist(),
                                removed_in_photographed_state=removed,
                                faces_sampled=n_faces, registered_physical_leaves=len(shapes),
                                statistics_px=metrics, points=[dict(id=p.tag, role=p.role, name=p.name,
                                    reference=p.ref, uv_mm=p.uv.tolist(), observed_px=p.pick.tolist(),
                                    predicted_px=loc.tolist(), error_px=float(e))
                                    for p, loc, e in zip(obs, predicted, errors)]))
    finally:
        App.closeDocument(doc.Name)
    out.mkdir(parents=True, exist_ok=True)
    if individual:
        for sheet, cfg, report in zip(sheets, configs, reports):
            save_png(sheet, out / f"{STEM}_{Path(cfg['photo']).stem}.png", report)
    combined = Image.new('RGB', (PAGE_W, sum(sheet.height for sheet in sheets)), PAPER)
    y = 0
    for sheet in sheets:
        combined.paste(sheet, (0, y))
        y += sheet.height
    target = out / (STEM + '.png')
    save_png(combined, target, reports)
    print(f'=== Saved {target}  ({combined.width} × {combined.height})', flush=True)
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=ROOT / 'XKAH_PRO_A43_rebuilt.FCStd')
    parser.add_argument('--photos', type=Path, required=True, help='Original, unmodified JPEG directory')
    parser.add_argument('--out', type=Path, default=ROOT)
    parser.add_argument('--individual', action='store_true', help='Also write one complete page per photo')
    options = parser.parse_args()
    run(options.model, options.photos, options.out, options.individual)
