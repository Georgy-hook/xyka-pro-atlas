"""Registered component-side features of GYS005-S-088-A4.3. No netlist.

footprints(): fresh editable records. Origins, pad sizes and offsets are mm;
local +x/+y coincide with physical +u/+v at zero angle. Apply R_z(angle)
then translate by (u,v); do NOT mirror until converting to the editor frame.
outline is a closed local F.Fab silhouette, not board ink. pin1 is a body
mark, not the centre of a copper pad. marking is literal *package* text; for
master-text marks, marking_layout gives its local centre, CCW angle and
typesetting box, not a measured glyph outline. Do not put these on F.SilkS.
seating, where present, gives model heights above the component mask (w=0).
Numerical precision preserves the model, not the accuracy of the actual PCB.

smd = front copper; paste=False on exposed/vacant lands. pth = plated round
through-hole (plating estimated); npth = non-plated mechanical drill, id=''.
rratio = KiCad corner radius / shorter side; chamfer on U3.EP is given in the
physical local frame. fitted=False means a vacant component site (D27);
standalone test lands, holes and discs are present features, not DNP parts.

legends(): registered, centred board text (not body markings or arbitrary
ref text). silk_graphics(): measured board ink primitives in absolute UV.
No FreeCAD, images, other project files or installed package required.
"""
import json
from math import cos, pi, sin
from pathlib import Path

__all__ = ['footprints', 'legends', 'silk_graphics']
_DATA = json.loads(Path(__file__).with_name('footprints.json').read_text(encoding='utf-8'))
_SURFACE = 'pcb_surface.py; IMG_8914/8915/8908/8909/AD, registered mask plane'
_WIRE = 'pcb_connections.py + pcb_registration.json; IMG_8914/8920/8921/AD206911'
_HEADER = 'pcb_connections.py + pcb_registration.json; IMG_8913/8915/8916/8919/AD206911'
_GEOM = 'Positional IDs in the unrotated package frame; device pin numbers and functions unknown.'
_PACKAGE_SRC = {
    'qfn28': 'IMG_8914; Artery DS_AT32F421 v2.02 §6.5, Fig.32/Table 50',
    'flash8': 'IMG_8913/8914/8915; Hongchip QA-DT-176 rev.1.1 §9.1/§10, SOP8-208',
    'sop8small': 'IMG_8914/8920; narrow SO8 geometric analogue, not an identification',
    'qfn20': 'IMG_8915 x835:973 y764:910; IMG_8914: five contacts per edge',
    'tab4': 'IMG_8908/8909/8915; SOT89-like envelope, not a device identification',
    'ss14': 'IMG_8908/8909/8915; marked SS14; SMA-like geometry',
    'sot23': 'IMG_8908/8915; SOT23 family envelope (Q8 position: IMG_8914)',
    'buzz': 'IMG_8908/8909/8910/8913/8915; exterior only',
}

# Electrical footprint registration overrides. footprints.json retains the
# issued mechanical observations. Original JPEG pixels -> physical UV with
# pcb_registration.json, no rescaling/EXIF rotation; no 3-D master edits.
_OPTICAL = {
    'Q8': dict(angle=-90, north_limit=1.2105675,
               evidence='IMG_8914: pair ≈(753,985),(817,985); single near (804,930). '
                        'Two toes face down-image. Keep the mould centre (797,959); '
                        'the single toe is partly hidden: (804,930) bounds its exposed '
                        'reach on the Q8 side of the WireUpper cap/mask gap at y≈928–930.'),
    'U_QFN20': dict(origin=(1.2174, 29.1879),
                    evidence='IMG_8915: 10-toe mask-plane fit. E x=885.5,895.5,905,914.5,924 '
                             'at y≈794.4; W x=879.5,889.7,899.3,909,918.4 at y≈882.3. '
                             'Pitch 0.40, angle 0; labels are geometric, not a die pinout.'),
    'U_FLASH': dict(origin=(-7.5812806, 33.3322582),
                    south_limits=(4.0110744, 4.0255446, 4.1419747, 4.0766420),
                    evidence='IMG_8915: rigid translation from 8 toe centres, x=732,765,795,828 '
                             'at y≈1188 and x=740,772,802,836 at y≈985. Package span 7.90 '
                             'and pitch 1.27 unchanged. Outer edges of lands 1–4: IMG_8914 '
                             '(192.9,1092.1),(230.5,1096.8),(267.4,1104.4),(306.0,1107.7); '
                             'IMG_8915 (730.9,1198.5),(762.7,1197.5),(794.1,1199.3),(825.7,1195.4). '
                             'Mean rectified radial reaches at the wet-metal/dark-mask transition, '
                             'not body-toe tips; under-lead heels and widths remain model estimates.'),
    'D27': dict(origin=(14.0838528, 44.1699332),
                lands=(('1', -.0108036, -1.1387415, .96913, 1.09195),
                       ('2', .0108036, 1.1387415, .96314, 1.20035)),
                bar=(14.1008587, 44.1213282, 1.16620, .77011),
                evidence='IMG_8915: vacant land 1 (547,440), land 2 (482,437); origin is midpoint '
                         'of rectified centres. Pixel spans (left,right;top,bottom): '
                         '1=(531,562;421,452.5), 2=(464.5,499;419,450.5). Ink bar at (516,438), '
                         'span ≈(503,525;419,457). Reported widths are projected mask-edge estimates.'),
}


