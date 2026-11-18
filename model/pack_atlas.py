#!/usr/bin/env python3
"""Package the verified CAD, offline viewer, sources and English illustrated README.

The first CAD-only release is kept separately. No raw input photographs or
private temporary directories are copied. Run against an already issued tree.
"""

import argparse
import base64
import csv
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from pack_release import REQUIRED, checksum


ROOT = Path(__file__).resolve().parent.parent
STUDIO_IMAGES = {finish: Path('atlas/media') / f'hero-{finish}.webp'
                 for finish in ('graphite', 'silver', 'blue', 'pink')}
EXTENSIONS = {'.svg', '.png', '.pdf', '.js', '.cjs', '.css', '.html', '.py', '.md', '.txt', '.json',
              '.csv', '.glb', '.kicad_pcb', '.kicad_pro', '.kicad_mod'}


def check_drawings(root, native_sha):
    """Reject draft, stale or mixed-source sheets even if every file exists."""
    directory = root / 'drawings'
    index = json.loads((directory / 'index.json').read_text(encoding='utf-8'))
    rows = index['sheets']
    pdf = root / 'XKAH_PRO_A43_drawings.pdf'
    if (index.get('draft') is not False or index['sourceSHA256'] != native_sha
            or index['pdf'] != pdf.name or index['pdfSHA256'] != checksum(pdf)
            or not rows or len(rows) != index['pageCount']):
        raise ValueError('Drawing set is not the indexed final PDF for this assembly')
    boards = {'main': root / 'pcb/main/GYS005-S-088-A4.3.kicad_pcb',
              'display': root / 'pcb/display/20260305A.kicad_pcb'}
    if set((root / 'pcb').rglob('*.kicad_pcb')) != set(boards.values()):
        raise ValueError('Unexpected or missing KiCad board files')
    board_hash = {key: checksum(path) for key, path in boards.items()}
    expected = {f'pcb-{key}-{n:02d}': key for key in boards for n in (1, 2)}
    pcb_dir = directory / 'pcb'
    pcb_manifest = pcb_dir / 'pcb-sheets.json'
    if checksum(pcb_manifest) != index['pcbManifestSHA256']:
        raise ValueError('Standalone PCB prints and assembly drawings differ in provenance')
    pcb_data = json.loads(pcb_manifest.read_text(encoding='utf-8'))
    pcb_pages = {item['id']: item for item in pcb_data['sheets']}
    if set(pcb_pages) != set(expected) or len(pcb_pages) != len(pcb_data['sheets']):
        raise ValueError('Wrong set of standalone PCB sheets')
    seen = set()
    pcb_sheets = set()
    for page, row in enumerate(rows, 1):
        sheet_id = row['id']
        svg = directory / (sheet_id + '.svg')
        if (Path(sheet_id).name != sheet_id or sheet_id in seen or page != row['page']
                or row['svg'] != f'drawings/{svg.name}' or row['svgSHA256'] != checksum(svg)):
            raise ValueError(f'Drawing sheet does not match its index: {sheet_id}')
        seen.add(sheet_id)
        if row['geometrySource'] == 'KiCad':
            key = expected[sheet_id]
            ref = pcb_data['sources'][key]
            printed = row['sources']
            if printed['board'] != boards[key].relative_to(root).as_posix() or printed['sha256'] != board_hash[key]:
                raise ValueError(f'{sheet_id}: signed drawing index names another board')
            if any(ref[k] != board_hash[key] for k in ('sha256', 'expected_handoff_sha256', 'restored_sha256')):
                raise ValueError(f'{sheet_id}: native board differs from its plotted and reopened source')
            for ext, field in (('pdf', 'nativePDFSHA256'), ('svg', 'nativeSVGSHA256')):
                item = pcb_pages[sheet_id]
                original = pcb_dir / f'{sheet_id}.{ext}'
                if item[ext] != original.name or item[f'{ext}_sha256'] != printed[field] or checksum(original) != printed[field]:
                    raise ValueError(f'{sheet_id}: standalone {ext} not the physical source used in the set')
            for name, value in {**ref['evidence_sources'], **ref['companions']}.items():
                companion = (root / name).resolve(strict=True)
                if not companion.is_relative_to(boards[key].parent) or checksum(companion) != value:
                    raise ValueError(f'{sheet_id}: changed evidence or footprint: {name}')
            pcb_sheets.add(sheet_id)
    if pcb_sheets != set(expected) or {p.stem for p in directory.glob('*.svg')} != seen:
        raise ValueError('Drawing sheets missing or superseded sheets still present')


