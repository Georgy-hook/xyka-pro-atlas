"""Read installed BReps, screen their material volumes, and isolate slow OCC operations."""

from dataclasses import dataclass
from functools import cached_property
import multiprocessing as mp
import time

import FreeCAD as App
import numpy as np
import Part
from scipy.spatial import cKDTree

from assembly_units import LAYOUT, MODULES, UNITS

LEGACY_GROUPS = ('Housing', 'MainPCB', 'DisplayPCB', 'Heater', 'Battery', 'Harness', 'Mounts')
EPS = 1e-6  # mm; numerical coincidence only
DEFLECTION = 0.08
SKIN_GUARD = 0.24  # mm, screening guard, NOT a clearance requirement or proven error bound


def xyz(p):
    return np.array([p.x, p.y, p.z])


def vec(p):
    return App.Vector(*map(float, p))


def world(obj):
    s = obj.Shape.copy()
    s.Placement = obj.getGlobalPlacement()
    return s


def bounds(s, tight=False):
    # Do not tighten via a potentially coarse display tessellation.
    b = s.optimalBoundingBox(False, False) if tight else s.BoundBox
    return np.array([[b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]])


def extents(a, b):
    return np.minimum(a[1], b[1]) - np.maximum(a[0], b[0])


def box_gap(a, b):
    return float(np.linalg.norm(np.maximum(-extents(a, b), 0)))


def box_hits(boxes, box, guard=0.):
    return ((boxes[:, 1] >= box[0] - guard) & (boxes[:, 0] <= box[1] + guard)).all(axis=1)


@dataclass
class Material:
    shape: object

    @cached_property
    def box(self):
        return bounds(self.shape, True)

    @cached_property
    def triangles(self):
        # Fine screening only. An empty intersection of these facet boxes is NOT an OCC result.
        verts, faces = self.shape.tessellate(DEFLECTION)
        if not faces:
            raise ValueError('Empty solid tessellation')
        triangles = np.array([xyz(p) for p in verts])[np.asarray(faces, dtype=int)]
        return np.stack((triangles.min(axis=1), triangles.max(axis=1)), axis=1)

    @cached_property
    def point(self):
        return self.shape.Vertexes[0].Point


@dataclass
class Leaf:
    name: str
    group: str
    obj: object
    shape: object
    solids: list

    @cached_property
    def box(self):
        boxes = np.array([s.box for s in self.solids])
        return np.array([boxes[:, 0].min(axis=0), boxes[:, 1].max(axis=0)])

    @cached_property
    def contact(self):
        return str(getattr(self.obj, 'Contact', '')) if self.group == 'Harness' else ''

    @cached_property
    def stations(self):
        return np.array([xyz(s.getGlobalPlacement().Base) for s in self.obj.Sections])

    @cached_property
    def tube(self):
        if not self.contact or self.obj.TypeId != 'Part::Loft':
            return None
        skins = [f for f in self.shape.Faces if f.Surface.TypeId == 'Part::GeomBSplineSurface']
        if len(skins) != 1:
            return None  # no straight-line stand-in for an unknown loft topology
        skin = skins[0]
        u0, u1, v0, v1 = skin.ParameterRange
        sections = self.stations
        diameter = 2 * self.obj.Sections[0].Radius.Value
        count = max(41, int(3 * np.linalg.norm(np.diff(sections, axis=0), axis=1).sum()) + 1)
        rings = np.array([[xyz(skin.valueAt(u, v)) for u in np.linspace(u0, u1, 12, endpoint=False)]
                          for v in np.linspace(v0, v1, count)])
        centers = rings.mean(axis=1)
        radii = np.linalg.norm(rings - centers[:, None, :], axis=2).max(axis=1)
        # Verify native cap centres and OD before trusting this orientation of the B-spline poles.
        ends = np.linalg.norm(centers[[0, -1]] - sections[[0, -1]], axis=1)
        if max(ends) > 0.02 or abs(2 * radii[0] - diameter) > 0.06:
            return None
        # Include the local axial sample spacing as well as angular/meshing allowance.
        steps = np.linalg.norm(np.diff(centers, axis=0), axis=1)
        padding = radii + np.maximum(np.r_[0, steps], np.r_[steps, 0]) / 2 + SKIN_GUARD
        boxes = np.stack((centers - padding[:, None], centers + padding[:, None]), axis=1)
        return Tube(centers, radii, padding, boxes, cKDTree(centers))


@dataclass
class Tube:
    centers: object
    radii: object
    padding: object
    boxes: object
    tree: object


