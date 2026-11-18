"""Optically traced XYKA Pro lower-end ink; no words re-typeset or inferred.

Copy this module and retail_battery_endprint.json together. Coordinates in the
JSON are nominal cartridge XY (mm), not camera or viewport coordinates. Looking
at the underside with the heading readable, right = -Y and down = +X.
"""

import json
from pathlib import Path

import FreeCAD as App
import Part

from mech_shapes import scaled_part


_DATA = Path(__file__).with_suffix('.json')
_FACE_Z = 0.420
_INK = 0.020


def _wire(points):
    """Return a closed OCC wire; the stored ring has no repeated last point."""
    vertices = [App.Vector(x, y, _FACE_Z) for x, y in points]
    return Part.makePolygon(vertices + [vertices[0]])


def add_end_print(c, pack, ratios, origin):
    """Register one underside ink leaf, scaled/placed by the caller, and return it.

    All islands and counters are real BRep. The top of the thin film shares the
    datum of the recessed plate; its visible surface is 0.020 mm toward -Z.
    Does not alter the panel or create contacts, windows, a plug, or a texture.
    """
    with _DATA.open(encoding='utf-8') as stream:
        data = json.load(stream)

    solids = []
    for field in data['fields']:
        for outer, *holes in field['polygons_mm']:
            wires = [_wire(ring) for ring in (outer, *holes)]
            solids.append(Part.Face(wires).extrude(App.Vector(0, 0, -_INK)))

    source = data['source'] + ' | f1210 | SHA256: ' + data['sha256']
    leaf = scaled_part(
        c, pack, 'PackEndInk', 'XYKA · маркировка нижнего торца',
        Part.makeCompound(solids), tuple(data['ink_srgb']), source,
        'PHOTO TRACE / ESTIMATED REGISTRATION',
        'Пиксельная трассировка: контур предупреждения, ВНИМАНИЕ и слабый '
        'многострочный блок на противоположной стороне. Неразборчивые знаки '
        'не дополнялись; это надпись на корпусе, не техническая спецификация.',
        ratios=ratios, origin=origin,
    )
    view = getattr(leaf, 'ViewObject', None)
    if view is not None and 'Shaded' in view.listDisplayModes():
        view.DisplayMode = 'Shaded'
    return leaf
