#!/usr/bin/env python3
"""Publish drawings from a saved XKAH FCStd without using or changing its GUI state.

From the workspace (macOS FreeCAD bundle):
  R=/Applications/FreeCAD.app/Contents/Resources
  PYTHONPATH="$R/lib" "$R/bin/python" model/plates.py

--input and --out override the standard paths. --cache may name a scratch folder;
its keys include the whole source FCStd plus geometry renderer source hashes.
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import pyplot as plt

from plates_assets import Assets, digest, progress
from plates_scene import Scene
import plates_studio as studio
import plates_mechanical as mech
import plates_electronics as elec

BASE = Path(__file__).resolve().parent.parent
# Publication is a read-only consumer of the shared dimensional spreadsheet.
PARAMS = []
PAGES = [('01-assembly', studio.cover), ('02-orthographic', mech.ortho),
         ('03-shell-section', mech.shell), ('04-pcb-mounting', mech.seating),
         ('05-main-pcb', elec.pcb), ('06-display-pcb', elec.ui),
         ('07-fasteners', mech.hardware), ('08-exploded', studio.exploded),
         ('09-electronics', studio.electronics)]


def build(c):
    """Integration hook. Publish the *saved* CAD, never an incomplete scene.

    Use the bundle interpreter of the caller in a separate process so a GUI
    session holding this document is not changed or closed by publication.
    """
    name = c.doc.FileName
    if not name or not Path(name).is_file():
        raise ValueError('Save the completed FCStd before publishing drawings')
    source = Path(name).resolve()
    output = Path(getattr(c, 'root', source.parent)).resolve()
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--input', str(source),
                    '--out', str(output)], check=True)


def publish(args):
    args.out.mkdir(parents=True, exist_ok=True)
    sc = Scene(args.input)
    try:
        a = Assets(sc, cache=args.cache, quick=args.quick)
        counts = ', '.join(f'{k}: {len(v)}' for k, v in sc.by.items())
        progress(f'Reopened {sc.src.name}: {len(sc.items)} physical leaves ({counts})')
        progress(f'Source SHA-256 {a.fingerprint}')
        full = args.pages is None
        wanted = set(range(1, len(PAGES)+1)) if full else set(args.pages)
        if not wanted or min(wanted) < 1 or max(wanted) > len(PAGES):
            raise ValueError('--pages accepts sheet numbers 1…9')
        if (args.quick or not full) and args.out.resolve() == BASE:
            raise ValueError('Use a scratch --out for partial/quick renders')
        pdfname = 'XKAH_PRO_A43_drawings.pdf' if full else 'plates-preview.pdf'
        with tempfile.TemporaryDirectory(prefix='plates-publish-', dir=args.out) as t:
            tmp = Path(t)
            (tmp/'drawings').mkdir()
            meta = dict(Title='XKAH PRO • A4.3 | Альбом реконструкции',
                        Author='XKAH PRO / CAD reconstruction',
                        Subject=f'Геометрия из {sc.src.name} | SHA-256 {a.fingerprint}',
                        Keywords='FreeCAD; XKAH PRO; GYS005-S-088-A4.3; 20260305A; EST',
                        CreationDate=datetime.now(timezone.utc))
            with PdfPages(tmp/pdfname, metadata=meta) as pdf:
                for index, (stem, fn) in enumerate(PAGES, start=1):
                    if index not in wanted:
                        continue
                    progress(f'Sheet {stem}')
                    sheet = fn(a)
                    sheet.finish()
                    pdf.savefig(sheet.fig, dpi=160, facecolor='white')
                    sheet.fig.savefig(tmp/'drawings'/(stem+'.svg'), format='svg', dpi=155,
                                      metadata={'Title': f'XKAH PRO / A4.3 / {stem}',
                                                'Description': 'FreeCAD model: ' + a.fingerprint})
                    plt.close(sheet.fig)
            if full:
                progress('High-resolution studio PNGs')
                studio.save_posters(a, tmp)
            if digest(sc.src) != a.fingerprint:
                raise RuntimeError('Source FCStd changed during publication; refusing to issue stale sheets')
            (args.out/'drawings').mkdir(exist_ok=True)
            for svg in (tmp/'drawings').glob('*.svg'):
                os.replace(svg, args.out/'drawings'/svg.name)
            for f in tmp.iterdir():
                if f.is_file():
                    os.replace(f, args.out/f.name)
        progress(f'Saved {len(wanted)} sheets at {args.out.resolve()}')
    finally:
        sc.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', type=Path, default=BASE/'XKAH_PRO_A43_rebuilt.FCStd')
    p.add_argument('--out', type=Path, default=BASE)
    p.add_argument('--cache', type=Path, help='Optional generated-geometry scratch cache')
    p.add_argument('--pages', type=int, nargs='+', help='Partial preview, requires a separate --out')
    p.add_argument('--quick', action='store_true', help='Smaller studio previews, requires a separate --out')
    try:
        publish(p.parse_args())
    except Exception:
        traceback.print_exc()
        result = 1
    else:
        result = 0
    # Close native FreeCAD/Cocoa libraries after all outputs have been flushed.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result)
