#!/usr/bin/env python3
"""Read-only check for true board dimensions and mount section geometry after pose edits.

Use FreeCAD's bundled Python, for example:
    PYTHONPATH="$R/lib" "$R/bin/python" model/plates_verify_pose.py --input staging/assembly.FCStd

The extra test orientations are applied to copies of the B-reps, never to the
open document. No reference measurements or assumed world-aligned board are used.
"""

import argparse
from dataclasses import replace
from pathlib import Path

import FreeCAD as App
import numpy as np

from plates_assets import Assets
from plates_scene import Scene, board_layers, distance_between_layers, flat_face_normal, frame_box, substrate


def placed(item, transform):
    shape = item.shape.copy()
    shape.Placement = transform.multiply(shape.Placement)
    return replace(item, shape=shape)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(scene):
    roots = ('MainPCB', 'DisplayPCB')
    layers = [board_layers(scene, root) for root in roots]
    frames = [scene.board_frame(root) for root in roots]
    dims = []
    for root, current, frame in zip(roots, layers, frames):
        face = flat_face_normal(substrate(scene, root))
        require(abs(face @ frame[2]) > .99999, f'{root}: group normal is not normal to laminate')
        lo, hi = frame_box(current, frame)
        dims.append(hi-lo)
        require(scene.board_studio_frame(root)[2] @ frame[2] > .85, f'{root}: wrong studio side')
        print(f'{root}: W × L × t = {hi[0]-lo[0]:.3f} × {hi[1]-lo[1]:.3f} × {hi[2]-lo[2]:.3f} mm')
    gap = distance_between_layers(*layers)
    print(f'Shortest substrate-to-substrate distance: {gap:.3f} mm (not assembled clearance).')

    for direction, angle in (((1, 0, 0), -18), ((.29, .6, -.73), 47), ((.2, .8, -.41), 87)):
        rot = App.Rotation(App.Vector(*direction), angle)
        transform = App.Placement(App.Vector(-15.25, 26.75, 13.125), rot)
        basis = np.stack([tuple(rot.multVec(App.Vector(*v))) for v in np.eye(3)])
        moved = []
        for root, current, frame, expected in zip(roots, layers, frames, dims):
            copy = [placed(item, transform) for item in current]
            lo, hi = frame_box(copy, frame @ basis)
            require(np.allclose(hi-lo, expected, rtol=0, atol=.001),
                    f'{root}: false projected material length/width/thickness after {angle}° rotation')
            moved.append(copy)
        require(np.isclose(gap, distance_between_layers(*moved), rtol=0, atol=.001),
                f'Substrate separation changed under {angle}° common rigid rotation')

    u, _, w = scene.board_frame('DisplayPCB')
    cut = Assets(scene).cuts()
    require(np.allclose(cut.seat_frame[2], u, atol=1e-7), 'Section B normal disagrees with locator right')
    require(abs(u @ cut.mount_point - cut.seat_depth) < 1e-6, 'Section B misses retained mount centre')
    require(abs(w @ cut.seat_frame[2]) < 1e-7, 'Section B must be edge-on in its locator')
    print(f'Б–Б: through {cut.mount.name}; normal XYZ {u.round(7).tolist()}.')
    print('PASS: physical board frames, three off-axis poses, true material extents and section incidence.')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input', type=Path, required=True)
    scene = Scene(cli.parse_args().input)
    try:
        check(scene)
    finally:
        scene.close()
