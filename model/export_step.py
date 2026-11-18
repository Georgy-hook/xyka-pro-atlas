"""Export only registered physical results; construction profiles and display links stay native."""

import FreeCAD as App
import Import

from context import world_shape
from assembly_units import OUTER


def export_sets(c):
    exchange = App.newDocument('XkahExchange')
    top = exchange.addObject('App::Part', 'Product')
    top.Label = 'XKAH PRO • A4.3 • photographic reconstruction'
    copies = {c.assembly.Name: top}

    def clone_group(group):
        if group.Name not in copies:
            parent = clone_group(c.parents[group.Name])
            assembly = exchange.addObject('App::Part', group.Name)
            assembly.Label = group.Label
            parent.addObject(assembly)
            copies[group.Name] = assembly
        return copies[group.Name]

    try:
        for obj in c.physical:
            parent = clone_group(c.parents[obj.Name])
            shape = world_shape(obj)
            if shape.isNull():
                raise ValueError(f'Empty registered geometry: {obj.Name}')
            leaf = exchange.addObject('Part::Feature', obj.Name)
            parent.addObject(leaf)
            leaf.Label = obj.Label
            leaf.Shape = shape
            leaf.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
            colors = obj.ViewObject.DiffuseColor
            if len(colors) > 1:
                leaf.ViewObject.DiffuseColor = colors
        exchange.recompute()
        names = [('rebuilt', [top]),
                 ('outer_housing', [copies[c.groups[k].Name] for k in OUTER]),
                 ('electronics', [copies[c.groups[k].Name] for k in ('main', 'display', 'wires')])]
        for title, shapes in names:
            path = c.root / f'XKAH_PRO_A43_{title}.step'
            print(f'=== STEP {title}', flush=True)
            Import.export(shapes, str(path))
            if not path.is_file() or path.stat().st_size < 1000:
                raise RuntimeError(f'STEP export failed: {path}')
    finally:
        App.closeDocument(exchange.Name)
        App.setActiveDocument(c.doc.Name)
