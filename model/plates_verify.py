#!/usr/bin/env python3
"""Check the published ESKD drawing register and its physical, vector, and source invariants.

Run in ordinary Python with PyMuPDF, Pillow and NumPy. --allow-draft checks a
scratch (possibly partial) collection. Passing cannot certify dimensions or
documentation as factory, manufacturing, or measured data.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

import fitz
import numpy as np
from PIL import Image

from plates_eskd_pack import check_page, dimensions_by_document
from plates_verify_marks import check_marks
from plates_verify_positions import check_coverage, printed_quantities, printed_shelves


BASE = Path(__file__).resolve().parents[1]
SVG = {'s': 'http://www.w3.org/2000/svg'}
MM = 25.4 / 72
REQUIRED = {'overall', 'assembly-section', 'assembly-exploded', 'upper-section', 'upper-battery-seat',
            'upper-retention', 'lower-assembly', 'fascia-assembly', 'front-film', 'battery', 'pod-assembly',
            'pod-cup', 'pod-screen', 'pod-lid', 'heater-guard', 'pcb-main-01', 'pcb-main-02',
            'pcb-display-01', 'pcb-display-02', 'index-01', 'spec-product-01', 'spec-upper-01',
            'spec-lower-01', 'spec-pod-01'}


def require(cond, message):
    if not cond:
        raise ValueError(message)


def file_digest(path):
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def svg_mm(text):
    m = re.fullmatch(r'\s*(\d+(\.\d+)?)\s*(pt|mm)\s*', text)
    if not m:
        raise ValueError('SVG size needs explicit physical units, not browser pixels')
    return float(m[1]) * (MM if m[3] == 'pt' else 1)


def _segments(drawings):
    for path in drawings:
        if path.get('color') is None:
            continue
        for item in path['items']:
            if item[0] == 'l':
                yield (item[1].x, item[1].y, item[2].x, item[2].y)
            elif item[0] == 're':
                r = fitz.Rect(item[1])
                for a, b in ((r.tl, r.tr), (r.tr, r.br), (r.br, r.bl), (r.bl, r.tl)):
                    yield (a.x, a.y, b.x, b.y)
            elif item[0] == 'qu':
                # MuPDF reports a closed Matplotlib frame as a quad rather
                # than PDF's special rectangle operator. Preserve its edges.
                q = item[1]
                for a, b in ((q.ul, q.ur), (q.ur, q.lr), (q.lr, q.ll), (q.ll, q.ul)):
                    yield (a.x, a.y, b.x, b.y)


def check_frame(drawings, width, height, where):
    # PDF top-left origin in MuPDF. Each of the four frame rails may contain
    # several adjoining segments, so test interval COVERAGE, not line count.
    seg = np.asarray(list(_segments(drawings)), dtype=float).reshape(-1, 4) * MM
    require(len(seg) >= 16, where + ': missing drawn contours/frame')
    for axis, v, tail, head in [(0, 20., 5., height-5), (0, width-5, 5., height-5),
                                (1, 5., 20., width-5), (1, height-5, 20., width-5)]:
        parallel = seg[(abs(seg[:, axis] - v) < .08) & (abs(seg[:, axis+2] - v) < .08)]
        spans = np.sort(parallel[:, [1-axis, 3-axis]], axis=1)
        cursor = tail
        for lo, hi in spans[np.argsort(spans[:, 0])]:
            if lo <= cursor + .09:
                cursor = max(cursor, hi)
        require(cursor >= head - .09, f'{where}: incomplete or shifted paper frame at {v:g} mm')
    mid = .5 * (seg[:, :2] + seg[:, 2:])
    interior = ((mid[:, 0] > 22) & (mid[:, 0] < width-7)
                & (mid[:, 1] > 21) & (mid[:, 1] < height-61))
    require(interior.sum() >= 7, where + ': empty drawing field above title block')
    return int(interior.sum())


def check_svg(path, code, paper_mm, sha):
    root = ET.parse(path).getroot()
    require(sha in ''.join(e.text or '' for e in root.iter() if e.tag.endswith(('description', 'metadata', 'desc'))),
            path.name + ': missing assembly provenance')
    require(not root.findall('.//s:image', SVG), path.name + ': contains raster artwork')
    require(root.find('.//s:path', SVG) is not None, path.name + ': no vector geometry')
    size = [svg_mm(root.get(name, '')) for name in ('width', 'height')]
    require(np.allclose(size, paper_mm, atol=.03, rtol=0), path.name + ': wrong physical SVG size')
    text = ''.join(''.join(e.itertext()) for e in root.findall('.//s:text', SVG))
    require(''.join(code.split()) in ''.join(text.split()), path.name + ': nonsearchable designation')
    return root


def verify(out, source, allow_draft=False):
    data = json.loads((out/'drawings/index.json').read_text(encoding='utf-8'))
    is_draft = data.get('draft')
    require(is_draft is False or (allow_draft and is_draft is True), 'Expected an issued, not draft, catalog')
    checksum = file_digest(source)
    require(checksum == data['sourceSHA256'], 'Index and FCStd source disagree')
    pdfpath = out / data['pdf']
    require(pdfpath.name == ('XKAH_PRO_A43_drawings_DRAFT.pdf' if is_draft else 'XKAH_PRO_A43_drawings.pdf'),
            'Incorrect primary PDF name')
    require(file_digest(pdfpath) == data['pdfSHA256'], 'PDF and drawing register disagree')
    ids = [row['id'] for row in data['sheets']]
    require(len(ids) == len(set(ids)) == data['pageCount'], 'Duplicate or missing sheet IDs')
    if not is_draft:
        require(REQUIRED <= set(ids), 'Missing required drawing(s): ' + ', '.join(sorted(REQUIRED-set(ids))))
    required_svgs = {row['svg'] for row in data['sheets']}
    actual_svgs = {p.relative_to(out).as_posix() for p in (out/'drawings').glob('*.svg')}
    require(required_svgs == actual_svgs, 'Directory contains a missing, stale, or unindexed SVG')
    with fitz.open(pdfpath) as doc:
        require(len(doc) == len(ids) and checksum in (doc.metadata.get('subject') or ''), 'Wrong PDF source/count')
        bookmarked = [p for lvl, _, p in doc.get_toc() if lvl == 2]
        require(bookmarked == list(range(1, len(doc)+1)), 'Missing sheet index/bookmark targets')
        font_ids = set()
        ref_docs = {}
        drawn_positions, specification = {}, {}
        for page, row in zip(doc, data['sheets']):
            key = row['id']
            require(row['page'] == page.number + 1, f'{key}: index page number disagrees')
            paper = check_page(page, row)
            if row['section'] in ('Механика', 'Печатные платы'):
                ref_docs.setdefault(row['designation'], []).append((row, page.get_text()))
            width, height = (420., 297.) if paper == 'A3' else (210., 297.)
            paths = page.get_drawings()
            if row['designation'].endswith(' СБ'):
                code = row['designation'].removesuffix(' СБ')
                printed = printed_shelves(page, paths)
                drawn_positions.setdefault(code, []).extend(p['position'] for p in printed)
            elif key.startswith('spec-'):
                cells = printed_quantities(page, row['number'])
                existing = specification.setdefault(row['designation'], {})
                require(existing.keys().isdisjoint(cells), key + ': duplicate local specification row')
                existing.update(cells)
            field_segments = check_frame(paths, width, height, key)
            for p in paths:
                for role in ('color', 'fill'):
                    c = p.get(role)
                    if c is not None and len(c) == 3:
                        require(max(c)-min(c) <= .015, f'{key}: coloured presentation graphic in vector sheet')
            font_ids.update(x[0] for x in page.get_fonts())
            for block in page.get_text('blocks'):
                r = fitz.Rect(block[:4])
                require(r.x0 >= -.15 and r.y0 >= -.15 and r.x1 < page.rect.x1+.15
                        and r.y1 < page.rect.y1+.15, key + ': text falls outside paper')
            name = out / row['svg']
            require(file_digest(name) == row['svgSHA256'], name.name + ': file differs from index')
            svg = check_svg(name, row['designation'], (width, height), checksum)
            check_marks(svg, paths, key)
            print(f"{page.number+1:02} {paper}: {key} | {row['designation']} | {field_segments:,} field segments; pure vector")
        dimensions_by_document(ref_docs, partial=is_draft)
        if not is_draft:
            check_coverage(drawn_positions, specification)
        require(font_ids and all(doc.extract_font(xref)[3] for xref in font_ids), 'PDF font not embedded')
    if not is_draft:
        for stem in ('assembly_assembled', 'assembly_exploded', 'electronics'):
            name = out / f'XKAH_PRO_A43_{stem}.png'
            with Image.open(name) as img:
                require(img.mode == 'RGB' and min(img.size) >= 1000, name.name+': not a full RGB render')
                require(img.info.get('CADSourceSHA256') == checksum, name.name+': wrong native revision')
                array = np.asarray(img)[img.height//8:img.height*4//5].astype(np.int16)
                ink = np.abs(array - [241, 244, 241]).max(axis=2) > 18
                require(float(ink.mean()) > .035, name.name+': nearly blank render')
                print(f'{name.name}: {img.width} × {img.height} RGB')
    print(f'PASS: {len(ids)} indexed vector sheets; CAD {checksum}; PDF {data["pdfSHA256"]}')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out', type=Path, default=BASE)
    cli.add_argument('--input', type=Path)
    cli.add_argument('--allow-draft', action='store_true')
    args = cli.parse_args()
    verify(args.out, args.input or args.out / 'XKAH_PRO_A43_rebuilt.FCStd', args.allow_draft)
