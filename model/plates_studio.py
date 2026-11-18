"""Three standalone CAD studio PNGs. None are placed on the engineering sheets."""

from pathlib import Path

from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

TEAL, INK, MUTE, STUDIO_BG = '#006b69', '#172e35', '#496168', '#f1f4f1'


def _font(n, bold=False):
    return ImageFont.truetype(font_manager.findfont(font_manager.FontProperties(
        family='DejaVu Sans', weight='bold' if bold else 'normal')), n)


def save_posters(a, dest):
    """Standalone images retain native raster detail, independent of A3 page sampling."""
    render_specs = [('assembled', 'assembly_assembled', 'Сборка в корпусе', '01',
                     'Закрытая сборка  ·  со стороны панели  ·  оценочная реконструкция'),
                    ('exploded', 'assembly_exploded', 'Разнесённая сборка', '02',
                     'Номера — модули CAD, не позиции спецификации. Разнос условный.'),
                    ('electronics', 'electronics', 'Электроника и жгут', '03',
                     'Монтажная сторона  ·  корпус скрыт  ·  положение плат и проводов сохранено')]
    for key, fname, title, n, detail in render_specs:
        r = a.raster(key)
        w, h = r.image.size
        z = w/1550
        margin = round(44*z)
        upper, lower = round(150*z), round((150 if key == 'exploded' else 75)*z)
        final = Image.new('RGB', (w, h+upper+lower), STUDIO_BG)
        final.paste(r.image, (0, upper))
        d = ImageDraw.Draw(final)
        d.text((margin, round(30*z)), f'XKAH PRO   /   CAD   /   A4.3', fill=TEAL, font=_font(round(22*z), True))
        d.text((margin, round(72*z)), title, fill=INK, font=_font(round(48*z), True))
        d.text((w-margin, round(90*z)), f'ВИД   {n} / 03', fill=MUTE, anchor='ra', font=_font(round(22*z)))
        d.line((margin, upper-2, w-margin, upper-2), fill='#b4c1bd', width=max(1, round(1.6*z)))
        d.line((margin, h+upper+1, w-margin, h+upper+1), fill='#b4c1bd', width=max(1, round(1.6*z)))
        if key == 'exploded':
            u0, v0, u1, v1 = r.extent
            anchors = a.anchors('exploded')
            entries = a.service.entries
            rad = round(15*z)
            for i, (root, _) in enumerate(entries):
                if root not in anchors:
                    continue
                u, v = anchors[root]
                x, y = round((u-u0)*w/(u1-u0)), round((v1-v)*h/(v1-v0))+upper
                d.ellipse((x-rad, y-rad, x+rad, y+rad), fill='#ffffff', outline=TEAL, width=max(1, round(2*z)))
                d.text((x,y), str(i+1), font=_font(round(17*z), True), fill=TEAL, anchor='mm')
            font = _font(round(19*z), True)
            rows = ['']
            for n, (_, title) in enumerate(entries, 1):
                entry = f'{n:02d}  {title}'
                candidate = '      '.join(filter(None, (rows[-1], entry)))
                if d.textlength(candidate, font=font) > w - 2*margin:
                    rows.append(entry)
                else:
                    rows[-1] = candidate
            for j, row in enumerate(rows):
                d.text((margin, h+upper+round((15+30*j)*z)), row, fill=INK, font=font)
        d.text((margin, h+upper+lower-round(24*z)), detail, fill=MUTE, font=_font(round(21*z)), anchor='ls')
        provenance = PngInfo()
        provenance.add_text('CADSource', a.scene.src.name)
        provenance.add_text('CADSourceSHA256', a.fingerprint)
        final.save(Path(dest)/f'XKAH_PRO_A43_{fname}.png', optimize=True, dpi=(160, 160),
                   pnginfo=provenance)
