"""Draft four reference-only ESKD PCB sheets from two native KiCad boards.

Run with the FreeCAD distribution's Python (matplotlib, fontTools) and a
KiCad CLI. `--out` must be a NEW directory; render/verify both boards before
publishing the directory in one rename. Never run a project build or save a
board from this tool. The manifest is the input to plates.py --pcb-manifest.
"""
import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

from plates_eskd_frame import Sheet, write_sheet
from eskd_pcb_geometry import read_board
from eskd_pcb_overlay import add_copper
from eskd_pcb_plot import plot_copper
from eskd_pcb_sheets import DISPLAY, MAIN, SIDES, choose_scale, mechanical, pattern, ratio


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def source_name(path):
    root = Path(__file__).resolve().parents[1]
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name


def drc(cli, pcb, work, env):
    out = work/'drc.json'
    args = [str(cli), 'pcb', 'drc', '--format', 'json', '--units', 'mm', '--severity-all',
            '--exit-code-violations', '-o', str(out), str(pcb)]
    run = subprocess.run(args, cwd=work, env=env, capture_output=True, text=True, timeout=120)
    # KiCad CLI returns code 5 for a completed check with violations. Do not
    # conflate 'completed' with 'clean', or let an unreadable file pass.
    if run.returncode not in (0, 5) or not out.is_file():
        raise RuntimeError(f'KiCad DRC failed ({run.returncode}): {run.stdout} {run.stderr}')
    data = json.loads(out.read_text(encoding='utf-8'))
    categories = ('violations', 'unconnected_items', 'schematic_parity')
    if not isinstance(data.get('violations'), list):
        raise ValueError('DRC report is missing its violations list')
    severity = Counter(i.get('severity', 'unspecified') for k in categories for i in data.get(k, []))
    return {'exit_code':run.returncode, 'sha256':sha(out), 'scope':'KiCad file check, not manufacturing acceptance',
            'items':{k:len(data.get(k, [])) for k in categories}, 'severities':dict(severity),
            'types':dict(Counter(i.get('type', 'unspecified') for k in categories for i in data.get(k, [])))}


def cli_env(work):
    env = os.environ.copy()
    for var, folder in (('HOME', 'home'), ('CFFIXED_USER_HOME', 'home'), ('KICAD_CONFIG_HOME', 'config'),
                        ('KICAD_DOCUMENTS_HOME', 'documents'), ('XDG_CONFIG_HOME', 'config'),
                        ('XDG_CACHE_HOME', 'cache'), ('TMPDIR', 'tmp')):
        where = work/folder
        where.mkdir(exist_ok=True)
        env[var] = str(where)
    return env


def restore_context(source, work):
    """Copy only genuine local KiCad check inputs; no downloads/global libs."""
    files = [p for p in (source.with_suffix('.kicad_pro'), source.with_suffix('.kicad_dru')) if p.is_file()]
    table = source.parent/'fp-lib-table'
    if table.is_file():
        files.append(table)
        for uri in re.findall(r'\(uri\s+"([^"]+)"\)', table.read_text(encoding='utf-8')):
            if not uri.startswith('${KIPRJMOD}/'):
                raise ValueError(f'Expected a project-local footprint library, got {uri}')
            directory = (source.parent/uri.removeprefix('${KIPRJMOD}/')).resolve(strict=True)
            if not directory.is_relative_to(source.parent) or directory.suffix != '.pretty':
                raise ValueError(f'Invalid local footprint library: {uri}')
            files.extend(sorted(directory.glob('*.kicad_mod')))
    hashes = {}
    for file in files:
        if file.is_symlink():
            raise ValueError(f'Expected an ordinary project input: {file}')
        dest = work/file.relative_to(source.parent)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dest)
        hashes[source_name(file)] = sha(dest)
    return hashes


