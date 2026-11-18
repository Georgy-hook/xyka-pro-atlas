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
import tempfile
import zipfile

from pack_release import REQUIRED, checksum


ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = {'.svg', '.png', '.js', '.cjs', '.css', '.html', '.py', '.md', '.txt', '.json', '.glb'}


def check(root):
    native = root/'XKAH_PRO_A43_rebuilt.FCStd'
    sha = checksum(native)
    qa = json.loads((root/'ATLAS_ACCEPTANCE.json').read_text())
    accepted = json.loads((root/'VERIFICATION.json').read_text())
    if sha != accepted['source_sha256'] or sha != qa['sourceSHA256'] or not accepted['valid_reopened_shapes']:
        raise ValueError('Native verification or browser check does not match the FCStd')
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
    for name in ('atlas-assembly', 'atlas-mainboard'):
        if checksum(root/'docs/screenshots'/(name+'.png')) != qa['screenshotSHA256'][name]:
            raise ValueError(f'Screenshot not from verified release: {name}')
    if len(list((root/'drawings').glob('*.svg'))) != 9:
        raise ValueError('Missing A3 sheets')
    return sha


def entries(root):
    paths = {root/n for n in (*REQUIRED, 'XKAH_Finish.FCMacro', 'ATLAS_ACCEPTANCE.json', 'LICENSE',
                             'atlas/index.html', 'atlas/viewport.js', 'atlas/vendor/three-atlas.js',
                             'atlas/evidence.js', 'atlas/data/scene.js', 'atlas/data/atlas.glb')}
    for pattern in ('model/*.py', 'model/*.json', 'model/*.cjs', 'drawings/*.svg', 'drawings/*.png',
                    'XKAH_PRO_A43_*.png', 'atlas/**/*', 'docs/**/*'):
        for item in root.glob(pattern):
            private = any(x.startswith('.') or x in {'__pycache__', 'node_modules'} for x in item.relative_to(root).parts)
            if not private and item.is_file() and (item.suffix in EXTENSIONS or item.name == 'LICENSE'):
                paths.add(item)
    for item in paths:
        if not item.is_file() or item.is_symlink() or not item.stat().st_size:
            raise ValueError(f'Missing or unsafe release entry: {item}')
    return sorted(paths)


def package(root, out):
    sha = check(root)
    paths = entries(root)
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
    args = parser.parse_args()
    base = args.root.resolve()
    package(base, (args.output or base/'XKAH_PRO_A43_browser_atlas.zip').resolve())
