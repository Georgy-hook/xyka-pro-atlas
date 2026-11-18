"""Installed service hardware, separated by access side, not by nearby PCB holes."""

from collections import Counter
import math

import numpy as np

from fit_frames import Frame
from fit_geometry import EPS, bounds, unit, vec, xyz
from fit_keymask import NativeRays

FACE_SITES = ('TopL', 'TopR', 'SideL', 'SideR', 'Foot')
BASE_FAMILIES = {'Seal': ('Left', 'Right', 'Rear'), 'Inner': ('FrontL', 'FrontR', 'RearL', 'RearR')}


def retail(leaves):
    return bool(leaves and next(iter(leaves.values())).obj.Document.getObject('UpperUnit'))


def film_members(leaves):
    """Only the registered descendants of the peeling film move in that step."""
    film = next(iter(leaves.values())).obj.Document.getObject('MechFrontFilm')
    stack = [film] if film is not None else []
    result = set()
    while stack:
        obj = stack.pop()
        if obj.Name in leaves:
            result.add(obj.Name)
        else:
            stack.extend(getattr(obj, 'Group', []))
    return result


def _inventory(leaves, prefix, sites, emit):
    actual = {n for n in leaves if n.startswith(prefix)}
    expected = {prefix + site for site in sites}
    wrong = sorted(n for n in actual if leaves[n].group in ('MainPCB', 'DisplayPCB'))
    ok = actual == expected and not wrong
    emit('CHECKED' if ok else 'REVIEW', 'service hardware inventory', prefix, metric='registered leaves',
         value=len(actual), detail=f'Expected {len(expected)}; missing={sorted(expected - actual)}; '
         f'unexpected={sorted(actual - expected)}; wrongly on PCBs={wrong}. Not board screws.')
    return actual


class FaceAccess:
    def __init__(self, leaves, emit):
        self.rays = NativeRays(leaves)
        self.film = film_members(leaves)
        self.screws = _inventory(leaves, 'MechServiceScrew', FACE_SITES, emit)
        _inventory(leaves, 'MechPanelEar', FACE_SITES, emit)
        if not {'MechServiceCover', 'MechCoverWindow'} <= self.film:
            emit('REVIEW', 'peeling film', detail=f'Mask and transmitting zone must both belong to the removable film: {sorted(self.film)}')
        lcd = leaves.get('UiGlass')
        self.inward = Frame(lcd.obj).direction((0, 0, -1)) if lcd else None

    def measure(self, frame, lug, hole, rh, ear, screw, emit):
        """What is visible from the face before peel, after peel and with screws out?

        Stop at the distal end of the ear: a circuit board behind an empty bore
        is not a plugged bore. The fifth SideL is from sep01, not a fifth directly
        observed opening in the owner's partially obscured photo.
        """
        axis = frame.direction((0, 1, 0))
        positive = self.inward is None or np.dot(axis, self.inward) >= 0
        inward = axis if positive else -axis
        far = hole.copy()
        far[1] = lug.box[int(positive), 1] + (-EPS if positive else EPS)
        probes = [far]
        for angle in range(0, 360, 45):
            p = far.copy()
            p[[0, 2]] += .70 * rh * np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
            probes.append(p)
        steps = [('installed', set(), self.film, 'HIDDEN_BY_FILM'),
                 ('film peeled', self.film, {screw.name}, 'HEAD_VISIBLE'),
                 ('film and face screws removed', self.film | self.screws, {'OPEN_VOID'}, 'OPEN_BORE')]
        for state, skip, expected, status in steps:
            counts = Counter()
            bad = []
            first = None
            for probe in probes:
                end = frame.point(probe)
                origin = end - inward * self.rays.travel
                name, hit = self.rays.first_from(origin, inward, self.rays.travel, skip)
                at = end if hit is None else hit
                if first is None:
                    first = at
                counts[name] += 1
                if name not in expected:
                    bad.append((name, at))
            who, where = bad[0] if bad else (next(iter(counts)), first)
            emit('BLOCKED_VIEW' if bad else status, 'face fixing / ' + state, ear.name, who, where, inward,
                 'unexpected first hits of 9', len(bad), detail=f'Centre and 8 sites at 0.70 × true bore R={rh:.4f} mm. '
                 f'First opaque material from outside, ending at inner lip: {dict(counts)}. '
                 + ('Comparative A4.3 sep01 station (occluded in owner view).' if ear.name.endswith('SideL')
                    else 'Owner-sited housing ear; not a board hole.'))


def head_seat(frame, screw, carrier, inward, emit):
    """Distance along the axis between opposed, actually overlapping bearing lands.

    Capturing a shank does not prove its head isn't floating over the recess.
    A zero total distance can instead be incidental side-wall contact.
    """
    sign = 1 if inward is None or np.dot(frame.direction((0, 1, 0)), inward) >= 0 else -1

    def flats(leaf, side, annular=False):
        for face in frame.solid(leaf).shape.Faces:
            b = bounds(face, True)
            if b[1, 1] - b[0, 1] > EPS or (annular and len(face.Wires) < 2):
                continue
            u0, u1, v0, v1 = face.ParameterRange
            normal = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
            if normal.y * side <= 0:
                continue
            y = face.CenterOfMass.y
            yield b[:, [0, 2]], y, face.translated(vec((0, -y, 0)))

    choices = []
    supports = list(flats(carrier, -sign))
    for box, y, land in flats(screw, sign, annular=True):
        for other, depth, seat in supports:
            if np.min(np.minimum(box[1], other[1]) - np.maximum(box[0], other[0])) <= EPS:
                continue
            shared = land.common(seat)
            if shared.Faces and shared.Area > EPS * EPS:
                # A ring's centroid is VOID: a vertex is a real common support point.
                p = xyz(shared.Faces[0].Vertexes[0].Point)
                p[1] = (y + depth) / 2
                choices.append((sign * (depth - y), shared.Area, p))
    if not choices:
        emit('MISSED_CAPTURE', 'face screw bearing', screw.name, carrier.name,
             detail='No overlapping trimmed, opposed annular head and rigid seat lands found.')
        return
    gap, area, at = min(choices, key=lambda item: (abs(item[0]), -item[1]))
    status = 'NOMINAL_SEAT' if abs(gap) <= EPS else 'MISSED_CAPTURE' if gap > 0 else 'SEAT_COMMON'
    emit(status, 'face screw bearing', screw.name, carrier.name, frame.point(at), frame.direction((0, sign, 0)),
         'signed axial bearing gap mm', gap, detail=f'Projected annular bearing material {area:.4f} mm². '
         'Positive = head floats; negative = crossed bearing planes, check bulk separately. Not thread engagement or torque.')