def compose(edition, source, expected, evidence, stage, work, cli, version, verify_python, proof):
    key = edition.key
    work.mkdir()
    original = sha(source)
    if expected is not None and original.lower() != expected.strip().lower():
        raise ValueError(f'{edition.product}: expected SHA-256 {expected}, got {original}')
    # macOS KiCad can write a .kicad_prl beside an input even for CLI export.
    # Use restored byte-for-byte copies. Keep genuine rule inputs if provided;
    # never refill zones, save-board, create a project, or tune DRC rules here.
    restored = work/source.name
    shutil.copyfile(source, restored)
    companions = restore_context(source, work)
    board = read_board(restored)
    if board.sha256 != original:
        raise ValueError('Restored source does not match the handoff')
    scale = choose_scale(board)
    env = cli_env(work)
    print(f'{key}: KiCad {version}; restored SHA-256 {original}; Edge.Cuts {board.bounds}', flush=True)
    check = drc(cli, restored, work, env)
    # Source plotting uses its own private KiCad configuration and input copy.
    plot_work = work/'plots'
    plot_work.mkdir()
    plots = plot_copper(restored, cli, plot_work)
    native = {}
    if proof is not None:
        proof.mkdir()
        shutil.copyfile(work/'drc.json', proof/'drc.json')
        shutil.copyfile(plots['F.Cu'].raw_path.parent/'Edge.Cuts-drill0.svg', proof/'Edge.Cuts.svg')
    for side in SIDES:
        p = plots[side]
        if p.source_sha256 != original or sha(p.raw_path) != p.sha256:
            raise ValueError(f'{side}: plot and source were not restored from the same input')
        if proof is not None:
            shutil.copyfile(p.raw_path, proof/f'{side}-drill2.svg')
            shutil.copyfile(p.raw_path.parent/f'{side}-drill0.svg', proof/f'{side}-drill0.svg')
        native[side] = {
            'objects':board.counts[side], 'track_widths_mm':list(board.widths[side]),
            'tracks_extents_kicad_mm':board.routes[side], 'ink_extents_kicad_mm':p.bounds,
            'native_plot_sha256':p.sha256, 'native_plot_ink_count':p.ink_count,
        }
        print(f"{key} {side}: {board.counts[side]}, ink bbox {p.bounds}, track bbox {board.routes[side]}", flush=True)
    citations = {source_name(p):sha(p) for p in evidence}
    sheets = []
    technical = {}
    for n, form, title in ((1, '1', 'Контур и отверстия'), (2, '2a', 'Проводящий рисунок')):
        stem = f'pcb-{key}-{n:02d}'
        sheet = Sheet(edition.designation, edition.title, ratio(scale), paper='A3',
                      form=form, number=n, sheets=2, product=edition.product)
        pdf, svg = stage/(stem+'.pdf'), stage/(stem+'.svg')
        if n == 1:
            technical['drill_table'] = mechanical(sheet, board, edition, scale)
        else:
            placements, inspection = pattern(sheet, board, plots, edition, scale, source.name)
            technical['inspection_detail'] = inspection
        write_sheet(sheet, pdf, svg, source=f'{source_name(source)} | SHA-256 {original} | {edition.photos} | NON PRODUCTION')
        if n == 2:
            technical['overlay_qa'] = add_copper(pdf, svg, placements, verify_python=verify_python)
        sheet.fig.clear()
        sheets.append({'id':stem, 'title':f'{edition.title}. {title}', 'designation':edition.designation,
                       'number':n, 'sheets':2, 'scale':ratio(scale), 'paper':'A3', 'pdf':pdf.name,
                       'svg':svg.name, 'pdf_sha256':sha(pdf), 'svg_sha256':sha(svg)})
    if sha(source) != original or sha(restored) != original or read_board(restored).sha256 != original:
        raise ValueError('Input changed during rendering; refusing to publish')
    for p in evidence:
        if sha(p) != citations[source_name(p)]:
            raise ValueError('Evidence input changed during rendering')
    return sheets, {
        'product':edition.product, 'designation':edition.designation, 'board':source_name(source),
        'sha256':original, 'expected_handoff_sha256':expected, 'restored_sha256':sha(restored),
        'evidence_sources':citations, 'photos':edition.photos, 'companions':companions,
        'edge_cuts_centerline_bounds_kicad_mm':board.bounds, 'thickness_in_file_mm':board.thickness,
        'origin_kicad_mm':[board.bounds[0], board.bounds[3]],
        'coordinates':'X = xKiCad - xmin, Y = ymax - yKiCad; reverse viewed from outside, X points left',
        'plating':'not established by photographs; hole classes refer to file types only',
        'layer_stack':'unknown in specimen; F.Cu/B.Cu are file surfaces, not proof of stackup or hidden connectivity',
        'holes':len(board.holes), 'layers':native, 'drc':check, **technical,
    }


