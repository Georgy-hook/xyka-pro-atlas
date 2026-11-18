"""Local package solids for the component face of GYS005-S-088-A4.3 (mm).

Call package(c, positioned_part, style, mark=''). The XY origin is the centre
of the moulding, not a lead centroid. +Z is out of the soldermask; nothing
extends through the board. Only the caller places/rotates the App::Part.

* qfn28: laser index at (-x,+y); pad 1 on the west edge, y=+1.20.
* flash8: four pins along x on each ±y edge. As in the Hongchip TOP view,
  pin 1 is (-x,-y); HCT reads toward +x. Do not mirror this footprint.
* tab4: broad tab +y, three small exits -y. ss14: band +x.
* sot23: the pair at y<0, the single lead at y>0; Y1 is opt-in.
* qfn16 is the requested selector for the UNKNOWN **5 per side** part.
  No unseen centre slug, pin numbering or function inferred for it.
* sop8small is a generic narrow outline, NOT the Hongchip package.
* buzz: D and H override the estimated outside diameter and mounted height;
  the moulded + is on the -y half. No assumed PCB drill/pin pattern.

The master shapes are local, cached, native Open CASCADE B-reps. FCStd/STEP
carry solid text and do not require this module, a font or a proxy to reopen.
The land/fillet shapes describe the photographed mounting, NOT production
footprints. Colours distinguish surfaces; they do not certify metallurgy.
"""

from dataclasses import dataclass
from functools import lru_cache
from math import acos, cos, isfinite, radians, sin, sqrt, tan
from pathlib import Path

import FreeCAD as App
import Part


V = App.Vector
_Z = V(0, 0, 1)
_LAND = 0.030  # Estimated exposed land surface above the mask datum.
_SEAT = 0.065  # Lead seating plane incl. land and a thin solder bond line.
_INK = 0.009   # Visibility thickness of a laser/print surface, not a coating spec.
BUZZ_D = 13.0
BUZZ_H = 8.5

_HONGCHIP = 'https://www.scribd.com/embeds/1053108175/content?start_page=84&view_mode=scroll'
_NEX = 'https://assets.nexperia.com/documents/'


@dataclass(frozen=True)
class _Evidence:
    title: str
    source: str
    confidence: str
    body_colour: tuple


_CONF = 'ФОТО + НОМИНАЛ ДАТАШИТА'
_FAMILY = 'ФОРМА ПО ФОТО; РАЗМЕРЫ ПО ТИПОВОМУ ЧЕРТЕЖУ'
_EST = 'ОЦЕНКА / ESTIMATE'
_DATA = {
    'qfn28': _Evidence('AT32F421G8U7 · QFN28',
                       'IMG_8914; Artery DS_AT32F421 v2.02 §6.5, fig.32 / table 50, pp.65–66: '
                       'https://www.arterychip.com/download/DS/DS_AT32F421_V2.02_EN.pdf',
                       _CONF, (0.165, 0.162, 0.158)),
    'flash8': _Evidence('HC25FQ128GSSIG · SOP8-208',
                        'IMG_8913/8914/8915; Hongchip QA-DT-176 rev.1.1, §9.1 p.84, '
                        f'§10 pp.90–91: {_HONGCHIP}', _CONF, (0.19, 0.19, 0.185)),
    'tab4': _Evidence('6209A · SOT-89-like',
                      'IMG_8908/8909/8915; аналог геометрии, Nexperia SOT89 fig.1: '
                      + _NEX + 'package-information/SOT89.pdf', _FAMILY, (0.20, 0.195, 0.185)),
    'ss14': _Evidence('D26 · SS14', 'IMG_8908/8909/8915; аналог SMA (DO-214AC), '
                      'Vishay 88746 p.4: https://www.vishay.com/docs/88746/ss12.pdf',
                      _FAMILY, (0.162, 0.15, 0.154)),
    'sot23': _Evidence('SOT-23', 'IMG_8908/8915; аналог Nexperia SOT23 fig.1: '
                       + _NEX + 'outline-drawing/SOT23.pdf', _FAMILY, (0.155, 0.155, 0.15)),
    'qfn16': _Evidence('UNKNOWN · квадратный 20',
                       'IMG_8915 (1152×2048), ROI x835:973 y764:910; IMG_8914',
                       '5 × 4 ПО ФОТО; ГАБАРИТЫ ОЦЕНОЧНЫЕ', (0.172, 0.166, 0.155)),
    'sop8small': _Evidence('UNKNOWN · SO8 узкий',
                           'Типовой корпус, не идентификация микросхемы; Nexperia SO8 '
                           'SOT96-1 fig.1: ' + _NEX + 'package-information/SOT96-1.pdf',
                           _EST, (0.165, 0.17, 0.178)),
    'buzz': _Evidence('Зуммер', 'IMG_8908/8909/8910/8913/8915; внешняя форма по фото',
                      _EST, (0.113, 0.113, 0.117)),
}
_ROLE = {
    'Body': ('корпус', None),
    'Leads': ('выводы', (0.68, 0.70, 0.69)),
    'Lands': ('посадочные площадки', (0.61, 0.59, 0.525)),
    'Solder': ('галтели припоя', (0.71, 0.73, 0.74)),
    'Legend': ('маркировка', (0.61, 0.585, 0.51)),
}


