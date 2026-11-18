#!/usr/bin/env python3
"""Independent audit of a physical-size ESKD PDF; does not generate or alter a sheet.

    python3 model/verify_eskd.py SHEETS.pdf [--fcstd MODEL.FCStd] [--json REPORT.json]
    python3 model/verify_eskd.py SHEETS.pdf --probes handpicked.json --json REPORT.json

The vendor-independent print profile is stricter than some electronic-document
exceptions. PDF results do not prove material, metrology, legality or signatures.
Exit 0: no deterministic failures in the checks performed (reviews may remain);
1: at least one failure; 2: missing/invalid input. Positive dimension/chain claims
require separately registered vector witnesses, not a renderer-supplied manifest.
"""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import pymupdf as pdf

from verify_eskd_probes import check_chains, check_probes, listed_scale
from verify_eskd_vectors import (AxisLines, HEIGHT, MM, cell_data, sheet_rect,
                                 stamp_candidate)

FORMATS = {'А0': (841, 1189), 'А1': (594, 841), 'А2': (420, 594),
           'А3': (297, 420), 'А4': (210, 297), 'А5': (148, 210)}
RATIO = re.compile(r'([1-9]\d*(?:[.,]\d+)?)\s*:\s*([1-9]\d*(?:[.,]\d+)?)')


def digest(path):
    with path.open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def page_words(page):
    return [(*sheet_rect(page, word[:4]), word[4]) for word in page.get_text('words')]


def scale_value(text):
    match = RATIO.search(text)
    if match:
        a, b = (float(value.replace(',', '.')) for value in match.groups())
        return a / b
    return None


def strip_space(s):
    return ''.join(s.split()).casefold()


def number(s):
    mm = re.findall(r'(?<!\d)\d+(?!\d)', s)
    return int(mm[-1]) if mm else None


