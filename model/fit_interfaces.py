"""Positive assembly checks on actual holes, window sections and named jacket outlets."""

from collections import Counter
import re

import numpy as np
import Part

from fit_geometry import EPS, bounds, box_gap, exact_gap, unit, vec, world, xyz

LOWER = ('B+', 'B-', 'F+', 'F-', 'Clear1', 'Clear2', 'GND', 'KEY+', 'S-', 'S+')
UPPER = ('RGB1', 'RGB2', 'RGB3', 'RGB4')


def main_boards(leaves):
    boards = {}
    for group, names in [('MainPCB', ('PcLaminateCore', 'MainSubstrate')),
                         ('DisplayPCB', ('UiSubstrate',))]:
        choices = [a for a in leaves.values() if a.group == group]
        known = next((leaves[n] for n in names if n in leaves and leaves[n].group == group), None)
        if known is None:
            # Refuse to guess from largest bounding box alone (e.g. an ink compound).
            candidates = [a for a in choices if 'substrate' in a.name.lower()
                          or (a.obj.TypeId == 'PartDesign::Body' and re.search(r'FR.?4|ламинат', a.obj.Label, re.I))]
            if len(candidates) == 1:
                known = candidates[0]
        if known:
            boards[group] = known
    return boards


def norm_contact(s):
    return re.sub('[^a-z0-9]', '', s.lower().replace('+', 'plus').replace('-', 'minus'))


def named_anchor(a, contact):
    n = norm_contact(a.name)
    key = norm_contact(contact)
    return a.group == 'MainPCB' and any(n.endswith(stem + key) for stem in ('solder', 'joint', 'fillet'))


def circle_sections(a, dim, coordinate):
    """Measure near-circular OCC section loops (Part::Scale may turn circles into splines).

    Reject open/scalloped/rectangular sections, even when their x and z spans match.
    The residual threshold identifies a nominal circular model face, not a tolerance.
    """
    planar = [i for i in range(3) if i != dim]
    loops = a.shape.slice(vec(np.eye(3)[dim]), float(coordinate))
    circles = []
    for loop in loops:
        if not loop.isClosed():
            continue
        pts = np.array([xyz(p)[planar] for p in loop.discretize(Number=33)[:-1]])
        mean = pts.mean(axis=0)
        local = pts - mean
        mat = np.column_stack([local * 2, np.ones(len(pts))])
        center = np.linalg.lstsq(mat, np.sum(local * local, axis=1), rcond=None)[0][:2] + mean
        radius = np.linalg.norm(pts - center, axis=1)
        if np.ptp(radius) > 0.008 or abs(loop.Length / (2 * np.pi) - np.mean(radius)) > 0.008:
            continue
        p = np.full(3, float(coordinate))
        p[planar] = center
        circles.append((p, float(np.mean(radius))))
    return circles


def _rgb_mouth(leaves, wire, emit, capture):
    number = wire.contact[3:]
    plug = leaves.get('PcRGBPlugBody')
    sleeve = leaves.get('PcRGBEntry' + number)
    if plug is None or sleeve is None:
        return False
    p = wire.stations[0]
    # Open throat faces +v = installed +Z. Slice just behind its mouth, not
    # through the relieved pick slots or along a polygonal silhouette.
    throat = circle_sections(plug, 2, plug.box[1, 2] - 0.03)
    receiver = circle_sections(sleeve, 2, np.mean(sleeve.box[:, 2]))
    if not throat or not receiver:
        emit('REVIEW', 'plug mouth', wire.name, plug.name, p, detail='Could not identify cylindrical throat or numbered contact sleeve')
        return True
    center = receiver[0][0]
    axis, radius = min(throat, key=lambda t: np.linalg.norm(t[0][:2] - center[:2]))
    delta = axis - p
    delta[2] = 0
    radius_wire = wire.obj.Sections[0].Radius.Value
    margin = radius - radius_wire - np.linalg.norm(delta)
    axial = p[2] - plug.box[1, 2]
    status = 'CAPTURED' if margin >= -EPS and abs(axial) < .01 else 'ANCHOR_GAP'
    emit(status, 'numbered plug mouth', wire.name, plug.name, p, unit(delta), 'radial margin mm', margin,
         detail=f'{wire.contact} at {sleeve.name}; measured throat R={radius:.3f}, jacket R={radius_wire:.3f}; axis offset={np.linalg.norm(delta):.4f}, cap-to-mouth Z={axial:.4f} mm. No pinout/continuity inferred.')
    if status == 'CAPTURED':
        capture[wire.name, plug.name] = (p, 2.4, 'connector outlet')
        capture[wire.name, sleeve.name] = (p, 2.4, 'connector outlet')
    return True


