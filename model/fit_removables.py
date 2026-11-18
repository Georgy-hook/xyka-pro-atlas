"""Installed retail pod and pack fits. Inputs are fit_geometry.installed() leaves.

Assembly +Z is toward the upper heater. Work on copies in that one frame;
report witnesses in world coordinates. Only named, visible material is paired.
The caller owns the time-bounded full-leaf material distances and commons.
"""

from itertools import permutations
from math import cos, pi

import numpy as np
import Part

from fit_frames import Frame
from fit_geometry import EPS, bounds, exact_gap, material_gap, unit, vec, xyz

CUP, LID, SCREEN = 'MechRemovablePod', 'MechPodLid', 'MechPodScreen'
RECEIVER, GUARD = 'MechChamberInsert', 'MechHeatGuard'
PACK, WELL = 'MechBatteryEnvelope', 'MechPackWell'
ENDS, SOCKETS = 'MechPackEndContacts', 'MechPackSeatSockets'
UP = (0, 0, 1)

# Positive identities from the retail pod plates, pack service face (XYKA f1210)
# and separate open-well photo. The dark end-arc windows are NOT terminals.
REQUIRED = {
    'Pod': (CUP, LID, SCREEN), 'LowerBody': (RECEIVER,), 'Heater': (GUARD,),
    'Battery': (PACK, 'MechPackCap', ENDS), 'Housing': (WELL, SOCKETS),
}
# Additional to fit_interfaces.MATE_PAIRS. Keep the most important distances
# first for a bounded exact-work budget. Optional marks are not mating datums.
PAIRS = (
    (ENDS, SOCKETS), (SCREEN, CUP), (SCREEN, LID), (SCREEN, GUARD),
    (LID, RECEIVER), ('MechPackCap', 'MechPackWellMouth'),
    (ENDS, 'MechPackSeatCarrier'), (PACK, SOCKETS), (PACK, 'MechPackSeatCarrier'),
    ('MechPodWallMark', RECEIVER), (CUP, 'MechHeatGuardRim'),
)
_PAIR_KEYS = {frozenset(pair) for pair in PAIRS}
_EXPECTED = {name: group for group, names in REQUIRED.items() for name in names}
_EXPECTED.update({'MechPackWellMouth': 'Housing', 'MechPackSeatCarrier': 'Housing',
                  'MechPodWallMark': 'Pod', 'MechHeatGuardRim': 'Heater'})


def _pack_print(a):
    return a.group == 'Battery' and a.name.startswith('MechRetailBatteryRu')


def pack_print_distance(a, b):
    return ((a.name == WELL and _pack_print(b)) or (b.name == WELL and _pack_print(a)))


def _print_clearance(mark, well, frame, emit):
    """Positive lower bound for ALL glyphs, not a surrogate ink-to-wall distance.

    The intact lettering can have hundreds of curved solids. Enclose all of
    their native support extrema in a solid cylinder and distance that simple
    supersolid from the unmodified well. A touching enclosure proves nothing.
    Whether or not this supplementary bound is reported, the exact glyph job
    and the ordinary material-common checks remain in scope.
    """
    paper, wall = frame.solid(mark), frame.solid(well)
    axis = wall.box.mean(axis=0)
    axis[2] = 0
    support = 0.
    # Eight rotations × four box normals = 32 directions over 360°. Nearest
    # measured normal is at most pi/32 away from ANY true radial direction.
    for angle in np.arange(8) * 11.25:
        b = bounds(paper.shape.rotated(vec(axis), vec(UP), angle), True) if angle else paper.box
        support = max(support, np.max(np.abs(b[:, :2] - axis[:2])))
    radius = float(support / cos(pi / 32) + EPS)
    z0, z1 = paper.box[:, 2]
    enclosing = Part.makeCylinder(radius, float(z1 - z0 + 2 * EPS), vec((*axis[:2], z0 - EPS)))
    gap = material_gap(enclosing, wall.shape)
    if gap['value'] <= EPS:
        return False
    emit('BOUND', 'pack exterior / fixed well', mark.name, well.name, frame.point(gap['point']),
         frame.direction(gap['normal']), 'proven material gap lower bound mm', gap['value'],
         detail=f'All {len(mark.solids)} registered solids inside circumscribed native 32-direction envelope '
         f'R={radius:.5f} mm over full label height. Distance from this enclosing cylinder to real well; '
         'witness midpoint belongs to this bound, not the exact nearest printed glyph. Material commons remain in scope.')
    return True