def check_page(page, checks, electronic):
    faults, reviews = [], []
    w, h = page.rect.width * MM, page.rect.height * MM
    fmt = next((k for k, dim in FORMATS.items() if
                max(abs(i - j) for i, j in zip(sorted((w, h)), dim)) <= 0.40), None)
    if fmt is None:
        reviews.append('not a standard main format: check an allowed derivative format')
    words = page_words(page)
    text = page.get_text()
    if not words or '\ufffd' in text or not re.search('[А-Яа-яЁё]', text):
        faults.append('no usable searchable Cyrillic text / replacement glyph')
    off_sheet = [row[4] for row in words if min(row[:2]) < -0.4 or
                 row[2] > w + 0.4 or row[3] > h + 0.4]
    if off_sheet:
        faults.append('word boxes outside the displayed page')
    index = AxisLines(page)
    frame = [('h', 5, 20, w - 5), ('v', w - 5, 5, h - 5),
             ('h', h - 5, 20, w - 5), ('v', 20, 5, h - 5)]
    edge = [index.coverage(*line) for line in frame]
    if not all(index.has(*line) for line in frame):
        faults.append('20/5/5/5 mm continuous vector frame absent/incomplete (print profile)')
    candidates = [stamp_candidate(index, w, h, shape) for shape in HEIGHT]
    best = max(candidates, key=lambda unit: (unit.ratio, unit.hits))
    form = best.form if best.ratio >= 0.6 else None
    cells, overhang = {}, {}
    if form is None:
        faults.append('no recognisable vector title block at the printed frame corner')
    else:
        if best.missing:
            faults.append('title-block grid departs from appendix B: see missing local lines')
        cells, overhang = cell_data(best, words)
        if not cells['id'].strip():
            faults.append('designation cell 2 empty or not searchable')
        if form != '2а' and not cells['name'].strip():
            faults.append('name cell 1 empty or not searchable')
        if form == '1' and not (scale_value(cells['scale']) or
                                'см.лист1' in strip_space(cells['scale'])):
            faults.append('scale cell 6 empty / not a ratio or continuation reference')
        if form == '1' and scale_value(cells['scale']) and not listed_scale(scale_value(cells['scale'])):
            faults.append('stamp scale is not in the mechanical scale series (2.302-68 §2/4)')
        if form != '2а' and not cells['issuer'].strip():
            (faults if electronic else reviews).append('originator cell 9 empty: no invented organisation')
        if not cells['version'].strip():
            message = 'version cell 35 empty (required for a DE or its paper copy)'
            (faults if electronic else reviews).append(message)
        if cells.get('signatures', '').strip():
            reviews.append('signature-area text present; verify its authority, do not infer approval')
        if overhang:
            reviews.append('horizontal word boxes protrude from cells; visually inspect print')
    # Recognise the conventional A4 vertical specification header in content only,
    # not «Лист» from the title block. Other lawful forms need manual classification.
    top = ' '.join(row[4] for row in words if row[1] < min(42, h / 3)).casefold()
    spec = all(key in top for key in ('обозначен', 'наименован', 'поз'))
    if fmt == 'А4' and w > h and not spec:
        reviews.append('A4 landscape: only the permitted specification case, not normal A4 drawing')
    rects = [sheet_rect(page, image['bbox']) for image in page.get_image_info()]
    if form:
        def stamp_area(rect):
            x, y, xx, yy = rect
            return max(0, min(xx, w - 5) - max(x, best.x)) * max(0, min(yy, h - 5) - max(y, best.y))
        if any(stamp_area(r) > 80 for r in rects):
            reviews.append('image overlaps title-block area: inspect actual compositing')
    flags = pdf.TEXTFLAGS_DICT & ~pdf.TEXT_PRESERVE_IMAGES
    spans = [s for block in page.get_text('dict', flags=flags)['blocks']
             for line in block.get('lines', []) for s in line['spans'] if s['text'].strip()]
    em = Counter(round(s['size'] * MM, 2) for s in spans)
    results = check_probes(index, words, text, cells, checks, faults, reviews)
    return {'page': page.number + 1, 'paper_mm': [round(w, 3), round(h, 3)], 'format': fmt,
            'frame_edge_coverage_T_R_B_L': [[round(a, 4), round(b, 3)] for a, b in edge],
            'frame_columns': ['covered_fraction', 'largest_gap_mm'], 'form': form,
            'grid_candidates': {c.form: round(c.ratio, 3) for c in candidates},
            'missing_lines_local_mm': best.missing if form else None, 'cells': cells,
            'word_overhang_review': overhang, 'outside_words': off_sheet[:15],
            'possible_specification_header': spec, 'word_count': len(words),
            'reference_note': bool(re.search(r'(?:все\s+)?размеры\s+для\s+справок', text, re.I)),
            'vector_paths': index.paths, 'stroke_width_mm_path_counts': dict(index.widths.most_common(12)),
            'painted_images_mm': [[round(a, 2) for a in r] for r in rects],
            'text_em_mm_counts_not_ink_height': dict(em.most_common(12)),
            'dimension_probes': results, 'failures': faults, 'review': reviews}