def build(args):
    out = args.out.expanduser().resolve()
    if out.exists():
        raise FileExistsError(f'Output exists; choose a fresh output directory: {out}')
    out.parent.mkdir(exist_ok=True, parents=True)
    proof = None if args.proof_dir is None else args.proof_dir.expanduser().resolve()
    if proof is not None and (proof.exists() or proof.parent != out.parent or proof == out):
        raise ValueError('--proof-dir must be a new sibling of --out')
    cli = args.kicad_cli.expanduser().resolve()
    version = subprocess.check_output([str(cli), 'version'], text=True, timeout=20).strip()
    main, display = args.main.resolve(), args.display.resolve()
    if main == display and not args.coupon:
        raise ValueError('Distinct main/display source boards required; --coupon is scratch testing only')
    for path in (main, display):
        if path.suffix.lower() != '.kicad_pcb':
            raise ValueError('Input must be a native .kicad_pcb')
    if not args.coupon and (args.main_sha256 is None or args.display_sha256 is None):
        raise ValueError('Supply both final board handoff SHA-256 digests (or --coupon for scratch tests only)')
    manifest = {'schema':'xkah.pcb_sheets/1', 'status':'COUPON TEST' if args.coupon else 'NON PRODUCTION',
                'kicad_cli_version':version, 'sheets':[], 'sources':{}}
    with TemporaryDirectory(prefix='.eskd-pcb-', dir=out.parent) as tmp:
        tree = Path(tmp)
        stage = tree/'leaves'
        stage.mkdir()
        proof_stage = tree/'native-proof'
        if proof is not None:
            proof_stage.mkdir()
        for edition, path, digest, evidence in ((MAIN, main, args.main_sha256, args.main_evidence),
                                                (DISPLAY, display, args.display_sha256, args.display_evidence)):
            if args.coupon:
                # Even an individual test PDF must not masquerade as an XKAH
                # drawing. Test designations also fail the master release gate.
                edition = replace(edition, designation='КУПОН.01' if edition == MAIN else 'КУПОН.02',
                                  title='Купон проверки регистрации', product='КОНТРОЛЬНЫЙ ПРОГОН',
                                  photos='тестовый файл KiCad', limit='Проверка компоновки; не применять как документацию на изделие.')
            pages, source = compose(edition, path, digest, [p.resolve() for p in evidence], stage,
                                    tree/edition.key, cli, version, args.verify_python,
                                    None if proof is None else proof_stage/edition.key)
            manifest['sheets'].extend(pages)
            manifest['sources'][edition.key] = source
        report(stage/'pcb-sheets.json', manifest)
        # Across both boards, not just one render: no first-board stale hash.
        if any(sha(path) != manifest['sources'][key]['restored_sha256'] for key, path in [('main', main), ('display', display)]):
            raise ValueError('Source changed before publication')
        if proof is not None:
            proof_stage.rename(proof)
        stage.rename(out)
    print(f'{len(manifest["sheets"])} A3 leaves: {out / "pcb-sheets.json"}', flush=True)


def parse(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for board in ('main', 'display'):
        p.add_argument('--'+board, type=Path, required=True)
        p.add_argument('--'+board+'-sha256', help='expected frozen native board SHA-256')
        p.add_argument('--'+board+'-evidence', type=Path, action='append', default=[], help='hash a supporting evidence file')
    p.add_argument('--kicad-cli', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--proof-dir', type=Path, help='new sibling directory for native CLI exports and DRC receipts')
    p.add_argument('--verify-python', help='Python with PyMuPDF used by the vector compositor')
    p.add_argument('--coupon', action='store_true', help='scratch fixture mode, not a deliverable')
    return p.parse_args(argv)


if __name__ == '__main__':
    build(parse())