def extra_scope(a, b):
    """Symmetric predicate for the caller's material/common pass."""
    if frozenset((a.name, b.name)) in _PAIR_KEYS:
        return a.group == _EXPECTED[a.name] and b.group == _EXPECTED[b.name]
    return ((a.name == WELL and a.group == 'Housing' and _pack_print(b)) or
            (b.name == WELL and b.group == 'Housing' and _pack_print(a)))


def _inventory(leaves, emit):
    present = {}
    groups = {a.group for a in leaves.values()}
    for group, names in REQUIRED.items():
        if group not in groups:
            emit('REVIEW', 'retail removable group', group,
                 detail='No installed material in this required module (absent or empty).')
        for name in names:
            leaf = leaves.get(name)
            if leaf is None or leaf.group != group:
                why = 'absent' if leaf is None else f'in {leaf.group}, not {group}'
                emit('REVIEW', 'retail physical identity', name, group,
                     detail=f'Required observable retail part {why}; no lookalike substituted.')
            else:
                present[name] = leaf
        if all(name in present for name in names):
            emit('CHECKED', 'retail physical identity', group, detail='Installed: ' + ', '.join(names))
    emit('LIMIT', 'retail removable scope', detail='Visible service faces and removable geometry only. '
         'Hidden pin type, nets, spring travel, seat compression, thread and tolerance are unknown, '
         'not missing components. Optional print/rim pairs are checked only when present.')
    return present


def _flat_z(face):
    lo, hi = bounds(face, True)[:, 2]
    return (lo + hi) / 2 if hi - lo <= EPS else None


def _circle(wire):
    """Recognize a circular loop; a square with the same XY bounds is not one."""
    if not wire.isClosed():
        raise ValueError('open rim boundary')
    box = bounds(wire, True)
    center = box.mean(axis=0)
    radius = wire.Length / (2 * pi)
    samples = np.array([xyz(p) for p in wire.discretize(Number=33)])
    residual = abs(np.linalg.norm(samples[:, :2] - center[:2], axis=1) - radius)
    # Recognition of circular topology only; NOT a fit allowance.
    if radius <= EPS or residual.max() > .0001 or np.ptp(box[:, 2]) > EPS:
        raise ValueError('no identifiable circular boundary normal to the assembled axis')
    return center, radius


def _end_ring(shape, upper):
    """The actual planar, annular outward end face; not a section through a boss."""
    z = bounds(shape, True)[int(upper), 2]
    rings = []
    for face in shape.Faces:
        if len(face.Wires) != 2:
            continue
        plane = _flat_z(face)
        if plane is not None and abs(plane - z) <= EPS:
            (p, ro), (q, ri) = sorted(map(_circle, face.Wires), key=lambda t: -t[1])
            if ro > ri and np.linalg.norm((p - q)[:2]) <= EPS:
                rings.append((p, ro, ri, face))
    if len(rings) != 1:
        raise ValueError('no unique exposed annulus on the expected end')
    return rings[0]


