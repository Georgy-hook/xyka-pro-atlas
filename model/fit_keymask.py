"""Probe the annulus between each key and the service cover on the installed native BReps.

The seam remains a mechanical clearance. It should not be an optical path to a PCB,
bright internal shell or empty space. Ray angles refer to the assembly, not world axes.
"""

from collections import Counter
import math

import numpy as np
import Part

from fit_frames import Frame
from fit_geometry import DEFLECTION, EPS, bounds, unit, vec, xyz

# Front retail view + oblique from both sides and above/below, plus the true face normal.
# First-hit probes, not a claim of recovered camera intrinsics or all-direction sealing.
VIEWS = (('front', 0, 0), ('oblique+', 32, 12), ('oblique-', -32, 12),
         ('above', 0, 22), ('below', 0, -22))
RIM_SITES = 32
FRACTIONS = (.20, .50, .80)


class NativeRays:
    """Ray/box pruning only; first hits and hit ordering come from trimmed OCC faces."""

    def __init__(self, leaves):
        self.leaves = list(leaves.values())
        self.boxes = np.array([a.box for a in self.leaves])
        self.travel = float(np.linalg.norm(self.boxes[:, 1].max(axis=0) - self.boxes[:, 0].min(axis=0))) + 2
        self.intersectors = {}
        try:
            from OCC.Core.IntCurvesFace import IntCurvesFace_ShapeIntersector
            from OCC.Core.gp import gp_Dir, gp_Lin, gp_Pnt
            self.engine = IntCurvesFace_ShapeIntersector
            self.line = lambda p, n: gp_Lin(gp_Pnt(*p), gp_Dir(*n))
        except ImportError:
            self.engine = None  # exact FreeCAD section fallback, never a mesh stand-in

    def intersections(self, leaf, origin, normal, depth):
        if self.engine is None:
            end = origin + normal * depth
            trace = leaf.shape.section(Part.makeLine(vec(origin), vec(end)))
            return sorted(float((xyz(v.Point) - origin) @ normal) for v in trace.Vertexes)
        if leaf.name not in self.intersectors:
            solver = self.engine()
            solver.Load(Part.__toPythonOCC__(leaf.shape), EPS)
            self.intersectors[leaf.name] = solver
        solver = self.intersectors[leaf.name]
        solver.Perform(self.line(origin, normal), 0., depth)
        if not solver.IsDone():
            raise RuntimeError('No ray solution for ' + leaf.name)
        return sorted(solver.WParameter(i) for i in range(1, solver.NbPnt() + 1))

    def first(self, station, inward, skip=()):
        return self.first_from(station - self.travel * inward, inward, self.travel * 2, skip)

    def first_from(self, origin, inward, end, skip=()):
        """Finite path. Skip only material explicitly removed in a named service state."""
        lo = np.zeros(len(self.leaves))
        hi = np.full(len(self.leaves), end)
        for k, direction in enumerate(inward):
            near = self.boxes[:, 0, k] - EPS - origin[k]
            far = self.boxes[:, 1, k] + EPS - origin[k]
            if abs(direction) < 1e-12:
                hi[(near > 0) | (far < 0)] = -1
            else:
                x, y = near / direction, far / direction
                lo = np.maximum(lo, np.minimum(x, y))
                hi = np.minimum(hi, np.maximum(x, y))
        ids = np.flatnonzero(lo <= hi)
        best_name = 'OPEN_VOID'
        best = end
        for i in ids[np.argsort(lo[ids], kind='stable')]:
            if lo[i] >= best:
                break
            leaf = self.leaves[i]
            if leaf.name in skip or float(getattr(leaf.obj, 'OpticalTransparency', 0)) > 0:
                continue  # an explicitly transmissive pane is not an opaque blocker
            hits = self.intersections(leaf, origin, inward, min(end, hi[i] + EPS))
            if hits and hits[0] < best:
                best, best_name = hits[0], leaf.name
        return best_name, None if best_name == 'OPEN_VOID' else origin + inward * best


def _section_loops(shape, z):
    return [w for w in shape.slice(vec([0, 0, 1]), float(z)) if w.isClosed()]