def installed(doc):
    root = doc.getObject('Assembly')
    if root is None:
        raise ValueError('Missing installed Assembly')
    leaves = {}
    issues = []
    children = {o.Name for o in root.Group}
    # A broken retail tree with both units missing must NOT masquerade as the
    # flat legacy model merely because none of its root child names are units.
    retail = bool(children & set(UNITS)) or any(doc.getObject(n) is not None
                                                for n in set(MODULES) - set(LEGACY_GROUPS))
    required = set(MODULES if retail else LEGACY_GROUPS)
    parents = {name: unit for _, name, _, unit, _ in LAYOUT} if retail else dict.fromkeys(required, root.Name)
    if retail:
        issues.extend((unit, 'Missing assembled unit') for unit in sorted(set(UNITS) - children))
        issues.extend((o.Name, 'Installed unit must be a native App::Part') for o in root.Group
                      if o.Name in UNITS and o.TypeId != 'App::Part')
    stack = [(o, root.Name, None) for o in root.Group]
    seen = set()
    while stack:
        obj, parent, group = stack.pop()
        if obj.TypeId == 'App::Link':
            issues.append((obj.Name, 'Unexpected link below installed Assembly (not counted as material)'))
            continue  # presentation copies are never installed material
        if obj.Name in required:
            group = obj.Name
            seen.add(group)
            if parent != parents[group]:
                issues.append((group, f'Expected below {parents[group]}, found {parent}'))
        if not {'EvidenceSource', 'ColorHex', 'DimensionalStatus'}.issubset(obj.PropertiesList):
            stack.extend((o, obj.Name, group) for o in getattr(obj, 'Group', []))
            continue
        if obj.Name in leaves:
            raise ValueError('Duplicate physical leaf: ' + obj.Name)
        if group is None:
            issues.append((obj.Name, 'Registered solid outside all installed functional modules'))
        s = world(obj)
        solids = [] if s.isNull() else [Material(sub) for sub in s.Solids]
        if not solids:
            issues.append((obj.Name, 'Registered leaf has no material solids'))
        else:
            leaves[obj.Name] = Leaf(obj.Name, group or 'UNASSIGNED', obj, s, solids)
    populated = {a.group for a in leaves.values()}
    issues.extend((name, 'Missing installed module') for name in sorted(required - seen))
    issues.extend((name, 'Module contains no registered solids') for name in sorted(seen - populated))
    return leaves, issues


def tube_pair(a, b):
    """Closest *sampled* radial envelopes. Include non-nearest centres with larger radii."""
    links = a.tree.query_ball_tree(b.tree, max(a.padding) + max(b.padding))
    pairs = [(i, j) for i, js in enumerate(links) for j in js]
    if not pairs:
        return None
    i, j = np.array(pairs, dtype=int).T
    delta = a.centers[i] - b.centers[j]
    d = np.linalg.norm(delta, axis=1)
    keep = d <= a.padding[i] + b.padding[j]
    if not np.any(keep):
        return None
    i, j, d = i[keep], j[keep], d[keep]
    gap = d - a.radii[i] - b.radii[j]
    k = int(gap.argmin())
    ia, jb = i[k], j[k]
    n = (a.centers[ia] - b.centers[jb]) / max(d[k], 1e-12)
    p = (a.centers[ia] - a.radii[ia] * n + b.centers[jb] + b.radii[jb] * n) / 2
    return dict(point=p.tolist(), normal=n.tolist(), gap=float(gap[k]))


def tube_vs_solid(tube, solid):
    hit = box_hits(tube.boxes, solid.box)
    if not hit.any():
        return False
    # Check containment as well as nearby boundary patches: a tube entirely inside
    # a block does not have to cross that block's skin. A boundary hit is only a candidate.
    boxes = tube.boxes[hit]
    envelope = np.array([boxes[:, 0].min(axis=0), boxes[:, 1].max(axis=0)])
    tri = solid.triangles
    tri = tri[box_hits(tri, envelope, DEFLECTION * 2)]
    if len(tri) and any(box_hits(tri, box, DEFLECTION * 2).any() for box in boxes):
        return True
    return solid.shape.isInside(vec(tube.centers[hit][0]), EPS, False)