def _site(ref, value, u, v, pads, source, note, *, angle=0, fitted=True, **details):
    return dict(ref=ref, value=value, u=u, v=v, angle=angle, pads=pads, source=source,
                fitted=fitted, note=note, **details)


def _pad(pid, x, y, w, h, shape='rect', kind='smd', **details):
    return dict(id=str(pid), x=round(x, 9), y=round(y, 9), w=round(w, 9),
                h=round(h, 9), shape=shape, kind=kind, **details)


def _rounded(pid, x, y, w, h, radius):
    return _pad(pid, x, y, w, h, 'roundrect', rratio=radius/min(w, h))


def _outline(width, height, clip=0):
    x, y = width/2, height/2
    if clip:
        points = [[-x+clip, -y], [x-clip, -y], [x, -y+clip], [x, y-clip],
                  [x-clip, y], [-x+clip, y], [-x, y-clip], [-x, -y+clip]]
    else:
        points = [[-x, -y], [x, -y], [x, y], [-x, y]]
    return points + [points[0][:]]


def _seating(base, top, lead_plane=.065, land_top=.030):
    return dict(body_bottom=base, body_top=top, lead_plane=lead_plane, land_top=land_top)


def _qfn(mcu):
    side, n, extra = (4., 7, .26) if mcu else (3., 5, .45)
    span = .40 + extra                     # radial land = [side/2-.40, side/2+extra]
    r = side/2 - .40 + span/2
    pads = []
    for edge in ('W', 'S', 'E', 'N'):
        for i in range(n):
            t = (i - (n-1)/2)*.40
            x, y, w, h = {'W': (-r, -t, span, .25), 'S': (t, -r, .25, span),
                          'E': (r, t, span, .25), 'N': (-t, r, .25, span)}[edge]
            # TOP-view MCU numbers CCW, starting NW on the west side. For the
            # unknown, describe edges only: W/E count top down, S/N left to right.
            idx = n-i if edge in ('E', 'N') else i+1
            pid = str(len(pads)+1) if mcu else f'{edge}{idx}'
            pads.append(_rounded(pid, x, y, w, h, .075))
    details = dict(outline=_outline(side, side, .042),
                   seating=_seating(.085, .815 if mcu else .865))
    if mcu:
        # 2.40 mm is the *slug*. Matching PCB copper is 2.36 with a NW clip.
        pads.append(_pad('EP', 0, 0, 2.36, 2.36, 'roundrect', rratio=0.,
                         chamfer='NW', chamfer_ratio=.35/2.36))
        details.update(pin1=[-1.55, 1.53], pin1_radius=.137)
    return pads, details


# length/width of mould, lead span, outer toe extension, land width,
# body clearance above lead seating plane, package height above that plane.
_WINGS = {'flash8': (5.165, 5.255, 7.90, .48, .68, .15, 1.95),
          'sop8small': (4.90, 3.90, 6., .36, .62, .15, 1.55),
          'sot23': (2.90, 1.30, 2.30, .38, .64, .065, 1.)}


