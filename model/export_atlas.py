#!/usr/bin/env python3
"""Publish a saved FreeCAD assembly as glTF 2.0 and an offline browser payload.

Use FreeCAD's Python, e.g. ``python model/export_atlas.py --input FILE.FCStd --out DIR``.
No model generation, recompute, export document or intermediate exchange file.
"""

import argparse
import base64
import csv
import hashlib
from importlib.util import find_spec
import json
import os
from pathlib import Path
import re
import struct
import sys
from tempfile import TemporaryDirectory


# Visual response under light, not measurements or declarations of composition.
# Always combine a profile with the *individual CAD ColorHex*, never recolor.
# Moderate metallic factors keep the features visible without an environment map.
FINISH = {  # name: (metallic, roughness)
    'matte': (0.0, 0.74), 'satin-shell': (0.32, 0.44), 'bright-rim': (0.57, 0.27),
    'key-field': (0.46, 0.34), 'key-mark': (0.21, 0.42), 'exposed-metal': (0.73, 0.32),
    'solder': (0.57, 0.39), 'gloss-front': (0.0, 0.21), 'window': (0.0, 0.14),
    'pcb-mask': (0.0, 0.40), 'disk-surface': (0.0, 0.55), 'disk-graphic': (0.0, 0.46),
    'jacket': (0.0, 0.54),
}

SHELL = {'MechUpperFairing', 'MechLowerShroud', 'MechBevelGrip', 'MechRearClevis', 'MechRearHingeLeaf'}
KEYS = {'MechOuterKeyL', 'MechOuterKeyC', 'MechOuterKeyR', 'MechFrontUnlockKey',
        'MechPackReleaseKey', 'MechRearEjectKey'}
EXPOSED = {'MechHeatGuard', 'MechRemovablePod', 'MechPodLid', 'MechStemFacePlate', 'MechStemSocket',
           'MechClosurePin', 'MechClosurePinGuide', 'MechHingeAxle', 'PcPlatedWalls', 'PcRGBFootprints',
           'PcRGBTails', 'UiRim', 'UiPerforatedLand', 'UiWitnessEye', 'UiFieldBrightSites'}
BY_ID = {**dict.fromkeys(SHELL, 'satin-shell'), **dict.fromkeys(EXPOSED, 'exposed-metal'),
         **dict.fromkeys(KEYS, 'bright-rim'), **{k + 'Field': 'key-field' for k in KEYS},
         **{k + 'Mark': 'key-mark' for k in KEYS}, 'MechFrontUnlockBezel': 'bright-rim',
         'MechServiceCover': 'gloss-front', 'UiGlass': 'window',
         'PcMaskFace': 'pcb-mask', 'PcMaskRear': 'pcb-mask', 'UiSubstrate': 'pcb-mask',
         'MechHeaterPlate': 'disk-surface', 'MechHeaterFaceBands': 'disk-graphic'}


def finish_for(name, group):
    if name in BY_ID:
        return BY_ID[name]
    if group == 'Harness':
        return 'jacket'  # even the two clear jackets stay opaque for reliable picking/sorting
    if name.startswith(('PcJoint', 'UiSolderWitness')) or name.endswith('_Solder'):
        return 'solder'
    if (name.endswith(('_Leads', '_Lands')) or (name.startswith('PcSm') and name.endswith('Ends'))
            or name.startswith(('MechServiceScrew', 'PcSolderLand', 'PcRGBEntry', 'UiFlexFinger',
                                'UiFlexPad', 'UiSwitchPads', 'UiSwitchCan', 'UiSwitchClips', 'UiSwitchLeads'))
            or re.fullmatch(r'Ui(Contact(Eye)?|Edge(Pad|Eye))\d+', name)):
        return 'exposed-metal'
    return 'matte'


def json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def ids_digest(names):
    return hashlib.sha256('\n'.join(sorted(names)).encode('utf-8')).hexdigest()