def _compound(shapes):
    return Part.makeCompound(list(shapes))


def _placed(shape, x=0.0, y=0.0, z=0.0, angle=0.0):
    result = shape.copy()
    loc = App.Placement(V(x, y, z), App.Rotation(_Z, angle))
    result.Placement = loc.multiply(result.Placement)
    return result


def _poly(points):
    return Part.makePolygon([*points, points[0]])


def _prism(outline, base, height):
    return Part.Face(_poly([V(x, y, base) for x, y in outline])).extrude(V(0, 0, height))


def _chamfer_ring(length, width, z, clip):
    x, y = length / 2, width / 2
    xy = [(-x + clip, -y), (x - clip, -y), (x, -y + clip), (x, y - clip),
          (x - clip, y), (-x + clip, y), (-x, y - clip), (-x, -y + clip)]
    return _poly([V(a, b, z) for a, b in xy])


def _mould(length, width, sections, clip):
    """Corresponding rings: mould draft, parting belt and crown facets."""
    rings = [_chamfer_ring(length - 2 * inset, width - 2 * inset, z, clip)
             for z, inset in sections]
    return Part.makeLoft(rings, True, True)


def _wire(segments):
    """A 2-point segment is straight; 3 points specify a genuine circular arc."""
    return Part.Wire([Part.makeLine(*s) if len(s) == 2 else Part.Arc(*s).toShape()
                      for s in segments])


def _land(inside, outside, width, radius):
    """Rounded plated land centred on x=0, extending out towards +y."""
    h = width / 2
    r = min(radius, h * 0.99, (outside - inside) * 0.49)
    q = r / sqrt(2)
    a, b, c, d = (V(-h + r, inside, 0), V(h - r, inside, 0),
                  V(h, inside + r, 0), V(h, outside - r, 0))
    e, f, g, j = (V(h - r, outside, 0), V(-h + r, outside, 0),
                  V(-h, outside - r, 0), V(-h, inside + r, 0))
    wire = _wire([(a, b), (b, V(h - r + q, inside + r - q, 0), c), (c, d),
                  (d, V(h - r + q, outside - r + q, 0), e), (e, f),
                  (f, V(-h + r - q, outside - r + q, 0), g), (g, j),
                  (j, V(-h + r - q, inside + r - q, 0), a)])
    return Part.Face(wire).extrude(V(0, 0, _LAND))


def _joint(inside, tip, outside, width, rise):
    """Bond line plus concave toe fillet, tangent to the land and terminal."""
    def p(y, z):
        return V(-width / 2, y, z)

    bottom, end = p(inside, _LAND), p(outside, _LAND)
    wet, toe, heel = p(tip, _SEAT + rise), p(tip, _SEAT), p(inside, _SEAT)
    curve = Part.BezierCurve()
    curve.setPoles([end, p(tip, _LAND), wet])
    wire = Part.Wire([Part.makeLine(bottom, end), curve.toShape(), Part.makeLine(wet, toe),
                      Part.makeLine(toe, heel), Part.makeLine(heel, bottom)])
    return Part.Face(wire).extrude(V(width, 0, 0))