def check(root):
    native = root/'XKAH_PRO_A43_rebuilt.FCStd'
    sha = checksum(native)
    qa = json.loads((root/'ATLAS_ACCEPTANCE.json').read_text())
    accepted = json.loads((root/'VERIFICATION.json').read_text())
    if sha != accepted['source_sha256'] or sha != qa['sourceSHA256'] or not accepted['valid_reopened_shapes']:
        raise ValueError('Native verification or browser check does not match the FCStd')
    service = accepted['service_assembly']
    if not qa.get('releaseAccepted') or service['native_instanced_leaves'] != accepted['physical_features']:
        raise ValueError('Incomplete physical service issue')
    if accepted['wire_anchors_and_colors'] != 14 or accepted['edit_check']['shape_errors']:
        raise ValueError('Native wire or edit check did not pass')
    if any(checksum(root/record['file']) != record['sha256'] for record in accepted['step_reimport'].values()):
        raise ValueError('Unverified STEP')
    if sha not in (root/'FIT_CHECK.csv').read_text(encoding='utf-8-sig'):
        raise ValueError('Fit report belongs to another edition')
    asset = root/'atlas/data/atlas.glb'
    glb = asset.read_bytes()
    if glb[:4] != b'glTF' or qa['glbSHA256'] != hashlib.sha256(glb).hexdigest():
        raise ValueError('Wrong exchange GLB')
    doc = json.loads(glb[20:20+struct.unpack_from('<I', glb, 12)[0]])
    script = (root/'atlas/data/scene.js').read_text()
    scene = json.loads(script[script.index('{'):].strip().removesuffix(';'))
    with (root/'MODEL_MANIFEST.csv').open(encoding='utf-8-sig', newline='') as src:
        ids = {r['object_id'] for r in csv.DictReader(src)}
    group_ids = {p['id'] for p in scene['groups']}
    if (sha != scene['sourceSHA256'] or sha != doc['asset']['extras']['sourceSHA256']
            or base64.b64decode(scene['glbBase64'], validate=True) != glb
            or ids != {p['id'] for p in scene['parts']} or ids != {mesh['name'] for mesh in doc['meshes']}
            or len(ids) != qa['physicalFeatures'] or group_ids != set(qa['groupCounts'])):
        raise ValueError('Mesh and register mismatch')
    readme_views = {'atlas-assembly': 'all', 'atlas-model': 'all', 'atlas-battery': 'Battery', 'atlas-mainboard': 'MainPCB'}
    for name, group in readme_views.items():
        state = qa['screenshotMetadata'][name]
        expected = len(ids) if group == 'all' else sum(part['group'] == group for part in scene['parts'])
        if (state['lang'] != 'en' or state['group'] != group or state['visibleParts'] != expected
                or state['serviceStep'] or state['explode'] != 0):
            raise ValueError(f'English screenshot shows the wrong model state: {name}')
        if checksum(root/'docs/screenshots'/(name+'.png')) != qa['screenshotSHA256'][name]:
            raise ValueError(f'Screenshot not from verified release: {name}')
    if {finish: checksum(root / path) for finish, path in STUDIO_IMAGES.items()} != qa['product']['imageSHA256']:
        raise ValueError('Studio finish images differ from the accepted product page')
    if [s['id'] for s in scene['service']['steps']] != service['steps']:
        raise ValueError('Wrong teardown sequence in offline payload')
    check_drawings(root, sha)
    return sha