def _battery(end, seat, frame, emit):
    counts = len(end.shape.Solids), len(seat.shape.Solids)
    if counts != (4, 4):
        raise ValueError(f'visible four-to-four pattern not resolved; solid counts = {counts}')
    tips = [_end_ring(s, False) for s in end.shape.Solids]
    eyes = [_end_ring(s, True) for s in seat.shape.Solids]
    for pattern in (tips, eyes):
        for i, ring in enumerate(pattern):
            if any(np.linalg.norm((ring[0] - other[0])[:2]) <= EPS for other in pattern[:i]):
                raise ValueError('duplicate exposed centres; no distinct four-face registration')

    # Fully bijective, based solely on native XY geometry, not subshape order,
    # colour, nearest-any-compound distance or a guessed electrical pin number.
    def cost(order):
        return sum(np.sum((tip[0][:2] - eye[0][:2]) ** 2) for tip, eye in zip(tips, order))

    for tip, eye in zip(tips, min(permutations(eyes), key=cost)):
        p, _, _, moving = tip
        q, _, _, fixed = eye
        dz = p[2] - q[2]
        offset = np.linalg.norm((p - q)[:2])
        projected = moving.copy()
        projected.translate(vec((0, 0, -dz)))
        footprint = projected.common(fixed)
        area = sum(f.Area for f in footprint.Faces)
        if area > EPS * EPS:
            # A point on BOTH trimmed face projections, even for eccentric rings.
            mid = xyz(footprint.Faces[0].Vertexes[0].Point)
            mid[2] += dz / 2
        else:
            _, witnesses, _ = moving.distToShape(fixed)
            if not witnesses:
                raise ValueError('no face distance witnesses')
            a, b = witnesses[0]
            mid = (xyz(a) + xyz(b)) / 2
        if dz > EPS:
            status = 'ANCHOR_GAP'
        elif dz < -EPS or area <= EPS * EPS:
            status = 'MISSED_CAPTURE'
        else:
            status = 'CAPTURED' if offset <= EPS else 'REVIEW'
        emit(status, 'retail pack / fixed service faces', ENDS, SOCKETS,
             frame.point(mid), frame.direction(UP), 'signed axial face gap mm', dz,
             detail=f'Seat XY=({q[0]:.3f},{q[1]:.3f}) in Assembly; axis offset={offset:.4f} mm; '
             f'projected annular material overlap={area:.4f} mm². Positive = separated, '
             'negative = crossed planes (not a bulk common). No pin assignment or electrical claim.')


def _pierced_faces(s):
    """Axial planes bearing a field of actual holes, not just the outer lip."""
    planes = []
    for face in s.shape.Faces:
        if len(face.Wires) >= 3:
            z = _flat_z(face)
            if z is not None:
                planes.append((z, face))
    if len(planes) < 2:
        raise ValueError('pierced face field not identified on two axial surfaces')
    return sorted(planes, key=lambda item: item[0])


def _closure(cup, lid, frame, emit):
    floor = _pierced_faces(cup)[0]
    above = floor[0] - cup.box[:, 2].mean()
    emit('CHECKED' if above > EPS else 'MISSED_CAPTURE', 'pod fixed floor faces heater', CUP,
         point=frame.point(xyz(floor[1].Vertexes[0].Point)), normal=frame.direction(UP),
         metric='lowest pierced plane above cup mid-height mm', value=above,
         detail='Fixed perforated floor must be at the upper end of the cup; open mouth toward stem.')
    disk = _pierced_faces(lid)
    bottom, face = disk[0]
    top = disk[-1][0]
    down = abs(bottom - lid.box[0, 2]) <= EPS and lid.box[1, 2] > top + EPS
    emit('CHECKED' if down else 'MISSED_CAPTURE', 'pod pierced lid faces down', LID, CUP,
         frame.point(xyz(face.Vertexes[0].Point)), frame.direction((0, 0, -1)),
         'edge return above pierced disk mm', lid.box[1, 2] - top,
         detail='The perforated disk is the stem-side extreme; its folded edges turn back toward the cup.')
    p, _, opening, lip = _end_ring(cup.shape, False)
    q, rim = _circle(face.OuterWire)
    radial = p - q
    radial[2] = 0
    offset = np.linalg.norm(radial)
    radial = radial / offset if offset > EPS else np.array((1., 0., 0.))
    cover = rim - opening - offset
    within_fold = top - EPS <= p[2] <= lid.box[1, 2] + EPS
    _, witnesses, _ = Part.Vertex(vec(p + opening * radial)).distToShape(lip)
    if not witnesses:
        raise ValueError('no resolved cup mouth edge witness')
    emit('CAPTURED' if down and cover >= -EPS and within_fold else 'MISSED_CAPTURE',
         'pod lid / open mouth', LID, CUP, frame.point(xyz(witnesses[0][1])), frame.direction(radial),
         'projected mouth edge coverage mm', cover,
         detail=f'Actual mouth inner R={opening:.4f}, disk outer R={rim:.4f}, offset={offset:.4f} mm. '
         f'Lip Z={p[2]:.4f} vs disk/edge return {top:.4f}..{lid.box[1,2]:.4f} mm. '
         'Closure outline only: holes intentionally open, no seal or latch force inferred.')