def _stamped(path, radii, width, gauge):
    """Constant-gauge formed strip. Fillet the YZ neutral line, then offset its
    lines and circular bends on *both* sides before extruding in x. Also makes
    the reverse-fold J terminals; no boxes masquerading as descending leads.
    """
    pts = [V(-width / 2, y, z) for y, z in path]
    dirs = [(b - a).normalize() for a, b in zip(pts, pts[1:])]
    normals = [V(0, -u.z, u.y) for u in dirs]

    def boundary(offset):
        here = pts[0] + offset * normals[0]
        result = []
        for i, radius in enumerate(radii):
            u, v = dirs[i:i + 2]
            n, m = normals[i:i + 2]
            turn = 1 if u.y * v.z > u.z * v.y else -1
            angle = acos(max(-1.0, min(1.0, u.dot(v))))
            setback = radius * tan(angle / 2)
            entry = pts[i + 1] - u * setback
            centre = entry + turn * radius * n
            a = entry + offset * n
            b = pts[i + 1] + v * setback + offset * m
            mid = centre + ((a - centre) + (b - centre)).normalize() * (radius - turn * offset)
            result.extend([(here, a), (a, mid, b)])
            here = b
        result.append((here, pts[-1] + offset * normals[-1]))
        return result

    upper, lower = boundary(gauge / 2), boundary(-gauge / 2)
    loop = upper + [(upper[-1][-1], lower[-1][-1])]
    loop += [tuple(reversed(s)) for s in reversed(lower)]
    loop.append((lower[0][0], upper[0][0]))
    return Part.Face(_wire(loop)).extrude(V(width, 0, 0))


def _copies(unit, rows):
    for angle, offsets in rows:
        a = radians(angle)
        for x in offsets:
            yield _placed(unit, x=x * cos(a), y=x * sin(a), angle=angle)


def _layers(body, leads, lands, joints, description, terminal_note):
    return (('Body', body, description), ('Leads', _compound(leads), terminal_note),
            ('Lands', _compound(lands), 'Контур открытой металлизации оценочный, не Gerber.'),
            ('Solder', _compound(joints), 'Оценка: слой под выводом и вогнутая галтель снаружи.'))


def _qfn_contact(side, width, depth, metal_h):
    tip = side / 2
    inner = tip - depth
    r = width / 2
    a, b = V(-r, tip, _SEAT), V(-r, inner + r, _SEAT)
    c, d = V(r, inner + r, _SEAT), V(r, tip, _SEAT)
    wire = _wire([(a, b), (b, V(0, inner, _SEAT), c), (c, d), (d, a)])
    return Part.Face(wire).extrude(V(0, 0, metal_h))


def _slug(size, clip, base, height):
    # Bottom view in Artery fig.32 is mirrored relative to this TOP-view frame.
    t = size / 2
    return _prism([(-t, -t), (t, -t), (t, t), (-t + clip, t), (-t, t - clip)], base, height)