def _key_seam(frame, key, cover):
    """Find the actual cap wall and enclosing HOLE, not the cover's outer silhouette."""
    cap = frame.solid(key)
    mask = frame.solid(cover)
    lo = max(cap.box[0, 2], mask.box[0, 2])
    hi = min(cap.box[1, 2], mask.box[1, 2])
    if hi - lo <= EPS:
        raise ValueError('key does not span cover thickness')
    # The outer half is used for the moving seam. The backing ledge may close the
    # inner half by design. Never choose a section based on whether its rays pass.
    z = lo + .75 * (hi - lo)
    center = cap.box.mean(axis=0)
    center[2] = z
    cap_loops = _section_loops(cap.shape, z)
    if not cap_loops:
        raise ValueError('no closed key wall in fascia plane')
    cap_wall = max(cap_loops, key=lambda w: Part.Face(w).Area)
    enclosing = sorted([(Part.Face(w).Area, w) for w in _section_loops(mask.shape, z)
                        if Part.Face(w).isInside(vec(center), EPS, True)], key=lambda pair: pair[0])
    if len(enclosing) < 2:
        raise ValueError('no distinct cover aperture enclosing this key')
    hole = enclosing[0][1]
    gap = cap_wall.distToShape(hole)[0]
    if gap <= EPS or not Part.Face(hole).isInside(cap_wall.Vertexes[0].Point, EPS, True):
        raise ValueError('key contour touches/crosses or lies outside the aperture')
    points = []
    for point in cap_wall.discretize(Number=RIM_SITES + 1)[:-1]:
        distance, pairs, _ = Part.Vertex(point).distToShape(hole)
        if not pairs or distance <= EPS:
            raise ValueError('unresolved or pinched running seam')
        q = xyz(pairs[0][1])
        p = xyz(point)
        points.extend(frame.point(p + t * (q - p)) for t in FRACTIONS)
    return gap, points, Part.Face(hole).cut(Part.Face(cap_wall))


def _backing(leaves, frame, key, ring, ray, allowed, emit):
    """Continuous normal-projection complement of actual trimmed opaque end faces.

    This complements the sampled first-hit measurements. Proving there is some
    dark material behind a ring does not prove every possible first hit is dark.
    Do not require the clearance around a moving cap itself to become zero.
    """
    original = bounds(ring, True)
    z = original[:, 2].mean()
    inward = frame.direction((0, 0, -1))
    rest = ring
    providers = []
    for name in ('MechKeyCarrier', 'MechKeySeat' + key.name[-1], 'UiKeyMembrane'):
        if name not in leaves or float(getattr(leaves[name].obj, 'OpticalTransparency', 0)) > 0:
            continue
        for face in frame.solid(leaves[name]).shape.Faces:
            lo, hi = bounds(face, True)
            if hi[2] > z + EPS or hi[2] - lo[2] > EPS:
                continue
            if np.any(hi[:2] < original[0, :2] - EPS) or np.any(lo[:2] > original[1, :2] + EPS):
                continue
            patch = face.translated(vec((0, 0, z - face.CenterOfMass.z)))
            new = rest.cut(patch)
            if new.Area < rest.Area:
                providers.append(name)
            rest = new
            if not rest.Faces:
                emit('BACKED_RING', 'complete seam projection', key.name, name,
                     metric='area without verified dark backing mm²', value=0.,
                     detail=f'Full native annulus {ring.Area:.5f} mm² covered along the normal by '
                     f'trimmed faces of {", ".join(dict.fromkeys(providers))}. Foreground and obliques probed separately.')
                return
    # Do not turn a missing planar certificate into an assertion of leakage:
    # an inclined/curved backing may still block the actual normal ray.
    for face in rest.Faces:
        points, tri = face.tessellate(DEFLECTION)
        coords = np.array([xyz(p) for p in points])
        spot = next((p for idx in tri for p in [coords[list(idx)].mean(axis=0)]
                     if face.isInside(vec(p), EPS, False)), None)
        if spot is None:
            emit('REVIEW', 'complete seam projection', key.name, metric='unresolved patch mm²', value=face.Area,
                 detail='Could not find a strict interior witness in the remaining planar patch.')
            continue
        station = frame.point(spot)
        who, at = ray.first(station, inward)
        emit('REVIEW' if who in allowed else 'KEY_SIGHT_LEAK', 'complete seam projection', key.name, who,
             station if at is None else at, inward, 'patch not certified by planar backing mm²', face.Area,
             detail='Single first-hit witness within this patch; remainder may be blocked by curved surfaces.')


