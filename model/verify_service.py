"""Acceptance of the two installed units and the actual linked service representation."""

from collections import Counter
import json
import math

import FreeCAD as App

from assembly_units import MODULES, UNITS
from context import world_shape


def verify_service(doc, leaves):
    names = {leaf.Name for leaf in leaves}
    if {o.Name for o in doc.Assembly.Group} != set(UNITS):
        raise ValueError('Assembly must split into the installed upper and lower units')
    roots = {part.Name for unit in doc.Assembly.Group for part in unit.Group}
    if roots != set(MODULES):
        raise ValueError('Missing, duplicate or unexpected functional groups')
    # Traverse actual containment, not arbitrary external dependencies of CAD expressions.
    def nodes(parent, prefix=''):
        if parent.Name in names:
            return [(parent, prefix)]
        if not parent.isDerivedFrom('App::Part'):
            return []
        return [record for obj in parent.Group for record in nodes(obj, prefix + obj.Name + '.')]

    families = {name: {p.Name for p, path in nodes(doc.getObject(name))} for name in MODULES}
    if any(not group for group in families.values()) or sum(map(len, families.values())) != len(names):
        raise ValueError('A physical part has no unique installed parent')
    if not {'MechRemovablePod', 'MechPodLid', 'MechPodScreen', 'MechPodWallMark'} <= families['Pod']:
        raise ValueError('Cup, lid and insert not present as three physical features of the tobacco pod')
    if not {'MechHeatGuard', 'MechHeaterPlate'} <= families['Heater']:
        raise ValueError('Heater missing from upper unit')
    if 'UiKeyMembrane' not in families['DisplayPCB']:
        raise ValueError('Key membrane must detach from the display PCB')
    delta = {name: App.Vector() for name in names}
    steps = json.loads(doc.Evidence.ServicePlanJSON)['steps']
    # Verify membership and physical companionship independently of the display
    # distances. A perfectly valid link can otherwise leave ink on an empty seat.
    film = {'MechServiceCover', 'MechCoverWindow'}
    inner = {n for n in names if n.startswith('MechServiceBaseInnerScrew')}
    if len(inner) != 4:
        raise ValueError('Four separate inner fasteners are required')
    stage_members = {
        'battery': families['Battery'], 'halves': families['LowerBody'] | families['Pod'],
        'pod': families['Pod'], 'pod-parts': {'MechPodScreen', 'MechPodLid'},
        'face-film': film, 'base-fasteners': inner | {'MechServiceBaseInsert'},
    }
    for step in steps:
        moved = set()
        for move in step['moves']:
            # Saved service plan uses glTF metres. Reconstruct native CAD millimetres independently.
            a, b, c = move['d']
            if not all(math.isfinite(x) for x in (a, b, c)):
                raise ValueError('Nonfinite service displacement')
            shift = App.Vector(1000 * a, -1000 * c, 1000 * b)
            for name in move['ids']:
                if name in moved or name not in names:
                    raise ValueError('Duplicate or unknown moving leaf ' + name)
                delta[name] = delta[name] + shift
                moved.add(name)
        if not moved or set(step['focusIds']) - names:
            raise ValueError('Empty service step or missing focus target: ' + step['id'])
        key = step['id']
        if key in stage_members and moved != stage_members[key]:
            raise ValueError(f'{key}: unexpected moving leaves: {moved ^ stage_members[key]}')
        for group, carrier in ((families['Battery'], 'MechBatteryEnvelope'),
                               (film, 'MechServiceCover'), ({'MechPodWallMark'}, 'MechRemovablePod')):
            if any((delta[n] - delta[carrier]).Length > 5e-5 for n in group):
                raise ValueError(f'{key}: an integral surface did not follow {carrier}')
        if key == 'base-fasteners' and any(delta[n].z <= delta['MechServiceBaseInsert'].z for n in inner):
            raise ValueError('Inner screw heads must be shown above the detached insert')
    seen = Counter()
    for link in doc.Exploded.Group:
        if link.TypeId != 'App::Link' or not link.LinkedObject or not link.LinkTransform:
            raise ValueError('Invalid native exploded representation')
        for obj, path in nodes(link.LinkedObject):
            key = obj.Name
            seen[key] += 1
            if (obj.ServiceExplodeMM - delta[key]).Length > 5e-5:
                raise ValueError(f'Mismatch between service sequence and recorded final translation: {key}')
            # Compare vertex on a real displayed instance, not just stored numbers.
            shape = link.getSubObject(path) if path else link.Shape
            a = shape.Vertexes[0].Point
            b = world_shape(obj).Vertexes[0].Point
            if (a - b - delta[key]).Length > 2e-5:
                raise ValueError(f'Incorrect native presentation of {key}: {a - b} vs {delta[key]}')
    if seen != Counter(names):
        raise ValueError('Linked view does not contain exactly one instance of each registered physical feature')
    step_ids = [s['id'] for s in steps]
    if len(set(step_ids)) != len(step_ids) or step_ids.index('halves') >= step_ids.index('pod-parts'):
        raise ValueError('Invalid service state order')
    for child in ('Battery', 'Heater', 'MainPCB', 'DisplayPCB', 'Fascia'):
        if doc.getObject(child) not in doc.UpperUnit.Group:
            raise ValueError(f'Upper-unit dependency missing: {child}')
    if doc.Pod not in doc.LowerUnit.Group or doc.LowerBody not in doc.LowerUnit.Group:
        raise ValueError('Installed cartridge is not in the removable lower unit')
    return {'units': list(UNITS), 'module_counts': {key: len(v) for key, v in families.items()},
            'native_link_count': len(doc.Exploded.Group), 'native_instanced_leaves': len(seen),
            'steps': step_ids, 'cup_lid_screen_selectable': True, 'display_membrane_selectable': True}
