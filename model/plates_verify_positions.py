"""Compare positions read from printed shelves against the printed A4 specification cells."""

from collections import defaultdict
from math import hypot

import fitz


MM = 25.4 / 72


def _distance(a, b):
    return hypot(a[0]-b[0], a[1]-b[1])


def _xy(point, height):
    return (point[0]*MM, height-point[1]*MM)


def printed_shelves(page, drawings):
    """Require a physical dot, a continuous leader, a horizontal shelf and raised numeral."""
    height = page.rect.height*MM
    numbers = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                text = span['text'].strip()
                if 16 < span['size'] < 22 and text.isdecimal():
                    bb = fitz.Rect(span['bbox'])
                    numbers.append((int(text), .5*MM*(bb.x0+bb.x1), height-MM*span['origin'][1]))
    dots = []
    for path in drawings:
        box = path['rect']
        if (path['type'] == 'f' and 1.26 < box.width*MM < 1.34 and 1.26 < box.height*MM < 1.34
                and all(item[0] == 'c' for item in path['items'])):
            dots.append(_xy((box.tl+box.br)*.5, height))
    result = []
    for path in drawings:
        edges = path['items']
        if path['type'] != 's' or len(edges) != 2 or not all(e[0] == 'l' for e in edges):
            continue
        start, knee = (_xy(p, height) for p in edges[0][1:3])
        a, end = (_xy(p, height) for p in edges[1][1:3])
        if _distance(knee, a) > .01 or abs(end[1]-knee[1]) > .01 or _distance(knee, end) < 6:
            continue
        matches = [point for point in dots if _distance(start, point) < .015]
        if not matches:
            continue
        cx = (end[0]+knee[0])/2
        raised = [n for n, x, y in numbers if abs(x-cx) < .12 and .5 < y-end[1] < 3.5]
        if len(matches) != 1 or len(raised) != 1:
            raise ValueError(f'Unlabelled or ambiguous position shelf on page {page.number+1} at {start}')
        result.append(dict(position=raised[0], dot=start, elbow=knee, shelf_end=end))
    if len(result) != len(dots):
        raise ValueError(f'An assembly position dot on page {page.number+1} has no numbered shelf')
    return result


def printed_quantities(page, ordinal):
    """Rows of specification form 1/1а, not occurrences of digits anywhere in text."""
    cells = defaultdict(dict)
    bottom, pitch = (45, 8) if ordinal == 1 else (20, 257/32)
    for word in page.get_text('words'):
        x, y = _xy(((word[0]+word[2])/2, (word[1]+word[3])/2), page.rect.height*MM)
        if not bottom < y < 277:
            continue
        col = 'position' if 32 <= x < 40 else 'quantity' if 173 <= x < 183 else None
        if col is not None:
            if not word[4].isdecimal():
                raise ValueError('Nonnumeric printed position/quantity')
            cells[int((277-y)/pitch)][col] = int(word[4])
    if any(set(c) != {'position', 'quantity'} or min(c.values()) < 1 for c in cells.values()):
        raise ValueError('Unpaired printed specification position/quantity')
    return {cell['position']: cell['quantity'] for cell in cells.values()}


def check_coverage(views, specs):
    """Only a document with its own assembly drawing has mandatory local shelves."""
    for code, numbers in views.items():
        expected = set(specs.get(code, {}))
        if not expected or set(numbers) != expected:
            raise ValueError(f'{code}: drawing/specification mismatch; missing {expected-set(numbers)}, '
                             f'extra {set(numbers)-expected}')
    print(f'Local positions: {sum(len(set(v)) for v in views.values())} rows matched on '
          f'{len(views)} assembly documents; {sum(map(len, views.values()))} actual printed shelves')