def public_files(root):
    """Use reviewed Git paths plus named release products, never a working-directory sweep."""
    git = ['git', '-C', str(root)]
    top = subprocess.check_output([*git, 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(top).resolve() != root:
        raise ValueError('The public release must be built from the root of the project checkout')
    sources = ('README.md', 'LICENSE', 'MEASUREMENT_GAPS.md', 'XKAH_Finish.FCMacro',
               'build_model.py', 'model', 'pcb', 'atlas', 'docs')
    names = subprocess.check_output([*git, 'ls-tree', '-r', '-z', '--name-only', 'HEAD', '--', *sources])
    files = {root / os.fsdecode(name) for name in names.split(b'\0') if name}
    files.update(root / name for name in (
        'atlas/data/atlas.glb', 'atlas/data/scene.js', 'atlas/vendor/three-atlas.js', 'atlas/evidence.js',
        'ATLAS_ACCEPTANCE.json', 'VERIFICATION.json', 'MODEL_MANIFEST.csv', 'DIMENSIONS.csv',
        'FIT_CHECK.csv', 'WIRE_REGISTER.csv', 'XKAH_PRO_A43_rebuilt.FCStd', 'XKAH_PRO_A43_drawings.pdf',
        'XKAH_PRO_A43_rebuilt.step', 'XKAH_PRO_A43_electronics.step', 'XKAH_PRO_A43_outer_housing.step',
        'XKAH_PRO_A43_assembly_assembled.png', 'XKAH_PRO_A43_assembly_exploded.png', 'XKAH_PRO_A43_electronics.png',
        'pcb/main/copper_front.svg', 'pcb/main/copper_back_through_only.svg', 'drawings/index.json',
        'drawings/pcb/pcb-sheets.json',
    ))
    # check_drawings has already verified these exact sheet paths and their digests.
    index = json.loads((root / 'drawings/index.json').read_text(encoding='utf-8'))
    for sheet in index['sheets']:
        files.add(root / sheet['svg'])
        if sheet['geometrySource'] == 'KiCad':
            for extension in ('pdf', 'svg'):
                files.add(root / 'drawings/pcb' / f"{sheet['id']}.{extension}")
    return files


def entries(root):
    paths = {root/n for n in (*REQUIRED, 'XKAH_Finish.FCMacro', 'ATLAS_ACCEPTANCE.json', 'LICENSE',
                             'atlas/index.html', 'atlas/viewport.js', 'atlas/vendor/three-atlas.js',
                             'atlas/evidence.js', 'atlas/data/scene.js', 'atlas/data/atlas.glb')}
    paths.update(root / image for image in STUDIO_IMAGES.values())
    for pattern in ('model/*.py', 'model/*.json', 'model/*.cjs', 'drawings/**/*', 'pcb/**/*',
                    'XKAH_PRO_A43_*.png', 'XKAH_PRO_A43_*.pdf', 'atlas/**/*', 'docs/**/*'):
        for item in root.glob(pattern):
            private = any(x.startswith('.') or x in {'__pycache__', 'node_modules'} for x in item.relative_to(root).parts)
            if not private and item.is_file() and (item.suffix in EXTENSIONS or item.name in {'LICENSE', 'fp-lib-table'}):
                paths.add(item)
    return paths


def package(root, out, public=False):
    sha = check(root)
    paths = sorted(public_files(root) if public else entries(root))
    for item in paths:
        if item.resolve() != item or not item.is_relative_to(root) or not item.is_file() or not item.stat().st_size:
            raise ValueError(f'Missing or unsafe release entry: {item}')
    with tempfile.TemporaryDirectory(prefix='xkah-atlas-', dir=out.parent) as tmp:
        archive = Path(tmp)/out.name
        hashes = []
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for item in paths:
                name = item.relative_to(root).as_posix()
                z.write(item, name)
                hashes.append(f'{checksum(item)}  {name}')
            z.writestr('SHA256SUMS.txt', '\n'.join(hashes)+'\n')
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None or len(z.namelist()) != len(paths)+1:
                raise ValueError('ZIP readback failed')
            for line in z.read('SHA256SUMS.txt').decode().splitlines():
                expected, name = line.split('  ', 1)
                if hashlib.sha256(z.read(name)).hexdigest() != expected:
                    raise ValueError(f'Bad checksum: {name}')
        os.replace(archive, out)
    print(f'{len(paths)} files + SHA256SUMS.txt; input CAD {sha}; ZIP {out.stat().st_size:,} bytes; SHA-256 {checksum(out)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--public', action='store_true',
                        help='Build the GitHub edition without private photo overlays or workspace captures')
    args = parser.parse_args()
    base = args.root.resolve()
    default = 'XYKA_PRO_A43_Studio.zip' if args.public else 'XKAH_PRO_A43_browser_atlas.zip'
    package(base, (args.output or base / default).resolve(), public=args.public)