def _wing(style):
    length, width, span, extra, w, clearance, height = _WINGS[style]
    inner = width/2 + .54*(span-width)/2 - .24
    outer = span/2 + extra
    y = (inner+outer)/2
    if style == 'sot23':
        locations = [('SW', -.95, -y), ('SE', .95, -y), ('N', 0, y)]
    else:
        xs = [(i-1.5)*1.27 for i in range(4)]
        if style == 'flash8':
            locations = [(i+1, x, -y) for i, x in enumerate(xs)]
            locations += [(i+5, x, y) for i, x in enumerate(reversed(xs))]
        else:
            locations = [(f'{edge}{i+1}', x, dy) for edge, dy in [('S', -y), ('N', y)]
                         for i, x in enumerate(xs)]
    pads = [_rounded(pid, x, dy, w, outer-inner, w*.26) for pid, x, dy in locations]
    clip = .56*(.06 if style == 'sot23' else .13)
    details = dict(outline=_outline(length, width, clip),
                   seating=_seating(.065+clearance, .065+height))
    if style == 'flash8':
        details['pin1'] = [-length/2+.64, -width/2+.64]
        details['pin1_radius'] = (.38**2 - .285**2)**.5  # Aperture of the moulded pit at the roof.
    return pads, details


def _device(ref, style, u, v, angle, mark):
    if style in ('qfn28', 'qfn20'):
        mcu = style == 'qfn28'
        pads, details = _qfn(mcu)
        value = 'AT32F421G8U7' if mcu else 'UNKNOWN QFN20'
        note = ('TOP view: west pin 1 at y=+1.20; separate clipped EP land, no assigned net.'
                if mcu else _GEOM + ' No observed index or verified centre land.')
    elif style in _WINGS:
        pads, details = _wing(style)
        if style == 'flash8':
            value = 'HC25FQ128GSSIG'
            note = '208 mil SOP8. TOP: pins 1–4 from −x to +x on −y, then 5–8 back on +y.'
        else:
            value = ('UNKNOWN SO8' if style == 'sop8small' else 'SOT23')
            if mark:
                value += ' · ' + mark
            note = _GEOM + ' Only legible top code is transcribed; no commercial ID implied.'
    elif style == 'tab4':
        pads = [_rounded(k, x, -1.81, .76, 1.54, .20) for k, x in [('L', -1.5), ('C', 0), ('R', 1.5)]]
        pads.append(_rounded('TAB', 0, 1.37, 2.06, 1.80, .60))
        details = dict(outline=_outline(4.50, 2.50, .075), seating=_seating(.085, 1.565))
        value = '6209A · 3+tab'
        note = _GEOM + ' Independent land IDs, no assumed electrical tie between C and TAB.'
    elif style == 'ss14':
        pads = [_rounded('1', 2.13, 0, 1.68, 1.85, .17), _rounded('2', -2.13, 0, 1.68, 1.85, .17)]
        # Two top-face stripes: [centre x, centre y, width, height]. Not board silk.
        details = dict(outline=_outline(4.25, 2.665, .07), seating=_seating(.170, 2.195),
                       stripes=[[1.092, 0, .064, 2.25], [1.3475, 0, .075, 2.25]])
        value, note = 'SS14', 'Cathode = 1 on striped +x end; placed +90°, band faces crest (+v).'
    elif style == 'buzz':
        r = 11.74/2
        points = [[r*cos(i*pi/36), r*sin(i*pi/36)] for i in range(72)]
        pads = []
        details = dict(outline=points+[points[0][:]], seating=dict(body_bottom=0., body_top=8.3),
                       marking_xy=[0, -.69*r], diameter=2*r)
        value = 'Buzzer · Ø11.74'
        note = 'Moulded + on −y half. Acoustic port in the cap; no observed PCB drill or hidden terminals.'
    else:
        raise ValueError(f'Unrecognised footprint style: {style}')
    src = 'main_pcb.py / pcb_packages.py; ' + _PACKAGE_SRC[style]
    if ref in _OPTICAL:
        correction = _OPTICAL[ref]
        u, v = correction.get('origin', (u, v))
        angle = correction.get('angle', angle)
        src += '; electrical mask registration: ' + correction['evidence']
        if ref == 'Q8':
            # Measured upper bound, not a guessed solder joint shared with WireUpper.
            i = next(i for i, p in enumerate(pads) if p['id'] == 'N')
            inner = pads[i]['y'] - pads[i]['h']/2
            limit = correction['north_limit']
            pads[i] = _rounded('N', 0, (limit+inner)/2, .64, limit-inner, .64*.26)
        elif ref == 'U_FLASH':
            for i, outer in enumerate(correction['south_limits']):
                p = pads[i]  # Pins 1–4 are on local −y.
                inner = abs(p['y']) - p['h']/2
                pads[i] = _rounded(p['id'], p['x'], -(outer+inner)/2,
                                   p['w'], outer-inner, p['w']*.26)
    if mark:
        details['marking'] = mark
        # As typeset on pcb_packages' mould, separate from measured board ink.
        layout = {'qfn28': (.08, 0, -90, 3.12, 2.52, 'left', 1.30),
                  'flash8': (0, .12, 0, 4.26, 2.62, 'lot-right', 1.70),
                  'tab4': (0, 0, 0, 3.60, 1.55, 'centre', 1.30),
                  'ss14': (-.42, 0, 180, 2.43, .92, 'centre', 1.30),
                  'sot23': (0, 0, 0, 2.90*.76, 1.30*.56, 'centre', 1.30)}
        if style in layout:
            keys = ('x', 'y', 'angle', 'w', 'h', 'align', 'leading')
            details['marking_layout'] = dict(zip(keys, layout[style]))
        note += ' Body mark: ' + ' / '.join(mark.splitlines()) + '.'
    return _site(ref, value, u, v, pads, src, note, angle=angle, **details)


