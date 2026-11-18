"""FreeCAD scene graph, shared dimensional ledger and evidence on physical leaves."""

from pathlib import Path
import csv
import json
import re

import FreeCAD as App
import Part

from assembly_units import EXPLODE, GROUPS, PARENT, UNITS

# Reference rows describe fixed library package geometry; they are deliberately
# not a knob for stretching a standardized integrated circuit with the PCB.
PACKAGE_REFERENCES = [
    ('QfnBodyNominal', 4.0, 'U3 AT32F421G8U7: D=E=3.90…4.10 mm, nominal 4.00; Artery v2.02, tab.50. Reference only.', None),
    ('QfnPitchNominal', 0.40, 'U3: lead pitch e=0.40 BSC; Artery v2.02 §6.5, tab.50. Reference only.', None),
    ('FlashPitchNominal', 1.27, 'HC25FQ128GSSIG, SOP8-208; Hongchip QA-DT-176 §9.1 p.84. Reference only.', None),
]


def text_property(obj, key, value, section='Evidence'):
    if key not in obj.PropertiesList:
        obj.addProperty('App::PropertyString', key, section)
    setattr(obj, key, str(value))


def write_table(path, rows, keys):
    with Path(path).open('w', newline='', encoding='utf-8-sig') as out:
        writer = csv.DictWriter(out, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def world_shape(obj):
    """Apply the ancestor transform once; retain any intrinsic OCCT shape placement."""
    shape = obj.Shape.copy()
    ancestor = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
    shape.Placement = ancestor.multiply(shape.Placement)
    return shape


class Context:
    def __init__(self, doc, out, specs):
        self.doc = doc
        self.root = Path(out)
        self.sheet = doc.addObject('Spreadsheet::Sheet', 'Parameters')
        self.p = {}
        self.spec_by_group = {}
        self.cells = {}
        self.physical = []
        self.groups = {}
        self.rows = []
        self.parents = {}
        self._load_sheet(specs)
        self.assembly = self.sub(None, 'Assembly', 'A  •  XKAH PRO  /  сборка')
        self.units = {name: self.sub(self.assembly, name, label) for name, label in UNITS.items()}
        for key, (name, label) in GROUPS.items():
            self.groups[key] = self.sub(self.units[PARENT[key]], name, label)

    def _load_sheet(self, specs):
        sheet = self.sheet
        headers = ['Параметр / alias', 'Номинал', '± оценка¹', 'Статус', 'Источник и метод', 'Узел']
        for col, header, width in zip('ABCDEF', headers, (180, 108, 103, 170, 630, 130)):
            sheet.set(col + '1', header)
            sheet.setColumnWidth(col, width)
        sheet.setStyle('A1:F1', 'bold', 'add')
        sheet.setBackground('A1:F1', (0.12, 0.25, 0.32))
        sheet.setForeground('A1:F1', (1.0, 1.0, 1.0))
        for group, parameters in specs:
            self.spec_by_group[group] = []
            for name, value, source, uncertainty in parameters:
                if name in self.p:
                    raise ValueError(f'Duplicate parameter alias: {name}')
                self.p[name] = float(value)
                self.spec_by_group[group].append(name)
                index = len(self.p) + 1
                cell = 'B' + str(index)
                self.cells[name] = cell
                status = 'DATASHEET NOMINAL' if uncertainty is None else 'ESTIMATE'
                quantity = ('=' if value < 0 else '') + f'{value:g} mm'
                values = [name, quantity, '—' if uncertainty is None else f'{uncertainty:g} mm',
                          status, str(source), group]
                for col, item in zip('ABCDEF', values):
                    sheet.set(f'{col}{index}', item)
                sheet.setAlias(cell, name)
                sheet.setBackground(cell, (0.83, 0.94, 0.96) if uncertainty is None else (1., 0.93, 0.78))
                self.rows.append(dict(parameter=name, value_mm=value, estimated_plusminus_mm=uncertainty,
                                      source=source, confidence=status, measured_yes_no='NO',
                                      needs_user_measurement='NO (nominal package only)' if uncertainty is None else 'YES',
                                      subsystem=group, freecad_cell=cell))
        idx = len(self.p) + 3
        sheet.set(f'A{idx}', '¹ Интервалы — инженерные оценки, не допуски и не 95%-ные доверительные интервалы.')
        sheet.mergeCells(f'A{idx}:F{idx}')
        self.doc.recompute()

    def sub(self, parent, name, label):
        obj = self.doc.addObject('App::Part', name)
        obj.Label = label
        if parent is not None:
            parent.addObject(obj)
        self.parents[obj.Name] = parent
        return obj

    def register(self, obj, parent, color, source, confidence, notes=''):
        if parent is not None and obj not in parent.Group:
            parent.addObject(obj)
        self.parents[obj.Name] = parent
        self.physical.append(obj)
        rgb = tuple(float(n) for n in color[:3])
        text_property(obj, 'ColorHex', '#' + ''.join(f'{round(255*v):02X}' for v in rgb), 'Presentation')
        text_property(obj, 'EvidenceSource', source)
        text_property(obj, 'Confidence', confidence)
        text_property(obj, 'ReconstructionNote', notes)
        text_property(obj, 'DimensionalStatus', 'ESTIMATE unless explicitly documented in Parameters; not measured')
        if obj.ViewObject:
            obj.ViewObject.ShapeColor = rgb
            obj.ViewObject.LineColor = tuple(max(0.04, v * 0.40) for v in rgb)
            obj.ViewObject.LineWidth = 1.0
            obj.ViewObject.DisplayMode = 'Flat Lines'
        return obj

    def solid(self, parent, name, label, shape, color, source, confidence, notes=''):
        obj = self.doc.addObject('Part::Feature', name)
        obj.Label = label
        obj.Shape = shape
        return self.register(obj, parent, color, source, confidence, notes)

    def at(self, obj, x, y, z):
        placement = obj.Placement
        v = placement.Base
        for axis, value in zip('xyz', (x, y, z)):
            if not isinstance(value, str):
                setattr(v, axis, float(value))
        placement.Base = v
        obj.Placement = placement
        for axis, value in zip('xyz', (x, y, z)):
            if isinstance(value, str):
                obj.setExpression('Placement.Base.' + axis, value)
        return obj

    def frames(self):
        from mech_profiles import cassette_frame

        front = App.Rotation(App.Vector(1, 0, 0), 90)
        back = App.Rotation(App.Vector(0, 0, 1), 180).multiply(front)
        for key, rot, depth, base in [('display', front, 'UiDepth', 'UiBase'),
                                      ('main', back, 'MainDepth', 'PanelBase'),
                                      ('wires', back, 'MainDepth', 'PanelBase')]:
            obj = self.groups[key]
            cassette_frame(self, obj, rot, depth, base)

    def lineage(self, obj):
        lineage = []
        while self.parents.get(obj.Name) is not None:
            obj = self.parents[obj.Name]
            lineage.append(obj)
        return lineage[::-1]

    def make_exploded(self, evidence):
        from retail_service import service_layout

        plan = service_layout(self)
        text_property(evidence, 'ServicePlanJSON', json.dumps({'steps': plan.steps}, ensure_ascii=False), 'Service')
        for obj in self.physical:
            obj.addProperty('App::PropertyVector', 'ServiceExplodeMM', 'Service')
            obj.ServiceExplodeMM = App.Vector(*plan.xyz[obj.Name])
            text_property(obj, 'ServiceStage', plan.role[obj.Name], 'Service')
        group = self.sub(None, 'Exploded', 'B  •  Разнесённая сборка  /  скрыта')
        text_property(group, 'Operation', 'Вид после разъединения штатных и сервисных узлов. Смещения показательные; ссылки ведут на установленные детали.')
        children = {}
        for leaf in self.physical:
            for node in [leaf, *self.lineage(leaf)]:
                children.setdefault(node.Name, set()).add(leaf.Name)

        def link_branch(obj):
            leaves = children.get(obj.Name, set())
            if not leaves:
                return
            vectors = {plan.xyz[name] for name in leaves}
            if len(vectors) > 1:
                for child in obj.Group:
                    link_branch(child)
                return
            offset, = vectors
            parent = self.parents[obj.Name]
            delta = App.Placement(App.Vector(*offset), App.Rotation())
            link = self.doc.addObject('App::Link', 'Expl_' + obj.Name)
            group.addObject(link)
            link.LinkedObject = obj
            link.LinkTransform = True
            link.Label = obj.Label + '  ↗'
            # Nested plates have a non-world frame. LinkPlacement adds only
            # the parent frame: LinkTransform already keeps the target's own.
            link.LinkPlacement = delta.multiply(parent.getGlobalPlacement())

        for module in self.groups.values():
            link_branch(module)
        self.doc.recompute()
        group.Visibility = False
        return group

    def registers(self):
        write_table(self.root / 'DIMENSIONS.csv', self.rows, self.rows[0].keys())
        rows = []
        for obj in self.physical:
            lineage = self.lineage(obj)
            shape = obj.Shape.copy()
            shape.Placement = App.Placement()
            bbox = shape.BoundBox
            aliases = set()
            for item in [obj, *lineage, *obj.OutList]:
                for _, expr in getattr(item, 'ExpressionEngine', []):
                    aliases.update(re.findall(r'Parameters(?:>>)?\.(\w+)', str(expr)))
            local_aliases = ', '.join(sorted(aliases)) or 'Placement / source generator'
            rows.append(dict(object_id=obj.Name, component=obj.Label,
                             tree_path=' / '.join(node.Label for node in lineage),
                             solid_count=len(shape.Solids), evidence_photo=obj.EvidenceSource,
                             confidence=obj.Confidence, size_source=obj.EvidenceSource,
                             dimensional_status=obj.DimensionalStatus,
                             editable_parameter=local_aliases, envelope_x_mm=f'{bbox.XLength:.3f}',
                             envelope_y_mm=f'{bbox.YLength:.3f}', envelope_z_mm=f'{bbox.ZLength:.3f}',
                             measured_yes_no='NO', note=obj.ReconstructionNote,
                             service_stage=obj.ServiceStage,
                             surface_material=getattr(obj, 'SurfaceMaterialNote', ''),
                             material_source=getattr(obj, 'SurfaceMaterialSource', '')))
        write_table(self.root / 'MODEL_MANIFEST.csv', rows, rows[0].keys())