def anchors(leaves, emit):
    """Map only identified sockets/joints. Nearest *unidentified* solder is not an electrical match."""
    wires = [a for a in leaves.values() if a.contact]
    counts = Counter(a.contact for a in wires)
    expected = set(LOWER + UPPER)
    if counts != Counter(LOWER + UPPER):
        emit('REVIEW', 'wire inventory', detail=f'Expected one each: {LOWER + UPPER}; found {dict(counts)}')
    else:
        emit('CHECKED', 'wire inventory', detail='10 named soldered jackets + four lighting strands, one of each. No hidden end/net inferred.')
    capture = {}
    for wire in sorted(wires, key=lambda w: w.contact):
        key = wire.contact
        if key not in expected or not getattr(wire.obj, 'Sections', None):
            emit('REVIEW', 'anchor', wire.name, detail='Unknown contact or no native sections')
            continue
        first = wire.obj.Sections[0]
        p = wire.stations[0]
        circle = world(first)
        cap = Part.Face(Part.Wire(circle.Edges))
        rgb = key in UPPER
        if rgb and _rgb_mouth(leaves, wire, emit, capture):
            continue
        if rgb:
            candidates = [leaves['RGBConnector']] if 'RGBConnector' in leaves else []
        else:
            candidates = [a for a in leaves.values() if named_anchor(a, key)]
        if not candidates:
            emit('REVIEW', 'anchor', wire.name, point=p, detail=f'{key}: no identified matching material in MainPCB')
            continue
        results = []
        for a in candidates:
            inside = any(s.shape.isInside(vec(p), EPS, False) for s in a.solids)
            r = dict(value=0., point=p.tolist(), normal=None) if inside else exact_gap(cap, a.shape)
            results.append((r['value'], a.name, a, r, inside))
        d, _, mate, r, inside = min(results, key=lambda z: z[:2])
        reach = max(2.4, 3.0 * first.Radius.Value)
        if rgb:
            # Identify containment in a relieved socket separately from solder/material contact.
            around_outlet = any(np.all(p >= a.box[0] - EPS) and np.all(p <= a.box[1] + EPS) for a in candidates)
            status = 'CAPTURE_CANDIDATE' if around_outlet or d <= EPS else 'ANCHOR_GAP'
            note = 'connector outlet; proximity/envelope does not establish engagement, pin identity or continuity'
            if status != 'ANCHOR_GAP':
                for a in candidates:
                    capture[wire.name, a.name] = (p, reach, 'connector outlet')
        else:
            status = 'SEATED' if d <= EPS else 'ANCHOR_GAP'
            note = 'first cap centre inside its named solder' if inside else 'first cap to its named solder; shortest BRep gap'
            if status == 'SEATED':
                capture[wire.name, mate.name] = (p, reach, 'named solder')
        emit(status, 'anchor', wire.name, mate.name, p, r['normal'], 'cap/material gap mm', d,
             detail=f'{key}; {note}. Witness = first native station centre.')
    return capture


