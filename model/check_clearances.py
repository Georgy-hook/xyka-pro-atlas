#!/usr/bin/env python3
"""Nominal installed-fit QA, read-only on an existing FreeCAD reconstruction.

R=/Applications/FreeCAD.app/Contents/Resources
PYTHONPATH=$R/lib $R/bin/python model/check_clearances.py path/to/assembly.FCStd --out FIT_CHECK.csv

The default exit code indicates whether the report was written, not whether the
assembly is interference-free. --strict also fails on unresolved/negative findings.
"""

import argparse
from collections import Counter, defaultdict, deque
import csv
import hashlib
from itertools import combinations, product
import os
from pathlib import Path
import sys
import tempfile
import time

import FreeCAD as App
import numpy as np

from fit_geometry import BoundedOCC, EPS, SKIN_GUARD, ProjectedBoxes, box_gap, candidate, installed, vec
from fit_interfaces import MATE_PAIRS, anchors, main_boards, mounts, removable_mates, window
from fit_keymask import membrane_stack, optical_checks
from fit_removables import extra_mates, extra_scope, pack_print_distance
from fit_service import retail, service_scope

MATES = {frozenset(pair) for pair in MATE_PAIRS}

FIELDS = ('status', 'check', 'object_A', 'object_B', 'world_XYZ_mm', 'direction_XYZ',
          'metric', 'value', 'largest_common_mm3', 'interpretation')
ATTENTION = {'INTERFERENCE', 'TRACE_COMMON', 'INTERIOR_WITNESS', 'REVIEW', 'ANCHOR_GAP',
             'BLOCKED_VIEW', 'EXPOSED_EDGE', 'RADIAL_CLASH', 'MISSED_CAPTURE', 'BORE_OCCLUDED', 'SEAT_COMMON',
             'KEY_SIGHT_LEAK', 'STACK_OVERLAP', 'AXIS_OFFSET', 'TRANSFER_GAP'}


def triple(value):
    return '' if value is None else ' '.join(f'{float(x):.4f}' for x in value)


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def phase(text):
    print('=== ' + text, flush=True)


class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, check, a='', b='', point=None, normal=None, metric='', value=None, volume=None, detail=''):
        self.rows.append((status, check, a, b, triple(point), triple(normal), metric,
                          '' if value is None else f'{value:.6g}', '' if volume is None else f'{volume:.7g}', detail))

    def write(self, path):
        with tempfile.NamedTemporaryFile('w', dir=path.parent, newline='', encoding='utf-8-sig', delete=False) as out:
            tmp = Path(out.name)
            writer = csv.writer(out)
            writer.writerow(FIELDS)
            writer.writerows(self.rows)
        os.replace(tmp, path)


def scope(a, b, board_ids):
    groups = {a.group, b.group}
    names = frozenset((a.name, b.name))
    if names in MATES or groups in ({'Pod'}, {'Pod', 'Heater'}) or extra_scope(a, b):
        return 'removable/thermal interface'
    if 'UiKeyMembrane' in names:
        return 'silicone/material'  # the whole sheet, not just the button axes
    if 'MechServiceCover' in names and (a.name.startswith('MechOuterKey') or b.name.startswith('MechOuterKey')):
        return 'cap/cover'
    if a.name.startswith('MechPanelEar') and b.name == a.name.replace('PanelEar', 'ServiceScrew'):
        return 'case ear/screw'
    if b.name.startswith('MechPanelEar') and a.name == b.name.replace('PanelEar', 'ServiceScrew'):
        return 'case ear/screw'
    pcb = groups & {'MainPCB', 'DisplayPCB'}
    if a.contact and b.contact:
        return 'jacket/jacket'
    if a.contact or b.contact:
        other = b if a.contact else a
        return 'jacket/' + other.group
    if groups == {'MainPCB', 'DisplayPCB'}:
        return 'main/display stack'
    if pcb and len(groups) == 2:
        return next(iter(pcb)) + '/' + next(iter(groups - pcb))
    if len(groups) == 1 and pcb and (a.name in board_ids or b.name in board_ids):
        return 'on-board material/' + a.group
    if service_scope(a, b):
        return 'service hardware/material'
    if any(n.startswith(('MechOuterKey', 'MechKeySeat', 'MechKeyCarrier', 'MechCoverWindow')) for n in names):
        return 'fascia/material'
    return None


