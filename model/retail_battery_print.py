"""Regional XYKA battery print, reproduced from the supplied front photograph.

Integration: add_print(c, pack, ratios, origin) -> tuple of registered leaves.
Keep the adjacent retail_battery_*.json files with this module. Local axes and
nominal millimetres are the pack's: 22.70 mm radius, Z=0..80, view toward +Y.
No fonts, images, SVG engine, ShapeStrings, decal textures or document proxies.
Shapely (included in the tested FreeCAD bundle) clips 2-D outlines; all saved
and exported geometry consists of ordinary native Part::Scale B-rep results.
"""

import json
import math
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

import FreeCAD as App
import Part
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient

from mech_shapes import scaled_part


_HERE = Path(__file__).resolve().parent
_LAYOUT = 'retail_battery_layout.json'

# Depth is measured *toward the front* along -Y from a common folded surface.
# These are optical media, not a claim about film thickness or extruded text.
# Shared layer interfaces prevent z-fighting even at grazing angles. In mm.
_TOP = {
    'body': 0.000,
    'carrier': 0.066,
    'spec': 0.116,
    'warning': 0.116,
    'tile': 0.162,
    'dark': 0.208,
}
_PIGMENT = 0.046

# Internal keys are not inferred from the spelling of any reference inscription.
_LEAVES = {
    'carrier': ('RuCarrier', 'Печатная подложка'),
    'spec': ('RuSpecPanel', 'Поле характеристик'),
    'warning': ('RuWarningPanel', 'Поле предупреждения'),
    'light.spec': ('RuSpecInk', 'Характеристики и знаки'),
    'light.carrier': ('RuBrandInk', 'Логотип, сайт и разделитель'),
    'light.warning': ('RuWarningInk', 'Инструкции и выходные данные'),
    'yellow.warning': ('RuCautionInk', 'Жёлтый знак'),
    'tile': ('RuOpticalPaper', 'Светлое поле оптического знака'),
    'dark': ('RuOpticalInk', 'Оптический знак · видимый рисунок'),
}


def _read(name):
    return json.loads((_HERE / name).read_text(encoding='utf-8'))


class _Projection:
    """The same tangent stations for carrier, copies, knockout holes and tile.

    For station a, n=(sin(a), -cos(a), 0) and n.p=R. Neighbour planes meet
    at radius R/cos(step/2). Map the *projected* image X, not a linear angle:
    treating photo pixels as an unrolled strip squeezes the two outer panels.
    """

    def __init__(self, reg):
        self.radius = reg['body_radius_mm']
        self.axis = reg['axis_u_px']
        self.sx = self.radius / reg['body_radius_px']
        self.bottom = reg['bottom_v_px']
        self.sz = reg['body_height_mm'] / (self.bottom - reg['top_v_px'])
        pitch = math.radians(4.0)
        # Sub-pixel offset avoids dropping a seam exactly onto a source vertex.
        phase = math.radians(0.371)
        self.angles = [i * pitch + phase for i in range(-18, 19)]
        vertex_r = self.radius / math.cos(pitch * 0.5)
        bounds = [a - pitch * 0.5 for a in self.angles]
        bounds.append(self.angles[-1] + pitch * 0.5)
        self.bounds = [self.axis + vertex_r * math.sin(b) / self.sx for b in bounds]
        self.windows = [box(lo, -1, hi, reg['image_size_px'][1] + 1)
                        for lo, hi in zip(self.bounds, self.bounds[1:])]
        self.slopes = [math.tan(a) for a in self.angles]
        self.intercepts = [-self.radius / math.cos(a) for a in self.angles]

    def point(self, strip, uv, front):
        u, v = uv
        x = (u - self.axis) * self.sx
        y = self.slopes[strip] * x + self.intercepts[strip] - front
        return App.Vector(x, y, (self.bottom - v) * self.sz)

    def pieces(self, shape):
        lo, _, hi, _ = shape.bounds
        if not self.bounds[0] < lo <= hi < self.bounds[-1]:
            raise ValueError('Outline outside the registered front of the pack')
        start = bisect_right(self.bounds, lo) - 1
        stop = bisect_right(self.bounds, hi) - 1
        if start == stop:
            yield start, shape
            return
        for strip in range(start, stop + 1):
            clipped = shape.intersection(self.windows[strip])
            for part in _area_parts(clipped):
                yield strip, part


def _area_parts(g):
    # A tangency can also leave a Point or LineString, which is not ink.
    if g.is_empty:
        return
    if g.geom_type == 'Polygon':
        yield g
    elif g.geom_type in ('MultiPolygon', 'GeometryCollection'):
        for child in g.geoms:
            yield from _area_parts(child)


def _prism(projection, strip, polygon, back, front):
    """Planar, analytic caps and straight walls; counters are real holes."""
    poly = orient(polygon, sign=-1.0)
    wires = []
    for ring in (poly.exterior, *poly.interiors):
        points = [projection.point(strip, uv, back) for uv in ring.coords]
        wires.append(Part.makePolygon(points))
    face = Part.Face(wires)
    return face.extrude(App.Vector(0, back - front, 0))


