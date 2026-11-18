#!/usr/bin/env python3
"""Build the partial GYS005-S-088-A4.3 board using only the Python stdlib.

This is a physical observation model, not a netlist recovery algorithm. A
track stops where its source observation stops. In particular do not connect
separate track groups merely because they appear to point at one another.
"""
import argparse
import json
import math
import uuid
from pathlib import Path

from footprints import footprints, legends, silk_graphics

HERE = Path(__file__).resolve().parent
STEM = 'GYS005-S-088-A4.3'
NAMESPACE = uuid.UUID('b3a33042-69b3-478f-a1cf-be3e87c738ee')
LAYERS = ((0, 'F.Cu', 'signal'), (2, 'B.Cu', 'signal'), (13, 'F.Paste', 'user'),
          (15, 'B.Paste', 'user'), (5, 'F.SilkS', 'user'), (7, 'B.SilkS', 'user'),
          (1, 'F.Mask', 'user'), (3, 'B.Mask', 'user'), (17, 'Dwgs.User', 'user'),
          (19, 'Cmts.User', 'user'), (25, 'Edge.Cuts', 'user'),
          (35, 'F.Fab', 'user'), (33, 'B.Fab', 'user'))

# Native line and three-point arc geometry of the registered 29.30 x 64.20 mm
# edge. The end of one entry is the start of the next. Notches and the crest
# are routed features, NOT the rectangular bounding box.
ROUTE_START = (-11.83, 0.)
ROUTE = ((10.28, 0), (14.65, 5.33), (14.65, 12.09), (13.70, 14.25, 14.65, 16.41),
         (14.65, 61.74), (14.49, 61.90), (4.25, 61.9), (3.88, 62.07, 3.74, 62.49),
         (3.74, 63.70), (3.5935533906, 64.0535533906, 3.24, 64.2), (-2.08, 64.2),
         (-2.4335533906, 64.0535533906, -2.58, 63.70), (-2.58, 62.51),
         (-2.73, 62.09, -3.14, 61.90), (-13.78, 61.90), (-14.65, 40.02),
         (-14.65, 16.24), (-13.85, 14.43, -14.65, 12.62), (-14.65, 4.22), ROUTE_START)


def quote(text):
    return json.dumps(str(text), ensure_ascii=False)


def fmt(value):
    return f'{value:.6f}'.rstrip('0').rstrip('.') or '0'


def pair(pt):
    return ' '.join(map(fmt, pt))


def ident(name):
    return str(uuid.uuid5(NAMESPACE, name))


def uid(name):
    return f'(uuid "{ident(name)}")'


def kxy(uv):
    """Upright AD owner photo datum -> front-view KiCad absolute XY in mm."""
    return (100. + uv[0], 130. - uv[1])


def relative(point):
    return point[0], -point[1]


def project(h, point):
    x, y = point
    den = h[2][0] * x + h[2][1] * y + h[2][2]
    return tuple((row[0] * x + row[1] * y + row[2]) / den for row in h[:2])


def pad_uv(fp, pad):
    a = math.radians(fp.get('angle', 0))
    x, y = pad['x'], pad['y']
    return (fp['u'] + x * math.cos(a) - y * math.sin(a),
            fp['v'] + x * math.sin(a) + y * math.cos(a))


def effects(size, width):
    return f'(effects (font (size {fmt(size)} {fmt(size)}) (thickness {fmt(width)})))'


def stroke(w):
    return f'(stroke (width {fmt(w)}) (type solid))'


def edges():
    last = ROUTE_START
    for i, item in enumerate(ROUTE):
        end = item[-2:]
        start_at = pair(kxy(last))
        end_at = pair(kxy(end))
        if len(item) == 4:
            head = f'gr_arc (start {start_at}) (mid {pair(kxy(item[:2]))})'
        else:
            head = f'gr_line (start {start_at})'
        yield f'({head} (end {end_at}) {stroke(.05)} (layer "Edge.Cuts") {uid(f"route/{i}")})'
        last = end


