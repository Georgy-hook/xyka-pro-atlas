"""Service-view selection from native unit membership and registered leaf IDs.

The two-part front film (opaque mask and its tinted window) stays installed
on closed views. Its service view uses the saved per-leaf displacements.
"""

from functools import cached_property

from plates_scene import BOTTOM, EXPLODED, STUDIO, camera


TITLES = {
    'Housing': 'Верхний кожух', 'LowerBody': 'Нижний корпус', 'Fascia': 'Лицевая кассета',
    'LightRing': 'Световое кольцо', 'Battery': 'Аккумулятор', 'Pod': 'Чаша для табака',
    'Heater': 'Нагреватель', 'MainPCB': 'Основная PCB', 'DisplayPCB': 'Дисплейная PCB',
    'Harness': 'Жгут', 'Mounts': 'Крепёж',
}


class ServiceViews:
    def __init__(self, scene):
        self.scene = scene

    @cached_property
    def film(self):
        return [i for i in self.scene.by.get('Fascia', [])
                if 'MechFrontFilm' in i.chain]

    @cached_property
    def membrane(self):
        return [i for i in self.scene.by['DisplayPCB'] if 'UiKeyMembrane' in (i.name, *i.chain)]

    @cached_property
    def exterior(self):
        return self.scene.items

    @cached_property
    def pod_parts(self):
        """Three different real leaves. No heater component can qualify."""
        items = self.scene.by.get('Pod', [])
        if not items:
            return {}
        by_id = {i.name: i for i in items}
        return {'А': (by_id['MechRemovablePod'], 'Корпус чаши'),
                'Б': (by_id['MechPodLid'], 'Крышка'), 'В': (by_id['MechPodScreen'], 'Сито')}

    @cached_property
    def guards(self):
        return [i for i in self.scene.by['Heater'] if 'MechHeatGuard' in (i.name, *i.chain)]

    @cached_property
    def entries(self):
        # Keep printed position numbers stable across viewing direction and
        # leaf count. Which unit owns a module follows the actual tree.
        scene = self.scene
        result = []
        for root in scene.roots:
            title = TITLES[root] if scene.structured or root != 'Housing' else 'Корпус'
            result.append((root, title))
        return tuple(result)

    def check(self):
        scene = self.scene
        if not scene.structured:
            return
        for root, unit in (('Battery', 'UpperUnit'), ('Pod', 'LowerUnit'), ('Heater', 'UpperUnit')):
            if any(i.unit != unit for i in scene.by[root]):
                raise ValueError(f'{root}: wrong unit, expected {unit}')
        if not {'MechServiceCover', 'MechCoverWindow'} <= {i.name for i in self.film}:
            raise ValueError('The removable fascia film must include its physical mask AND window')
        if not self.membrane or not self.guards:
            raise ValueError('Cannot identify removable film, UI membrane or heating guard in retail CAD')
        delta = scene.leaf_offsets
        unique_shifts = {tuple(delta[i.name].round(5)) for i, _ in self.pod_parts.values()}
        if len(unique_shifts) != 3:
            raise ValueError('Pod cup, lid and sieve do not have three separate native service translations')

    def specs(self):
        scene = self.scene
        specs = {
            'assembled': (self.exterior, STUDIO, None, (1380, 1510)),
            'exploded': (scene.items, EXPLODED, scene.leaf_offsets, (2100, 1500)),
            'electronics': (scene.subset('MainPCB', 'Harness', 'DisplayPCB'),
                            scene.board_studio_frame('MainPCB'), None, (1460, 1480)),
            'electronics-front': (scene.subset('MainPCB', 'Harness', 'DisplayPCB'),
                                  scene.board_studio_frame('DisplayPCB'), None, (1060, 1380)),
        }
        if scene.structured:
            specs.update({
                # The upper unit is seen from below: the heating guard remains
                # with this unit; the separate tobacco cup is in the lower one.
                'upper-unit': (scene.by_unit['UpperUnit'],
                               camera((.6, -1.1, -.78)), None, (850, 750)),
                'lower-unit': (scene.by_unit['LowerUnit'], camera((.55, -1.2, .96)), None, (850, 580)),
                'battery-print': (scene.by['Battery'], camera((.02, -1, .04), (1, 0, 0)), None, (950, 630)),
                'battery-end': (scene.by['Battery'], BOTTOM, None, (760, 660)),
                'pod-service': (scene.by['Pod'], camera((.75, -1.75, .55)), scene.leaf_offsets, (1050, 720)),
                'film-service': (self.film, camera((.48, -1.2, .35)), scene.leaf_offsets, (650, 680)),
                'key-service': (self.membrane, scene.board_studio_frame('DisplayPCB'),
                                scene.leaf_offsets, (750, 510)),
            })
        return specs
