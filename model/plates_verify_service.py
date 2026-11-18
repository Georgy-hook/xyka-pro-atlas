#!/usr/bin/env python3
"""Read-only check that the actual native exploded state and drawing use the same poses.

Run with FreeCAD Python. --fixture permits a development document without native
exploded links or finished battery artwork; never use that waiver to accept an issue.
"""

import argparse
from collections import Counter
from pathlib import Path

import FreeCAD as App
import numpy as np

from plates_assets import Assets
from plates_scene import Scene, flat_face_normal, frame_box, global_shape


def check(condition, message):
    if not condition:
        raise ValueError(message)


def box(shape):
    b = shape.optimalBoundingBox(False, False)
    return np.array([b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax])


def native_links(scene):
    root = scene.doc.getObject('Exploded')
    check(root is not None and len(root.Group) > 0, 'Missing native Exploded state')
    covered = Counter()
    worst = 0.
    for link in root.Group:
        check(link.TypeId == 'App::Link' and link.LinkTransform, f'{link.Name}: not a transformed link')
        target = link.LinkedObject
        members = [i for i in scene.items if target.Name in (*i.chain, i.name)]
        check(members, f'{link.Name}: the native link does not reference registered Assembly geometry')
        delta = scene.leaf_offsets[members[0].name]
        check(all(np.allclose(scene.leaf_offsets[i.name], delta, atol=1e-7, rtol=0) for i in members),
              f'{link.Name}: link groups leaves with distinct native shifts')
        covered.update(i.name for i in members)
        # LinkTransform preserves the target's local placement. Its stored
        # LinkPlacement must therefore include that target's *parent* frame.
        target_parent = target.getGlobalPlacement().multiply(target.Placement.inverse())
        diff = root.getGlobalPlacement().multiply(link.LinkPlacement).multiply(target_parent.inverse())
        check(abs(diff.Rotation.Angle) < 1e-6 and np.allclose(tuple(diff.Base), delta, atol=2e-5, rtol=0),
              f'{link.Name}: link placement is not the saved global-mm drawing shift')
        # Independent geometric readback: actual linked B-rep versus the real
        # installed target translated according to the renderer, not the layout script.
        expected = global_shape(target)
        expected.translate(App.Vector(*delta))
        # App::Link need not expose GeoFeature.getGlobalPlacement. Its own
        # Shape already contains LinkPlacement; add ONLY its container.
        actual = link.Shape.copy()
        actual.Placement = root.getGlobalPlacement().multiply(actual.Placement)
        error = max(abs(box(actual) - box(expected)))
        check(error < .015, f'{link.Name}: B-rep extent mismatch {error:g} mm')
        check(abs(actual.Volume - expected.Volume) < max(.001, abs(expected.Volume)*2e-7),
              f'{link.Name}: different linked material')
        worst = max(worst, error)
    check(set(covered) == set(scene.named) and max(covered.values()) == 1,
          'Native links omit or duplicate registered physical leaves')
    print(f'Native readback: {len(root.Group)} actual links, {len(covered)} unique leaves, '
          f'max projected-independent 3-D bound error {worst:.6g} mm.')


def verify(scene, fixture=False):
    check(scene.structured, 'Expected the native upper/lower retail hierarchy')
    a = Assets(scene)
    delta = scene.leaf_offsets
    unique = {tuple(d) for d in delta.values()}
    check(len(unique) > 1 and set(delta) == set(scene.named), 'Invalid per-leaf service state')
    registered = {o.Name for o in scene.doc.Objects
                  if o.TypeId != 'App::Link' and 'ColorHex' in o.PropertiesList and hasattr(o, 'Shape')}
    check(registered == set(scene.named), 'Registered solid outside Assembly or repeated source traversal')
    check(all(i in a.service.exterior for i in a.service.film), 'U mask or its pane missing from closed view')
    check(np.array_equal(delta['MechCoverWindow'], delta['MechServiceCover']), 'Mask and pane separated')
    carrier = delta['MechKeyCarrier']
    check(not np.array_equal(delta['MechCoverWindow'], carrier), 'Outer film not removable from carrier')
    check(all(np.array_equal(delta[i.name], carrier) for i in scene.by['Fascia'] if i.name.startswith('MechOuterKey')),
          'A permanent outer key mark detached from its actuator')
    check(not np.array_equal(delta[a.service.membrane[0].name], delta['UiGlass']), 'Membrane not separate in service state')
    frame = scene.board_frame('DisplayPCB')
    for name in ('UiGlass', 'MechCoverWindow'):
        item = scene.named[name]
        check(abs(flat_face_normal(item) @ frame[2]) > .9999, f'{name}: unexpected optical plane')
        lo, hi = frame_box([item], frame)
        print(f'{name}: local W × L × t = {hi[0]-lo[0]:.3f} × {hi[1]-lo[1]:.3f} × {hi[2]-lo[2]:.3f} mm (CAD, not active pixels).')
    if not fixture:
        for item in scene.by['Pod']:
            if item.name not in ('MechPodScreen', 'MechPodLid'):
                check(np.array_equal(delta[item.name], delta['MechRemovablePod']),
                      f'{item.name}: marking or body does not move with cup')
        check(all(np.array_equal(delta[i.name], delta['PcLaminateCore']) for i in scene.by['Harness']),
              'Harness does not travel with its board')
        check(scene.named['MechPackEndContacts'].root == 'Battery' and
              scene.named['MechPackSeatSockets'].root != 'Battery', 'Pack/seat contacts conflated')
    if not fixture or scene.doc.getObject('Exploded') is not None:
        native_links(scene)
    print(f'PASS: {len(scene.units)} physical units, {len(scene.roots)} registered modules, '
          f'{len(scene.items)} leaves and {len(unique)} distinct stored translations.'
          + (' DEVELOPMENT FIXTURE.' if fixture else ''))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--fixture', action='store_true')
    args = p.parse_args()
    scene = Scene(args.input)
    try:
        verify(scene, args.fixture)
    finally:
        scene.close()
