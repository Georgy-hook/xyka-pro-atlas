"""Exploded assembly drawing: orthogonal, in projection, no painted 3-D view."""

import numpy as np

from plates_eskd_geom import Drawing, moved_items
from plates_render import root_anchors
from plates_scene import FRONT, LEFT


# The physical printed skins still exist in the CAD and the standalone PNG.
# At the scale of the product assembly omit micrometre-deep printed symbols
# on batteries, heat shields and board silkscreen. Do not omit any housing,
# film, switch, membrane, retaining feature, functional module or physical PCB.
def drawn_parts(scene):
    return [i for i in scene.items
            if not (i.root == 'Battery' and i.name.startswith(('MechRetailBattery', 'MechPackEndPrint')))
            and not (i.root == 'Heater' and i.name in ('MechHeatGuardCaption', 'MechHeatGuardRimLegend',
                                                      'MechHeatGuardHotSymbol', 'MechHeatGuardCenterMark'))
            and not (i.root in ('MainPCB', 'DisplayPCB') and
                     any(part in i.name.casefold() for part in ('silk', 'legend', 'artwork')))]


def exploded(a):
    sc = a.scene
    parts = moved_items(drawn_parts(sc), sc.leaf_offsets)
    d = Drawing('XKAH.43.000 СБ', 'XKAH PRO. Сборочный чертёж', '1:2',
                number=2, sheets=2, form='2a')
    front, side = [a.line(parts, f) for f in (FRONT, LEFT)]
    bounds = np.asarray((front.bounds, side.bounds))
    z = (bounds[:, 1].min() + bounds[:, 3].max()) / 2
    scale = .5
    maps = []
    for cx, p in ((119, front), (311, side)):
        mid_u = (p.bounds[0] + p.bounds[2]) / 2
        box = (cx-91, 56, 182, 226)
        if (p.bounds[2]-p.bounds[0])*scale > box[2]-2 or (p.bounds[3]-p.bounds[1])*scale > box[3]-2:
            raise ValueError('Native service state does not fit assembly sheet 2 at its stated scale')
        maps.append(d.view(p, box, scale, center=(mid_u, z), weight=.55))
    # Form 2а does not repeat the scale cell. Both linked images on this
    # sheet use 1:2, unlike the 1:1 section on sheet 1 of this document.
    d.text(215, 271, f'Разнесённое положение ({d.scale})', h=3.5, ha='center')
    # Same world Z-centre and scale on both sides; view FROM LEFT lies to the
    # RIGHT of the front view. Numbers belong only to this parent specification.
    picks = root_anchors(parts, FRONT, width=1250, name_mode=True)
    shape_ids = ('MechUpperFairing', 'MechLowerShroud')
    for n, name in enumerate(shape_ids, 1):
        if name not in picks:
            raise ValueError(f'Cannot attach a visible main-assembly position to {name}')
        dot = maps[0].uv(*picks[name])
        s = 1 if n == 1 else -1
        shelf = (46, dot[1]+s*12)
        d.leader(dot, shelf, n, side='left')
    d.tech(['1. Состав верхнего и нижнего блоков — по спецификациям XKAH.43.100 и XKAH.43.200.',
            '2. Перемещения условные; направления и длины хода при разборке не установлены.',
            '3. Мелкая маркировка показана упрощённо. Части чаши — на XKAH.43.220 СБ.'],
           x=26, y=45, h=3.0, step=6)
    return d
