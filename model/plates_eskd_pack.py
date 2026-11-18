"""Combine already drawn paper-sized PDFs natively; no image conversion or resizing.

Uses PyMuPDF in an ordinary Python interpreter (the CAD distribution need not
carry it). The source rows and printed index are produced by the same catalog.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

import fitz


PAPER = {'A3': (420, 297), 'A4': (210, 297)}


def dimensions_by_document(pieces, *, partial=False):
    """GOST 2.307–2011 §4.3 applies to a DOCUMENT, not to each separate view.

    All mechanical dimensions in this reconstruction are reference-only. The
    count of actual holes, a sheet number or the chosen drawing scale is not a
    measured manufacturing dimension. No individual star in this convention.
    An isolated page proof need not repeat a notice from the first document page.
    """
    for designation, members in pieces.items():
        text = ' '.join(part for _, part in members)
        if re.search(r'(?:\d|[⌀Ø])\s*\*|\*\s*Размеры\s+для\s+справок', text, re.I):
            raise ValueError(f'{designation}: individual reference stars on an all-reference document')
        complete = {r['number'] for r, _ in members} == set(range(1, members[0][0]['sheets'] + 1))
        if (complete or not partial) and 'размеры для справок' not in ' '.join(text.casefold().split()):
            raise ValueError(f'{designation}: missing document-level reference-dimensions note')


def check_page(page, record):
    width, height = (v * 25.4 / 72 for v in (page.rect.width, page.rect.height))
    paper = next((name for name, (w, h) in PAPER.items()
                  if abs(w - width) < .02 and abs(h - height) < .02), None)
    if paper is None or record.get('paper', paper) != paper:
        raise ValueError(f"{record['id']}: unexpected sheet bounds {width:.3f} × {height:.3f}")
    if page.get_image_info():
        raise ValueError(f"{record['id']}: raster image(s) painted on an engineering sheet")
    text = ''.join(page.get_text().split())
    code = ''.join(record['designation'].split())
    if not (code in text and 'Лист' in text and 'Подп.' in text):
        raise ValueError(f"{record['id']}: no searchable common title block for {record['designation']}")
    # On the second assembly sheet form 2а has no scale box, and its two
    # linked views have a different scale from the main section on sheet 1.
    if record['id'] == 'assembly-exploded' and f"({record['scale']})" not in text:
        raise ValueError('Missing printed scale of the exploded orthographic pair')
    # Check the ACTUAL field 35, not a '1' somewhere in the drawing or sheet
    # ordinal. The reconstruction's first document issue is not PCB revision A4.3.
    continuation = record['number'] > 1
    is_text = record['section'] in ('Указатель', 'Спецификации', 'Поставка')
    block = 15 if continuation else 40 if is_text else 55
    bx = width - 190 + (165 if continuation else 175)
    mm = 72. / 25.4
    cell = fitz.Rect(bx*mm, (height-5-block+5)*mm, (bx+10)*mm, (height-5-block+15)*mm)
    # A font's em-box may cross a ruling while its ink does not. Test whole
    # word centres rather than clipping adjacent 'Масштаб'/'Листов' glyphs.
    words = [word[4] for word in page.get_text('words')
             if ((word[0]+word[2])*.5, (word[1]+word[3])*.5) in cell]
    if words != ['1']:
        raise ValueError(f"{record['id']}: wrong version in title-block field 35")
    return paper


def assemble(recipe, output, index_path):
    raw = json.loads(Path(recipe).read_text(encoding='utf-8'))
    output = Path(output)
    rows, bookmarks = [], []
    reference_documents = {}
    pdf = fitz.open()
    try:
        for n, row in enumerate(raw.pop('pages'), 1):
            file = Path(row.pop('pdf_input'))
            page_i = row.pop('source_page') - 1
            with fitz.open(file) as leaf:
                if not 0 <= page_i < len(leaf):
                    raise ValueError(f'{file.name}: missing page {page_i+1}')
                row['paper'] = check_page(leaf[page_i], row)
                if row['section'] in ('Механика', 'Печатные платы'):
                    reference_documents.setdefault(row['designation'], []).append((row, leaf[page_i].get_text()))
                pdf.insert_pdf(leaf, from_page=page_i, to_page=page_i, links=False, annots=False)
            if n == 1 or row['section'] != rows[-1]['section']:
                bookmarks.append([1, row['section'], n])
            bookmarks.append([2, f"{row['designation']} · {row['title']} ({row['number']}/{row['sheets']})", n])
            row['page'] = n
            rows.append(row)
        dimensions_by_document(reference_documents, partial=raw['draft'])
        pdf.set_toc(bookmarks)
        pdf.set_metadata({'title': 'XKAH PRO. Чертежи и спецификации реконструкции',
                          'subject': 'Комплект: FCStd SHA-256 ' + raw['sourceSHA256'],
                          'keywords': 'ЕСКД; фотооценка; A4.3; FreeCAD; KiCad', 'author': ''})
        pdf.save(output, garbage=4, deflate=True, no_new_id=True)
    finally:
        pdf.close()
    raw.update(pdf=output.name, pdfSHA256=sha256(output.read_bytes()).hexdigest(),
               pageCount=len(rows), sheets=rows)
    Path(index_path).write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'=== Векторное объединение: {len(rows)} листов, {raw["pdfSHA256"]}', flush=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('recipe', type=Path)
    cli.add_argument('pdf', type=Path)
    cli.add_argument('index', type=Path)
    args = cli.parse_args()
    assemble(args.recipe, args.pdf, args.index)