def _bore(cup):
    wires = cup.shape.slice(vec(UP), float(cup.box[:, 2].mean()))
    if len(wires) != 2:
        raise ValueError('could not identify two circular walls at cup waist')
    rims = sorted(((_circle(w), w) for w in wires), key=lambda entry: entry[0][1])
    ((p, ri), inner), ((q, ro), _) = rims
    if np.linalg.norm((p - q)[:2]) + ri >= ro:
        raise ValueError('waist walls are not nested')
    # The circle recognizer isn't itself a fit tolerance. Use the *nearest*
    # wall point for the inscribed radius and retain the actual trimmed loop.
    radius, witnesses, _ = inner.distToShape(Part.Vertex(vec(p)))
    if not witnesses or radius <= EPS:
        raise ValueError('no resolved waist radius')
    return p, radius, Part.Face(inner)


def _screen_fit(cup, screen, frame, emit):
    axis, bore, aperture = _bore(cup)
    points = np.array([xyz(v.Point) for v in screen.shape.Vertexes])
    offsets = points - axis
    offsets[:, 2] = 0
    radii = np.linalg.norm(offsets, axis=1)
    i = np.argmax(radii)
    # The wire mesh has no circular OD face. Bound its ENTIRE XY projection:
    # every radial direction is <= pi/16 from one of 16 support normals. OCC
    # directional bounds include curved strand tips between BRep vertices.
    support = 0.
    for degrees in (0., 22.5, 45., 67.5):
        if degrees:
            rotated = screen.shape.copy()
            rotated.rotate(vec(axis), vec(UP), degrees)
            box = bounds(rotated, True)
        else:
            box = screen.box
        support = max(support, np.abs(box[:, :2] - axis[:2]).max())
    margin = bore - support / cos(pi / 16)
    status = 'CAPTURED'
    if margin < -EPS:
        projected = Part.Vertex(vec((*points[i, :2], axis[2])))
        missed = projected.distToShape(aperture)[0] > EPS
        status = 'MISSED_CAPTURE' if missed else 'REVIEW'
    emit(status, 'pod screen / projected cup bore', SCREEN, CUP, frame.point(points[i]),
         frame.direction(unit(offsets[i])), 'lower bound on projected radial margin mm', margin,
         detail=f'Waist R={bore:.4f}; mesh maximum R between {radii[i]:.4f} (actual vertex at witness) '
         f'and {bore-margin:.4f} mm (16-direction bound). A straddling bound is unresolved; '
         'projection through this section only, not a floor clearance or removal-path simulation.')
    # These are sampled material points, not a filled disk or a fabricated outer ring.
    distances = np.linalg.norm(points[:, :2] - screen.box.mean(axis=0)[:2], axis=1)
    core = points[distances <= .45 * max(distances)]
    tips = points[distances >= .97 * max(distances)]
    if not len(core) or not len(tips):
        raise ValueError('mesh has no distinct central and outer material witnesses')
    q = tips[np.argmin(tips[:, 2])]
    rise = q[2] - max(core[:, 2])
    emit('CHECKED' if rise > EPS else 'MISSED_CAPTURE' if rise < -EPS else 'REVIEW',
         'pod dished screen direction', SCREEN, CUP, frame.point(q), frame.direction(UP),
         'sampled tip rise above centre mm', rise,
         detail='Outermost mesh vertices versus central vertices: bent ends turn toward the fixed floor, '
         'away from the down-facing lid. No specified bend depth or weave assumed.')


