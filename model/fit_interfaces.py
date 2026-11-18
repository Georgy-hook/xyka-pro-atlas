"""Positive assembly checks on actual holes, window sections and named jacket outlets."""

from collections import Counter
import re

import numpy as np
import Part

from fit_geometry import EPS, bounds, box_gap, exact_gap, unit, vec, world, xyz
from fit_frames import Frame

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
    dim and coordinate refer to the already framed BRep. The residual threshold
    identifies a nominal circular model face, not a fit tolerance.
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
    station = wire.stations[0]
    # Modelled in the plug's PCB axes (u,v,w): the open end faces local +v.
    # Use the SAME frame for plug, sleeve and cap; independent placements matter.
    frame = Frame(plug.obj)
    body = frame.solid(plug)
    entry = frame.solid(sleeve)
    p = frame.local_point(station)
    nose = body.box[1, 1]
    throat = circle_sections(body, 1, nose - 0.03)
    receiver = circle_sections(entry, 1, entry.box[:, 1].mean())
    if not throat or not receiver:
        emit('REVIEW', 'plug mouth', wire.name, plug.name, station, detail='Could not identify cylindrical throat or numbered contact sleeve')
        return True
    center = receiver[0][0]
    axis, radius = min(throat, key=lambda t: np.linalg.norm((t[0] - center)[[0, 2]]))
    delta = axis - p
    delta[1] = 0
    radius_wire = wire.obj.Sections[0].Radius.Value
    margin = radius - radius_wire - np.linalg.norm(delta)
    axial = p[1] - nose
    status = 'CAPTURED' if margin >= -EPS and abs(axial) < .01 else 'ANCHOR_GAP'
    emit(status, 'numbered plug mouth', wire.name, plug.name, station, frame.direction(unit(delta)), 'radial margin mm', margin,
         detail=f'{wire.contact} at {sleeve.name}; measured throat R={radius:.3f}, jacket R={radius_wire:.3f}; axis offset={np.linalg.norm(delta):.4f}, cap-to-mouth along plug +v={axial:.4f} mm. No pinout/continuity inferred.')
    if status == 'CAPTURED':
        capture[wire.name, plug.name] = (station, 2.4, 'connector outlet')
        capture[wire.name, sleeve.name] = (station, 2.4, 'connector outlet')
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
            frame = Frame(mate.obj)
            enclosed = frame.solid(mate).box
            local = frame.local_point(p)
            around_outlet = np.all(local >= enclosed[0] - EPS) and np.all(local <= enclosed[1] + EPS)
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
    # Native LCD frame: (u,v) lie in the glass; +w points out at the viewer.
    # Transform the *cover* into this frame, not each part into its own origin:
    # an off-centre / skew cover must still fail the optical registration.
    frame = Frame(glass.obj)
    mask = frame.solid(cover)
    gb, cb = frame.solid(glass).box, mask.box
    center = gb.mean(axis=0)
    center[2] = cb[:, 2].mean()
    # Cut actual cover material with two centre lines. A smaller optical opening than
    # the glass is expected: an inset is mask coverage, not a through-material clash.
    for dim, axis in ((0, 'u'), (1, 'v')):
        p, q = center.copy(), center.copy()
        p[dim], q[dim] = cb[0, dim] - 1, cb[1, dim] + 1
        line = Part.makeLine(vec(p), vec(q))
        trace = mask.shape.common(line)
        intervals = sorted((lo[dim], hi[dim]) for lo, hi in (bounds(e, True) for e in trace.Edges))
        if any(lo + EPS < center[dim] < hi - EPS for lo, hi in intervals):
            emit('BLOCKED_VIEW', 'window section ' + axis, glass.name, cover.name, frame.point(center),
                 detail='Cover material crosses the centre of the glass projection')
            continue
        neg = [hi for _, hi in intervals if hi <= center[dim] + EPS]
        pos = [lo for lo, _ in intervals if lo >= center[dim] - EPS]
        if not neg or not pos:
            emit('REVIEW', 'window section ' + axis, glass.name, cover.name, frame.point(center),
                 detail='Did not identify a bounded opening across the glass centre')
            continue
        left, right = max(neg), min(pos)
        overhang = (left - gb[0, dim], gb[1, dim] - right)
        emit('MASKED_EDGE' if min(overhang) >= -EPS else 'EXPOSED_EDGE', 'window section ' + axis,
             glass.name, cover.name, frame.point(center), frame.direction(np.eye(3)[dim]), 'clear aperture mm', right - left,
             detail=f'Glass coverage at negative/positive {axis} edge: {overhang[0]:.3f}/{overhang[1]:.3f} mm; positive = intentional bezel mask, not a solid overlap. Active pixels unknown.')
    blocked = []
    for fu in (-.40, 0., .40):
        for fv in (-.40, 0., .40):
            u = center[0] + fu * (gb[1, 0] - gb[0, 0])
            v = center[1] + fv * (gb[1, 1] - gb[0, 1])
            p = vec([u, v, max(cb[1, 2], gb[1, 2]) + 1])
            q = [u, v, gb[1, 2]]
            if mask.shape.common(Part.makeLine(p, vec(q))).Length > EPS:
                blocked.append(q)
    emit('REVIEW' if blocked else 'OPEN', 'window sight lines', glass.name, cover.name,
         frame.point(blocked[0] if blocked else [center[0], center[1], gb[1, 2]]), frame.direction((0, 0, -1)),
         'blocked rays of 9', len(blocked), detail='Nine lines along inward LCD normal (−w) from outside to glass through actual service cover; not a test of active image extent.')
    return [(glass, cover)]


