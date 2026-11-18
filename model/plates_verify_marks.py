"""Read open cutting-plane strokes from actual SVG and PDF page coordinates."""

import re

import numpy as np


MM = 25.4 / 72
SVG = '{http://www.w3.org/2000/svg}'
EXPECTED = {
    'assembly-section': 'А', 'upper-section': 'Б', 'upper-battery-seat': 'В',
    'upper-retention': 'ИЛН', 'lower-assembly': 'А', 'fascia-assembly': 'А',
    'front-film': 'А', 'pod-assembly': 'А', 'pod-cup': 'А', 'pod-screen': 'А',
    'pod-lid': 'А', 'heater-guard': 'А',
}


def _near(p, q):
    return np.linalg.norm(p - q) < .006


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _one_line(item):
    first, second = item[1:3]
    return np.asarray((tuple(first), tuple(second))) * MM


def check_marks(root, drawings, sheet_id):
    """Verify 10.0×0.70 paper marks, 2.5 mm arrow tip and unchanged pair direction.

    The SVG identifies the semantic role. The PDF must independently have the
    stroke at the same coordinates, an actual perpendicular arrow shank, and
    a filled arrowhead whose vertex ends on it. Ordinary axes, dimensions and
    single view-direction arrows do not count as cutting-plane marks.
    """
    groups = {g.get('id'): g for g in root.iter(SVG+'g') if g.get('id', '').startswith('cut-')}
    expected = {f'cut-{ord(letter):04x}-{side}' for letter in EXPECTED.get(sheet_id, '')
                for side in (1, 2)}
    _check(set(groups) == expected, sheet_id + ': missing or extra open cutting-plane mark')
    if not groups:
        return []
    lines, shanks, heads = [], [], []
    for d in drawings:
        items = d['items']
        if len(items) == 1 and items[0][0] == 'l' and d.get('color') is not None:
            pen = (d['width'] or 0) * MM
            if abs(pen - .70) < .002 or abs(pen - .25) < .002:
                pair = _one_line(items[0])
                length = np.linalg.norm(pair[1] - pair[0])
                if abs(pen - .70) < .002 and abs(length - 10.) < .01:
                    lines.append(pair)
                elif abs(pen - .25) < .002 and abs(length - 9.) < .01:
                    shanks.append(pair)
        elif d.get('fill') is not None and len(items) == 3 and all(i[0] == 'l' for i in items):
            heads.append(np.asarray([tuple(i[1]) for i in items]) * MM)
    marks = []
    for key, g in sorted(groups.items()):
        path = g.find(SVG+'path')
        name = f'{sheet_id}/{key}'
        _check(path is not None, name + ': absent SVG stroke')
        data = path.get('d', '').split()
        _check(len(data) == 6 and data[0] == 'M' and data[3] == 'L', name + ': not one SVG stroke')
        ends = np.asarray([data[1:3], data[4:6]], dtype=float) * MM
        start, end = ends
        ink = re.search(r'stroke-width\s*:\s*([+\d.eE-]+)', path.get('style', ''))
        _check(ink and abs(float(ink[1]) * MM - .7) < .002, name + ': wrong SVG pen')
        _check(abs(np.linalg.norm(end-start)-10) < .004, name + ': wrong SVG stroke length')
        matching = [pair for pair in lines if _near(pair[0], start) and _near(pair[1], end)]
        _check(len(matching) == 1, name + ': PDF and SVG strokes disagree')
        tip = start + .25 * (end - start)
        arrows = [pair for pair in shanks if _near(pair[1], tip)]
        _check(len(arrows) == 1, name + ': 2.5 mm inset or arrow shank absent in PDF')
        tail, actual = arrows[0]
        axis = (end-start) / np.linalg.norm(end-start)
        look = (actual-tail) / np.linalg.norm(actual-tail)
        _check(abs(look @ axis) < .001, name + ': wrong arrow direction relative to section')
        triangles = [pts for pts in heads if any(_near(v, actual) for v in pts)]
        _check(len(triangles) == 1, name + ': missing actual filled arrowhead')
        marks.append(dict(key=key, start=start.tolist(), end=end.tolist(), tail=tail.tolist(),
                          tip=actual.tolist(), direction=look.tolist(),
                          arrowInsetMM=float(np.linalg.norm(actual-start)),
                          lengthMM=float(np.linalg.norm(matching[0][1]-matching[0][0]))))
    for a, b in zip(marks[::2], marks[1::2]):
        _check(a['key'][:-1] == b['key'][:-1], sheet_id + ': unmatched marks')
        _check(_near(np.asarray(a['direction']), np.asarray(b['direction'])),
               sheet_id + ': pair of arrows looks in opposite directions')
        axis = np.asarray(a['end']) - a['start']
        normal = np.array((-axis[1], axis[0])) / np.linalg.norm(axis)
        _check(abs((np.asarray(b['end']) - a['start']) @ normal) < .006,
               sheet_id + ': pair does not lie on the same section trace')
    return marks