def window(leaves, emit):
    glass = leaves.get('UiGlass')
    cover = next((leaves[n] for n in ('MechServiceCover', 'FaceCassette') if n in leaves), None)
    if glass is None or cover is None:
        emit('REVIEW', 'window', detail='Glass or registered service cover not identified')
        return []
    gb, cb = glass.box, cover.box
    center = gb.mean(axis=0)
    center[1] = cb[:, 1].mean()
    # Cut actual cover material with two centre lines. A smaller optical opening than
    # the glass is expected: an inset is mask coverage, not a through-material clash.
    for dim, axis in ((0, 'X'), (2, 'Z')):
        p, q = center.copy(), center.copy()
        p[dim], q[dim] = cb[0, dim] - 1, cb[1, dim] + 1
        line = Part.makeLine(vec(p), vec(q))
        trace = cover.shape.common(line)
        intervals = sorted((lo[dim], hi[dim]) for lo, hi in (bounds(e, True) for e in trace.Edges))
        if any(lo + EPS < center[dim] < hi - EPS for lo, hi in intervals):
            emit('BLOCKED_VIEW', 'window section ' + axis, glass.name, cover.name, center,
                 detail='Cover material crosses the centre of the glass projection')
            continue
        neg = [hi for _, hi in intervals if hi <= center[dim] + EPS]
        pos = [lo for lo, _ in intervals if lo >= center[dim] - EPS]
        if not neg or not pos:
            emit('REVIEW', 'window section ' + axis, glass.name, cover.name, center,
                 detail='Did not identify a bounded opening across the glass centre')
            continue
        left, right = max(neg), min(pos)
        mask = (left - gb[0, dim], gb[1, dim] - right)
        emit('MASKED_EDGE' if min(mask) >= -EPS else 'EXPOSED_EDGE', 'window section ' + axis,
             glass.name, cover.name, center, np.eye(3)[dim], 'clear aperture mm', right - left,
             detail=f'Glass coverage at negative/positive {axis} edge: {mask[0]:.3f}/{mask[1]:.3f} mm; positive = intentional bezel mask, not a solid overlap. Active pixels unknown.')
    blocked = []
    for fx in (-.40, 0., .40):
        for fz in (-.40, 0., .40):
            x = center[0] + fx * (gb[1, 0] - gb[0, 0])
            z = center[2] + fz * (gb[1, 2] - gb[0, 2])
            p = vec([x, min(cb[0, 1], gb[0, 1]) - 1, z])
            q = vec([x, gb[0, 1], z])
            if cover.shape.common(Part.makeLine(p, q)).Length > EPS:
                blocked.append((x, gb[0, 1], z))
    emit('REVIEW' if blocked else 'OPEN', 'window sight lines', glass.name, cover.name,
         blocked[0] if blocked else [center[0], gb[0, 1], center[2]], (0, 1, 0), 'blocked rays of 9', len(blocked),
         detail='Nine lines from outside (-Y) to glass face through actual service cover; not a test of active image extent.')
    return [(glass, cover)]


def _bore_alignment(a, b, source, target, emit):
    """No shank presumed: does the larger coaxial opening expose the smaller one?"""
    p, r = source
    q, s = target
    delta = q - p
    delta[1] = 0
    offset = np.linalg.norm(delta)
    side_margin = r - s - offset
    gap = box_gap(a.box, b.box)
    emit('BORES_ALIGNED' if side_margin >= -EPS else 'BORE_OCCLUDED', 'coaxial open bores', a.name, b.name,
         q, unit(delta), 'axis offset XZ mm', offset,
         detail=f'R(A/B)={r:.4f}/{s:.4f}, radial margin for full clear bore B={side_margin:.4f} mm. Envelope gap={gap:.4f} mm. No screw inferred.')