def _stack(parts, frame, emit):
    cup, screen = parts[CUP], parts[SCREEN]
    axis, bore, _ = _bore(cup)
    points = np.array([xyz(v.Point) for v in screen.shape.Vertexes])
    # Real material witnesses INSIDE the bore, not rays down a nominal screen
    # centre (often an open cell). Trace at several radii in four quadrants.
    points = points[np.linalg.norm(points[:, :2] - axis[:2], axis=1) < .8 * bore]
    pairs = [(a, b) for a, b in ((LID, SCREEN), (SCREEN, CUP), (CUP, GUARD)) if a in parts and b in parts]
    used = {pair: [] for pair in pairs}
    floor_bias = {}
    z0 = min(s.box[0, 2] for s in parts.values()) - 1
    z1 = max(s.box[1, 2] for s in parts.values()) + 1
    if len(points):
        for x, y in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
            for frac in (.23, .43):
                target = axis[:2] + frac * bore * np.array([x, y])
                p = points[np.argmin(np.linalg.norm(points[:, :2] - target, axis=1))]
                line = Part.makeLine(vec((*p[:2], z0)), vec((*p[:2], z1)))
                heights = {SCREEN: (p[2], p[2])}
                for name in (CUP, LID, GUARD):
                    if name in parts:
                        trace = parts[name].shape.common(line)
                        if trace.Length > EPS:
                            heights[name] = bounds(trace, True)[:, 2]
                if LID in heights and CUP in heights:
                    # Relative location, not an assumed zero clearance at the floor.
                    floor_bias[tuple(p)] = (p[2] - heights[LID][1]) - (heights[CUP][0] - p[2])
                for a, b in pairs:
                    if a in heights and b in heights:
                        lo, hi = heights[a][1], heights[b][0]
                        used[a, b].append((hi - lo, (*p[:2], (lo + hi) / 2), tuple(p[:2])))
    for (a, b), rows in used.items():
        count = len({r[2] for r in rows})
        if not rows:
            emit('REVIEW', 'pod axial material order', a, b, detail='No shared material projection at the probes.')
            continue
        dz, mid, _ = min(rows, key=lambda row: row[0])
        emit('MISSED_CAPTURE' if dz < -EPS else 'CHECKED' if count >= 3 else 'REVIEW',
             'pod axial material order', a, b, frame.point(mid), frame.direction(UP),
             'least signed axial separation at probes mm', dz,
             detail=f'{count} distinct XY stations. Actual mesh vertices and axial material cuts inside '
             'the cup bore: lid → screen → integral cup floor → separate upper guard. Holes yield no '
             'hit; fewer than three stations do not verify order. Not a global minimum or thermal fit.')
    if LID in parts:
        if floor_bias:
            p = min(floor_bias, key=floor_bias.get)
            bias = floor_bias[p]
            status = 'MISSED_CAPTURE' if bias < -EPS else 'CHECKED' if bias > EPS and len(floor_bias) >= 3 else 'REVIEW'
            emit(status, 'pod screen at floor end', SCREEN, CUP, frame.point(p), frame.direction(UP),
                 'lid minus floor distance at mesh witnesses mm', bias,
                 detail='Minimum signed bias on common pierced-material probes; positive puts the '
                 'mesh toward the fixed cup floor rather than just anywhere behind the lid. No seat gap prescribed.')
        else:
            emit('REVIEW', 'pod screen at floor end', SCREEN, CUP, detail='No probe resolved both lid and fixed floor.')


def _section_material(local, z):
    """Actual material at one station, including holes and disconnected islands."""
    faces = []
    for solid in local.shape.Solids:
        wires = solid.slice(vec(UP), float(z))
        if not wires:
            continue
        if not all(w.isClosed() for w in wires):
            raise ValueError('open native section contour')
        section = Part.makeFace(wires, 'Part::FaceMakerBullseye')
        if not section.Faces or not section.isValid():
            raise ValueError('unresolved section face; not discarding a possible obstacle')
        faces.extend(section.Faces)
    if not faces:
        raise ValueError('no closed material section')
    region = faces[0] if len(faces) == 1 else faces[0].multiFuse(faces[1:]).removeSplitter()
    if not region.isValid() or not region.Faces or region.Area <= EPS * EPS:
        raise ValueError('invalid planar material region')
    return region


