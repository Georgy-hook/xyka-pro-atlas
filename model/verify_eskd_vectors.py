"""PDF centreline measurements, in printed millimetres. No renderer imports.

The tests use the *printed-sheet profile* of GOST R 2.104-2023, appendix B.
They do not decide whether the exceptions for an electronic document apply.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import hypot
import re

import pymupdf as pdf

MM = 25.4 / 72
TOL = 0.28  # PDF centreline matching only; never a tolerance on the product
HEIGHT = {'1': 55, '2': 40, '2а': 15}


def sheet_rect(page, box):
    """Reported PDF words/paths use the unrotated page, page.rect does not."""
    return tuple(v * MM for v in (pdf.Rect(box) * page.rotation_matrix))


def black(color):
    return color is not None and sum(color) / len(color) < 0.70


class AxisLines:
    """Index dark stroked centre lines and narrow filled bars, not picture pixels."""

    def __init__(self, page):
        self.bins = defaultdict(list)
        self.widths = Counter()
        self.paths = 0
        self.page = page
        for path in page.get_drawings():
            self.paths += 1
            stroke = 's' in path['type'] and black(path.get('color'))
            stroke = stroke and (path.get('stroke_opacity') or 0) > 0.45
            fill = 'f' in path['type'] and black(path.get('fill'))
            fill = fill and (path.get('fill_opacity') or 0) > 0.45
            if stroke:
                self.widths[round(MM * path['width'], 2)] += 1
                pattern = re.search(r'\[([^\]]*)\]', str(path.get('dashes') or ''))
                # A dashed border can have a single long PDF path: not a solid line.
                if pattern and pattern[1].strip():
                    stroke = False
            for item in path['items']:
                if item[0] == 'l' and stroke:
                    self.line(self.point(item[1]), self.point(item[2]))
                elif item[0] == 're':
                    x, y, x1, y1 = sheet_rect(page, item[1])
                    if stroke:
                        self.rectangle(x, y, x1, y1)
                    elif fill and min(x1 - x, y1 - y) < 1.5:
                        if x1 - x > y1 - y:
                            self.line((x, (y + y1) / 2), (x1, (y + y1) / 2))
                        else:
                            self.line(((x + x1) / 2, y), ((x + x1) / 2, y1))
                elif item[0] == 'qu' and stroke:
                    q = item[1]
                    for a, b in ((q.ul, q.ur), (q.ur, q.lr), (q.lr, q.ll), (q.ll, q.ul)):
                        self.line(self.point(a), self.point(b))

    def point(self, p):
        p = p * self.page.rotation_matrix
        return p.x * MM, p.y * MM

    def rectangle(self, x, y, x1, y1):
        self.line((x, y), (x1, y))
        self.line((x, y1), (x1, y1))
        self.line((x, y), (x, y1))
        self.line((x1, y), (x1, y1))

    def line(self, a, b):
        x, y = a
        u, v = b
        if hypot(x - u, y - v) < 0.35:
            return
        if abs(y - v) <= 0.025:
            axis, pos, ends = 'h', (y + v) / 2, (x, u)
        elif abs(x - u) <= 0.025:
            axis, pos, ends = 'v', (x + u) / 2, (y, v)
        else:
            return
        self.bins[(axis, round(pos * 4))].append((pos, min(ends), max(ends)))

    def coverage(self, axis, pos, start, end):
        start, end = sorted((start, end))
        if end <= start:
            raise ValueError('Zero-length PDF probe')
        intervals = []
        for k in range(round(pos * 4) - 2, round(pos * 4) + 3):
            for center, a, b in self.bins.get((axis, k), ()):
                if abs(pos - center) <= TOL and a < end and b > start:
                    intervals.append((max(a, start), min(b, end)))
        cursor = start
        largest = 0
        covered = 0
        for a, b in sorted(intervals):
            largest = max(largest, a - cursor)
            covered += max(0, b - max(a, cursor))
            cursor = max(cursor, b)
        return covered / (end - start), max(largest, end - cursor)

    def has(self, axis, pos, a, b):
        coverage, gap = self.coverage(axis, pos, a, b)
        return coverage >= 0.94 and gap <= 0.65


def grid(form):
    """Witness lines in stamp-local coordinates: origin at its top left, y down.

    Excludes conditional/dashed fields including those above the stamp.
    The upper 'Вер.' compartment and its actual content are reported separately.
    """
    d = HEIGHT[form]
    top = {'1': 25, '2': 15, '2а': 15}[form]
    legs = [('h', 0, 0, 185), ('v', 0, 0, d), ('v', 7, 0, top)]
    legs += [('v', x, 0, d) for x in (17, 40, 55, 65)]
    legs += [('h', y, 0, 65) for y in range(5, d, 5)]
    if form == '1':
        legs += [('h', 15, 65, 185), ('h', 20, 135, 185), ('h', 35, 135, 185),
                 ('h', 40, 65, 185), ('v', 135, 15, 55), ('v', 140, 20, 35),
                 ('v', 145, 20, 35), ('v', 150, 15, 35), ('v', 167, 15, 35),
                 ('v', 155, 35, 40)]
    elif form == '2':
        legs += [('h', 15, 65, 185), ('h', 20, 135, 185), ('h', 25, 135, 185),
                 ('v', 135, 15, 40), ('v', 140, 20, 25), ('v', 145, 20, 25),
                 ('v', 150, 15, 25), ('v', 165, 15, 25)]
    else:
        legs += [('v', 175, 0, 15), ('h', 5, 175, 185)]
    return legs


@dataclass
class Stamp:
    form: str
    x: float
    y: float
    hits: int
    missing: list

    @property
    def ratio(self):
        return self.hits / (self.hits + len(self.missing))


def stamp_candidate(index, w, h, form):
    x, y = w - 190, h - 5 - HEIGHT[form]
    missing = []
    good = 0
    for axis, p, a, b in grid(form):
        p0, e0 = (y, x) if axis == 'h' else (x, y)
        if index.has(axis, p0 + p, e0 + a, e0 + b):
            good += 1
        else:
            missing.append([axis, p, a, b])
    return Stamp(form, x, y, good, missing)


CELLS = {
    '1': {'id': (65, 0, 175, 15), 'name': (65, 15, 135, 40),
          'material': (65, 40, 135, 55), 'mass': (150, 20, 167, 35),
          'scale': (167, 20, 185, 35), 'sheet': (135, 35, 155, 40),
          'sheets': (155, 35, 185, 40), 'issuer': (135, 40, 185, 55),
          'version': (175, 5, 185, 15), 'signatures': (40, 25, 55, 55)},
    '2': {'id': (65, 0, 175, 15), 'name': (65, 15, 135, 40),
          'sheet': (150, 20, 165, 25), 'sheets': (165, 20, 185, 25),
          'issuer': (135, 25, 185, 40), 'version': (175, 5, 185, 15),
          'signatures': (40, 15, 55, 40)},
    '2а': {'id': (65, 0, 165, 15), 'sheet': (175, 5, 185, 15),
           'version': (165, 5, 175, 15)},
}


def words_in(words, box):
    a, b, c, d = box
    return [row for row in words if a <= (row[0] + row[2]) / 2 < c
            and b <= (row[1] + row[3]) / 2 < d]


def cell_data(stamp, words):
    result, overhang = {}, {}
    for key, (a, b, c, d) in CELLS[stamp.form].items():
        box = (a + stamp.x, b + stamp.y, c + stamp.x, d + stamp.y)
        ww = words_in(words, box)
        result[key] = ' '.join(row[4] for row in ww)
        # Font ascender/descender boxes can overhang with no actual ink outside;
        # report horizontal protrusions only, to be checked on the rendered crop.
        outside = [row[4] for row in ww if row[0] < box[0] - TOL or row[2] > box[2] + TOL]
        if outside:
            overhang[key] = outside
    return result, overhang