def optical_checks(leaves, emit):
    cover = leaves.get('MechServiceCover')
    glass = leaves.get('UiGlass')
    if not cover or not glass:
        emit('REVIEW', 'key ring', detail='Installed service cover / LCD datum missing')
        return
    frame = Frame(glass.obj)
    ray = NativeRays(leaves)
    root = glass.obj.Document.getObject('Assembly')
    body = Frame(root)
    directions = [('mask normal', frame.direction((0., 0., -1.)))]
    for view, azimuth, elevation in VIEWS:
        az, el = map(math.radians, (azimuth, elevation))
        eye = np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
        directions.append((view, body.direction(-eye)))
    # Only identified exterior solids and the optical backing qualify. An unknown
    # dark lead or a bare black PCB is NOT a mask; a rear bright wall is not a pass.
    allowed = {cover.name, 'UiKeyMembrane', 'MechKeyCarrier'}
    allowed.update('MechKeySeat' + s for s in 'LCR')  # separate opaque back-stops under the holes
    allowed.update(f'MechOuterKey{s}{suffix}' for s in 'LCR' for suffix in ('', 'Field', 'Mark', 'Foot'))
    for side in 'LCR':
        key = leaves.get('MechOuterKey' + side)
        if not key:
            emit('REVIEW', 'key ring', 'MechOuterKey' + side, detail='missing cap')
            continue
        try:
            gap, stations, ring = _key_seam(frame, key, cover)
        except ValueError as err:
            emit('REVIEW', 'key ring', key.name, cover.name, detail=str(err))
            continue
        emit('GAP', 'running seam section', key.name, cover.name, metric='minimum section gap mm', value=gap,
             detail='Exact outer-wall to aperture contour at 75% of their overlapping depth; not stroke clearance.')
        if 'MechCoverWindow' in leaves or 'MechKeyCarrier' in leaves:
            _backing(leaves, frame, key, ring, ray, allowed, emit)
        for view, inward in directions:
            counts = Counter()
            leaked = []
            for p in stations:
                name, at = ray.first(p, inward)
                counts[name] += 1
                if name not in allowed:
                    leaked.append((name, p if at is None else at))
            who, where = leaked[0] if leaked else (cover.name, stations[0])
            emit('KEY_SIGHT_LEAK' if leaked else 'SCREENED', 'key ring / ' + view, key.name, who, where, inward,
                 'leaking / sampled rays', len(leaked), detail=f'{len(stations)} sampled; native first hits: ' +
                 '; '.join(f'{name}={n}' for name, n in sorted(counts.items())) +
                 '. Witness = first leaking hit (seam station for open void), else first seam station.')