class ProjectedBoxes:
    """Second conservative broadphase in ONE rigid cassette basis for both bodies.

    A raked PCB and hundreds of packages touch (or clear) within a layer only
    much thinner than their WORLD boxes. Bound transformed native geometry, NOT
    a rotated world AABB or the tessellation. A negative still means no bulk.
    """

    def __init__(self, datum):
        self.inverse = datum.getGlobalPlacement().inverse()
        self.cache = {}

    def box(self, leaf, i=None):
        key = (leaf.name, i if len(leaf.solids) > 1 else None)
        if key not in self.cache:
            shape = (leaf.shape if i is None else leaf.solids[i].shape).copy()
            shape.Placement = self.inverse.multiply(shape.Placement)
            self.cache[key] = bounds(shape, True)
        return self.cache[key]


def candidate(a, b, projected=None):
    """Return rejection method or the solid-index pairs selected for exact work."""
    if np.min(extents(a.box, b.box)) <= EPS:
        return 'AABB', [], None
    if projected and np.min(extents(projected.box(a), projected.box(b))) <= EPS:
        return 'local AABB', [], None
    hint = None
    if a.contact and b.contact and a.tube and b.tube:
        hint = tube_pair(a.tube, b.tube)
        if hint is None:
            return 'sample', [], None
    selected = []
    sampled = False
    for i, x in enumerate(a.solids):
        for j, y in enumerate(b.solids):
            if np.min(extents(x.box, y.box)) <= EPS:
                continue
            if projected and np.min(extents(projected.box(a, i), projected.box(b, j))) <= EPS:
                continue
            if a.contact and b.contact:
                selected.append((i, j))
                continue
            if a.contact and a.tube:
                near = tube_vs_solid(a.tube, y)
            elif b.contact and b.tube:
                near = tube_vs_solid(b.tube, x)
            else:
                # No nearby facet and the other connected solid's witness outside:
                # screen as a mesh negative, never present this as an exact clearance.
                near = True
                for one, other in ((x, y), (y, x)):
                    if (not box_hits(one.triangles, other.box, SKIN_GUARD).any()
                            and not one.shape.isInside(other.point, EPS, False)):
                        near = False
                        break
            if near:
                selected.append((i, j))
            else:
                sampled = True
    return ('candidate' if selected else 'sample' if sampled else 'AABB'), selected, hint


def unit(delta):
    n = float(np.linalg.norm(delta))
    return (delta / n).tolist() if n > EPS else None


def exact_gap(a, b):
    d, points, _ = a.distToShape(b)
    if not points or not np.isfinite(d):
        raise ValueError('No OCC distance witnesses')
    p, q = map(xyz, points[0])
    return dict(value=float(d), point=((p + q) / 2).tolist(), normal=unit(q - p))


def split_material_gap(a, b):
    """Exact minimum over connected native solids. Only proven box lower bounds prune.

    Used for curved pack lettering against the fixed well, not for folded lofts.
    A single distant glyph or a positive envelope bound must not stand in for the
    closest one. Any failed competitive distance aborts the job as unresolved.
    """
    aa, bb = a.Solids, b.Solids
    boxes_a = [bounds(s, True) for s in aa]
    boxes_b = [bounds(s, True) for s in bb]
    jobs = sorted((box_gap(x, y), i, j) for i, x in enumerate(boxes_a) for j, y in enumerate(boxes_b))
    if not jobs:
        raise ValueError('No connected material solids for the selected distance')
    best = None
    checked = 0
    for lower, i, j in jobs:
        if best is not None and lower >= best['value']:
            break
        r = exact_gap(aa[i], bb[j])
        checked += 1
        if best is None or r['value'] < best['value']:
            best = dict(r, solid_a=i + 1, solid_b=j + 1)
    return dict(best, checked=checked, possible=len(jobs))


def material_gap(a, b):
    """Disjoint connected boundaries + no possible nesting implies disjoint material.

    On a long folded native B-spline loft OCC's solid-distance shortcut can
    misclassify a distant cap vertex as an interior witness and return zero.
    Do not simply use shell gaps either: one solid could enclose the other.
    """
    aa = [bounds(s, True) for s in a.Solids]
    bb = [bounds(s, True) for s in b.Solids]

    def encloses(x, y):
        return (x[0] <= y[0] + EPS).all() and (x[1] >= y[1] - EPS).all()

    if not any(encloses(x, y) or encloses(y, x) for x in aa for y in bb):
        return exact_gap(Part.makeCompound(a.Shells), Part.makeCompound(b.Shells))
    return exact_gap(a, b)  # keep zero / unresolved when containment is possible


