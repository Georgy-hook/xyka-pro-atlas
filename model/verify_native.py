"""Reopen FCStd, exercise native dependencies and compare three reimported STEP sets.

Run with FreeCAD's bundled Python (see README). Changes are intentionally never saved.
"""

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
import traceback

import FreeCAD as App
import Part
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps

from context import world_shape
from pack_release import checksum


PREFIX = 'XKAH_PRO_A43_'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def bbox(shape):
    b = shape.BoundBox
    return (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)


def solid_volume(solid):
    # A fixed-order quadrature of trimmed splines can differ after STEP
    # reparametrizes the *same* surface. Integrate both B-reps adaptively;
    # do not relax the exchange acceptance threshold or use a mesh volume.
    props = GProp_GProps()
    brepgprop.VolumeProperties(Part.__toPythonOCC__(solid), props, 1e-7, True, False)
    volume = abs(props.Mass())
    require(math.isfinite(volume) and volume > 0., 'Degenerate solid in volume measurement')
    return volume


def step_summary(objects):
    solids = 0
    volume = 0.0
    boxes = []
    for obj in objects:
        shape = world_shape(obj)
        # A printed feature can contain both solids and closed ink outlines.
        solids += len(shape.Solids)
        volume += sum(solid_volume(solid) for solid in shape.Solids)
        boxes.append(bbox(shape))
    bounds = [min(bb[j] for bb in boxes) if j < 3 else max(bb[j] for bb in boxes) for j in range(6)]
    return solids, volume, bounds


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as csvfile:
        return list(csv.DictReader(csvfile))


def fascia_profile(doc):
    """Use the reopened *physical* cheeks, mask and glass; ignore display meshes."""
    def face_normal(face):
        u0, u1, v0, v1 = face.ParameterRange
        return face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)

    # A rigid rotation of the *entire* old model produces a similar front
    # angle to world Z. The socket mouth must still lie in the chassis base.
    socket = world_shape(doc.MechStemSocket)
    end_faces = [f for f in socket.Faces if f.Surface.TypeId == 'Part::GeomPlane']
    require(end_faces and abs(face_normal(max(end_faces, key=lambda f: f.Area)).z) > .9999,
            'Base socket is not upright: do not tilt the entire assembly')
    shapes = [world_shape(doc.getObject(n)) for n in ('MechUpperFairing', 'MechServiceCover')]
    for key in ('TopL', 'TopR', 'SideR', 'Foot'):
        ear = doc.getObject('MechPanelEar' + key)
        require(len(ear.Shape.Solids) == 1, f'Disconnected mounting-ear offcut: {key}')
    height = doc.Parameters.BodyH.Value
    levels = [height * f for f in (.60, .72, .90)]
    ys = []
    for z in levels:
        loops = [wire for shape in shapes for wire in shape.slice(App.Vector(0, 0, 1), z)]
        require(loops, f'No front profile at Z={z:.2f} mm')
        ys.append(min(w.optimalBoundingBox(False, False).YMin for w in loops))

    # In the side photograph the upper edge retreats inward; in the earlier
    # model these three cut planes all met the same vertical front at Y=0.
    angle = math.degrees(math.atan2(ys[-1] - ys[0], levels[-1] - levels[0]))
    require(ys[0] < ys[1] < ys[2] and 4 < angle < 13, 'Front of the screen bay is not raked inward')
    outward = doc.DisplayPCB.getGlobalPlacement().Rotation.multVec(App.Vector(0, 0, 1))
    alignments = []
    for shape in (shapes[-1], world_shape(doc.UiGlass)):
        face = max(shape.Faces, key=lambda f: f.Area)
        alignments.append(abs(face_normal(face).dot(outward)))
    require(min(alignments) > .999 and outward.y < 0 and outward.z > .05,
            'Mask, glass and display board do not face the same inclined opening')
    return dict(section_z_mm=[round(z, 4) for z in levels], foremost_y_mm=[round(y, 4) for y in ys],
                side_rake_deg=round(angle, 3), glass_and_mask_follow_display_normal=True,
                base_socket_upright=True,
                status='ESTIMATE: side-image comparison, not a production angle')


