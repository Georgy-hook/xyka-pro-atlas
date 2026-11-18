"""Printed sheet register, including document-local sheet numbers and physical PDF pages."""

from functools import partial
from math import ceil

from plates_eskd_catalog import Entry
from plates_eskd_frame import Sheet


def _page(records, ordinal, n_index, per_page):
    s = Sheet('XKAH.43.000 Д1', 'Указатель листов комплекта', '', paper='A4',
              number=ordinal, sheets=n_index, form='2' if ordinal == 1 else '2a')
    s.text(112.5, 281, 'Указатель листов', h=5.0, ha='center')
    s.text(112.5, 270, 'XKAH PRO. Реконструкция по фотографиям и открытым источникам',
           h=3.0, ha='center')
    xs = [20, 32, 80, 95, 205]
    y = 262
    rows = records[(ordinal - 1) * per_page:ordinal * per_page]
    bottom = y - 9 - 8 * len(rows)
    for x in xs[1:-1]:
        s.line(((x, y), (x, bottom)), width=.35)
    s.line(((20, y), (205, y)), width=.7)
    for x0, x1, name in zip(xs, xs[1:], ('Стр.', 'Обозначение', 'Лист', 'Наименование')):
        s.text((x0+x1)/2, y-4.5, name, h=3.0, ha='center')
    y -= 9
    s.line(((20, y), (205, y)), width=.7)
    for pi, designation, no, title in rows:
        s.text(26, y-4, str(pi), h=3.0, ha='center')
        s.text(34, y-4, designation, h=3.0)
        s.text(87.5, y-4, no, h=3.0, ha='center')
        s.text(97, y-4, title, h=3.0)
        y -= 8
        s.line(((20, y), (205, y)), width=.25)
    if ordinal == n_index:
        s.text(24, bottom-8, 'Обозначения — учётные номера реконструкции, не заводские номера.', h=3.0)
        s.text(24, bottom-14, 'Размеры механических чертежей — для справок. Обмер изделия не выполнен.', h=3.0)
        s.text(24, bottom-20, 'Комплект не содержит производственных допусков или заключения об аттестации.', h=3.0)
    return s


def with_index(entries):
    if not entries:
        raise ValueError('Cannot index an empty document set')
    per_page = 21
    n_index = max(1, ceil(len(entries) / (per_page-1)))
    intro = [Entry(f'index-{n:02d}', 'XKAH.43.000 Д1', 'Указатель листов комплекта',
                   'Указатель', n, n_index) for n in range(1, n_index+1)]
    all_pages = [*intro, *entries]
    records = [(i, row.designation, f'{row.number}/{row.sheets}', row.title)
               for i, row in enumerate(all_pages, 1)]
    for row in intro:
        row.make = partial(_page, records, row.number, n_index, per_page)
    return all_pages