def local_hit(c, b):
    """A point of the common and its nearest exit from B, not a translation for all of A."""
    p = c.CenterOfMass
    q = xyz(p)
    if not c.isInside(p, EPS, False):
        # A hollow/common crescent need not contain its own centroid. Walk inward
        # from an actual surface triangle, testing BOTH normal signs.
        vertices, triangles = c.tessellate(DEFLECTION)
        coords = np.array([xyz(v) for v in vertices])
        found = False
        for ijk in triangles[::max(1, len(triangles) // 18)]:
            tri = coords[list(ijk)]
            n = unit(np.cross(tri[1] - tri[0], tri[2] - tri[0]))
            if n is None:
                continue
            for offset in (0.01, -0.01, 0.001, -0.001):
                q = tri.mean(axis=0) + np.array(n) * offset
                if c.isInside(vec(q), EPS, False):
                    found = True
                    break
            if found:
                break
        if not found:
            q = xyz(c.Vertexes[0].Point)
    shell = Part.makeCompound(b.Shells)
    d, points, _ = Part.Vertex(vec(q)).distToShape(shell)
    n = unit(xyz(points[0][1]) - q) if points else None
    return dict(point=q.tolist(), normal=n, value=float(d))


def exact_common(a, b, pairs, hint):
    best = None
    count = 0
    hull = None
    for i, j in pairs:
        x, y = a.Solids[i], b.Solids[j]
        common = x.common(y)
        if common.isNull():
            continue
        for c in common.Solids:
            vol = c.Volume
            if abs(vol) < 1e-8:
                continue
            if not c.isValid() or vol < 0 or vol > min(x.Volume, y.Volume) + max(1e-5, vol * 1e-5):
                raise ValueError('Invalid OCC common, negative or impossible volume')
            count += 1
            box = bounds(c, True)
            hull = box if hull is None else np.array([np.minimum(hull[0], box[0]), np.maximum(hull[1], box[1])])
            if best is None or vol > best[0]:
                best = (vol, c, y)
    if best is None:
        if hint and hint['gap'] < 0:
            p = vec(hint['point'])
            if a.isInside(p, EPS, False) and b.isInside(p, EPS, False):
                raise ValueError('Empty common contradicts strict shared interior witness')
        return {}
    vol, c, y = best
    return dict(**local_hit(c, y), volume=vol, count=count, hull=hull.tolist())


def _worker(path, pipe):
    try:
        doc = App.openDocument(str(path))
        cache = {}
        pipe.send(True)
        while True:
            task = pipe.recv()
            if task is None:
                break
            mode, an, bn, pairs, hint = task
            try:
                for n in (an, bn):
                    if n not in cache:
                        cache[n] = world(doc.getObject(n))
                a, b = cache[an], cache[bn]
                if mode == 'gap':
                    result = material_gap(a, b)
                elif mode == 'split_gap':
                    result = split_material_gap(a, b)
                elif mode == 'common':
                    result = exact_common(a, b, pairs, hint)
                else:
                    raise ValueError('Unknown selected BRep operation: ' + mode)
                pipe.send((result, None))
            except Exception as ex:
                pipe.send((None, f'{type(ex).__name__}: {ex}'))
    except (BrokenPipeError, EOFError):
        pass
    finally:
        pipe.close()


class BoundedOCC:
    """A stuck native Boolean cannot be interrupted reliably by a Python alarm."""

    def __init__(self, path, timeout):
        self.path = path
        self.timeout = timeout
        self.process = None

    def close(self):
        if self.process is not None:
            self.process.kill()
            self.process.join()
            self.pipe.close()
            self.process = None

    def call(self, mode, a, b, pairs=(), hint=None, remaining=None, operation_timeout=None):
        if self.process is None:
            ctx = mp.get_context('spawn')  # do not fork live OCC/Qt threads
            self.pipe, peer = ctx.Pipe()
            self.process = ctx.Process(target=_worker, args=(self.path, peer), daemon=True)
            self.process.start()
            peer.close()
            if not self.pipe.poll(25) or not self.pipe.recv():
                self.close()
                raise RuntimeError('Could not load the FCStd in the isolated OCC worker')
        start = time.monotonic()
        try:
            self.pipe.send((mode, a.name, b.name, pairs, hint))
            limit = self.timeout if operation_timeout is None else operation_timeout
            wait = limit if remaining is None else max(0.01, min(limit, remaining))
            if self.pipe.poll(wait):
                return self.pipe.recv()
            reason = f'OCC time limit ({time.monotonic() - start:.1f} s)'
        except (BrokenPipeError, EOFError, OSError) as ex:
            reason = f'OCC worker stopped: {ex}'
        self.close()
        return None, reason
