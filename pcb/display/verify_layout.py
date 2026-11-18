#!/usr/bin/env python3
"""Check the actual KiCad board using KiCad's Python/pcbnew and command-line tools.

Pass a fresh --out directory (plots/reports only). This never modifies the
board and does not interpret default DRC exit 5 as a fabrication pass.
"""

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import shutil
import xml.etree.ElementTree as ET

import pcbnew as pcb


HERE = Path(__file__).resolve().parent


def uv(pos):
    return [pcb.ToMM(pos.x) - 100, 100 - pcb.ToMM(pos.y)]


def point(u, v):
    return pcb.VECTOR2I(pcb.FromMM(100 + u), pcb.FromMM(100 - v))


def expect(condition, message):
    if not condition:
        raise ValueError(message)


def read_board(path, obs_csv):
    b = pcb.LoadBoard(str(path))
    footprints = list(b.GetFootprints())
    pads = list(b.GetPads())
    tracks = list(b.GetTracks())
    holes = [p for p in pads if p.GetAttribute() == pcb.PAD_ATTRIB_NPTH]
    expect(len(footprints) == 20 and len(pads) == 43 and len(holes) == 2, 'Unexpected physical inventory')
    expect(len(tracks) == 11 and not any(isinstance(t, pcb.PCB_VIA) for t in tracks), 'Unexpected trace/via inventory')
    expect(b.GetAreaCount() == 0 and all(t.GetLayer() == pcb.F_Cu and t.GetNetCode() == 0 for t in tracks),
           'A zone or named/inferred net has appeared')
    expect(all(p.GetNetCode() == 0 for p in pads), 'Unproven pad net assigned')
    expect(all(p.GetDrillSize().x == pcb.FromMM(1.25) and p.GetDrillSize().y == pcb.FromMM(1.25) for p in holes),
           'Wrong finished bore diameter')
    contour = pcb.SHAPE_POLY_SET()
    expect(b.GetBoardPolygonOutlines(contour, False) and contour.OutlineCount() == 1, 'Contour does not close')
    expect(sum(d.GetLayer() == pcb.Edge_Cuts and d.GetShape() == pcb.SHAPE_T_ARC for d in b.GetDrawings()) == 2,
           'Missing concave edge arcs')

    # Read actual placed native pads: the reference and fit tables alone cannot
    # catch a sign error in a footprint's local ordinate or mirrored numbering.
    errs_xy = []
    fit_errors = []
    check_errors = []
    reg = json.loads((HERE.parents[1] / 'model' / 'display_registration.json').read_text())
    h = reg['homogeneous_uv_to_xy_px']
    for row in csv.DictReader(obs_csv.open(encoding='utf-8')):
        role = row['role']
        if role not in ('fit', 'check', 'footprint_origin', 'pad centre'):
            continue
        ref, _, number = row['id'].partition('/')
        fp = b.FindFootprintByReference(ref)
        expect(fp is not None, f'Missing {ref}')
        if role == 'pad centre':
            p = fp.FindPadByNumber(number)
            expect(p is not None, f'Missing pad {ref}/{number}')
            pos = uv(p.GetPosition())
        elif ref.startswith('H'):
            pos = uv(next(iter(fp.Pads())).GetPosition())
        elif ref == 'TP5' and role in ('fit', 'check'):
            # Origin of the custom annulus is NOT its small KiCad copper anchor.
            box = next(iter(fp.Pads())).GetEffectivePolygon(pcb.F_Cu).BBox()
            pos = uv(box.Centre())
        else:
            pos = uv(fp.GetPosition())
        err = math.dist(pos, [float(row['u_mm']), float(row['v_mm'])])
        errs_xy.append(err)
        expect(err < .0001, f'Position error {row["id"]}: {err:g} mm')
        if role in ('fit', 'check'):
            a, c, z = [sum(t * p for t, p in zip(rr, (*pos, 1))) for rr in h]
            err = math.dist([a / z, c / z], [float(row['x_px']), float(row['y_px'])])
            (fit_errors if role == 'fit' else check_errors).append(err)

    # KiCad fractures polygons with holes internally. Test membership at all
    # observed negative spaces, not HoleCount() on its flattened pad cache.
    field = next(iter(b.FindFootprintByReference('MP1').Pads())).GetEffectivePolygon(pcb.F_Cu)
    bright = {(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (5, 4)}
    voids = 0
    for i in range(10):
        for j in range(8 if i < 3 else 6):
            uv_point = point(-6.89 + .23 + j * .478, 4.12 + 5.17 - i * .451)
            expect(field.Contains(uv_point) == ((i, j) in bright), f'Perforation {i}/{j} wrong')
            voids += (i, j) not in bright
    for j in range(4):
        expect(not field.Contains(point(-6.89 + 1.27 + j * .57, 4.12 + .22)), 'Lost detached row')
        voids += 1
    expect(voids == 64, 'Field aperture count')
    return {
        'footprints': len(footprints), 'smd_lands': len(pads) - len(holes), 'mechanical_drills': len(holes),
        'actual_segments': len(tracks), 'sum_segment_length_mm': sum(pcb.ToMM(t.GetLength()) for t in tracks),
        'widths_mm': sorted({pcb.ToMM(t.GetWidth()) for t in tracks}), 'field_surface_pits': voids,
        'physical_vias_asserted': 0, 'assigned_nets': 0, 'zones': 0,
        'native_xy_comparisons': len(errs_xy), 'max_xy_delta_mm': max(errs_xy),
        'fit_rms_px': math.sqrt(sum(e*e for e in fit_errors) / len(fit_errors)),
        'held_out_rms_px': math.sqrt(sum(e*e for e in check_errors) / len(check_errors)),
        'held_out_max_px': max(check_errors), 'board_edge_profile_area_mm2': contour.Area() / 1e12,
        'board_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def run(cli, out):
    out.mkdir(parents=True, exist_ok=True)
    # KiCad may create a per-user .kicad_prl during a CLI check. Keep even
    # these side effects OUT of the project and check the same local library.
    work = out / 'verification-input'
    if work.resolve() == HERE or HERE in work.resolve().parents:
        raise ValueError('--out must be outside the delivered source directory')
    work.mkdir(exist_ok=True)
    path = work / '20260305A.kicad_pcb'
    shutil.copyfile(HERE / path.name, path)
    shutil.copyfile(HERE / 'fp-lib-table', work / 'fp-lib-table')
    shutil.copytree(HERE / 'DisplayPhoto.pretty', work / 'DisplayPhoto.pretty', dirs_exist_ok=True)
    result = read_board(path, HERE / 'observations.csv')
    env = os.environ.copy()
    env.setdefault('KICAD_CONFIG_HOME', str(out / 'kicad_config'))

    def call(*args, expected=0):
        receipt = subprocess.run([str(cli), *map(str, args)], env=env, text=True, capture_output=True)
        expect(receipt.returncode == expected, f'{args}: exit {receipt.returncode}: {receipt.stderr} {receipt.stdout}')
        return receipt.stdout.strip()

    version = call('version')
    for side in ('F', 'B'):
        target = out / f'20260305A-{side}.svg'
        reverse = ['--mirror'] if side == 'B' else []
        call('pcb', 'export', 'svg', '--layers', f'{side}.Cu,Edge.Cuts,User.5', '--mode-single',
             '--exclude-drawing-sheet', '--page-size-mode', '2', '--drill-shape-opt', '2', *reverse,
             '-o', target, path)
        root = ET.parse(target).getroot()
        expect(root.tag.endswith('svg') and 'viewBox' in root.attrib, 'Invalid layer plot')
    drc_file = out / 'drc.json'
    call('pcb', 'drc', '--format', 'json', '--severity-all', '--exit-code-violations', '-o', drc_file, path, expected=5)
    drc = json.loads(drc_file.read_text())
    observed = Counter(item['type'] for item in drc['violations'])
    expected = {'track_dangling':6, 'track_width':4, 'copper_edge_clearance':2}
    expect(observed == expected and not drc['unconnected_items'], f'DRC changed: {observed}')
    drill = out / 'drill'
    drill.mkdir(exist_ok=True)
    call('pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm', '-o', drill, path)
    codes = (drill / '20260305A.drl').read_text()
    expect('T1C1.250' in codes and re.findall(r'^X.*$', codes, re.M) == ['X92.1Y-98.75','X108.25Y-98.75'],
           'Drill table changed')
    gerber = out / 'gerbers-QA'
    gerber.mkdir(exist_ok=True)
    call('pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu', '--no-protel-ext', '-o', gerber, path)
    reverse = (gerber / '20260305A-B_Cu.gbr').read_text()
    expect(not re.search(r'(?:\bG36\*|%ADD\d|D0[13]\*)', reverse), 'Unexpected back-layer copper')
    result.update(kicad_cli=version, drc_strict_exit=5, drc_unconnected_items=len(drc['unconnected_items']),
                  drc_violations=dict(observed), svg_front_exit=0, svg_back_exit=0, drill_exit=0,
                  back_gerber_draw_or_flash_count=0,
                  status='Optical reconstruction verified. Manufacturing DRC fails; not a fabrication or electrical design.')
    (out / 'validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', default='kicad-cli')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    run(args.cli, args.out.resolve())
