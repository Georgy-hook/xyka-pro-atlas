#!/usr/bin/env python3
"""Write the documented optical reconstruction. Pure Python, offline, deterministic.

By default write beside this script. --out changes only the delivery directory.
All user coordinates in the evidence table are in the original PCB u/v frame.
"""

import argparse
import csv
import json
import math
from pathlib import Path

from kicad_art import arc, circle, f, line, qi, rect, uid, xy
from land_patterns import CONTACTS, EDGE_PADS, HOLES, devices

HERE = Path(__file__).resolve().parent
REG = HERE.parents[1] / 'model' / 'display_registration.json'
LIB = 'DisplayPhoto'


def property_text(name, value, v, key):
    return (f'(property {qi(name)} {qi(value)} (at 0 {f(-v)} 0) (layer "F.Fab") (hide yes) '
            f'{uid(key)} (effects (font (size 0.7 0.7) (thickness 0.1))))')


def footprint(ref, typ, uv, description, maker, library=False):
    name = typ if library else LIB + ':' + typ
    key = ('lib/' + typ) if library else ('board/' + ref)
    head = (f'(footprint {qi(name)} (version 20240108) (generator "photo_reconstruction")'
            if library else f'(footprint {qi(name)}')
    body = ['(layer "F.Cu")']
    if not library:
        body += [uid(key), f'(at {xy(uv, True)})']
    body += [f'(descr {qi(description)})',
             property_text('Reference', 'REF**' if library else ref, 2.8, key + '/ref'),
             property_text('Value', typ, -2.8, key + '/value')]
    if ref.startswith('SW') or ref == 'FPC1':
        body.append('(attr smd exclude_from_bom)')
    else:
        body.append('(attr board_only exclude_from_pos_files exclude_from_bom)')
    body += maker(key)
    return head + '\n  ' + '\n  '.join(body) + '\n)'


def perimeter():
    # Trace on original 8917/18 is available beside the keypad only. Above
    # that, deliberately close to the same nominal envelope as the FCStd.
    depth = math.sqrt(1.85**2 - (1.85 - .95)**2)
    yr, yl = 11.15, 11.18
    poly = [(-10.60, 0), (11.07, 0), (14.10, 4.09), (14.10, yr - depth)]
    spans = [(a, b) for a, b in zip(poly, poly[1:])]
    upper = [(14.10, yr + depth), (14.10, 46.95), (10.65, 50.4), (-10.65, 50.4),
             (-14.10, 46.95), (-14.10, yl + depth)]
    spans += list(zip(upper, upper[1:]))
    spans += [((-14.1, yl - depth), (-14.1, 4.35)), ((-14.1, 4.35), poly[0])]
    out = [line(a, b, 'Edge.Cuts', .05, f'edge/{i}', True) for i, (a,b) in enumerate(spans)]
    out += [arc((14.1, yr - depth), (13.15, yr), (14.1, yr + depth), 'Edge.Cuts', .05, 'relief/R', True),
            arc((-14.1, yl + depth), (-13.15, yl), (-14.1, yl - depth), 'Edge.Cuts', .05, 'relief/L', True)]
    return out


def text(value, uv, angle, scale, layer, key, align='center'):
    justify = '' if align == 'center' else f' (justify {align})'
    return (f'(gr_text {qi(value)} (at {xy(uv, True)} {angle}) (layer {qi(layer)}) {uid(key)} '
            f'(effects (font (size {f(scale)} {f(scale)}) (thickness {f(scale*.15)})){justify}))')