def _hint_on_failure(a, b, hint, reason, emit, category):
    if hint:
        point = vec(hint['point'])
        shared = a.shape.isInside(point, EPS, False) and b.shape.isInside(point, EPS, False)
        emit('INTERIOR_WITNESS' if shared else 'REVIEW', category, a.name, b.name, hint['point'],
             hint['normal'], 'sample radial gap mm (~)', hint['gap'],
             detail=f'{reason}; ' + ('BRep classifier: point strictly inside both; ' if shared else 'candidate only; ')
             + 'sampled radial envelopes, negative = overlap proxy; vector from B towards A, not an MTD.')
    else:
        emit('REVIEW', category, a.name, b.name, detail=f'{reason}; solid boxes/skin selected pair, no resolved volume.')


def _station_note(a, b, p):
    return ' '.join(f'Near {w.obj.Sections[np.linalg.norm(w.stations - p, axis=1).argmin()].Name}.'
                    for w in (a, b) if w.contact)


def classify_hit(a, b, r, captures):
    status = 'INTERFERENCE' if r['volume'] >= 0.01 else 'TRACE_COMMON'
    note = ''
    names = {a.name, b.name}
    if names in ({'MechDisplaySeatL', 'UiHoleL'}, {'MechDisplaySeatR', 'UiHoleR'},
                 {'MechDisplaySeatL', 'UiLeftHoleInk'}):
        status = 'SEAT_COMMON'
        note = 'Intended bearing location; finite penetration of seat and rim/ink, not flush contact. '
    interface = captures.get((a.name, b.name))
    if interface is not None:
        point, reach, kind = interface
        # An otherwise expected wire/solder pair can still return through it later.
        # Never exempt the entire pair just because the first cap is in the fillet.
        far = np.maximum(abs(np.array(r['hull'][0]) - point), abs(np.array(r['hull'][1]) - point))
        if np.linalg.norm(far) <= reach:
            status = 'INTENDED_SOLDER' if kind == 'named solder' else 'CAPTURE_CANDIDATE'
            note = f'Common confined to {kind} neighbourhood at first cap ({reach:.2f} mm check radius). '
    return status, note


def closest_runs(leaves, occ, known_hits, emit, seconds):
    """Actual BRep minima on the critical routes; prune by conservative AABB bounds.

    A small or zero B-spline common can be ambiguous. A separately computed
    strictly positive distance on the unchanged installed pair is stronger evidence.
    """
    wires = [s for s in leaves.values() if s.contact]
    buzz = [s for s in leaves.values() if s.name in ('PcBuzzer_Body', 'Buzzer')]
    packages = [s for s in leaves.values() if s.group == 'MainPCB' and s.name.endswith('_Body') and s not in buzz]
    families = [('all jacket pairs', combinations(wires, 2)), ('jackets / buzzer', product(wires, buzz)),
                ('jackets / pack well', product(wires, [a for a in leaves.values() if a.name == 'MechPackWell'])),
                ('jackets / battery', product(wires, [a for a in leaves.values() if a.group == 'Battery'])),
                ('jackets / rigid IC and diode bodies', product(wires, packages))]
    deadline = time.monotonic() + seconds
    for label, family in families:
        pairs = sorted(((box_gap(a.box, b.box), a, b) for a, b in family), key=lambda t: (t[0], t[1].name, t[2].name))
        if not pairs:
            continue
        checked = 0
        best = None
        unresolved = []
        for lower, a, b in pairs:
            if best is not None and lower >= best[0]['value']:
                break
            left = deadline - time.monotonic()
            if left <= 0:
                unresolved.append((lower, 'family distance budget'))
                break
            r, err = occ.call('gap', a, b, remaining=left)
            checked += 1
            if err:
                unresolved.append((lower, f'{a.name}/{b.name}: {err}'))
                continue
            if best is None or r['value'] < best[0]['value']:
                best = (r, a, b)
        if best is None:
            emit('REVIEW', label, detail='No resolved nearest BRep pair in distance budget')
            continue
        r, a, b = best
        errors = [err for lower, err in unresolved if lower < r['value']]
        status = 'MIN_GAP'
        if r['value'] <= EPS:
            status = 'CONFIRMED_COMMON' if frozenset((a.name, b.name)) in known_hits else 'REVIEW'
        if errors:
            status = 'REVIEW'
        note = (f'{checked} OCC distances / {len(pairs)} scoped pairs; only pairs whose analytic AABB lower bound '
                'can beat the best need an exact distance. Witness midpoint; direction A → B.')
        if errors:
            note += ' Best resolved upper bound only: ' + '; '.join(errors)
        if status == 'REVIEW' and r['value'] <= EPS:
            note += ' Zero gap, possible tangency or unresolved sliver; not clear.'
        emit(status, label, a.name, b.name, r['point'], r['normal'], 'minimum BRep gap mm', r['value'], detail=note)