def _key_direction(wire):
    """Recognize a round contour or a curved contour with one supporting flat.

    Use edge arc length vs chord, including for affine-transformed curves. Never
    take the line orientation as a key direction: its normal has two signs.
    """
    flats = []
    curved = False
    center = xyz(Part.Face(wire).CenterOfMass)
    for edge in wire.Edges:
        p = xyz(edge.valueAt(edge.FirstParameter))
        q = xyz(edge.valueAt(edge.LastParameter))
        chord = np.linalg.norm(q - p)
        if edge.Length - chord > EPS:
            curved = True
        elif chord > EPS:
            d = (q - p) / chord
            n = np.array([-d[1], d[0], 0.])
            if (p - center) @ n < 0:
                n = -n
            flats.append((p, n))
    if not flats:
        _circle(wire)  # no chord alone does not make an arbitrary spline circular
        return 'round', None
    p, n = flats[0]
    if curved and all(np.linalg.norm(n - m) <= EPS and abs((q - p) @ n) <= EPS for q, m in flats):
        # An internal notch can also have a straight edge. Verify that the
        # entire contour lies on the inboard side of this candidate key flat.
        probe = wire.copy()
        probe.rotate(vec(center), vec(UP), -float(np.degrees(np.arctan2(n[1], n[0]))))
        if bounds(probe, True)[1, 0] - center[0] <= (p - center) @ n + EPS:
            return 'flat', n
    raise ValueError('no unique supporting flat on curved profile')


def _pack_station(guest, host, z, frame, gn, hn, frac, emit):
    g, h = _section_material(guest, z), _section_material(host, z)
    check = 'retail pack radial section'
    note = f'{frac:.0%} of {gn}/{hn} axial overlap; holder Z={z:.4f} mm. '
    # Test intersections of actual MATERIAL, not only its boundaries. A post
    # wholly inside the pack footprint has a positive curve-to-curve distance!
    overlap = g.common(h)
    if overlap.Faces and overlap.Area > EPS * EPS:
        emit('RADIAL_CLASH', check, gn, hn, frame.point(xyz(overlap.Faces[0].Vertexes[0].Point)),
             frame.direction(UP), 'section material common mm²', overlap.Area,
             detail=note + 'Witness on shared planar material; direction is section normal, not a penetration depth.')
        return False
    bores = [w for f in h.Faces for w in f.Wires if not w.isSame(f.OuterWire)]
    if len(bores) != 1 or len(g.Faces) != 1:
        raise ValueError(f'no unique bounded receiver aperture / connected guest ({len(bores)} / {len(g.Faces)})')
    aperture = Part.Face(bores[0])
    escaped = g.cut(aperture)
    enclosed = g.common(aperture)
    if abs(enclosed.Area + escaped.Area - g.Area) > EPS * g.Length:
        raise ValueError('planar footprint partition did not conserve section area')
    if escaped.Faces and escaped.Area > EPS * EPS:
        emit('MISSED_CAPTURE', check, gn, hn, frame.point(xyz(escaped.Faces[0].Vertexes[0].Point)),
             frame.direction(UP), 'guest outside bounded aperture mm²', escaped.Area,
             detail=note + 'Witness on escaped footprint. Being disjoint from well material is not containment.')
        return False
    guest_kind, a = _key_direction(g.Faces[0].OuterWire)
    host_kind, b = _key_direction(bores[0])
    keyed = a is not None and b is not None
    if keyed:
        angle = np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b)), a @ b))
        note += f'Outward flat-normal angle={angle:.4f}°; '
    else:
        note += 'No angular constraint demonstrated here; '
    gap = exact_gap(Part.makeCompound(g.Wires), Part.makeCompound(h.Wires))
    status = 'CAPTURED' if gap['value'] > EPS else 'NEAR'
    if b is not None and (a is None or np.linalg.norm(a - b) > EPS):
        status = 'REVIEW'  # fits this aperture, but nominal flat directions do not register
    emit(status, check, gn, hn, frame.point(gap['point']), frame.direction(gap['normal']),
         'minimum in-plane contour gap mm', gap['value'],
         detail=note + f'{guest_kind} guest / {host_kind} aperture. Entire material footprint contained, '
         'no sectional common area. Nearest boundary midpoint, guest → holder; no factory clearance inferred.')
    return keyed