def graphics(evidence):
    out = [text('20260305A', (-12.04, 9.60), -90, .97, 'F.SilkS', 'face-mark')]
    for name, pts in [
        ('strokeContact', [(-6.09, .18), (-6.09, 2.81), (-5.91, 3.20)]),
        ('strokeFlex', [(-1.92, 11.56), (-2.45, 11.56), (-2.55, 11.66), (-2.55, 12.21)]),
        ('strokeWitness', [(-4.04, 13.88), (-3.70, 13.80), (-2.72, 13.35)]),
    ]:
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            out.append(line(a,b,'F.SilkS',.064,f'{name}/{i}', True))
    # Optical micro-rings have NO drill or electrical layer span assigned.
    arrays = [(3.90, 4.83, (0, .48, .94), (0, .48)), (7.82, 3.08, (0, .47, .96), (0, .39)),
              (13, 7.77, (0, .53), (0, .42, .83)), (.48, 3.12, (0, .50), (0, .36)),
              (11.19, 5.99, (0, .59, 1.10, 1.91, 2.39), (0,))]
    for i,(u,v,xs,ys) in enumerate(arrays):
        for j,x in enumerate(xs):
            for k,y in enumerate(ys):
                out.append(circle(u+x,v+y,.062,'User.1',.028,f'witness/{i}/{j}/{k}',True))
    for i,(u,v) in enumerate(HOLES):
        # Purely geometric survey circles let a non-Gerber vector plot show
        # physical openings even on the unobserved reverse. NOT annular Cu.
        out.append(circle(u,v,.625,'User.5',.04,f'survey-bore/{i}',True))
    for path in evidence['documentary_paths']:
        pts=path['uv_mm']
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            out.append(line(a,b,'User.2',.09,f"{path['id']}/{i}",True))
    # dim_deui shows a projecting tab with a bright centre at the FAR end of
    # a comparative module. Its layer/carrier identity and the owner's far
    # end are obscured. Keep it on the comparison layer, outside all drills
    # and Edge.Cuts. Coordinates are weak extrapolations of the lower-plane fit.
    tab = [(-2.33,48.25),(-1.96,50.35),(2.96,49.57),(3.12,47.9)]
    for n,(a,b) in enumerate(zip(tab,tab[1:])):
        out.append(line(a,b,'User.2',.065,f'other-far-tab/{n}',True))
    out.append(circle(.83,48.79,.53,'User.2',.055,'other-far-tab/eye',True))
    # Only documentation, not material, mask, keepout or a fabrication edge.
    out += [line((-14.0,17.4), (14.0,17.4), 'User.3', .075, 'lcd/limit', True),
            text('LCD OCCLUSION / NO COPPER INFERRED', (0,29), 0, .85, 'User.3', 'lcd/status'),
            text('FAR OUTLINE ESTIMATE', (0,47.3), 0, .7, 'User.3', 'far/status'),
            text('B.Cu NOT OBSERVED', (0,25), 0, .85, 'User.3', 'reverse/status')]
    return out


def project(h, uv):
    p=(*uv,1.)
    a,b,c=[sum(i*j for i,j in zip(row,p)) for row in h]
    return [a/c,b/c]


