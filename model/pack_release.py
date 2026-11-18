"""Package only the finished reconstruction, its evidence reports and rebuild sources."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parent.parent
STEM = 'XKAH_PRO_A43_'
REQUIRED = ('README.md', 'MEASUREMENT_GAPS.md', 'build_model.py', 'DIMENSIONS.csv', 'WIRE_REGISTER.csv',
            'MODEL_MANIFEST.csv', 'FIT_CHECK.csv', 'VERIFICATION.json', 'drawings/FreeCAD_tree.png',
            STEM+'rebuilt.FCStd', STEM+'rebuilt.step', STEM+'outer_housing.step', STEM+'electronics.step',
            STEM+'drawings.pdf', STEM+'assembly_exploded.png', STEM+'overlay_reference.png')


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def pack(root, output):
    paths = {root / name for name in REQUIRED}
    for spec in ('model/*.py', 'model/*.json', 'drawings/*.svg', 'drawings/*.png', STEM+'*.png'):
        paths.update(root.glob(spec))
    for item in paths:
        if not item.is_file() or item.stat().st_size == 0:
            raise FileNotFoundError(item)
    if len(list((root/'drawings').glob('*.svg'))) != 9:
        raise ValueError('Missing A3 drawing sheet(s)')
    result = json.loads((root/'VERIFICATION.json').read_text())
    current_hash = checksum(root / (STEM + 'rebuilt.FCStd'))
    if (result['source_sha256'] != current_hash or not result['valid_reopened_shapes']
            or result['wire_anchors_and_colors'] != 14):
        raise ValueError('Invalid verification result')
    if any(checksum(root / data['file']) != data['sha256'] for data in result['step_reimport'].values()):
        raise ValueError('A STEP file changed after the round-trip check')
    if current_hash not in (root/'FIT_CHECK.csv').read_text(encoding='utf-8-sig'):
        raise ValueError('Fit check belongs to a different FCStd')
    hashes = []
    with tempfile.TemporaryDirectory(prefix='xkah-publication-', dir=output.parent) as tmp:
        archive = Path(tmp) / output.name
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
            for source in sorted(paths):
                name = source.relative_to(root).as_posix()
                out.write(source, name)
                hashes.append(checksum(source) + '  ' + name)
            out.writestr('SHA256SUMS.txt', '\n'.join(hashes) + '\n')
        with zipfile.ZipFile(archive) as check:
            if check.testzip() is not None or len(check.namelist()) != len(paths)+1:
                raise IOError('Release ZIP failed CRC/content checks')
        os.replace(archive, output)
    print(f'{output} — {len(paths)} files + SHA256SUMS.txt; {output.stat().st_size:,} bytes; CRC OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    pack(root, (args.output or root/(STEM+'release.zip')).resolve())
