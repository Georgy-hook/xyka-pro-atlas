"""Read the physical CAD in assembly space. No presentation links or construction shapes."""

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import FreeCAD as App
import numpy as np

# ROOTS remains the context's public module ordering for existing atlas clients;
# an opened file's authoritative list is scene.roots, not the installed context.
from context import EXPLODE, GROUPS

ROOTS = tuple(v[0] for v in GROUPS.values())
OFFSETS = {GROUPS[k][0]: np.array(v, dtype=float) for k, v in EXPLODE.items() if k in GROUPS}
FUNCTIONS = ('Housing', 'LowerBody', 'Fascia', 'LightRing', 'Battery', 'Pod', 'Heater',
             'MainPCB', 'DisplayPCB', 'Harness', 'Mounts')
UNITS = ('UpperUnit', 'LowerUnit')


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

    @property
    def unit(self):
        """Actual enclosing physical unit. Empty only for a legacy flat assembly."""
        return next((name for name in self.chain if name in UNITS), '')

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
        assembly = self.doc.getObject('Assembly')
        if assembly is None:
            raise ValueError('Missing assembled state: Assembly')
        self.units = {n.Name: n for n in assembly.Group if n.Name in UNITS}
        self.structured = bool(self.units)
        if self.structured and set(self.units) != set(UNITS):
            raise ValueError('Both physical unit containers must be children of Assembly')
        self.items = list(self._walk(assembly, '', ()))
        self.roots = tuple(name for name in FUNCTIONS if name in self.parts)
        if self.structured and set(self.roots) != set(FUNCTIONS):
            raise ValueError(f'Missing functional modules: {sorted(set(FUNCTIONS) - set(self.roots))}')
        self.by = {name: [i for i in self.items if i.root == name] for name in self.roots}
        self.by_unit = {name: [i for i in self.items if i.unit == name] for name in self.units}
        if not self.items or any(not group for group in self.by.values()):
            raise ValueError('Physical assembly or functional module is empty')
        if self.structured and any(not i.unit for i in self.items):
            raise ValueError('Retail physical leaf is not assigned to a unit')
        self.named = {i.name: i for i in self.items}
        if len(self.named) != len(self.items):
            raise ValueError('Repeated registered physical features in source hierarchy')

    def _walk(self, obj, root, chain):
        if obj.TypeId == 'App::Link':
            return
        if 'ColorHex' in obj.PropertiesList and hasattr(obj, 'Shape'):
            if not root:
                raise ValueError(f'Physical feature outside a functional module: {obj.Name}')
            if obj.Shape.isNull():
                raise ValueError(f'Empty registered shape: {obj.Name}')
            yield Item(obj, global_shape(obj), root, chain)
        elif obj.isDerivedFrom('App::Part'):
            if obj.Name in FUNCTIONS:
                if root:
                    raise ValueError(f'Functional modules must not overlap: {root} / {obj.Name}')
                root = obj.Name
                self.parts[root] = obj
            for child in obj.Group:
                yield from self._walk(child, root, (*chain, obj.Name))

    def subset(self, *roots):
        return [i for r in roots for i in self.by[r]]

    @cached_property
    def offsets(self):
        """Coarse module vectors for legacy consumers; never a retail leaf transform."""
        if self.structured:
            return {k: np.array(OFFSETS.get(k, np.zeros(3))) for k in self.roots}
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
        if set(offsets) != set(self.roots):
            raise ValueError('Native exploded presentation does not cover all physical modules')
        return offsets

    @cached_property
    def leaf_offsets(self):
        """Native total translations in global CAD mm, by unique physical leaf name.

        A film's additional service motion and its cassette motion are already
        summed in the FCStd. Never apply the module offset a second time.
        """
        result = {}
        for item in self.items:
            obj = item.obj
            if 'ServiceExplodeMM' in obj.PropertiesList:
                delta = np.asarray(tuple(obj.ServiceExplodeMM), dtype=float)
            elif self.structured:
                raise ValueError(f'{item.name}: missing native ServiceExplodeMM')
            else:
                delta = np.asarray(self.offsets[item.root], dtype=float)
            if delta.shape != (3,) or not np.isfinite(delta).all():
                raise ValueError(f'{item.name}: invalid service translation')
            result[item.name] = delta
        return result

    def board_frame(self, root):
        """World-space rows u (across), v (along), w (towards populated face)."""
        rotation = self.parts[root].getGlobalPlacement().Rotation
        return np.array([tuple(rotation.multVec(App.Vector(*v))) for v in np.eye(3)])

    def board_studio_frame(self, root):
        # Compose the studio orbit with THIS board's basis, not with world Y.
        # Its opposite board can be installed at an entirely different angle.
        orbit = (.50, .45, 1.35) if root == 'MainPCB' else (.50, .30, 1.5)
        return camera(orbit, (0, 1, 0)) @ self.board_frame(root)

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
    # Largest footprint in the board frame; world-AABB areas change under tilt.
    frame = scene.board_frame(root)
    return max(items, key=lambda i: np.prod(np.diff(frame_box([i], frame), axis=0)[0, :2]))


def board_layers(scene, root):
    """Include actual front/rear masks in stack height, not a core-only substitute."""
    principal = substrate(scene, root)
    layers = [i for i in scene.by[root] if i in (principal,) or i.name in ('PcMaskFace', 'PcMaskRear')]
    return layers


def combined_box(items):
    return np.stack((np.min([i.box[0] for i in items], axis=0),
                     np.max([i.box[1] for i in items], axis=0)))


def frame_box(items, frame):
    """Exact u,v,w bounds of the actual B-reps, in projected world millimetres.

    Transform first, bound second. Projecting a world AABB's eight corners
    overstates all three dimensions of a tilted laminate. No tessellation or
    replacement by a nominal spreadsheet dimension is used for dimensions.
    """
    matrix = np.eye(4)
    matrix[:3, :3] = frame
    view = App.Placement(App.Vector(), App.Rotation(App.Matrix(*matrix.ravel())))
    boxes = []
    for item in items:
        shape = item.shape.copy()
        shape.Placement = view.multiply(shape.Placement)
        b = shape.optimalBoundingBox(False, False)
        boxes.append(((b.XMin, b.YMin, b.ZMin), (b.XMax, b.YMax, b.ZMax)))
    if not boxes:
        raise ValueError('No geometry for projected dimension')
    bounds = np.array(boxes)
    return np.stack((bounds[:, 0].min(0), bounds[:, 1].max(0)))


def projected_box(items, frame):
    lo, hi = frame_box(items, frame)
    return (*lo[:2], *hi[:2])


def distance_between_layers(first, second):
    """Shortest unsigned distance between substrate bodies; not clearance to the carrier."""
    return min(a.shape.distToShape(b.shape)[0] for a in first for b in second)


def flat_face_normal(item):
    """Normal to its broadest planar face, including a plane represented as NURBS."""
    for face in sorted(item.shape.Faces, key=lambda f: f.Area, reverse=True):
        plane = face.findPlane(1e-6)
        if plane is not None:
            return unit(tuple(plane.Axis))
    raise ValueError(f'No planar face on {item.name}; cannot identify its normal')


def unique(items):
    return list(dict.fromkeys(items))
