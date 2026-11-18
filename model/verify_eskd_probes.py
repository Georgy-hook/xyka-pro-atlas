"""Independent, SHA-bound dimension witnesses and cycle checks for verify_eskd.

A plan has `pdf_sha256` and `dimensions`. Coordinates are *printed millimetres*
from the displayed page's top left. Each dimension has `page`, `name`, `source`
(independent CAD/record and datum), `axis` ('h' or 'v'), `start`, `end` and
`at` (dimension-line ends and transverse ordinate), `model_mm`, `label_box`
[x0,y0,x1,y1], and `label` (e.g. '29,3*'). `scale` defaults to the stamp;
when overridden a `scale_box` for the local scale legend must be supplied.
`extensions`: optional [[start,end],[start,end]], endpoints along each witness
line. `nodes`: optional named pair of model datums, with `view` a stable physical
frame identifier, for a dimension-chain check. Deliberately register a narrow
box only after observing the *actual PDF*. No inference from a sidecar SVG.
"""
from collections import defaultdict
import math
import re

from verify_eskd_vectors import words_in


def norm(text):
    return (''.join(text.casefold().split()).replace(',', '.').replace('ø', '⌀')
            .replace('∅', '⌀').replace('−', '-'))


def ratio(text):
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*:\s*(\d+(?:[.,]\d+)?)', text)
    if not m:
        return None
    n, d = (float(v.replace(',', '.')) for v in m.groups())
    return n / d if n > 0 and d > 0 else None


def listed_scale(value):
    reductions = (2, 2.5, 4, 5, 10, 15, 20, 25, 40, 50, 75, 100, 200, 400, 500, 800, 1000)
    increases = (1, 2, 2.5, 4, 5, 10, 20, 40, 50, 100)
    if any(math.isclose(value, r) for r in increases + tuple(1 / n for n in reductions)):
        return True
    # §4: when needed, (100n):1. §3 is for site master plans, not these parts.
    return value >= 100 and math.isclose(value / 100, round(value / 100))


def box_text(words, box):
    if len(box) != 4 or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError('invalid witness rectangle')
    return ' '.join(w[4] for w in words_in(words, box))


def all_reference(text):
    # A note for starred dimensions is NOT a blanket reference note.
    for m in re.finditer(r'\bразмеры\s+для\s+справок\b', text, re.I):
        if not text[:m.start()].rstrip().endswith('*'):
            return True
    return False