def _qfn(mcu):
    if mcu:
        side, n, extra, z_top = 4.0, 7, 0.26, _SEAT + 0.75
        note = '4 × 4; A=0.75, A1=0.02; семь выводов на сторону, шаг 0.40 мм.'
        term_note = '28 × b=0.20, L=0.40, c=0.20; открытая EP 2.40 × 2.40 со срезом 0.35.'
    else:
        side, n, extra, z_top = 3.0, 5, 0.45, _SEAT + 0.80
        note = ('Не QFN16: на IMG_8915 верхние центры x≈885,894,904,914,924 px; '
                'также пять снизу и слева. Шаг ≈9.6 px против ≈9.5 px у U3 (0.40 мм). '
                'Литьё ≈74 px → ≈3 × 3 мм; высота не измерена.')
        term_note = '20 краевых контактов; шаг ≈0.40. Скрытая центральная площадка не установлена.'
    tip = side / 2
    xs = [(i - (n - 1) / 2) * 0.4 for i in range(n)]
    rows = [(a, xs) for a in (0, 90, 180, 270)]
    body = _mould(side, side, [(_SEAT + 0.02, 0.018), (_SEAT + 0.10, 0.0),
                               (z_top - 0.04, 0.0), (z_top, 0.035)], 0.042)
    leads = list(_copies(_qfn_contact(side, 0.20, 0.40, 0.20), rows))
    lands = list(_copies(_land(tip - 0.40, tip + extra, 0.25, 0.075), rows))
    fillet = _joint(tip - 0.28, tip, tip + extra - 0.045, 0.202, 0.16)
    joints = list(_copies(fillet, rows))
    if mcu:
        leads.append(_slug(2.40, 0.35, _SEAT, 0.20))
        # Only the component slug is documented; its matching land is estimated.
        lands.append(_slug(2.36, 0.35, 0, _LAND))
        joints.append(_slug(2.34, 0.35, _LAND, _SEAT - _LAND))
    body = body.cut(leads)
    return _layers(body, leads, lands, joints, note, term_note)


@dataclass(frozen=True)
class _WingCase:
    length: float
    width: float
    span: float
    height: float  # overall from seating plane
    clearance: float
    lead: float
    gauge: float
    bend: float
    pad_extra: float
    land_width: float


_WINGS = {
    # Hongchip: D=5.00..5.33, E1=5.13..5.38; midpoints, not specified nominals.
    'flash8': _WingCase(5.165, 5.255, 7.90, 1.95, 0.15, 0.425, 0.22, 0.21, 0.48, 0.68),
    'sop8small': _WingCase(4.90, 3.90, 6.00, 1.55, 0.15, 0.41, 0.17, 0.17, 0.36, 0.62),
    'sot23': _WingCase(2.90, 1.30, 2.30, 1.00, 0.065, 0.42, 0.12, 0.115, 0.38, 0.64),
}


def _wing_case(style):
    d = _WINGS[style]
    bottom = _SEAT + d.clearance
    top = _SEAT + d.height
    hip = (bottom + top) / 2
    reach = (d.span - d.width) / 2
    root, tip = d.width / 2, d.span / 2
    foot_z = _SEAT + d.gauge / 2
    foot_start = root + 0.54 * reach
    path = [(root, hip), (root + 0.26 * reach, hip), (foot_start, foot_z), (tip, foot_z)]
    lead = _stamped(path, [d.bend, d.bend], d.lead, d.gauge)
    draft = 0.06 if style == 'sot23' else 0.13
    body = _mould(d.length, d.width, [(bottom, draft), (hip - d.gauge / 2, 0),
                                      (hip + d.gauge / 2, 0), (top - draft, draft),
                                      (top, 1.65 * draft)], draft * 0.56)
    if style == 'flash8':
        # Moulded index pit, not a painted disk. Sphere only nicks the roof.
        pit = Part.makeSphere(0.38, V(-d.length / 2 + 0.64, -root + 0.64, top + 0.285))
        body = body.cut(pit)
        note = ('SOP8 208 mil: D 5.00–5.33; E1 5.13–5.38; выбраны середины. '
                'E=7.90, A1=0.15, A2=1.80. IMG_8915: почти квадратное литьё '
                '(≈130 px вдоль ряда, шаг ≈31 px). Ключ -x,-y по §9.1 и IMG_8913–15.')
    elif style == 'sop8small':
        note = 'Сменный типовой SO8 4.90 × 3.90; не Flash. Ключ и надпись не додуманы.'
    else:
        note = '2.90 × 1.30, один вывод +y; код Y1 только для явно указанных экземпляров.'
    if style == 'sot23':
        rows = [(0, [0]), (180, [-0.95, 0.95])]
        term_note = 'Два вывода с шагом 1.90 мм напротив одиночного; назначение не задано.'
    else:
        xs = [(i - 1.5) * 1.27 for i in range(4)]
        rows = [(0, xs), (180, xs)]
        term_note = f'4 + 4; e=1.27 мм, размах {d.span:.2f}; два радиуса изгиба и полка.'
    outer = tip + d.pad_extra
    land = _land(foot_start - 0.24, outer, d.land_width, d.land_width * 0.26)
    joint = _joint(foot_start + 0.04, tip, outer - 0.09, d.lead + 0.018, d.gauge * 0.91)
    return _layers(body, _copies(lead, rows), _copies(land, rows), _copies(joint, rows),
                   note, term_note)


