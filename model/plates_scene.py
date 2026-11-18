"""Read the physical CAD in assembly space. No presentation links or construction shapes."""

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import FreeCAD as App
import numpy as np

# The same translation vectors as the native Exploded links, not assembly travel.
from context import EXPLODE, GROUPS

ROOTS = tuple(v[0] for v in GROUPS.values())
OFFSETS = {GROUPS[k][0]: np.array(v, dtype=float) for k, v in EXPLODE.items()}


def unit(a):
    a = np.asarray(a, dtype=float)
    return a / np.linalg.norm(a)


def camera(eye, up=(0, 0, 1)):
    """Rows: screen right, screen up, direction from object to observer."""
    eye = unit(eye)
    right = unit(np.cross(up, eye))
    return np.array([right, np.cross(eye, right), eye])


FRONT = camera((0, -1, 0))
REAR = camera((0, 1, 0))
LEFT = camera((-1, 0, 0))
RIGHT = camera((1, 0, 0))
TOP = camera((0, 0, 1), (0, 1, 0))
BOTTOM = camera((0, 0, -1), (0, -1, 0))
STUDIO = camera((0.72, -1.4, 0.61))
EXPLODED = camera((0.69, -1.2, 0.48))
ELEC = camera((-0.50, 1.35, 0.45))
ELEC_BACK = camera((0.50, -1.5, 0.30))


@dataclass(eq=False)
class Item:
    obj: object
    shape: object
    root: str
    chain: tuple

    @property
    def name(self):
        return self.obj.Name

    @property
    def label(self):
        return self.obj.Label

    @property
    def color(self):
        return self.obj.ColorHex

    @cached_property
    def box(self):
        b = self.shape.optimalBoundingBox(False, False)
        return np.array([[b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]])

    @property
    def center(self):
        return self.box.mean(axis=0)

    @property
    def text(self):
        return ' '.join([self.name, self.label, *self.chain[1:]]).casefold()


def global_shape(obj):
    # Shape.Placement normally contains the feature's local Placement already.
    # Add the parent transform only, retaining intrinsic BRep offsets if any.
    shape = obj.Shape.copy()
    ancestor = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
    shape.Placement = ancestor.multiply(shape.Placement)
    return shape


class Scene:
    def __init__(self, src):
        self.src = Path(src).resolve()
        self.doc = App.openDocument(str(self.src))
        self.parts = {}
        self.by = {}
        for name in ROOTS:
            part = self.doc.getObject(name)
            if part is None:
                raise ValueError(f'Physical root missing from FCStd: {name}')
            self.parts[name] = part
            self.by[name] = list(self._walk(part, name, ()))
            if not self.by[name]:
                raise ValueError(f'No registered physical leaves: {name}')
        self.items = [i for root in ROOTS for i in self.by[root]]
        self.named = {i.name: i for i in self.items}
        if len(self.named) != len(self.items):
            raise ValueError('Repeated registered physical features in source hierarchy')

    def _walk(self, obj, root, chain):
        if obj.TypeId == 'App::Link':
            return
        if 'ColorHex' in obj.PropertiesList and hasattr(obj, 'Shape'):
            if obj.Shape.isNull():
                raise ValueError(f'Empty registered shape: {obj.Name}')
            yield Item(obj, global_shape(obj), root, chain)
        elif obj.isDerivedFrom('App::Part'):
            for child in obj.Group:
                yield from self._walk(child, root, (*chain, obj.Name))

    def subset(self, *roots):
        return [i for r in roots for i in self.by[r]]

    @cached_property
    def offsets(self):
        """Read the actual native, translation-only exploded links when present."""
        group = self.doc.getObject('Exploded')
        if group is None:
            return OFFSETS  # Standalone development fixtures need not have native links.
        offsets = {}
        for link in group.Group:
            if link.TypeId != 'App::Link' or not link.LinkTransform:
                raise ValueError(f'Unsupported exploded presentation link: {link.Name}')
            if abs(link.LinkPlacement.Rotation.Angle) > 1e-7:
                raise ValueError('Exploded views expect published translation-only links')
            offsets[link.LinkedObject.Name] = np.array(link.LinkPlacement.Base, dtype=float)
        if set(offsets) != set(ROOTS):
            raise ValueError('Native exploded presentation does not cover all seven physical roots')
        return offsets

    def board_frame(self, root):
        rotation = self.parts[root].getGlobalPlacement().Rotation
        return np.array([tuple(rotation.multVec(App.Vector(*v))) for v in np.eye(3)])

    def close(self):
        App.closeDocument(self.doc.Name)


def choose(items, *tokens, avoid=(), required=True):
    """Deterministic preference: exact internal name, internal substring, then label."""
    candidates = [i for i in items if not any(t.casefold() in i.text for t in avoid)]
    for attr, exact in [('name', True), ('name', False), ('label', False)]:
        for t in tokens:
            t = t.casefold()
            for i in candidates:
                s = getattr(i, attr).casefold()
                if (s == t if exact else t in s):
                    return i
    if required:
        raise ValueError('No physical landmark for ' + ' / '.join(tokens))
    return None


def substrate(scene, root):
    items = scene.by[root]
    part = choose(items, 'PcLaminateCore', 'MainSubstrate', 'UiSubstrate', 'PCBSubstrate', 'substrate',
                  'подложк', 'основа платы', 'контур PCB', required=False)
    if part is not None:
        return part
    # Longest broad plate without depending on its orientation in the enclosure.
    return max(items, key=lambda p: np.prod(np.sort(p.box[1] - p.box[0])[-2:]))


def board_layers(scene, root):
    """Include actual front/rear masks in stack height, not a core-only substitute."""
    principal = substrate(scene, root)
    layers = [i for i in scene.by[root] if i in (principal,) or i.name in ('PcMaskFace', 'PcMaskRear')]
    return layers


def combined_box(items):
    return np.stack((np.min([i.box[0] for i in items], axis=0),
                     np.max([i.box[1] for i in items], axis=0)))


def projected_box(items, frame):
    from itertools import product
    pts = np.vstack([np.array(list(product(*i.box.T))) for i in items]) @ frame[:2].T
    return (*pts.min(axis=0), *pts.max(axis=0))


def unique(items):
    return list(dict.fromkeys(items))
