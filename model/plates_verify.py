#!/usr/bin/env python3
"""Read-only issue check. Run with ordinary Python + PyMuPDF, Pillow and NumPy.

  python3 model/plates_verify.py

Checks the PDF's FCStd fingerprint, sheet sizes, searchable Cyrillic, font
embedding and where raster illustrations are actually painted. The six CAD
drawing sheets must be pure vectors in both PDF and SVG. This check says
nothing about the accuracy of photo-derived dimensions.
"""

import argparse
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET

import fitz
import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
NAMES = ('01-assembly', '02-orthographic', '03-shell-section', '04-pcb-mounting',
         '05-main-pcb', '06-display-pcb', '07-fasteners', '08-exploded', '09-electronics')
SVG = {'s': 'http://www.w3.org/2000/svg'}


def require(predicate, message):
    if not predicate:
        raise ValueError(message)


def verify(out, source):
    digest = sha256()
    with source.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    with fitz.open(out/'XKAH_PRO_A43_drawings.pdf') as doc:
        require(len(doc) == len(NAMES), 'Incomplete PDF')
        require(digest.hexdigest() in doc.metadata.get('subject', ''), 'FCStd fingerprint mismatch')
        print('FCStd SHA-256:', digest.hexdigest())
        fonts = set()
        for number, (page, name) in enumerate(zip(doc, NAMES), start=1):
            where = f'Sheet {number:02}: '
            size = np.array([page.rect.width, page.rect.height]) * 25.4 / 72
            require(np.allclose(size, [420, 297], atol=.015), where+'not A3 landscape')
            text = ' '.join(page.get_text().split())
            require(f'ЛИСТ {number:02} / 09' in text and '\ufffd' not in text, where+'lost text')
            paints = len(page.get_image_info())
            expected = 0 if number in range(2, 8) else 2 if number == 9 else 1
            require(paints == expected, where+'unexpected raster artwork')
            paths = len(page.get_drawings())
            require(paths >= (12 if expected == 0 else 5), where+'missing vector geometry')
            fonts.update(font[0] for font in page.get_fonts())
            for block in page.get_text('blocks'):
                require(block[0] >= 0 and block[1] >= 0 and block[2] <= page.rect.width
                        and block[3] <= page.rect.height, where+'off-sheet text')
            svg = ET.parse(out/'drawings'/(name+'.svg')).getroot()
            meta = svg.find('s:metadata', SVG)
            require(meta is not None and digest.hexdigest() in ''.join(meta.itertext()),
                    where+'SVG was not generated from the specified FCStd')
            require(bool(svg.findall('.//s:path', SVG)) and bool(svg.findall('.//s:text', SVG)),
                    where+'SVG missing editable text or geometry')
            require(len(svg.findall('.//s:image', SVG)) == expected, where+'unexpected SVG raster')
            if number in (3, 4):
                require(bool(svg.findall('.//s:pattern', SVG)), where+'missing vector section hatching')
            print(f'{where}{paths:,} vector paths; {paints} painted CAD raster view(s).')
        require(all(doc.extract_font(xref)[3] for xref in fonts), 'Non-embedded PDF font')
    for stem in ('assembly_assembled', 'assembly_exploded', 'electronics'):
        path = out/f'XKAH_PRO_A43_{stem}.png'
        with Image.open(path) as image:
            image.load()
            require(image.info.get('CADSourceSHA256') == digest.hexdigest(), f'{stem}: wrong source hash')
            require(image.mode == 'RGB' and min(image.size) >= 1000, f'{stem}: not an issued RGB render')
            model = np.asarray(image)[image.height//8 : 4*image.height//5]
            delta = np.max(np.abs(model.astype(np.int16) - [241, 244, 241]), axis=2)
            require(np.mean(delta > 18) > .035, f'{stem}: empty or nearly blank model area')
            print(f'{path.name}: {image.width} × {image.height} RGB.')
    print('PASS: source-matched A3 issue, nine SVG sheets, and three standalone renders.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=BASE, type=Path)
    parser.add_argument('--input', type=Path, help='Native assembly (default: --out/XKAH_PRO_A43_rebuilt.FCStd)')
    args = parser.parse_args()
    verify(args.out, args.input or args.out/'XKAH_PRO_A43_rebuilt.FCStd')
