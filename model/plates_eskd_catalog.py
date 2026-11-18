"""Registered drawing documents. One row = one real sheet, not a poster or 3-D thumbnail."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path


@dataclass
class Entry:
    id: str
    designation: str
    title: str
    section: str
    number: int = 1
    sheets: int = 1
    make: object = None
    original_pdf: Path | None = None
    original_svg: Path | None = None
    original_page: int = 1
    sources: dict = field(default_factory=dict)
    scale: str = ''


def _sheet(module, name, assets):
    return getattr(import_module('plates_eskd_' + module), name)(assets)


# Internal reconstruction designations, not factory drawing numbers. The labels
# below are short, unambiguous names for the collection index, not a substitution
# for the standard document title inside each sheet's own primary inscription.
MECHANICAL = (
    ('overall', '000 ГЧ', 'Габаритный чертёж', 1, 1, 'assembly', 'overall'),
    ('assembly-section', '000 СБ', 'Сборка. Разрез по корпусу', 1, 2, 'assembly', 'assembly'),
    ('assembly-exploded', '000 СБ', 'Сборка. Разнесённое положение', 2, 2, 'explosion', 'exploded'),
    ('upper-section', '100 СБ', 'Верхний блок. Посадка плат', 1, 3, 'assembly', 'upper'),
    ('upper-battery-seat', '100 СБ', 'Верхний блок. Гнездо аккумулятора', 2, 3, 'battery', 'seat'),
    ('upper-retention', '100 СБ', 'Верхний блок. Узлы крепления', 3, 3, 'retention', 'retention'),
    ('lower-assembly', '200 СБ', 'Нижний блок. Гнездо чаши', 1, 1, 'pod', 'lower'),
    ('fascia-assembly', '130 СБ', 'Лицевая кассета', 1, 1, 'cassette', 'fascia'),
    ('front-film', '131 СБ', 'Съёмная лицевая накладка', 1, 1, 'cassette', 'film'),
    ('battery', '150', 'Съёмный аккумулятор', 1, 1, 'battery', 'battery'),
    ('pod-assembly', '220 СБ', 'Чаша для табака. Сборочный чертёж', 1, 1, 'pod', 'pod'),
    ('pod-cup', '221', 'Корпус чаши', 1, 1, 'pod', 'cup'),
    ('pod-screen', '222', 'Сетка чаши', 1, 1, 'pod', 'screen'),
    ('pod-lid', '223', 'Крышка чаши', 1, 1, 'pod', 'lid'),
    ('heater-guard', '171', 'Щиток нагревателя', 1, 1, 'pod', 'guard'),
)

PCB_IDS = ('pcb-main-01', 'pcb-main-02', 'pcb-display-01', 'pcb-display-02')


def installed(a):
    return [Entry(key, 'XKAH.43.' + code, title, 'Механика', number, sheets,
                  partial(_sheet, module, fn, a))
            for key, code, title, number, sheets, module, fn in MECHANICAL]


def specifications(a):
    from plates_eskd_spec import spec_pages
    return [Entry(key, code, title, 'Спецификации' if key != 'kit-note' else 'Поставка',
                  number, sheets, maker)
            for key, code, title, number, sheets, maker in spec_pages(a)]


def pcb_entries(manifest):
    manifest = Path(manifest).resolve(strict=True)
    raw = json.loads(manifest.read_text(encoding='utf-8'))
    rows = {row['id']: row for row in raw['sheets']}
    if len(raw['sheets']) != len(PCB_IDS) or set(rows) != set(PCB_IDS):
        raise ValueError('Expected the four agreed KiCad sheets in pcb-sheets.json')

    def path(name):
        local = (manifest.parent / name).resolve(strict=True)
        if not local.is_relative_to(manifest.parent) or not local.is_file():
            raise ValueError(f'PCB artifact must be a local file beside its manifest: {name}')
        return local

    result = []
    for i, key in enumerate(PCB_IDS):
        row = rows[key]
        code = 'XKAH.43.181' if i < 2 else 'XKAH.43.191'
        if row['designation'] != code or int(row['number']) != i % 2 + 1 or int(row['sheets']) != 2:
            raise ValueError(f'{key}: wrong PCB drawing designation or sheet ordinal')
        sources = row.get('sources') or raw.get('sources') or {}
        board = sources.get('main' if i < 2 else 'display', {})
        if not board.get('board') or not board.get('sha256'):
            raise ValueError(f'{key}: missing native board path or hash')
        pdf, svg = path(row['pdf']), path(row['svg'])
        for drawing, h in ((pdf, 'pdf_sha256'), (svg, 'svg_sha256')):
            if not row.get(h) or sha256(drawing.read_bytes()).hexdigest() != row[h]:
                raise ValueError(f'{key}: output differs from the KiCad generator manifest: {drawing.name}')
        sources = dict(board=board['board'], sha256=board['sha256'],
                       kicadCLI=raw.get('kicad_cli_version', ''),
                       nativePDFSHA256=row['pdf_sha256'], nativeSVGSHA256=row['svg_sha256'])
        result.append(Entry(key, code, row['title'], 'Печатные платы', i % 2 + 1, 2,
                            original_pdf=pdf, original_svg=svg, original_page=int(row.get('page', 1)),
                            sources=sources, scale=row['scale']))
    return result