def mounts(leaves, boards, emit):
    pairs = []
    main = boards.get('MainPCB')
    carrier = leaves.get('MechCartridgeFrame') or leaves.get('MainBoardBoss')
    if main and carrier:
        holes = circle_sections(main, 1, main.box[:, 1].mean())
        pilots = circle_sections(carrier, 1, carrier.box[:, 1].mean())
        if carrier.name == 'MainBoardBoss':
            pilots = sorted(pilots, key=lambda s: s[1])[:1]
        else:
            # Do not accidentally pair a solder drill with a carrier through-bore.
            dia = float(main.obj.Document.Parameters.BoardMountDia.Value)
            holes = [h for h in holes if abs(2 * h[1] - dia) < 0.008]
        if not pilots or not holes or (carrier.name == 'MechCartridgeFrame' and len(holes) != 4):
            emit('REVIEW', 'carrier holes', carrier.name, main.name,
                 detail=f'Found {len(pilots)} carrier bores and {len(holes)} identified board mounting holes.')
        pending = list(holes)
        for pilot in pilots:
            if not pending:
                break
            i = min(range(len(pending)), key=lambda j: np.linalg.norm((pending[j][0] - pilot[0])[[0, 2]]))
            _bore_alignment(carrier, main, pilot, pending.pop(i), emit)
        if len(pilots) != len(holes):
            emit('REVIEW', 'carrier bore count', carrier.name, main.name, detail='Mounting openings were not paired one-to-one.')
        pairs.append((carrier, leaves.get('PcMaskRear', main)))
    for letter in 'LR':
        seat = leaves.get('MechDisplaySeat' + letter)
        rim = leaves.get('UiHole' + letter)
        if not seat or not rim:
            continue
        openings = [circle_sections(a, 1, a.box[:, 1].mean()) for a in (seat, rim)]
        if all(openings):
            _bore_alignment(seat, rim, *(min(loops, key=lambda s: s[1]) for loops in openings), emit)
        else:
            emit('REVIEW', 'display seat', seat.name, rim.name, detail='Cap or plated bore missing at mid-plane')
        pairs.append((seat, rim))
    # Rims on the housing are not PCB holes. Only the two upper ears have a
    # registered illustrated fastener. Inspect three sections along each bore.
    for suffix in ('TopL', 'TopR', 'SideR', 'Foot'):
        ear = leaves.get('MechPanelEar' + suffix)
        screw = leaves.get('MechServiceScrew' + suffix)
        if ear is None:
            continue
        ear_loops = circle_sections(ear, 1, ear.box[:, 1].mean())
        if not ear_loops:
            emit('REVIEW', 'case ear', ear.name, detail='Could not measure circular bore')
            continue
        hole, rh = min(ear_loops, key=lambda s: s[1])
        if screw is None:
            emit('OPEN_BORE', 'case ear', ear.name, point=hole, metric='open radius mm', value=rh,
                 detail='Visible case ear; no fastener material paired. Not a PCB bore.')
            continue
        pairs.append((screw, ear))
        ys = np.linspace(ear.box[0, 1] + .05, ear.box[1, 1] - .05, 3)
        measured = [circle_sections(screw, 1, y) for y in ys]
        if not all(measured):
            q = screw.box.mean(axis=0)
            delta = hole - q
            emit('MISSED_CAPTURE', 'service screw / ear', screw.name, ear.name, q, unit(delta),
                 'centre-to-ear mm', np.linalg.norm(delta), detail='No circular shank at one or more required Y sections; vector from installed fastener envelope centre to ear.')
            continue
        margins = []
        for sample in measured:
            center, radius = max(sample, key=lambda s: s[1])
            delta = hole - center
            delta[1] = 0
            margins.append((rh - radius - np.linalg.norm(delta), center, delta, radius))
        margin, point, delta, rad = min(margins, key=lambda m: m[0])
        emit('CAPTURED' if margin >= -EPS else 'RADIAL_CLASH', 'service screw / ear', screw.name, ear.name,
             point, unit(delta), 'radial margin mm', margin,
             detail=f'Three circular shank sections along bore. R(ear)={rh:.3f}, limiting shank R={rad:.3f} mm; no thread or torque claim.')
    if not pairs:
        emit('REVIEW', 'mount inventory', detail='No supported mount interfaces identified')
    return pairs