def _tab_case():
    # SOT89 drawing: planar leadframe, NOT a four-sided gullwing package. The
    # middle exit and clipped broad tab are the two ends of one stamping.
    wide, narrow = 0.8, 0.235
    tab_tip, pin_tip = 1.75, 2.25
    gauge = 0.32
    tab = _prism([(-narrow, -pin_tip), (narrow, -pin_tip), (narrow, -0.65), (wide, -0.65),
                  (wide, tab_tip - 0.19), (wide - 0.19, tab_tip), (-wide + 0.19, tab_tip),
                  (-wide, tab_tip - 0.19), (-wide, -0.65), (-narrow, -0.65)], _SEAT, gauge)
    blade = _prism([(-0.21, -0.98), (0.21, -0.98), (0.21, -pin_tip + 0.04),
                    (0.17, -pin_tip), (-0.17, -pin_tip), (-0.21, -pin_tip + 0.04)],
                   _SEAT, gauge)
    leads = [tab, _placed(blade, x=-1.5), _placed(blade, x=1.5)]
    body = _mould(4.50, 2.50, [(_SEAT + 0.02, 0), (_SEAT + gauge, 0),
                               (_SEAT + 1.45, 0.155), (_SEAT + 1.50, 0.195)], 0.075)
    body = body.cut(leads)
    rows = [(180, [-1.50, 0, 1.50])]
    lands = list(_copies(_land(1.04, 2.58, 0.76, 0.20), rows))
    lands.append(_land(0.47, 2.27, 2.06, 0.60))
    joints = []
    for x, width in [(-1.5, 0.38), (0.0, 0.46), (1.5, 0.38)]:
        joints.append(_placed(_joint(1.27, pin_tip, 2.51, width, 0.23), x=x, angle=180))
    joints.append(_joint(0.86, tab_tip, 2.20, 1.25, 0.25))
    return _layers(body, leads, lands, joints, '6209A; 4.50 × 2.50. Производитель не установлен.',
                   'Три узких выхода -y, противоположный широкий выход +y; шаг 1.50 мм.')


def _diode():
    length, width = 4.25, 2.665
    gauge, span = 0.215, 5.10
    root, tip = length / 2, span / 2
    hip = _SEAT + 1.025
    foot = _SEAT + gauge / 2
    back = tip - gauge / 2
    lead = _stamped([(root, hip), (back, hip), (back, foot), (tip - 1.09, foot)],
                    [0.155, 0.19], 1.45, gauge)
    rows = [(-90, [0]), (90, [0])]  # Formed in YZ; orient the pair along x.
    leads = list(_copies(lead, rows))
    top = _SEAT + 2.13
    body = _mould(length, width, [(_SEAT + 0.105, 0.11), (hip - gauge / 2, 0.0),
                                  (hip + gauge / 2, 0.0), (top - 0.075, 0.115),
                                  (top, 0.16)], 0.07).cut(leads)
    land = _land(tip - 1.26, tip + 0.42, 1.85, 0.17)
    joint = _joint(tip - 1.04, tip, tip + 0.36, 1.40, 0.39)
    return _layers(body, leads, _copies(land, rows), _copies(joint, rows),
                   'SMA-подобный SS14: литьё 4.25 × 2.665, полоса +x (IMG_8915).',
                   'Два широких J-образных вывода с подгибом под основание; размах 5.10 мм.')