def fp_block(fp, pad_nets):
    ref = fp['ref']
    pos = pair(kxy((fp['u'], fp['v'])))
    angle = fp.get('angle', 0)
    yield f'(footprint {quote(ref)} (layer "F.Cu") {uid(ref)}'
    yield f'  (at {pos} {fmt(angle)})'
    yield f'  (descr {quote(fp["note"])})'
    for key, value in [('Reference', ref), ('Value', fp['value']), ('Evidence', fp['source']),
                       ('Interpretation', fp['note'])]:
        yield (f'  (property {quote(key)} {quote(value)} (at 0 0 {fmt(angle)}) (layer "F.Fab") '
               f'(hide yes) {uid(ref + "/" + key)} {effects(.65, .10)})')
    kinds = {p['kind'] for p in fp['pads']}
    attrs = ['through_hole' if kinds & {'pth', 'npth'} else 'smd']
    if not fp.get('fitted', True):
        attrs.extend(('dnp', 'exclude_from_bom', 'exclude_from_pos_files'))
    yield f'  (attr {" ".join(attrs)})'
    # Package silhouettes belong to the placement/fabrication layer. Filling
    # this layer with body rectangles must not manufacture new board silkscreen.
    polygon = fp.get('outline') or []
    if polygon and polygon[0] != polygon[-1]:
        polygon = [*polygon, polygon[0]]
    for i, (a, b) in enumerate(zip(polygon, polygon[1:])):
        yield (f'  (fp_line (start {pair(relative(a))}) (end {pair(relative(b))}) '
               f'{stroke(.08)} (layer "F.Fab") {uid(ref+f"/outline/{i}")})')
    index = fp.get('pin1')
    if index:
        x, y = relative(index)
        yield (f'  (fp_circle (center {pair((x,y))}) (end {pair((x+.11,y))}) '
               f'{stroke(.055)} (fill none) (layer "F.Fab") {uid(ref+"/index")})')
    # These inscriptions are on the BODY. F.Fab, never imaginary F.SilkS.
    marking = fp.get('marking')
    if marking and polygon:
        text_lines = marking.splitlines()
        width = max(p[0] for p in polygon) - min(p[0] for p in polygon)
        height = max(p[1] for p in polygon) - min(p[1] for p in polygon)
        text_angle = -90 if fp['ref'] == 'U3' else 180 if fp['ref'] == 'D26' else 0
        extent = height if abs(text_angle) == 90 else width
        size = min(.60, .72 * extent / (.82 * max(map(len, text_lines))))
        offset = fp.get('marking_xy', (0, 0))
        yield (f'  (fp_text user {quote(marking)} (at {pair(relative(offset))} {fmt(angle+text_angle)}) '
               f'(layer "F.Fab") {uid(ref+"/mark")} {effects(size,max(.035,size*.13))})')
    for i, (cx, cy, w, h) in enumerate(fp.get('stripes', [])):
        a = relative((cx-w/2, cy+h/2))
        b = relative((cx+w/2, cy-h/2))
        yield (f'  (fp_rect (start {pair(a)}) (end {pair(b)}) {stroke(.01)} '
               f'(fill solid) (layer "F.Fab") {uid(ref+f"/stripe/{i}")})')
    for i, pad in enumerate(fp['pads']):
        kind = {'smd':'smd', 'pth':'thru_hole', 'npth':'np_thru_hole'}[pad['kind']]
        pid = str(pad['id'])
        # A pad's centre is footprint-relative, while its stored KiCad angle is
        # absolute. Hence the sign flip for y but no second inversion of angle.
        loc = pair(relative((pad['x'], pad['y'])))
        pa = angle + pad.get('angle', 0)
        yield (f'  (pad {quote(pid)} {kind} {pad["shape"]} (at {loc} {fmt(pa)}) '
               f'(size {pair((pad["w"],pad["h"]))})')
        if kind == 'smd':
            # Bare/test discs are not turned into paste-stencilled component pads.
            paste = pad.get('paste', True)
            layers = '"F.Cu" "F.Paste" "F.Mask"' if paste else '"F.Cu" "F.Mask"'
        else:
            yield f'    (drill {fmt(pad["drill"])})'
            layers = '"*.Cu" "*.Mask"'
        yield f'    (layers {layers})'
        if pad['shape'] == 'roundrect':
            yield f'    (roundrect_rratio {fmt(pad.get("rratio", .18))})'
            if pad.get('chamfer') == 'NW':
                yield f'    (chamfer_ratio {fmt(pad["chamfer_ratio"])}) (chamfer top_left)'
        if (ref, pid) in pad_nets:
            number, name = pad_nets[(ref,pid)]
            yield f'    (net {number} {quote(name)})'
        yield f'    {uid(ref+f"/pad/{i}/{pid}")})'
    yield ')'


def physical_silk():
    for i, text in enumerate(legends()):
        size = text['height']
        pos = pair(kxy((text['u'],text['v'])))
        yield (f'(gr_text {quote(text["text"])} (at {pos} {fmt(text.get("angle", 0))}) '
               f'(layer "F.SilkS") {uid("silk/"+str(i))} {effects(size, max(.065, size*.125))})')


def silk_ink():
    """Real silk outlines are distinct from package edges and copper holes."""
    for i, mark in enumerate(silk_graphics()):
        u, v = mark['u'], mark['v']
        kind = mark['kind']
        width = mark.get('width', 0)
        name = f'silk-geometry/{i}'
        if kind in ('rect', 'bar'):
            w = mark['w'] - width
            h = mark['h'] - width
            a = pair(kxy((u-w/2, v+h/2)))
            b = pair(kxy((u+w/2, v-h/2)))
            head = f'gr_rect (start {a}) (end {b}) {stroke(width)}'
            head += ' (fill solid)' if kind == 'bar' else ' (fill none)'
        else:
            radius = (mark['d']-width)/2
            if kind == 'crest':
                y = mark['cut']
                x = math.sqrt(radius*radius-y*y)
                a, m, b = (pair(kxy(p)) for p in ((u-x, v+y), (u,v-radius), (u+x,v+y)))
                head = f'gr_arc (start {a}) (mid {m}) (end {b}) {stroke(width)}'
            else:
                head = f'gr_circle (center {pair(kxy((u,v)))}) (end {pair(kxy((u+radius,v)))}) {stroke(width)}'
                head += ' (fill solid)' if kind == 'disk' else ' (fill none)'
        yield f'({head} (layer "F.SilkS") {uid(name)})'