def verify(root):
    path = root / (PREFIX + 'rebuilt.FCStd')
    doc = App.openDocument(str(path))
    sheet = doc.getObject('Parameters')
    manifest = rows(root / 'MODEL_MANIFEST.csv')
    dims = {r['parameter']: r for r in rows(root / 'DIMENSIONS.csv')}
    leaves = [doc.getObject(row['object_id']) for row in manifest]
    require(len(leaves) == len(set(x.Name for x in leaves)), 'Duplicate leaf IDs')
    require(all(x and 'EvidenceSource' in x.PropertiesList for x in leaves), 'Manifest / native leaf mismatch')
    require(all(not o.Shape.isNull() and o.Shape.isValid() for o in leaves), 'Invalid reopened BRep')
    require({x.Name for x in doc.Objects if 'EvidenceSource' in x.PropertiesList} == {x.Name for x in leaves},
            'Missing native item in manifest')
    groups = ['Housing', 'MainPCB', 'DisplayPCB', 'Heater', 'Battery', 'Harness', 'Mounts']
    require(all(doc.getObject(name).TypeId == 'App::Part' for name in groups), 'Missing assembly module')
    require(all(len(doc.getObject(name).Group) for name in groups), 'Empty assembly module')
    require(doc.Exploded.Visibility is False and doc.Assembly.Visibility, 'Startup visibility')
    require(len(doc.Exploded.Group) == len(groups) and all(o.LinkedObject for o in doc.Exploded.Group),
            'Dangling exploded reference')
    report = dict(source=path.name, source_sha256=checksum(path),
                  freecad_version='.'.join(App.Version()[:3]), physical_features=len(leaves),
                  document_objects=len(doc.Objects), parameter_aliases=len(dims),
                  exploded_links=len(doc.Exploded.Group), valid_reopened_shapes=True)
    report['installed_fascia'] = fascia_profile(doc)
    print('=== Native file reopened; assemblies, manifest, parameters and B-reps checked', flush=True)
    wires = {o.Contact: o for o in leaves if 'Contact' in o.PropertiesList and o.TypeId == 'Part::Loft'}
    expected = {'B+': 'red', 'B-': 'black', 'F+': 'blue', 'F-': 'blue', 'Clear1': 'clear', 'Clear2': 'clear',
                'GND': 'white', 'KEY+': 'white', 'S-': 'black', 'S+': 'red',
                'RGB1': 'white', 'RGB2': 'blue.rgb', 'RGB3': 'black', 'RGB4': 'red'}
    require({k: w.Insulation for k, w in wires.items()} == expected, 'Wire count or insulation mismatch')
    require(all(len(w.Shape.Solids) == 1 and len(w.Sections) >= 5 for w in wires.values()), 'Incomplete loft')
    wire_rows = rows(root / 'WIRE_REGISTER.csv')
    for row in wire_rows:
        start = wires[row['contact_or_pin']].Sections[0].Placement.Base
        nominal = App.Vector(float(row['u_over_w'])*sheet.BoardW.Value, float(row['v_over_l'])*sheet.BoardL.Value,
                             float(row['w_at_exit_mm']))
        require((start-nominal).Length < .001, f'Lead anchor: {row["contact_or_pin"]}')
    report['wire_anchors_and_colors'] = 14
    group_ids = {name: {obj.Name for obj in doc.getObject(name).Group + doc.getObject(name).OutListRecursive}
                 for name in groups}
    variants = {'rebuilt': groups, 'outer_housing': ['Housing', 'Mounts'],
                'electronics': ['MainPCB', 'DisplayPCB', 'Harness']}
    report['step_reimport'] = {}
    for suffix, selected in variants.items():
        print('=== Reimport STEP: ' + suffix, flush=True)
        ids = set.union(*(group_ids[name] for name in selected))
        expected_count, expected_volume, expected_bounds = step_summary(o for o in leaves if o.Name in ids)
        exchange = root / f'{PREFIX}{suffix}.step'
        saved = Part.read(str(exchange))
        actual = saved.Solids
        actual_volume = sum(solid_volume(s) for s in actual)
        delta = max(abs(a-b) for a, b in zip(bbox(saved), expected_bounds))
        volume_rel = abs(actual_volume-expected_volume) / max(expected_volume, 1)
        print(f'  {len(actual)} / {expected_count} solids; Δbounds {delta:.6f} mm; Δvolume {volume_rel:.3g}', flush=True)
        require(len(actual) == expected_count and volume_rel < 3e-5 and delta < .08,
                f'Geometry changed in {suffix}: count {len(actual)} vs {expected_count}, '
                f'bounds delta {delta}, relative volume delta {volume_rel}')
        report['step_reimport'][suffix] = dict(file=exchange.name, sha256=checksum(exchange),
                                               leaf_solids=len(actual), sum_volume_mm3=round(actual_volume, 3),
                                               bounds_delta_mm=round(delta, 6), relative_volume_delta=volume_rel)
    # Change actual aliases in the reopened document, not constants in the generator.
    s = wires['S+'].Sections[0]
    start0 = App.Vector(s.Placement.Base)
    main_sizes = {o.Name: bbox(o.Shape) for o in leaves if o.Name in group_ids['MainPCB']}
    before_w = sheet.BoardW.Value
    before_l = sheet.BoardL.Value
    for alias, increment in [('BoardW', 0.6), ('BoardL', 1.0)]:
        sheet.set(dims[alias]['freecad_cell'], f'{getattr(sheet,alias).Value + increment:.7f} mm')
    doc.recompute()
    require(math.isclose(s.Placement.Base.x, start0.x*(before_w+0.6)/before_w, abs_tol=1e-5) and
            math.isclose(s.Placement.Base.y, start0.y*(before_l+1)/before_l, abs_tol=1e-5), 'Wire start failed to move')
    moved = sum(any(abs(a-b) > .001 for a, b in zip(bb, bbox(doc.getObject(n).Shape))) for n, bb in main_sizes.items())
    require(moved > 10, 'PCB width/length did not drive component placement')
    require(all(not o.Shape.isNull() and o.Shape.isValid() for o in leaves), 'Invalid geometry after parameter edit')
    errors = [o.Name for o in doc.Objects if any('invalid' in str(s).lower() or 'error' in str(s).lower() for s in o.State)]
    require(not errors, f'Recompute errors: {errors}')
    report['edit_check'] = dict(change_mm={'BoardW': 0.6, 'BoardL': 1.0}, main_leaf_bounds_changed=moved,
                                wire_start_tracks_scale=True, shape_errors=errors, changes_saved=False)
    App.closeDocument(doc.Name)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.root.resolve())
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print('=== Native and exchange checks passed', flush=True)
        exitcode = 0
    except BaseException:
        traceback.print_exc()
        exitcode = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitcode)