def service_scope(a, b):
    """Additional physical BRep pairs, including integral catches on two large solids."""
    names = {a.name, b.name}
    if any(n.startswith(('MechServiceScrew', 'MechServiceBase', 'MechPanelEar')) for n in names):
        return True
    return names in ({'MechUpperFairing', 'MechTopBridge'}, {'MechTopBridge', 'MechLightRing'},
                     {'MechUpperFairing', 'MechLightRing'})


def base_fixings(leaves, emit, sections):
    """Register the separate 3 + 4 screw families to both material halves of the service base.

    A circle counts only if its centre and inner rim are void and the outside is
    a solid wall. Thus neither a solid boss nor the large central thermal opening
    stands in for a screw bore. The size/proximity filters IDENTIFY candidates:
    an unidentified interface is a review, never a passing clearance.
    """
    if not retail(leaves) and not any(n.startswith('MechServiceBase') for n in leaves):
        return []
    holder = leaves.get('MechHeaterCarrier')
    if holder is None:
        emit('REVIEW', 'internal base', detail='No installed heater holder to establish screw axis')
        return []
    frame = Frame(holder.obj)
    hosts = {n: frame.solid(leaves[n]) for n in ('MechHeaterCarrier', 'MechServiceBaseInsert') if n in leaves}
    if len(hosts) != 2:
        emit('REVIEW', 'internal base', detail='Missing heater holder or removable inner carrier with its two bore families')
    cache = {}

    def bores(name, z):
        key = (name, float(z))
        if key not in cache:
            host = hosts[name]
            result = []
            for p, r in sections(host, 2, z):
                if host.shape.isInside(vec(p), EPS, False):
                    continue
                e = np.array([r + max(.001 * r, EPS * 10), 0., 0.])
                if any(host.shape.isInside(vec(p + sign * e), EPS, False) for sign in (1, -1)):
                    result.append((p, r))
            cache[key] = result
        return cache[key]

    for family, expected in BASE_FAMILIES.items():
        names = _inventory(leaves, 'MechServiceBase' + family + 'Screw', expected, emit)
        for name in sorted(names):
            pin = frame.solid(leaves[name])
            z0, z1 = pin.box[:, 2]
            shaft = []
            # Include short tip chamfers and actual changes of the receiving
            # wall, not only equally spaced heights. Seal screws can enter a
            # complete bore only AFTER passing an open-sided counter-relief.
            levels = sorted({round(v.Point.z, 6) for s in (pin, *hosts.values()) for v in s.shape.Vertexes
                             if z0 + EPS < v.Point.z < z1 - EPS} | {z0, z1})
            heights = [(a + b) / 2 for a, b in zip(levels, levels[1:]) if b - a > EPS * 4]
            for z in heights:
                circles = sections(pin, 2, z)
                if circles:
                    shaft.append(max(circles, key=lambda it: it[1]))
            if not shaft or len(shaft) != len(heights):
                emit('REVIEW', 'service-base screw', name, detail='Could not identify outer screw sections in installed unit axes')
                continue
            head = max(r for _, r in shaft)
            for host in hosts:
                samples = []
                for p, r in shaft:
                    possible = [(q, bore) for q, bore in bores(host, p[2])
                                if bore <= 2 * head and np.linalg.norm((q - p)[:2]) < 2 * head]
                    if not possible:
                        continue  # may be outside this holder at one end of the screw
                    q, bore = min(possible, key=lambda it: np.linalg.norm((it[0] - p)[:2]))
                    delta = q - p
                    samples.append((bore - r - np.linalg.norm(delta[:2]), delta, p, r, bore))
                if not samples:
                    emit('REVIEW', 'service-base screw', name, host,
                         detail='No corresponding finished bore around any measured section; no capture asserted.')
                    continue
                margin, delta, point, r, bore = min(samples, key=lambda v: v[0])
                emit('CAPTURED' if margin >= -EPS else 'RADIAL_CLASH', 'service-base screw', name, host,
                     frame.point(point), frame.direction(unit(delta)), 'limiting sampled radial margin mm', margin,
                     detail=f'{len(samples)}/{len(shaft)} sections between real axial shoulders met a full bore of this holder; '
                     f'open-sided regions are not circular registers. R(screw/bore)={r:.4f}/{bore:.4f} mm; '
                     'separate material-common test; no thread, torque or service travel inferred.')
    # No extra copies of the four integral light tabs/catch are manufactured by
    # the checker. Full installed parent-material pair commons are in scope.
    return [(leaves[a], leaves[b]) for a, b in (('MechServiceBaseInsert', 'MechUpperFairing'),
            ('MechServiceBaseGasket', 'MechHeaterCarrier'), ('MechTopBridge', 'MechUpperFairing'),
            ('MechTopBridge', 'MechLightRing')) if a in leaves and b in leaves]
