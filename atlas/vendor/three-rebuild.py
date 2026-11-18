#!/usr/bin/env python3
"""Reproduce three-atlas.js (no network, npm install or Node required).

Usage: python3 three-rebuild.py /path/to/three-0.187.0.tgz /path/to/esbuild
Source: https://registry.npmjs.org/three/-/three-0.187.0.tgz (MIT, r187).
Tool: esbuild 0.28.2 CLI (https://github.com/evanw/esbuild/releases/tag/v0.28.2).
Only the generated classic script and the adjacent MIT license ship to the viewer.
"""

import argparse
import base64
import hashlib
from pathlib import Path
import subprocess
import tarfile
import tempfile


INTEGRITY = 'Qiu7R+Cmh8CstZsY1uJOSWnVlfo7ZtNLV7mF8Jltk3LB3AtDu9cRZlcnRKkAk8Y4z6KKw35z7Y7Urd7jWY8etA=='
VERSION = '0.28.2'
FILES = (
    'package.json', 'LICENSE', 'build/three.core.js', 'build/three.module.js',
    'examples/jsm/controls/OrbitControls.js', 'examples/jsm/loaders/GLTFLoader.js',
    'examples/jsm/utils/BufferGeometryUtils.js', 'examples/jsm/utils/SkeletonUtils.js',
)
ENTRY = """\
export {
    Box3, CanvasTexture, Color, DataTexture, DirectionalLight,
    EquirectangularReflectionMapping, FloatType, HemisphereLight, LinearSRGBColorSpace,
    LoadingManager, Mesh, NeutralToneMapping, PCFShadowMap, PerspectiveCamera,
    PlaneGeometry, Raycaster, RGBAFormat, Scene, ShadowMaterial, SRGBColorSpace,
    Vector2, Vector3, WebGLRenderer
} from 'three';
export { OrbitControls } from 'three/addons/controls/OrbitControls.js';
export { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
"""


def rebuild(tarball, esbuild):
    if hashlib.sha512(tarball.read_bytes()).digest() != base64.b64decode(INTEGRITY):
        raise SystemExit('Not the published three@0.187.0 tarball (SHA-512 mismatch).')
    cli = str(esbuild.resolve())
    if subprocess.check_output([cli, '--version'], text=True).strip() != VERSION:
        raise SystemExit(f'Expected esbuild {VERSION}.')

    vendor = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package = root / 'node_modules/three'
        with tarfile.open(tarball, 'r:gz') as archive:
            for name in FILES:
                dest = package / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.extractfile(f'package/{name}').read())
        (root / 'entry.js').write_text(ENTRY, encoding='utf-8')
        bundle = root / 'three-atlas.js'
        subprocess.run([
            cli, 'entry.js', '--bundle', '--format=iife', '--global-name=AtlasThree',
            '--platform=browser', '--target=es2020', '--minify', '--legal-comments=inline',
            '--banner:js=/*! three.js r187 · MIT · see three-LICENSE.txt */',
            f'--outfile={bundle.name}',
        ], cwd=root, check=True)
        (vendor / bundle.name).write_bytes(bundle.read_bytes())
        (vendor / 'three-LICENSE.txt').write_bytes((package / 'LICENSE').read_bytes())
        print('three-atlas.js SHA-256:', hashlib.sha256(bundle.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tarball', type=Path)
    parser.add_argument('esbuild', type=Path)
    args = parser.parse_args()
    rebuild(args.tarball, args.esbuild)