def audit(path, source, plan, electronic):
    probes = defaultdict(list)
    for p in plan.get('dimensions', []):
        probes[int(p['page'])].append(p)
    with pdf.open(path) as doc:
        if doc.needs_pass or not doc.is_pdf or not doc.page_count:
            raise ValueError('PDF not accessible, encrypted or empty')
        if set(probes) - set(range(1, len(doc) + 1)):
            raise ValueError('dimension plan references a missing PDF page')
        digest_pdf = digest(path)
        if plan and plan.get('pdf_sha256') != digest_pdf:
            raise ValueError('witness plan must be independently bound to this exact PDF SHA-256')
        rows = [check_page(p, probes[p.number + 1], electronic) for p in doc]
        fonts = {f[0]: f[3] for pg in doc for f in pg.get_fonts()}
        missing_fonts = [name for ref, name in fonts.items() if not doc.extract_font(ref)[3]]
        # Missing base-font embedding is a portability review, not a legal ESKD finding.
        issues, manual = [], []
        if missing_fonts:
            manual.append('fonts without embedded program: ' + ', '.join(missing_fonts))
        meta = ' '.join(str(v or '') for v in doc.metadata.values())
        sha_model = digest(source) if source else None
        fingerprints = re.findall(r'(?<![a-fA-F0-9])[a-fA-F0-9]{64}(?![a-fA-F0-9])', meta)
        if sha_model and sha_model not in fingerprints:
            if fingerprints:
                issues.append('supplied native SHA-256 differs from PDF metadata fingerprints')
            else:
                manual.append('no native SHA-256 in PDF metadata; provenance not established here')
        groups = defaultdict(list)
        for row in rows:
            if row['cells'].get('id'):
                groups[strip_space(row['cells']['id'])].append(row)
        for designation, group in groups.items():
            nums = [number(row['cells'].get('sheet', '')) for row in group]
            totals = [number(row['cells'].get('sheets', '')) for row in group]
            if len(group) > 1 and nums != list(range(1, len(group) + 1)):
                issues.append(f'{designation}: sheet numbers {nums} inconsistent within PDF group')
            if group[0]['form'] == '2а' or any(row['form'] == '2' for row in group[1:]):
                issues.append(f'{designation}: first/continuation form out of order')
            if group[0]['form'] in ('1', '2') and totals[0] != len(group):
                issues.append(f'{designation}: declared sheet total {totals[0]} does not match {len(group)} in PDF')
            for row, total in zip(group[1:], totals[1:]):
                if total is not None and total != len(group):
                    issues.append(f'{designation}: inconsistent total on PDF page {row["page"]}')
        chains = check_chains(rows, issues)
        if not any(row['dimension_probes'] for row in rows):
            manual.append('no registered dimension witnesses; no claim about scale of geometry or dimension chains')
        manual.append(
            'Additional views, arrow direction, shelf-to-spec mapping, hatching, '
            'real glyph height and visual occlusion require direct inspection.'
        )
        failures = sum(len(row['failures']) for row in rows) + len(issues)
        return {'profile': 'independent printed ESKD draft / not certification', 'pdf': str(path.resolve()),
                'pdf_sha256': digest_pdf, 'source_sha256_if_supplied': sha_model,
                'metadata_hashes': fingerprints, 'page_count': len(rows), 'pymupdf_version': pdf.VersionBind,
                'result': 'FAIL' if failures else 'AUTOMATED_CHECKS_ONLY', 'failure_count': failures,
                'issues': issues, 'review': manual, 'checked_chains': chains, 'pages': rows}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('pdf', type=Path)
    cli.add_argument('--fcstd', type=Path, help='optional read-only SHA-256 provenance check')
    cli.add_argument('--probes', type=Path, help='independently registered dimension witnesses in printed mm')
    cli.add_argument('--electronic', action='store_true', help='require DE version in graph 35')
    cli.add_argument('--json', type=Path, help='write evidence JSON (no output path means stdout only)')
    args = cli.parse_args()
    try:
        if args.json and (args.json.suffix.lower() != '.json' or args.json.resolve() in
                          {p.resolve() for p in (args.pdf, args.fcstd, args.probes) if p}):
            raise ValueError('refusing output path: use a separate evidence .json')
        plan = json.loads(args.probes.read_text(encoding='utf-8')) if args.probes else {}
        report = audit(args.pdf, args.fcstd, plan, args.electronic)
        data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        if args.json:
            args.json.write_text(data, encoding='utf-8')
            print(f'{report["result"]}; {report["page_count"]} sheets; '
                  f'{report["failure_count"]} findings; {args.json}')
        else:
            print(data, end='')
        return int(bool(report['failure_count']))
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
        print(f'verify_eskd: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