def _bore_alignment(a, b, source, target, frame, gap, emit):
    """Sections normal to the finished PCB's local +w. No shank presumed."""
    p, r = source
    q, s = target
    delta = q - p
    delta[2] = 0
    offset = np.linalg.norm(delta)
    side_margin = r - s - offset
    emit('BORES_ALIGNED' if side_margin >= -EPS else 'BORE_OCCLUDED', 'coaxial open bores', a.name, b.name,
         frame.point(q), frame.direction(unit(delta)), 'axis offset in PCB uv mm', offset,
         detail=f'R(A/B)={r:.4f}/{s:.4f}, radial margin for full clear bore B={side_margin:.4f} mm. PCB-frame envelope gap={gap:.4f} mm. No screw inferred.')


def mounts(leaves, boards, emit):
    pairs = []
    main = boards.get('MainPCB')
    carrier = leaves.get('MechCartridgeFrame') or leaves.get('MainBoardBoss')
    if main and carrier:
        frame = Frame(main.obj)
        board, support = frame.solid(main), frame.solid(carrier)
        holes = circle_sections(board, 2, board.box[:, 2].mean())
        pilots = circle_sections(support, 2, support.box[:, 2].mean())
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
            i = min(range(len(pending)), key=lambda j: np.linalg.norm((pending[j][0] - pilot[0])[:2]))
            _bore_alignment(carrier, main, pilot, pending.pop(i), frame, box_gap(support.box, board.box), emit)
        if len(pilots) != len(holes):
            emit('REVIEW', 'carrier bore count', carrier.name, main.name, detail='Mounting openings were not paired one-to-one.')
        pairs.append((carrier, leaves.get('PcMaskRear', main)))
    for letter in 'LR':
        seat = leaves.get('MechDisplaySeat' + letter)
        rim = leaves.get('UiHole' + letter)
        if not seat or not rim:
            continue
        frame = Frame(rim.obj)
        solids = [frame.solid(a) for a in (seat, rim)]
        openings = [circle_sections(a, 2, a.box[:, 2].mean()) for a in solids]
        if all(openings):
            source, target = (min(loops, key=lambda s: s[1]) for loops in openings)
            _bore_alignment(seat, rim, source, target, frame, box_gap(solids[0].box, solids[1].box), emit)
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
        # Separate fixing from the PCB: the bore was constructed along ear-local
        # +Y; the CASE ears need not follow a subsequent UI-only tilt or shift.
        frame = Frame(ear.obj)
        lug = frame.solid(ear)
        ear_loops = circle_sections(lug, 1, lug.box[:, 1].mean())
        if not ear_loops:
            emit('REVIEW', 'case ear', ear.name, detail='Could not measure circular bore')
            continue
        hole, rh = min(ear_loops, key=lambda s: s[1])
        if screw is None:
            emit('OPEN_BORE', 'case ear', ear.name, point=frame.point(hole), metric='open radius mm', value=rh,
                 detail='Visible case ear; no fastener material paired. Not a PCB bore.')
            continue
        pairs.append((screw, ear))
        pin = frame.solid(screw)
        ys = np.linspace(lug.box[0, 1] + .05, lug.box[1, 1] - .05, 3)
        measured = [circle_sections(pin, 1, y) for y in ys]
        if not all(measured):
            q = pin.box.mean(axis=0)
            delta = hole - q
            emit('MISSED_CAPTURE', 'service screw / ear', screw.name, ear.name, frame.point(q), frame.direction(unit(delta)),
                 'centre-to-ear mm', np.linalg.norm(delta), detail='No circular shank at one or more ear-normal sections; vector from installed fastener envelope centre to ear.')
            continue
        margins = []
        for sample in measured:
            center, radius = max(sample, key=lambda s: s[1])
            delta = hole - center
            delta[1] = 0
            margins.append((rh - radius - np.linalg.norm(delta), center, delta, radius))
        margin, point, delta, rad = min(margins, key=lambda m: m[0])
        emit('CAPTURED' if margin >= -EPS else 'RADIAL_CLASH', 'service screw / ear', screw.name, ear.name,
             frame.point(point), frame.direction(unit(delta)), 'radial margin mm', margin,
             detail=f'Three circular shank sections along bore. R(ear)={rh:.3f}, limiting shank R={rad:.3f} mm; no thread or torque claim.')
    if not pairs:
        emit('REVIEW', 'mount inventory', detail='No supported mount interfaces identified')
    return pairs