def run(path, out, timeout, budget, ink_timeout=20.):
    checksum = digest(path)
    report = Report()
    emit = report.add
    emit('INPUT', 'native assembly', path.name, detail='SHA256 ' + checksum + '; FreeCAD ' + '.'.join(App.Version()[:3]))
    emit('LIMIT', 'reference', detail='Installed X right, Y inward, Z up; mm. Handoff §§5/9, IMG_8920/8918/AD206911: routing, stack and interfaces visible, actual clearances/tolerances not measured. No electrical, thermal, flexible-motion, preload or as-built verification.')
    emit('LIMIT', 'scope', detail='Only registered solids below installed Assembly, including its functional groups in the upper/lower units. No Exploded links, construction history, hidden endpoints or exhaustive all-pairs search. Scoped material checks are counted below.')
    emit('LIMIT', 'method', detail=f'Analytic world and shared PCB-frame boxes of native shapes/solids reject bulk when overlap along any axis <= {EPS:g} mm (may still touch). Mesh AABB and native loft ring screens with ~{SKIN_GUARD:g} mm guard are not exact clearances. Selected actual BRep solid commons; 0.01 mm³ separates trace/bulk reporting only, not an allowable clash.')
    emit('LIMIT', 'witness', detail='For an exact common: point in/on largest connected common; direction and value = local exit from that point to the nearest shell of B, not a minimum translation for all of A. Volume is largest connected solid common, not cumulative compound volume. Unknown/budget/timeouts never count as clear.')
    phase('Read installed material volumes')
    doc = App.openDocument(str(path))
    occ = BoundedOCC(path, timeout)
    try:
        leaves, issues = installed(doc)
        for name, why in issues:
            emit('REVIEW', 'inventory', name, detail=why)
        counts = Counter(s.group for s in leaves.values())
        if not leaves:
            raise RuntimeError('No installed physical solids; refusing empty fit report')
        emit('CHECKED', 'installed inventory', metric='physical leaves', value=len(leaves), detail=str(dict(sorted(counts.items()))))
        boards = main_boards(leaves)
        datum = boards.get('MainPCB') or boards.get('DisplayPCB')
        projected = ProjectedBoxes(datum.obj) if datum else None
        board_ids = {b.name for b in boards.values()} | {'PcMaskFace', 'PcMaskRear'}
        for group in ('MainPCB', 'DisplayPCB'):
            if group not in boards:
                emit('REVIEW', 'substrate identity', group, detail='No unique registered board substrate identified')
        phase('Check named anchors, window and board bores')
        captures = anchors(leaves, emit)
        retail_case = retail(leaves)
        gaps = window(leaves, emit)
        gaps += mounts(leaves, boards, emit)
        gaps += removable_mates(leaves, emit)
        if retail_case or 'MechPodScreen' in leaves or 'MechPackEndContacts' in leaves:
            gaps += extra_mates(leaves, emit)
        phase('Probe three key annuli: occupied first surfaces in six views')
        optical_checks(leaves, emit)
        gaps += membrane_stack(leaves, emit)
        seating = {frozenset((a.name, b.name)) for a, b in gaps if 'Seat' in a.name or 'Frame' in a.name}
        if len(boards) == 2:
            gaps.append((boards['MainPCB'], boards['DisplayPCB']))
        for letter in 'LCR':
            if 'UiPlunger' + letter in leaves and 'MechOuterKey' + letter in leaves:
                gaps.append((leaves['UiPlunger' + letter], leaves['MechOuterKey' + letter]))
                if 'UiKeyMembrane' not in leaves:
                    seating.add(frozenset(('UiPlunger' + letter, 'MechOuterKey' + letter)))
        for group, categories in [('Battery', {'Battery'}), ('Heater/Pod', {'Heater', 'Pod'}),
                                  ('Case', {'Housing', 'Fascia', 'LowerBody', 'LightRing'})]:
            members = [s for s in leaves.values() if s.group in categories]
            for board in boards.values():
                if not members:
                    continue
                one = min(members, key=lambda x: box_gap(board.box, x.box))
                d = box_gap(board.box, one.box)
                emit('BOUND', 'subsystem/substrate', board.name, one.name, metric='AABB lower bound mm', value=d,
                     detail=f'Conservative minimum box-gap bound over all {group} leaves to this substrate only. Zero is inconclusive; exact gap requested for named candidate.')
                gaps.append((board, one))
        phase(f'Screen scoped pairs of {len(leaves)} installed leaves')
        stats = defaultdict(Counter)
        jobs = defaultdict(list)
        for a, b in combinations(sorted(leaves.values(), key=lambda s: s.name), 2):
            category = scope(a, b, board_ids)
            if not category:
                continue
            if b.contact and not a.contact:
                a, b = b, a
            method, pairs, hint = candidate(a, b, projected)
            if not pairs:
                stats[category][method] += 1
            else:
                priority = (0 if (a.name, b.name) in captures or a.name in board_ids or b.name in board_ids
                            else 1 if 'buzz' in (a.name + b.name).lower() else 2)
                jobs[category].append((priority, hint['gap'] if hint else 0, a, b, pairs, hint))
        njobs = sum(map(len, jobs.values()))
        phase(f'Exact BRep checks: {njobs} shortlisted pairs; per-operation timeout {timeout:g} s')
        # Round-robin categories: a cluster of sensitive near-tangent wire booleans
        # must not consume the whole exact budget before the rigid fits are checked.
        queues = {k: deque(sorted(v, key=lambda j: (j[0], j[1], j[2].name, j[3].name))) for k, v in jobs.items()}
        deadline = time.monotonic() + budget
        wire_spent = 0.
        nonclear = set()
        hits = set()
        while any(queues.values()):
            for category, queue in queues.items():
                if not queue:
                    continue
                _, _, a, b, pairs, hint = queue.popleft()
                remaining = deadline - time.monotonic()
                if category == 'jacket/jacket':
                    remaining = min(remaining, budget * 0.35 - wire_spent)
                if remaining <= 0:
                    r, reason = None, 'Selected exact-work budget exhausted'
                else:
                    start = time.monotonic()
                    r, reason = occ.call('common', a, b, pairs, hint, remaining)
                    if category == 'jacket/jacket':
                        wire_spent += time.monotonic() - start
                if reason:
                    nonclear.add(frozenset((a.name, b.name)))
                    stats[category]['unresolved common'] += 1
                    _hint_on_failure(a, b, hint, reason, emit, category)
                elif not r:
                    stats[category]['exact no bulk'] += 1
                else:
                    nonclear.add(frozenset((a.name, b.name)))
                    hits.add(frozenset((a.name, b.name)))
                    status, note = classify_hit(a, b, r, captures)
                    note += f"{r['count']} connected material common(s). " + _station_note(a, b, r['point'])
                    stats[category][status] += 1
                    emit(status, category, a.name, b.name, r['point'], r['normal'], 'local B exit mm', r['value'], r['volume'], note.strip())
        phase('Measure selected material-to-material gaps and write coverage')
        seen = set()
        gap_end = time.monotonic() + min(40, budget / 3)
        ink_left = 3 * ink_timeout  # separate cap; never take time from ordinary fits or commons
        for a, b in gaps:
            key = tuple(sorted((a.name, b.name)))
            if key in seen:
                continue
            seen.add(key)
            if pack_print_distance(a, b):
                start = time.monotonic()
                r, reason = (occ.call('split_gap', a, b, remaining=ink_left, operation_timeout=ink_timeout)
                             if ink_left > 0 else (None, 'Selected lettering distance budget exhausted'))
                elapsed = time.monotonic() - start
                ink_left -= elapsed
                gap_end += elapsed
            else:
                remaining = gap_end - time.monotonic()
                r, reason = occ.call('gap', a, b, remaining=remaining) if remaining > 0 else (None, 'Distance-work budget exhausted')
            if reason:
                emit('REVIEW', 'selected distance', a.name, b.name, detail=reason)
            else:
                status = 'NEAR' if r['value'] <= EPS else 'GAP'
                detail = 'Nearest BRep witnesses; midpoint and direction A → B. Zero alone is not proof of a seated joint.'
                if 'checked' in r:
                    detail += (f" Exact connected-solid distances: {r['checked']}/{r['possible']}; "
                               f"only AABB lower bounds prune. Limiting subshapes: Solid{r['solid_a']} / Solid{r['solid_b']}.")
                if status == 'NEAR' and frozenset(key) in seating and frozenset(key) not in nonclear:
                    status = 'NOMINAL_SEAT'
                    detail = 'Intended mating faces touch in the shown position, no detected bulk. No preload, travel, or measured fit inferred.'
                emit(status, 'selected distance', a.name, b.name,
                     r['point'], r['normal'], 'BRep gap mm', r['value'],
                     detail=detail)
        phase('Bound and measure actual critical jacket minima')
        closest_runs(leaves, occ, hits, emit, min(55, budget / 2))
        for category, stats_row in sorted(stats.items()):
            emit('COVERAGE', category, metric='scoped leaf pairs', value=sum(stats_row.values()),
                 detail='; '.join(f'{k}={v}' for k, v in sorted(stats_row.items())))
        if digest(path) != checksum:
            raise RuntimeError('Input FCStd changed during the run; no report published. Rerun on stable file.')
        report.write(out)
    finally:
        occ.close()
        App.closeDocument(doc.Name)
    findings = Counter(r[0] for r in report.rows if r[0] in ATTENTION)
    print(f'{out}: {len(report.rows)} rows; attention: {dict(findings)}', flush=True)
    return bool(findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('assembly', type=Path)
    parser.add_argument('--out', type=Path, help='default: FIT_CHECK.csv beside input')
    parser.add_argument('--pair-timeout', type=float, default=4., help='OCC seconds per selected pair')
    parser.add_argument('--ink-timeout', type=float, default=20., help='seconds per exact glyph/well distance; separate pool is 3× this value')
    parser.add_argument('--budget', type=float, default=120., help='seconds for exact commons; selected distances have separate capped budget')
    parser.add_argument('--strict', action='store_true', help='exit nonzero on negative/unresolved findings')
    args = parser.parse_args()
    path = args.assembly.resolve(strict=True)
    out = (args.out or path.with_name('FIT_CHECK.csv')).resolve()
    if path.suffix.lower() != '.fcstd' or out.suffix.lower() != '.csv' or min(args.pair_timeout, args.budget, args.ink_timeout) <= 0:
        parser.error('Expected a native FCStd, CSV output and positive time limits')
    problems = run(path, out, args.pair_timeout, args.budget, args.ink_timeout)
    return int(args.strict and problems)


if __name__ == '__main__':
    sys.exit(main())