def _solid(projection, contour, back, front):
    prisms = [(k, _prism(projection, k, patch, back, front))
              for k, patch in projection.pieces(contour)]
    if len(prisms) == 1:
        return prisms[0][1]

    # A panel or a wide mark crosses tangent stations. Keep the folded caps
    # and *outside* walls only, then sew the coincident cap edges: one solid per
    # connected printed island, not a pile of wedges or overlapping stickers.
    # All actual source corners are off the artificial clipping stations.
    faces = []
    for k, prism in prisms:
        left, right = [(u - projection.axis) * projection.sx
                       for u in projection.bounds[k:k + 2]]
        for face in prism.Faces:
            bounds = face.BoundBox
            on_station = min(abs(bounds.Center.x - left), abs(bounds.Center.x - right)) < 1e-7
            if bounds.XLength < 1e-7 and on_station:
                continue
            faces.append(face)
    shell = Part.makeShell(faces)
    if not shell.isClosed():
        raise ValueError(f'Unclosed ink shell at source bounds {contour.bounds}')
    return Part.makeSolid(shell)


def _color(hex_rgb):
    return tuple(c / 255.0 for c in bytes.fromhex(hex_rgb[1:]))


def _level(ink, poly, panels):
    if ink == 'carrier':
        return 'carrier', 'body'
    if ink in ('spec', 'warning'):
        return ink, 'carrier'
    if ink == 'tile':
        return ink, 'warning'
    if ink == 'dark':
        return ink, 'tile'
    if ink not in ('light', 'yellow'):
        raise ValueError(f'Unrecognized print color: {ink}')
    for panel, surface in panels.items():
        if surface.covers(poly):
            return f'{ink}.{panel}', panel
        if surface.intersects(poly):
            raise ValueError(f'Ink contour straddles {panel} boundary')
    return f'{ink}.carrier', 'carrier'


def add_print(c, pack, ratios, origin):
    """Register only the front print on pack; never recompute or save its document.

    ratios=(BatteryOD/45.4, BatteryOD/45.4, BatteryL/80); pass expressions or
    numbers accepted by mech_shapes.scaled_part. origin=(0, AXIS_Y, BodyH-BatteryL).
    Returns handles in draw-stack order, also present in c.physical.
    """
    layout = _read(_LAYOUT)
    projection = _Projection(layout['registration'])
    fields = list(layout['fields'])
    for filename in layout['outlines']:
        drawing = _read(filename)
        if drawing['sha256'] != layout['sha256']:
            raise ValueError(f'{filename}: source registration mismatch')
        fields.extend(drawing['fields'])

    geometry = defaultdict(list)
    captions = defaultdict(list)
    panels = {}
    for field in fields:
        ink = field['ink']
        for outer, *holes in field['polygons']:
            poly = Polygon(outer, holes)
            if not poly.is_valid or poly.is_empty or poly.area <= 0:
                raise ValueError(f"Invalid outline in {field['id']}")
            key, bed = _level(ink, poly, panels)
            if ink in ('spec', 'warning'):
                panels[ink] = poly
            back = _TOP[bed]
            front = _TOP.get(ink, back + _PIGMENT)
            try:
                solid = _solid(projection, poly, back, front)
            except Exception as exc:
                raise ValueError(f"Cannot build {field['id']} at {poly.bounds}") from exc
            geometry[key].append(solid)
            if field['text'] not in captions[key]:
                captions[key].append(field['text'])

    leaves = []
    source = layout['source'] + ' SHA-256: ' + layout['sha256']
    confidence = 'REGIONAL RETAIL IMAGE / VISUAL REPRODUCTION, NOT CERTIFICATION'
    for key, pieces in geometry.items():
        suffix, label = _LEAVES[key]
        rgb = _color(layout['color_srgb'][key.split('.')[0]])
        notes = layout['purpose'] + ' | ' + ' / '.join(captions[key])
        if key in ('tile', 'dark'):
            notes += ' | Visible photographic field only; no encoded payload or serial inferred.'
        leaf = scaled_part(c, pack, 'RetailBattery' + suffix, 'XYKA · ' + label,
                           Part.makeCompound(pieces), rgb, source, confidence,
                           notes, ratios=ratios, origin=origin)
        if leaf.ViewObject:
            # The normal assembly default, Flat Lines, outlines BOTH sides of
            # every micro-stroke. On ink the edge overlay obscures the letters.
            leaf.ViewObject.DisplayMode = 'Shaded'
            # FreeCAD's default bright specular streak breaks into bands across
            # planar patches. This print is matte, not a plated mechanical part.
            material = leaf.ViewObject.ShapeAppearance[0]
            material.SpecularColor = (0.0, 0.0, 0.0)
            leaf.ViewObject.ShapeAppearance = [material]
        leaves.append(leaf)
    return tuple(leaves)