def keyed_pack_seat(leaves, emit):
    """Emit sampled radial registration for the retail pack; no geometry or pair-list mutation.

    The cap can span BOTH the sleeve and the fixed keyed mouth. Discover flat
    directions on the actual sections, not from a nominal key radius or clock.
    This is not a swept insertion test, nor a clearance for all labels or Z.
    """
    cap, mouth = 'MechPackCap', 'MechPackWellMouth'
    names = (PACK, cap, WELL, mouth)
    parts = {}
    for n in names:
        leaf = leaves.get(n)
        if leaf is None or leaf.group != _EXPECTED[n]:
            emit('REVIEW', 'retail pack radial identity', n, detail='Missing or mis-grouped installed radial part.')
        else:
            parts[n] = leaf
    holder_leaf = parts.get(WELL) or parts.get(mouth)
    if holder_leaf is None:
        return
    # The lathed sleeve LEAF has a rotated sketch frame, not its holder's axes.
    holder = holder_leaf.obj.getParentGeoFeatureGroup()
    if holder is None or holder.Name != 'MechPackSeatAssembly':
        emit('REVIEW', 'retail pack radial frame', detail='Fixed pack holder +Z not identified.')
        return
    frame = Frame(holder)
    seen_key = False
    shapes = {n: frame.solid(leaf) for n, leaf in parts.items()}
    for hn in (WELL, mouth):
        for gn in (PACK, cap):
            if hn not in shapes or gn not in shapes:
                continue
            guest, host = shapes[gn], shapes[hn]
            lo = max(guest.box[0, 2], host.box[0, 2])
            hi = min(guest.box[1, 2], host.box[1, 2])
            if hi - lo <= EPS:
                if (gn, hn) in ((PACK, WELL), (cap, mouth)):
                    emit('MISSED_CAPTURE', 'retail pack radial section', gn, hn,
                         metric='signed axial envelope engagement mm', value=hi-lo,
                         detail='No interior engagement heights in the installed holder frame.')
                continue
            for frac in (.25, .50, .75):
                z = lo + frac * (hi - lo)
                try:
                    seen_key |= _pack_station(guest, host, z, frame, gn, hn, frac, emit)
                except (Part.OCCError, RuntimeError, ValueError) as exc:
                    emit('REVIEW', 'retail pack radial section', gn, hn,
                         detail=f'Holder Z={z:.4f} mm: {exc}; not a passing bound.')
    if not seen_key:
        emit('REVIEW', 'retail pack radial key', cap, mouth,
             detail='No contained section demonstrated a pair of identifiable flats; round-guide clearance is not key registration.')


def extra_mates(leaves, emit):
    """Emit observable installed checks and return extra leaf pairs for exact QA."""
    present = _inventory(leaves, emit)
    pairs = [(leaves[a], leaves[b]) for a, b in PAIRS
             if a in leaves and b in leaves and extra_scope(leaves[a], leaves[b])]
    if WELL in present:
        well = present[WELL]
        holder = well.obj.Document.getObject('MechPackSeatAssembly') or well.obj.Document.getObject('Assembly')
        for a in sorted((s for s in leaves.values() if _pack_print(s)), key=lambda s: s.name):
            pairs.append((a, well))  # exact connected-solid distance regardless of any enclosure bound
            try:
                if holder is not None:
                    _print_clearance(a, well, Frame(holder), emit)
            except (Part.OCCError, RuntimeError, ValueError):
                pass  # supplementary analytic bound unavailable; exact job already queued
    if not present:
        return pairs
    assembly = next(iter(present.values())).obj.Document.getObject('Assembly')
    if assembly is None:
        emit('REVIEW', 'retail removable frame', detail='No installed Assembly frame; not using world Z as a substitute.')
        return pairs
    frame = Frame(assembly)
    parts = {n: frame.solid(present[n]) for n in (ENDS, SOCKETS, CUP, LID, SCREEN, GUARD) if n in present}
    for names, measure in (((ENDS, SOCKETS), _battery), ((CUP, LID), _closure), ((CUP, SCREEN), _screen_fit)):
        if all(n in parts for n in names):
            try:
                measure(*(parts[n] for n in names), frame, emit)
            except (Part.OCCError, ValueError, RuntimeError) as exc:
                emit('REVIEW', 'retail removable measurement', *names, detail=str(exc))
    if SCREEN in parts and CUP in parts:
        try:
            _stack({n: parts[n] for n in (CUP, LID, SCREEN, GUARD) if n in parts}, frame, emit)
        except (Part.OCCError, ValueError, RuntimeError) as exc:
            emit('REVIEW', 'pod axial material order', SCREEN, CUP, detail=str(exc))
    return pairs