def observed_blocks(data, net_by_row):
    """Group native routing primitives so Edit Group reveals the optical ID."""
    for obs in data['observations']:
        key = obs['id']
        h = data['photo_to_local_mm'][obs['photo']]
        points = [kxy(project(h, point)) for point in obs['xy_px']]
        number = net_by_row.get(key, (0, ''))[0]
        obj_ids = []
        if obs['kind'] == 'track':
            for i, (a, b) in enumerate(zip(points, points[1:])):
                tag = f'{key}/{i}'
                yield (f'(segment (start {pair(a)}) (end {pair(b)}) (width {fmt(obs["width_mm_est"])}) '
                       f'(layer "F.Cu") (net {number}) {uid(tag)})')
                obj_ids.append(tag)
        elif obs['kind'] == 'via':
            yield (f'(via (at {pair(points[0])}) (size {fmt(obs["width_mm_est"])}) '
                   f'(drill {fmt(obs["drill_mm_est"])}) (layers "F.Cu" "B.Cu") (net 0) {uid(key)})')
            obj_ids.append(key)
        elif obs['kind'] == 'copper_patch':
            pts = ' '.join(f'(xy {pair(point)})' for point in points)
            yield f'(gr_poly (pts {pts}) {stroke(0)} (fill solid) (layer "F.Cu") {uid(key)})'
            obj_ids.append(key)
        else:
            raise ValueError(f'Unknown copper observation kind: {obs["kind"]}')
        # Groups are editor metadata, NOT extra silk or copper strokes.
        members = ' '.join(quote(ident(k)) for k in obj_ids)
        yield f'(group {quote("OBS / "+key)} {uid("group/"+key)} (members {members}))'


def optical_only(data):
    """Ambiguous single boundaries go to Comments.User; NEVER to copper."""
    for row in data.get('optical_only', []):
        key = row['id']
        h = data['photo_to_local_mm'][row['photo']]
        points = [kxy(project(h, p)) for p in row['xy_px']]
        members = []
        for i, (a, b) in enumerate(zip(points, points[1:])):
            tag = f'optical-only/{key}/{i}'
            members.append(quote(ident(tag)))
            yield (f'(gr_line (start {pair(a)}) (end {pair(b)}) (stroke (width 0.08) '
                   f'(type dash)) (layer "Cmts.User") {uid(tag)})')
        yield f'(group {quote("OPTICAL NOT Cu / "+key)} {uid("group/"+key)} (members {" ".join(members)}))'


def board_text(data):
    all_fps = footprints()
    lookup = {(f['ref'], str(p['id'])):(f,p) for f in all_fps for p in f['pads']}
    by_pad = {}
    by_row = {}
    for obs in data['observations']:
        link = obs.get('observed_pad')
        if link:
            key = (link['ref'], str(link['id']))
            if key not in lookup or key in by_pad:
                raise ValueError(f'Invalid witnessed terminal: {key}')
            number = len(by_pad) + 1
            by_pad[key] = by_row[obs['id']] = (number, 'OBS_'+obs['id'])
    lines = ['(kicad_pcb (version 20241229) (generator "photo_observations")',
             '  (generator_version "1.0")', '  (general (thickness 1.45))', '  (paper "A4")',
             '  (title_block (title "GYS005-S-088-A4.3") (rev "OPTICAL / PARTIAL")',
             '    (comment 1 "Photographic reconstruction; not a production design/netlist")',
             '    (comment 2 "Back routing not observed. See observations.json."))', '  (layers']
    lines.extend(f'    ({i} {quote(layer)} {kind})' for i, layer, kind in LAYERS)
    lines.extend(('  )', '  (setup (pad_to_mask_clearance 0))', '  (net 0 "")'))
    lines.extend(f'  (net {num} {quote(name)})' for num,name in by_pad.values())
    for fp in all_fps:
        lines.extend('  '+line for line in fp_block(fp,by_pad))
    for section in (edges(), physical_silk(), silk_ink(), observed_blocks(data, by_row), optical_only(data)):
        lines.extend('  '+line for line in section)
    lines.append(')')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / (STEM+'.kicad_pcb'))
    args = parser.parse_args()
    data = json.loads((HERE/'observations.json').read_text(encoding='utf-8'))
    args.output.write_text(board_text(data), encoding='utf-8')


if __name__ == '__main__':
    main()