def _passive(ref, u, v, angle, length, width, finish, src):
    coated = finish in ('dark', 'shadow', 'marked')
    # Issued pcb_passives._chip geometry at w=0, not a generic 0402/0603 pad.
    inner = length*(.58 if coated else .62)/2
    outer = length/2 + min(.17, length*.10)
    x = (inner+outer)/2
    pads = [_pad(k, sign*x, 0, outer-inner, width) for k, sign in [('1', -1), ('2', 1)]]
    details = dict(outline=_outline(length, width), finish=finish,
                   seating=dict(body_bottom=.045, body_top=width*(.49 if coated else .79)))
    if ref == 'R13':
        details['marking'] = '300'  # Literal IMG_8915 top code, not an ohmic rating.
    return _site(ref, 'Two-ended chip · ' + finish, u, v, pads, 'pcb_passives.py; '+src,
                 'Individual photographed site. Pad 1 = −x end, 2 = +x; no polarity or electrical value inferred.',
                 angle=angle, **details)


def _terminals():
    for key, u, v, w in _DATA['wires']:
        d = 3.06 if key.startswith('B') else (2.86 if key.startswith('F') else 2.48)
        drill = 1.39 if key.startswith(('B', 'F')) else (.84 if key.startswith('Clear') else .86)
        pad = _pad(key, 0, 0, d, d, 'circle', 'pth', drill=drill)
        ref = 'J_' + key.replace('+', 'Plus').replace('-', 'Minus')
        yield _site(ref, 'Soldered wire', u, v, [pad], _WIRE,
                    'One observed wire. Pad label is not a net; Clear1/2 are descriptive IDs. Bore/plating estimated.',
                    seating=dict(land_top=.03, wire_exit=w))
    for key, u, v in _DATA['holes']:
        pad = _pad('', 0, 0, 1.90, 1.90, 'circle', 'npth', drill=1.90)
        yield _site('H_'+key, 'Mechanical bore', u, v, [pad], 'pcb_profile.py / main_pcb.py / pcb_registration.json',
                    'Registered bore; nominal Ø1.90 ±0.35 mm from photos; no annular copper.')
    mouths = _DATA['header_mouths']
    u = sum(x for x, _ in mouths)/4
    pads = [_pad(i, x-u, -5.33, .54, 1.62) for i, (x, _) in enumerate(mouths, 1)]
    pads += [_pad('MP1', -4.10, -3.16, 1.06, 2.), _pad('MP2', 4.10, -3.16, 1.06, 2.)]
    # Fixed shroud including its two side ears. The cable plug is not another PCB footprint.
    body = [[-3.53,-4.74],[3.53,-4.74],[3.53,-3.895],[4.18,-3.895],[4.18,-1.685],
            [3.53,-1.685],[3.53,-1.49],[-3.53,-1.49],[-3.53,-1.685],[-4.18,-1.685],
            [-4.18,-3.895],[-3.53,-3.895],[-3.53,-4.74]]
    yield _site('J_RGB', 'Side-entry 4-way', u, mouths[0][1], pads, _HEADER,
                'Origin at plug mouth, facing +v. Tails 1…4 increase in u; MP1/2 are hold-downs. '
                'Colours white/blue/black/red and adjacent V/R/G/B ink are not a verified pinout.',
                outline=body, seating=_seating(.10, 3.29, .028, .028))