def write_records(out, evidence, registration):
    """13 preserved native features plus optical width/tangent samples; no resampled image picks passed off as clicks."""
    names = {**{f'UiContact{i}':f'CT{i}' for i in range(1,7)}, **{f'UiContact{i:02d}':f'CT{i}' for i in range(1,7)},
             **{f'UiEdgePad{i:02d}':f'TP{i}' for i in range(1,5)}, 'UiWitnessEye':'TP5','UiHoleL':'H1','UiHoleR':'H2'}
    h17=registration['homogeneous_uv_to_xy_px']
    h18=registration['secondary_image']['homogeneous_uv_to_xy_px']
    with (out/'observations.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.writer(file)
        writer.writerow(['id','role','layer','u_mm','v_mm','kicad_x','kicad_y','source','x_px','y_px','width_mm','limit'])
        for role in ('fit','check'):
            for obj,u,v,x,y in registration[role]:
                writer.writerow([names[obj],role,'MECHANICAL' if obj.startswith('UiHole') else 'F.Cu',u,v,
                                 f(100+u),f(100-v),'IMG_8917.jpg / original click',x,y,'',obj])
        for name,typ,(u,v),desc,_ in devices():
            writer.writerow([name,'footprint_origin','F.Cu or mechanical',u,v,f(100+u),f(100-v),
                             '8917/18 + installed CAD datum','','','',desc])
        # List the geometric terminal names used by the actual footprint, not
        # inferred electrical pin numbers. X/Y centres are ready for a drawing.
        for ref, _, (x0, y0), _, _ in devices():
            lands = []
            if ref.startswith('SW'):
                lands = [(row + col, x0 + x, y0 + y, .50, .55)
                         for col, x in [('L', -.96), ('R', .96)] for row, y in [('D', -2.045), ('U', 2.045)]]
            elif ref == 'FPC1':
                lands = [(str(15 - i), x0 + (i - 7) * .845, y0, .416, 2.16) for i in range(15)]
            for number, u, v, width, length in lands:
                writer.writerow([ref + '/' + number, 'pad centre', 'F.Cu', f(u), f(v), f(100+u), f(100-v),
                                 'IMG_8917/18 + nominal rectification', '', '', width,
                                 f'{width:g} x {length:g} mm EST; finish visible, buried land limits and electrical node UNKNOWN'])
        for path in evidence['paths']:
            for index, (u, v) in enumerate(path['uv_mm'], 1):
                px = [round(value, 2) for value in project(h18, (u, v))]
                writer.writerow([
                    path['id'], f'optical vertex {index}', 'F.Cu', u, v, f(100 + u), f(100 - v),
                    'IMG_8918.jpg / back-projected optical digitisation', *px, path['width_mm'], path['basis'],
                ])
            for index, (u, v) in enumerate(path['cross_section_uv'], 1):
                px = [round(value, 2) for value in project(h18, (u, v))]
                writer.writerow([
                    path['id'], f'width flank {index}', 'F.Cu', u, v, f(100 + u), f(100 - v),
                    'IMG_8918.jpg / back-projected profile sample', *px, '', 'Not an independent physical width.',
                ])
        for path in evidence['documentary_paths']:
            for i,(u,v) in enumerate(path['uv_mm'],1):
                writer.writerow([path['id'],f'comparative vertex {i}','User.2',u,v,f(100+u),f(100-v),
                                 'dim_deui.jpg / different specimen','','','',path['basis']])
    errors=[]
    for obj,u,v,x,y in registration['check']:
        pred=project(h17,(u,v))
        errors.append(math.dist(pred,(x,y)))
    return (sum(err**2 for err in errors)/len(errors))**.5


def build(out):
    out.mkdir(parents=True,exist_ok=True)
    library=out/(LIB+'.pretty')
    library.mkdir(exist_ok=True)
    evidence=json.loads((HERE/'trace_observations.json').read_text())
    registration=json.loads(REG.read_text())
    parts=[]
    written=set()
    for ref,typ,uv,desc,maker in devices():
        parts.append(footprint(ref,typ,uv,desc,maker))
        if typ not in written:
            (library/(typ+'.kicad_mod')).write_text(footprint(ref,typ,uv,desc,maker,True)+'\n',encoding='utf-8')
            written.add(typ)
    parts+=perimeter()+graphics(evidence)
    for path in evidence['paths']:
        pts=path['uv_mm']
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            parts.append(f'(segment (start {xy(a,True)}) (end {xy(b,True)}) (width {f(path["width_mm"])}) '
                         f'(layer "F.Cu") (net 0) {uid(path["id"]+"/"+str(i))})')
    header='''(kicad_pcb (version 20240108) (generator "photo_reconstruction")
  (general (thickness 0.8)) (paper "A4")
  (title_block (title "20260305A — photo-observed front artwork") (rev "E0.1 / ESTIMATE")
    (comment 1 "Not fabrication data. B.Cu, internal layers and circuit identities UNKNOWN."))
  (layers (0 "F.Cu" signal) (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user) (43 "Eco2.User" user) (44 "Edge.Cuts" user) (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user) (49 "F.Fab" user) (50 "User.1" user "Optical_Witnesses")
    (51 "User.2" user "Other_Specimen_Only") (52 "User.3" user "Evidence_Limits")
    (54 "User.5" user "Bore_Survey"))
  (setup (pad_to_mask_clearance 0) (aux_axis_origin 100 100) (grid_origin 100 100))
  (net 0 "")'''
    (out/'20260305A.kicad_pcb').write_text(header+'\n\n'+'\n\n'.join(parts)+'\n)\n',encoding='utf-8')
    (out/'fp-lib-table').write_text('(fp_lib_table (version 7)\n  (lib (name "DisplayPhoto")(type "KiCad")'
                                   '(uri "${KIPRJMOD}/DisplayPhoto.pretty")(options "")'
                                   '(descr "Original 20260305A photographic patterns; not factory footprints"))\n)\n',encoding='utf-8')
    rms=write_records(out,evidence,registration)
    print(f'{len(devices())} placed footprints, {len(written)} unique local patterns; nominal held-out RMS {rms:.2f} px')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=HERE)
    build(parser.parse_args().out.resolve())