def check_manifest(src, names):
    """The FCStd stands alone; if its release register is present it must agree."""
    manifest = src.with_name('MODEL_MANIFEST.csv')
    if not manifest.is_file():
        print('No adjacent MODEL_MANIFEST.csv; verifying against native physical leaves only.')
        return
    with manifest.open(encoding='utf-8-sig', newline='') as f:
        registered = [row['object_id'] for row in csv.DictReader(f)]
    expected = set(registered)
    if len(expected) != len(registered) or expected != names:
        raise ValueError(f'{manifest}: duplicate IDs={len(registered) - len(expected)}, '
                         f'only in register={sorted(expected - names)}, only in CAD={sorted(names - expected)}')
    print(f'{manifest.name}: all {len(expected)} unique object_id match the native leaves; '
          f'sorted ID SHA-256 {ids_digest(expected)}', flush=True)


def linear_rgb(color):
    # glTF baseColorFactor is linear-light; ColorHex and CSS encode sRGB.
    srgb = [n / 255.0 for n in bytes.fromhex(color[1:])]
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb]


class BinaryScene:
    def __init__(self, source_hash, groups):
        roots = list(range(len(groups)))
        self.root_ids = {group['id']: i for i, group in enumerate(groups)}
        self.by_finish = {}
        self.blob = bytearray()
        self.triangles = 0
        self.doc = {
            'asset': {'version': '2.0', 'generator': 'FreeCAD / XKAH atlas',
                      'extras': {'sourceSHA256': source_hash}},
            'scene': 0, 'scenes': [{'name': 'Assembly', 'nodes': roots}],
            'nodes': [{'name': g['id'], 'extras': g, 'children': []} for g in groups],
            'meshes': [], 'materials': [], 'accessors': [], 'bufferViews': [],
        }

    def accessor(self, data, target, kind, component, bounds=None):
        # Four-byte-aligned views; tightly packed little-endian arrays, no decoder/extensions.
        self.blob.extend(b'\x00' * (-len(self.blob) % 4))
        views = self.doc['bufferViews']
        view = len(views)
        views.append({'buffer': 0, 'byteOffset': len(self.blob), 'byteLength': data.nbytes,
                      'target': target})
        self.blob.extend(data.tobytes(order='C'))
        accessors = self.doc['accessors']
        result = {'bufferView': view, 'componentType': component, 'count': len(data), 'type': kind}
        if bounds is not None:
            result['min'], result['max'] = bounds
        accessors.append(result)
        return len(accessors) - 1

    def material(self, color, finish):
        key = (color, finish)
        if key not in self.by_finish:
            metallic, roughness = FINISH[finish]
            self.by_finish[key] = len(self.doc['materials'])
            self.doc['materials'].append({
                'name': f'{finish} {color}', 'extras': {'color': color, 'visualProfile': finish},
                'pbrMetallicRoughness': {'baseColorFactor': [*linear_rgb(color), 1.0],
                                         'metallicFactor': metallic, 'roughnessFactor': roughness},
            })
        return self.by_finish[key]

    def add_part(self, part, xyz, normals, indices):
        bbox = part['bbox']
        pos = self.accessor(xyz, 34962, 'VEC3', 5126, (bbox[:3], bbox[3:]))
        normal = self.accessor(normals, 34962, 'VEC3', 5126)
        index = self.accessor(indices.ravel(), 34963, 'SCALAR', 5123 if indices.itemsize == 2 else 5125)
        profile = finish_for(part['id'], part['group'])
        primitive = {'mode': 4, 'attributes': {'POSITION': pos, 'NORMAL': normal},
                     'indices': index, 'material': self.material(part['color'], profile)}
        meshes = self.doc['meshes']
        nodes = self.doc['nodes']
        name = part['id']
        nodes[self.root_ids[part['group']]]['children'].append(len(nodes))
        nodes.append({'name': name, 'extras': part, 'mesh': len(meshes)})
        meshes.append({'name': name, 'extras': {'id': name}, 'primitives': [primitive]})
        self.triangles += len(indices)

    def encode(self):
        self.doc['buffers'] = [{'byteLength': len(self.blob)}]
        scene = json_bytes(self.doc)
        scene += b' ' * (-len(scene) % 4)
        self.blob.extend(b'\x00' * (-len(self.blob) % 4))
        header = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(scene) + 8 + len(self.blob))
        return b''.join((header, struct.pack('<I4s', len(scene), b'JSON'), scene,
                         struct.pack('<I4s', len(self.blob), b'BIN\x00'), self.blob))