def _buzzer(d, h):
    # Meridional section, revolved: open port into an unspecified clearance
    # volume. Only the exterior is evidence; no guessed diaphragm or mechanism.
    r = d / 2
    port = 0.185 * r
    roof = 0.988 * h
    profile = [(0, 0), (0.974 * r, 0), (r, 0.022 * h), (r, 0.069 * h),
               (0.991 * r, 0.079 * h), (0.991 * r, 0.096 * h), (r, 0.106 * h),
               (r, 0.965 * h), (0.983 * r, h), (0.964 * r, h), (0.952 * r, roof),
               (port + 0.026 * r, roof), (port, 0.966 * h), (port, 0.89 * h),
               (0.87 * r, 0.89 * h), (0.87 * r, 0.10 * h), (0, 0.10 * h)]
    section = Part.Face(_poly([V(a, 0, b) for a, b in profile]))
    shell = section.revolve(V(), _Z, 360)
    # Black-on-black polarity mark. Draft the relief so even its top view
    # catches a little light without putting fictitious white ink on the cap.
    y = -0.69 * r
    relief = 0.010 * h
    centre = V(0, y, roof)
    ring = Part.makeCone(0.184 * r, 0.177 * r, relief, centre).cut(
        Part.makeCone(0.157 * r, 0.164 * r, relief, centre))

    def cross_wire(arm, stroke, z):
        xy = [(-stroke, arm), (stroke, arm), (stroke, stroke), (arm, stroke),
              (arm, -stroke), (stroke, -stroke), (stroke, -arm), (-stroke, -arm),
              (-stroke, -stroke), (-arm, -stroke), (-arm, stroke), (-stroke, stroke)]
        return _poly([V(a, y + b, z) for a, b in xy])

    plus = Part.makeLoft([cross_wire(0.120 * r, 0.029 * r, roof),
                          cross_wire(0.112 * r, 0.020 * r, roof + relief)], True, True)
    shell = shell.fuse([ring, plus]).removeSplitter()
    note = (f'Ø{d:g} × {h:g} мм, оценка; фаска, буртик, канал Ø{2 * port:.2f} и литой +. '
            'Содержимое, скрытые выводы и отверстия в плате не наблюдаются, не заданы.')
    return (('Body', shell, note),)


@lru_cache(maxsize=32)
def _geometry(style, d, h):
    if style in _WINGS:
        return _wing_case(style)
    if style in ('qfn28', 'qfn16'):
        return _qfn(style == 'qfn28')
    if style == 'tab4':
        return _tab_case()
    if style == 'ss14':
        return _diode()
    return _buzzer(d, h)


@lru_cache(maxsize=1)
def _font():
    # The first choice ships with FreeCAD. Font is needed only at build time.
    candidates = (Path(App.getResourceDir()) / 'Mod/TechDraw/Resources/fonts/osifont-lgpl3fe.ttf',
                  Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                  Path('/System/Library/Fonts/Supplemental/Arial.ttf'), Path('C:/Windows/Fonts/arial.ttf'))
    for font in candidates:
        if font.is_file():
            return font
    raise RuntimeError('Install FreeCAD TechDraw osifont or a system DejaVu Sans/Arial font')


@lru_cache(maxsize=96)
def _letter_faces(line):
    font = _font()
    glyphs = Part.makeWireString(line, str(font.parent) + '/', font.name, 1.0, 0.018)
    return _compound(Part.makeFace(wires, 'Part::FaceMakerBullseye') for wires in glyphs if wires)


def _text(text, x, y, z, width, height, angle=0, align='centre', leading=1.30):
    """Typeset at one common scale; preserve counters in 0/8/B/R etc."""
    lines = [_letter_faces(s.strip()) for s in text.splitlines() if s.strip()]
    if not lines:
        return []
    boxes = [line.BoundBox for line in lines]
    cap = max(b.YLength for b in boxes)
    longest = max(b.XLength for b in boxes)
    advance = leading * cap
    total = cap + advance * (len(lines) - 1)
    scale = min(width / longest, height / total)
    ink = []
    for i, (line, b) in enumerate(zip(lines, boxes)):
        offset = -b.XLength / 2
        if align == 'left':
            offset = -longest / 2
        elif align == 'lot' and i == len(lines) - 1:
            offset = longest / 2 - b.XLength
        faces = _placed(line, x=offset - b.XMin, y=total / 2 - cap - i * advance - b.YMin)
        faces.scale(scale)
        lettering = _compound(face.extrude(V(0, 0, _INK)) for face in faces.Faces)
        ink.append(_placed(lettering, x=x, y=y, z=z, angle=angle))
    return ink