def _opens():
    for label, u, v in _DATA['registered_lands']:
        edge = label in ('VCC', 'B1', 'G', 'R')
        d = 1.58 if edge else 1.
        pad = _pad(label, 0, 0, d, d, 'circle', paste=False)
        yield _site(('EDGE_' if edge else 'AUX_')+label, 'Open land', u, v, [pad], _SURFACE,
                    'Registered 8915 fit landmark. ID from visible legend, not a verified signal.')
    for label, v in [('V', 29.45), ('DIO', 27.51), ('CLK', 25.57), ('G', 23.63)]:
        yield _site('DBG_'+label, 'Open land', -13.04, v, [_pad(label, 0, 0, 1.04, 1.04, 'circle', paste=False)],
                    _SURFACE, 'Position in the photographed four-land strip; function unverified.')
    for label, v in [('RX', 26.67), ('TX', 25.42)]:
        yield _site('TP_'+label, 'Oval open land', -4.30, v, [_pad(label, 0, 0, 1.42, .74, 'oval', paste=False)],
                    _SURFACE, 'Master is an ellipse: native oval has the same major/minor axes, centre and bounds.')
    for ref, u, v, d, src in _DATA['discs']:
        yield _site(ref, 'Isolated open disc', u, v, [_pad('1', 0, 0, d, d, 'circle', paste=False)],
                    'pcb_passives.py; '+src, 'Flush rimless disc. No bore or assigned electrical function.')
    d27 = _OPTICAL['D27']
    pads = [_pad(*row, paste=False) for row in d27['lands']]
    yield _site('D27', 'Vacant two-land site', *d27['origin'], pads, _SURFACE+'; '+d27['evidence'],
                'Two visible lands and a central printed bar. IDs along +v; polarity unverified.', fitted=False)


def footprints() -> list[dict]:
    """Registered positions, independent dictionaries on every call; no nets."""
    return [*(_device(*row) for row in _DATA['devices']), *(_passive(*row) for row in _DATA['passives']),
            *_terminals(), *_opens()]


def legends() -> list[dict]:
    """Absolute UV, CCW baseline angle, original cap height (mm), centred text."""
    sources = {'s': _SURFACE, 'w': _WIRE, 'h': _HEADER}
    return [dict(text=text, u=u, v=v, angle=angle, height=h, source=sources.get(src, src))
            for text, u, v, angle, h, src in _DATA['legends']]


def silk_graphics() -> list[dict]:
    """Optional board ink. rect: outer w,h; ring: outer d; disk: filled d;
    crest: outer d, flat cutoff y=cut above centre. width is ink width (mm).
    These decorations are not copper and never ordinary default footprint borders.
    """
    def rect(u, v, w, h, width, source):
        return dict(kind='rect', u=u, v=v, w=w, h=h, width=width, source=source)

    def ring(u, v, d, width, source):
        return dict(kind='ring', u=u, v=v, d=d, width=width, source=source)

    items = [rect(u, v, w, h, .077, 'pcb_printmap.py; '+src) for u, v, w, h, src in _DATA['silk_boxes']]
    for label, u, v in _DATA['registered_lands']:
        if label in ('VCC', 'B1', 'G', 'R'):
            items.append(dict(kind='crest', u=u, v=v, d=2.10, width=.14, cut=.64, source=_SURFACE))
    items += [rect(-1.99, 35.825, 1.61, 7.42, .11, _SURFACE), rect(-13.04, 26.54, 1.54, 7.28, .10, _SURFACE),
              rect(*_OPTICAL['D27']['bar'], .08, _SURFACE+'; '+_OPTICAL['D27']['evidence']),
              dict(kind='disk', u=-5.69, v=25.83, d=.26, source=_SURFACE),
              dict(kind='disk', u=-10.74, v=35.73, d=.30, source=_SURFACE),
              rect(-8.22, 40.95, 9.54, 4.10, .095, 'pcb_printmap.py; IMG_8913/8914/8915'),
              ring(7.77, 17.97, 12.14, .14, 'pcb_printmap.py; IMG_8908/8909/8916/8920')]
    for key, u, v, _ in _DATA['wires']:
        r = 1.53 if key.startswith('B') else (1.43 if key.startswith('F') else 1.24)
        items.append(ring(u, v, 2*(r+.23), .13, _WIRE))
    items += [dict(kind='bar', u=-1.28, v=3.66, w=.10, h=3.82, source=_WIRE),
              dict(kind='bar', u=-3.49, v=5.53, w=4.53, h=.10, source=_WIRE)]
    return items