def export(src, out):
    import numpy as np
    from plates_scene import ROOTS, Scene
    from atlas_mesh import gltf_metres, tessellate

    src, out = src.resolve(), out.resolve()
    if src.suffix.casefold() != '.fcstd':
        raise ValueError('--input must be a saved .FCStd document')
    source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    scene = Scene(src)
    try:
        check_manifest(src, set(scene.named))
        groups = [{'id': root, 'label': scene.parts[root].Label,
                   'explode': gltf_metres(scene.offsets[root]).tolist()} for root in ROOTS]
        binary = BinaryScene(source_hash, groups)
        parts = []
        worst_mm = 0.0
        for root in ROOTS:
            for item in scene.by[root]:
                try:
                    p, n, ix = tessellate(item)
                except Exception as e:
                    raise RuntimeError(f'Cannot tessellate {item.name} ({item.label}): {e}') from e
                lo, hi = p.min(axis=0), p.max(axis=0)
                # After the Y sign flip, one axis's min and max trade places.
                cad = gltf_metres(item.box)
                err_mm = 1000 * np.max(np.abs(np.stack((lo, hi)) - np.sort(cad, axis=0)))
                if err_mm > 0.101:  # 2x maximum chord tolerance + numerical margin
                    raise ValueError(f'{item.name}: mesh bounds differ from placed B-rep by {err_mm:g} mm')
                worst_mm = max(worst_mm, err_mm)
                color = item.color.lower()
                if not re.fullmatch(r'#[0-9a-f]{6}', color):
                    raise ValueError(f'{item.name}: invalid ColorHex {item.color!r}')
                part = {'id': item.name, 'label': item.label, 'group': root, 'color': color,
                        'sub': scene.doc.getObject(item.chain[-1]).Label if len(item.chain) > 1 else '',
                        'bbox': lo.tolist() + hi.tolist(), 'evidence': item.obj.EvidenceSource,
                        'confidence': item.obj.Confidence, 'note': item.obj.ReconstructionNote}
                binary.add_part(part, p, n, ix)
                parts.append(part)
            print(f'{root}: {len(scene.by[root])} meshes', flush=True)
        if {m['name'] for m in binary.doc['meshes']} != set(scene.named):
            raise ValueError('Output mesh names do not match all registered leaves')
        glb = binary.encode()
    finally:
        scene.close()  # deliberately no recompute()/save()
    if hashlib.sha256(src.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError(f'Source changed during export; not publishing: {src}')
    payload = {'sourceSHA256': source_hash, 'groups': groups, 'parts': parts,
               'triangleCount': binary.triangles, 'glbBase64': base64.b64encode(glb).decode('ascii')}
    out.mkdir(parents=True, exist_ok=True)
    # Stage complete files before publishing: a failed export never leaves truncated JS/GLB.
    with TemporaryDirectory(prefix='.atlas-', dir=out) as tmp:
        js_path, glb_path = Path(tmp) / 'scene.js', Path(tmp) / 'atlas.glb'
        glb_path.write_bytes(glb)
        js_path.write_bytes(b'window.ATLAS_SCENE=' + json_bytes(payload) + b';\n')
        glb_path.replace(out / 'atlas.glb')
        js_path.replace(out / 'scene.js')
    print(f'{src.name} SHA-256 {source_hash}\n{out}: {len(parts)} parts, {binary.triangles} triangles, '
          f'{len(glb):,} GLB bytes; max mesh/CAD bbox error {worst_mm:.6f} mm', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='saved native assembly (.FCStd)')
    parser.add_argument('--out', type=Path, required=True, help='directory for atlas.glb and scene.js')
    args = parser.parse_args()
    # The stock macOS bundle ships bin/python but no bin/python3. A direct
    # ./export_atlas.py must not load an OCCT extension with Xcode's Python ABI.
    if sys.platform == 'darwin' and not all(find_spec(m) for m in ('FreeCAD', 'OCC')):
        bundle = Path('/Applications/FreeCAD.app/Contents/Resources')
        python = bundle / 'bin/python'
        if python.is_file():
            lib = str(bundle / 'lib')
            if Path(sys.executable).resolve() != python.resolve():
                env = os.environ.copy()
                env['PYTHONPATH'] = os.pathsep.join(filter(None, [lib, env.get('PYTHONPATH')]))
                os.execve(python, [str(python), __file__, *sys.argv[1:]], env)
            sys.path.insert(0, lib)
    export(args.input, args.out)


if __name__ == '__main__':
    main()