_DEFAULT_MARK = {'qfn28': 'AT32F421\nG8U7', 'flash8': 'HCT\n25FQ128GSSIG\n2546',
                 'tab4': '6209A', 'ss14': 'SS14'}


def _inscription(style, mark):
    if not isinstance(mark, str):
        raise TypeError('mark must be a string; use newlines for multiple lines')
    text = mark.strip()
    if style == 'flash8' and text.upper() in {'HC25FQ128GSSIG', '25FQ128GSSIG', 'HCT/25FQ128GSSIG/2546'}:
        text = ''
    if style == 'qfn28' and text.upper() == 'AT32F421G8U7':
        text = ''
    return text or _DEFAULT_MARK.get(style, '')


@lru_cache(maxsize=64)
def _legend(style, text):
    if style == 'buzz':
        return None  # Polarity mark is moulded into the roof itself.
    parts = []
    if style == 'qfn28':
        z = _SEAT + 0.75
        parts.append(Part.makeCylinder(0.137, _INK, V(-1.55, 1.53, z)))
        parts += _text(text, 0.08, 0, z, 3.12, 2.52, -90, 'left')
    elif style == 'ss14':
        z = _SEAT + 2.13
        for x, w in ((1.06, 0.064), (1.31, 0.075)):
            parts.append(Part.makeBox(w, 2.25, _INK, V(x, -1.125, z)))
        parts += _text(text, -0.42, 0, z, 2.43, 0.92, 180)
    elif style == 'flash8':
        # The short 2546 is right-aligned in both the photo and marking table.
        parts += _text(text, 0, 0.12, _SEAT + _WINGS[style].height, 4.26, 2.62,
                       align='lot', leading=1.70)
    elif style == 'tab4':
        parts += _text(text, 0, 0, _SEAT + 1.50, 3.60, 1.55)
    elif style in _WINGS:
        d = _WINGS[style]
        parts += _text(text, 0, 0, _SEAT + d.height, d.length * 0.76, d.width * 0.56)
    else:
        parts += _text(text, 0, 0, _SEAT + 0.80, 2.34, 1.90)
    return _compound(parts) if parts else None


def package(c, parent, style, mark='', *, D=None, H=None):
    """Populate an existing App::Part; return the registered Part::Feature tuple.

    ``mark`` overrides the known default; use literal newlines, e.g.
    ``mark='6209A\\n2522/33'`` on U5. Unknowns and SOT-23 are blank unless
    explicitly marked. D/H apply only to buzz; H includes its upper rim.
    """
    if style not in _DATA:
        raise ValueError(f'Unknown package {style!r}; choose from {", ".join(_DATA)}')
    if style != 'buzz' and (D is not None or H is not None):
        raise ValueError('D and H overrides are only defined for buzz')
    d = float(BUZZ_D if D is None else D)
    h = float(BUZZ_H if H is None else H)
    if not all(isfinite(v) and v > 0 for v in (d, h)):
        raise ValueError('D and H must be finite positive millimetres')
    text = _inscription(style, mark)
    data = _DATA[style]
    layers = list(_geometry(style, d, h))
    legend = _legend(style, text)
    if legend is not None:
        layers.append(('Legend', legend, ' / '.join(text.splitlines())))
    objects = []
    for role, shape, note in layers:
        label, colour = _ROLE[role]
        source = data.source
        confidence = data.confidence
        if role in ('Lands', 'Solder'):
            confidence = _EST
        elif role == 'Legend':
            if (text == _DEFAULT_MARK.get(style) or (style == 'sot23' and text == 'Y1')
                    or (style == 'tab4' and text == '6209A\n2522/33')):
                confidence = 'НАДПИСЬ ПО ФОТО'
            else:
                confidence = 'ТЕКСТ ЗАДАН ВЫЗОВОМ package()'
        item = c.solid(parent, f'{parent.Name}_{role}', f'{data.title} · {label}', shape.copy(),
                       colour or data.body_colour, source, confidence, note)
        objects.append(item)
    return tuple(objects)