def check_probes(index, words, text, cells, dimensions, faults, reviews):
    output = []
    blanket_reference = all_reference(text)
    for test in dimensions:
        name, source, axis = test['name'], test['source'], test['axis']
        if axis not in ('h', 'v') or not str(source).strip():
            raise ValueError(f'invalid axis or missing independent source for {name}')
        at, a, b, nominal = (float(test[k]) for k in ('at', 'start', 'end', 'model_mm'))
        if not all(map(math.isfinite, (at, a, b, nominal))) or a == b or nominal <= 0:
            raise ValueError(f'degenerate/non-finite witness {name}')
        printed = abs(b - a)
        label_box = test['label_box']
        observed = box_text(words, label_box)
        ok_label = norm(observed) == norm(test['label'])
        scale_note = cells.get('scale', '')
        if 'scale' in test:
            scale_note = box_text(words, test['scale_box'])
            target = ratio(str(test['scale']))
            if target is None or ratio(scale_note) != target:
                faults.append(f'{name}: local scale is not substantiated by the registered legend')
        sc = ratio(scale_note)
        if sc is not None and not listed_scale(sc):
            faults.append(f'{name}: printed scale not in the mechanical scale series of 2.302-68 §2/4')
        value = re.search(r'[-+]?\d+(?:\.\d+)?', norm(observed))
        numeric_ok = False
        if value:
            token = value.group()
            half_lsd = 0.5 * 10 ** -len(token.partition('.')[2])
            numeric_ok = abs(float(token) - nominal) <= half_lsd + 0.001
        coverage, gap = index.coverage(axis, at, a, b)
        line_ok = (coverage > 0.94 and gap <= 0.70)
        if not line_ok and test.get('interrupted_by_number'):
            # Only the gap under the *observed* number is exempt, not arbitrary missing linework.
            l0, l1 = (label_box[0], label_box[2]) if axis == 'h' else (label_box[1], label_box[3])
            lo, hi = sorted((a, b))
            if lo < l0 < l1 < hi:
                line_ok = index.has(axis, at, lo, l0) and index.has(axis, at, l1, hi)
        delta = None if not sc else printed - nominal * sc
        scale_ok = delta is not None and abs(delta) <= 0.35  # paper mm; sampling, not part tolerancing
        if not ok_label or not numeric_ok:
            faults.append(f'{name}: wrong or misplaced printed number (observed {observed!r})')
        if not line_ok:
            faults.append(f'{name}: missing measured vector dimension line')
        if not scale_ok:
            faults.append(f'{name}: printed span does not verify independent nominal × declared scale')
        extensions = []
        if 'extensions' in test:
            if len(test['extensions']) != 2:
                raise ValueError(f'{name}: expected both extension witnesses')
            other = 'v' if axis == 'h' else 'h'
            for foot, ends in zip((a, b), test['extensions']):
                ok = index.has(other, foot, *ends)
                extensions.append(ok)
                if not ok:
                    faults.append(f'{name}: extension line not found at {foot:g} mm')
        elif test.get('nodes'):
            reviews.append(f'{name}: semantic endpoints registered manually; extensions not probed')
        has_star = '*' in observed
        note = bool(re.search(r'\*\s*размеры\s+для\s+справок', text, re.I))
        if has_star and not (note or blanket_reference):
            reviews.append(f'{name}: starred value without a local note; check document requirements')
        result = {'name': name, 'source': source, 'axis': axis, 'observed_label': observed,
                  'label_ok': ok_label and numeric_ok, 'registered_endpoints_mm': [a, b],
                  'paper_mm': round(printed, 4), 'at_mm': at, 'model_mm': nominal,
                  'scale_seen': scale_note, 'delta_paper_mm': None if delta is None else round(delta, 4),
                  'line_coverage': round(coverage, 4), 'max_gap_mm': round(gap, 3),
                  'extensions_verified': extensions, 'reference': blanket_reference or (has_star and note),
                  'verified': bool(ok_label and numeric_ok and line_ok and scale_ok and all(extensions))}
        if 'nodes' in test:
            nodes = test['nodes']
            if len(nodes) != 2 or nodes[0] == nodes[1] or not test.get('view'):
                raise ValueError(f'{name}: use two distinct model datums and an explicit view/frame')
            result.update(nodes=nodes, frame=test['view'])
        output.append(result)
    return output


def check_chains(rows, issues):
    """Flag a closed chain of *driving* dimensions, not a legitimate reference loop."""
    by_view = defaultdict(list)
    for pg in rows:
        for p in pg['dimension_probes']:
            if 'nodes' in p and p['verified']:
                by_view[p['frame'], p['axis']].append(p)
    result = []
    for (frame, axis), probes in by_view.items():
        parent = {}

        def root(node):
            parent.setdefault(node, node)
            while node != parent[node]:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        refs, cycles = [], []
        for p in probes:
            if p['reference']:
                refs.append(p['name'])
                continue
            a, b = (root(n) for n in p['nodes'])
            if a == b:
                cycles.append(p['name'])
            else:
                parent[a] = b
        if cycles:
            issues.append(f'{frame}/{axis}: redundant closed driving chain (2.307-2011 4.13): {cycles}')
        result.append({'frame': frame, 'axis': axis, 'registered_edges': len(probes),
                       'driving_cycle_closures': cycles, 'reference_edges_excluded': refs})
    return result