def membrane_stack(leaves, emit):
    """Unloaded cap -> silicone -> plunger sections. No force or switch travel inferred."""
    membrane = leaves.get('UiKeyMembrane')
    board = leaves.get('UiSubstrate')
    if membrane is None or board is None:
        emit('REVIEW', 'silicone key stack', detail='Owner-reported silicone sheet or finished button PCB is absent')
        return []
    frame = Frame(board.obj)
    rays = NativeRays({membrane.name: membrane})
    inward = frame.direction((0, 0, -1))
    pad = frame.solid(membrane)
    base = frame.solid(board)
    emit('MEASURED', 'silicone mounting depth', membrane.name, board.name,
         metric='lowest membrane above substrate front mm', value=pad.box[0, 2] - base.box[1, 2],
         detail='Installed extents along PCB normal; not material distance or compression. Native solids checked separately.')
    pairs = [(membrane, board)]
    for side in 'LCR':
        cap = leaves.get('MechOuterKey' + side + 'Foot') or leaves.get('MechOuterKey' + side)
        plunger = leaves.get('UiPlunger' + side)
        if not cap or not plunger:
            emit('REVIEW', 'silicone key stack ' + side, detail='Missing stem or plunger')
            continue
        pairs.extend(((cap, membrane), (membrane, plunger)))
        stem, actuator = frame.solid(cap), frame.solid(plunger)
        # Bound the support footprints at the *two facing ends*, not from the
        # outer ornamental cap, which can be wide enough to hide an offset shaft.
        w_stem, w_plunger = stem.box[0, 2], actuator.box[1, 2]
        outlines = [_section_loops(s.shape, z) for s, z in
                    ((stem, w_stem + .025), (actuator, w_plunger - .025))]
        if not all(outlines):
            emit('REVIEW', 'key transfer axis', cap.name, plunger.name, detail='No facing stem/plunger footprint')
            continue
        faces = [max((Part.Face(w) for w in loops), key=lambda f: f.Area) for loops in outlines]
        p, q = (xyz(f.CenterOfMass) for f in faces)
        delta = q - p
        delta[2] = 0
        offset = np.linalg.norm(delta)
        axes_in = (faces[0].isInside(vec([*q[:2], p[2]]), EPS, True)
                   and faces[1].isInside(vec([*p[:2], q[2]]), EPS, True))
        point = frame.point([*q[:2], w_plunger])
        axis_status = 'COAXIAL' if offset <= EPS else 'AXIS_OFFSET' if axes_in else 'MISSED_CAPTURE'
        emit(axis_status, 'key transfer axis', cap.name, plunger.name,
             point, frame.direction(unit(delta)), 'stem/plunger axis offset mm', offset,
             detail=f'{side}: actual opposing footprints contain each other’s centre={axes_in}.')
        # Cast through silicone at the actuator centre. A trimmed hole is not
        # material; do not infer a transfer layer from the membrane AABB.
        start = frame.point([*q[:2], pad.box[1, 2] + 1])
        hits = rays.intersections(membrane, start, inward, pad.box[1, 2] - pad.box[0, 2] + 2)
        if not hits:
            emit('MISSED_CAPTURE', 'silicone transfer ' + side, cap.name, plunger.name, point, inward,
                 'direct neutral gap mm', w_stem - w_plunger,
                 detail='No silicone on the plunger centreline. A bare route is not a silicone transfer stack.')
            continue
        w = [frame.local_point(start + t * inward)[2] for t in hits]
        spans = [(hi, lo) for hi, lo in zip(w, w[1:]) if hi - lo > EPS and
                 pad.shape.isInside(vec([*q[:2], (lo + hi) / 2]), EPS, False)]
        if len(spans) != 1:
            emit('REVIEW', 'silicone transfer ' + side, cap.name, membrane.name, point, inward,
                 detail=f'Found {len(spans)} material intervals on actuator centreline; not a continuous crown.')
            continue
        top, bottom = spans[0]
        upper_gap, lower_gap = w_stem - top, bottom - w_plunger
        # An underside skirt may flank the plunger. Only material on the
        # actuator axis participates in this check, not the full sheet envelope.
        status = ('STACK_OVERLAP' if min(upper_gap, lower_gap) < -EPS else
                  'TRANSFER_GAP' if max(upper_gap, lower_gap) > EPS else 'END_CONTACTS')
        emit(status, 'silicone transfer ' + side, cap.name, membrane.name,
             frame.point([*q[:2], top]), inward, 'axis silicone span mm', top - bottom,
             detail=f'Stem → silicone={upper_gap:.4f}; silicone → {plunger.name}={lower_gap:.4f}; '
             f'pocket roof above underside={bottom - pad.box[0, 2]:.4f} mm. Zero = neutral end contact, not preload.')
        # Measure the molded crown AND the underside pocket independently. An
        # off-centre wide crown can cover the centreline without being coaxial.
        step = min(.025, (top - bottom) / 4)
        for label, height, is_hole, reference, mate in (
                ('crown', top - step, False, p, cap), ('pocket', bottom - step, True, q, plunger)):
            candidates = []
            for loop in _section_loops(pad.shape, height):
                face = Part.Face(loop)
                if not face.isInside(vec([*reference[:2], height]), EPS, True):
                    continue
                if is_hole and pad.shape.isInside(vec([*reference[:2], height]), EPS, False):
                    continue
                candidates.append(face)
            if not candidates or (is_hole and len(candidates) < 2):
                emit('MISSED_CAPTURE', 'silicone ' + label + ' / ' + side, membrane.name, mate.name,
                     point, inward, detail='No enclosing molded footprint / pocket around this actuator at the opposed end.')
                continue
            center = xyz(min(candidates, key=lambda f: f.Area).CenterOfMass)
            lateral = center - reference
            lateral[2] = 0
            offset = float(np.linalg.norm(lateral))
            emit('COAXIAL' if offset <= EPS else 'AXIS_OFFSET', 'silicone ' + label + ' / ' + side,
                 membrane.name, mate.name, frame.point(center), frame.direction(unit(lateral)),
                 'molded/actuator axis offset mm', offset, detail='Measured on the finite rounded rectangular section, not the bounding box of the joint sheet.')
    return pairs
