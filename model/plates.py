#!/usr/bin/env python3
"""Generate the vector-only ESKD collection and three independent CAD PNGs.

Run with FreeCAD's interpreter and PYTHONPATH=$F/lib. For a complete issue:
  model/plates.py --input PRODUCT.FCStd --expect-sha SHA256 --out OUT \
     --pcb-manifest PCB_OUTPUT/pcb-sheets.json --cache SCRATCH
Generate the four board leaves first using the separate native KiCad publisher.
PyMuPDF for lossless joining is supplied by --pdf-python (default: python3 on
PATH), not necessarily by FreeCAD. --draft --only ID ... makes a scratch proof;
its PDF and catalog are explicitly marked as a draft. No GUI state is changed.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from xml.sax.saxutils import escape

from plates_assets import Assets, digest, progress
from plates_eskd_catalog import PCB_IDS, installed, pcb_entries, specifications
from plates_eskd_frame import write_sheet
from plates_eskd_index import with_index
from plates_scene import Scene
from plates_studio import save_posters

BASE = Path(__file__).resolve().parents[1]
PARAMS = []


def build(c):
    """Read-only integration hook. The KiCad output is separate from native CAD."""
    path = Path(c.doc.FileName) if c.doc.FileName else None
    if path is None or not path.is_file():
        raise ValueError('Save the complete FCStd first')
    manifest = getattr(c, 'pcb_manifest', None) or os.environ.get('XKAH_PCB_SHEETS')
    if not manifest:
        raise ValueError('Pass c.pcb_manifest or set XKAH_PCB_SHEETS to the native KiCad sheet manifest')
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--input', str(path),
                    '--out', str(getattr(c, 'root', path.parent)), '--expect-sha', digest(path),
                    '--pcb-manifest', str(manifest)], check=True)


def _selected(a, args):
    entries = installed(a)
    ids = set(args.only or ())
    if not ids or any(i.startswith('spec-') or i == 'kit-note' for i in ids):
        entries += specifications(a)
    if args.pcb_manifest:
        entries += pcb_entries(args.pcb_manifest)
    elif not args.draft or ids.intersection(PCB_IDS):
        raise ValueError('Four source-matched KiCad leaves and --pcb-manifest are required')
    # Place PCB documents after mechanical drawings, before the reconciled A4 specs.
    order = {'Механика': 0, 'Печатные платы': 1, 'Спецификации': 2, 'Поставка': 3}
    entries.sort(key=lambda row: order[row.section])
    if ids:
        missing = ids - {r.id for r in entries}
        if missing:
            raise ValueError(f'Unknown or unavailable sheet(s): {sorted(missing)}')
        entries = [r for r in entries if r.id in ids]
    return with_index(entries)


def _pcb_svg(row, target, sha):
    # Never substitute a native FCStd hash for the actual KiCad geometry source.
    # Keep that generator's SVG and metadata, add a separate enclosing-set credit.
    body = row.original_svg.read_text(encoding='utf-8')
    tail = body.rfind('</svg>')
    if tail < 0:
        raise ValueError(f'{row.id}: invalid KiCad sheet SVG')
    cross = f'<metadata id="drawingSet">Enclosing assembly FCStd SHA-256 {escape(sha)}</metadata>\n'
    target.write_text(body[:tail] + cross + body[tail:], encoding='utf-8')


def _vector_pages(tmp, entries, a, args):
    drawings = tmp / 'drawings'
    drawings.mkdir()
    spool = tmp / 'spool'
    spool.mkdir()
    pages = []
    input_files = {}
    for n, row in enumerate(entries, 1):
        if not re.fullmatch(r'[a-z][a-z0-9-]*', row.id):
            raise ValueError(f'Unsafe sheet id: {row.id}')
        progress(f'Лист {n:02d}/{len(entries)}: {row.id} | {row.designation} | {row.title}')
        svg = drawings / (row.id + '.svg')
        if svg.exists():
            raise ValueError(f'Duplicate sheet id: {row.id}')
        record = dict(id=row.id, title=row.title, designation=row.designation,
                      number=row.number, sheets=row.sheets, section=row.section,
                      svg='drawings/' + svg.name, source_page=row.original_page)
        if row.original_pdf:
            pdf_input = row.original_pdf
            for path in (row.original_pdf, row.original_svg):
                input_files.setdefault(path, digest(path))
            _pcb_svg(row, svg, a.fingerprint)
            record.update(geometrySource='KiCad', sources=row.sources, scale=row.scale)
        else:
            pdf_input = spool / (row.id + '.pdf')
            sheet = row.make()
            try:
                if sheet.designation != row.designation or (sheet.number, sheet.sheets) != (row.number, row.sheets):
                    raise ValueError(f'{row.id}: title block and sheet registry disagree')
                source = 'FCStd: ' + a.scene.src.name + ' | SHA-256 ' + a.fingerprint
                origin = {'Механика': 'FCStd', 'Указатель': 'Drawing register',
                          'Спецификации': 'Installed assembly and position register',
                          'Поставка': 'Regional retail kit and installed configuration'}[row.section]
                if row.section == 'Поставка':
                    record['reference'] = 'https://xyka.pro/xyka-graphite'
                    source = 'Региональная поставка: ' + record['reference'] + ' | установленное изделие: ' + source
                write_sheet(sheet, pdf_input, svg, source=source)
                record.update(paper=sheet.paper, scale=sheet.scale, geometrySource=origin)
            finally:
                sheet.fig.clear()
        record.update(pdf_input=str(pdf_input), svgSHA256=digest(svg))
        pages.append(record)
    pdf = tmp / ('XKAH_PRO_A43_drawings_DRAFT.pdf' if args.draft else 'XKAH_PRO_A43_drawings.pdf')
    recipe = dict(schema=1, draft=args.draft, sourceFile=a.scene.src.name, sourceSHA256=a.fingerprint, pages=pages)
    if args.pcb_manifest:
        recipe['pcbManifestSHA256'] = digest(args.pcb_manifest)
    recipe_path = spool / 'recipe.json'
    recipe_path.write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding='utf-8')
    # An ordinary Python interpreter should not load FreeCAD's binary numpy, etc.
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    subprocess.run([str(args.pdf_python), str(Path(__file__).with_name('plates_eskd_pack.py')),
                    str(recipe_path), str(pdf), str(drawings/'index.json')], check=True, env=env)
    if any(digest(path) != checksum for path, checksum in input_files.items()):
        raise ValueError('A KiCad drawing changed during publication')
    return pdf


def _install(tmp, pdf, out, *, draft):
    # Other jobs own e.g. drawings/FreeCAD_tree.png and photo overlays. Never
    # rename that directory (even briefly); retire only this register's leaves.
    dest = out / 'drawings'
    if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
        raise ValueError('Output drawings is not an ordinary directory')
    dest.mkdir(exist_ok=True)
    index = dest / 'index.json'
    if index.is_symlink():
        raise ValueError('Unexpected linked drawing register')
    previous = json.loads(index.read_text(encoding='utf-8')) if index.is_file() else None
    if previous and draft and not previous.get('draft'):
        raise ValueError('Cannot replace an issued set by a draft')
    old = set()
    if previous:
        for row in previous['sheets']:
            stem = row['id']
            if not re.fullmatch(r'[a-z][a-z0-9-]*', stem) or row['svg'] != f'drawings/{stem}.svg':
                raise ValueError('Invalid prior drawing register')
            p = dest / (stem + '.svg')
            if p.is_symlink() or not p.is_file() or digest(p) != row['svgSHA256']:
                raise ValueError(f'Not overwriting a changed or missing source-matched SVG: {p.name}')
            old.add(p)
        old.add(index)
    if set(dest.glob('*.svg')) - old:
        raise ValueError('Use a clean active SVG set; refusing to remove unindexed legacy drawings')
    pages = [(p, dest / p.name) for p in (tmp/'drawings').glob('*.svg')]
    posters = [(p, out / p.name) for p in tmp.glob('XKAH_PRO_A43_*.png')]
    # Install the index last after the complete PDF, SVGs and PNGs exist.
    releases = [*pages, (pdf, out/pdf.name), *posters, (tmp/'drawings/index.json', index)]
    for _, target in releases:
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError('Unsafe output target: ' + str(target))
        if target.exists():
            if previous is None:
                raise ValueError('Refusing to overwrite an unindexed issue: ' + str(target))
            old.add(target)
    saved = tmp / 'previous'
    saved.mkdir()
    backed_up, installed = [], []
    try:
        for i, old_path in enumerate(sorted(old)):
            backup = saved / str(i)
            os.replace(old_path, backup)
            backed_up.append((backup, old_path))
        for source, target in releases:
            os.replace(source, target)
            installed.append(target)
    except BaseException:
        for target in reversed(installed):
            target.unlink(missing_ok=True)
        for backup, old_path in reversed(backed_up):
            os.replace(backup, old_path)
        raise


def publish(args):
    if args.draft and args.out.resolve() == BASE:
        raise ValueError('Drafts need a separate scratch output directory')
    if args.only and not args.draft:
        raise ValueError('--only is for --draft only')
    if not args.draft and not args.expect_sha:
        raise ValueError('Use --expect-sha <frozen FCStd SHA-256> to issue; otherwise use --draft')
    if args.expect_sha and args.expect_sha.lower() != digest(args.input):
        raise ValueError('Input FCStd SHA-256 does not match the requested frozen revision')
    pcb_digest = digest(args.pcb_manifest) if args.pcb_manifest else None
    if args.expect_pcb_sha and args.expect_pcb_sha.lower() != pcb_digest:
        raise ValueError('Unexpected KiCad sheet manifest; use the verified native PCB output')
    args.out.mkdir(parents=True, exist_ok=True)
    scene = Scene(args.input)
    try:
        if not scene.structured:
            raise ValueError('A retail Assembly with the actual upper/lower units is required; no legacy-album fallback')
        a = Assets(scene, cache=args.cache)
        entries = _selected(a, args)
        progress(f'{len(entries)} листов; физических объектов {len(scene.items)}; FCStd SHA-256 {a.fingerprint}')
        if args.list_sheets:
            for j, row in enumerate(entries, 1):
                print(f'{j}\t{row.id}\t{row.designation}\t{row.number}/{row.sheets}\t{row.title}')
            return
        with tempfile.TemporaryDirectory(prefix='eskd-publish-', dir=args.out) as work:
            tmp = Path(work)
            pdf = _vector_pages(tmp, entries, a, args)
            if not args.draft:
                progress('Три отдельные инженерные PNG (не часть чертежей)')
                save_posters(a, tmp)
            if digest(scene.src) != a.fingerprint or (pcb_digest and digest(args.pcb_manifest) != pcb_digest):
                raise ValueError('Input sources changed during publication; set not issued')
            _install(tmp, pdf, args.out, draft=args.draft)
        progress(f'Записано: {args.out / pdf.name}; {len(entries)} SVG и индекс')
    finally:
        scene.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--cache', type=Path)
    p.add_argument('--expect-sha')
    p.add_argument('--expect-pcb-sha', help='Optional required SHA-256 of the source KiCad drawing manifest')
    p.add_argument('--pcb-manifest', type=Path)
    p.add_argument('--pdf-python', default=os.environ.get('ESKD_PDF_PYTHON') or shutil.which('python3'))
    p.add_argument('--draft', action='store_true')
    p.add_argument('--only', nargs='+', metavar='SHEET_ID')
    p.add_argument('--list-sheets', action='store_true')
    try:
        publish(p.parse_args())
    except Exception:
        traceback.print_exc()
        result = 1
    else:
        result = 0
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result)
