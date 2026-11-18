"""Printable A4 specifications (ГОСТ Р 2.106-2019, изм. 1, §4.2 / прил. А).

Forms 1 / 1а use text-document title blocks 2 / 2а, not drawing blocks.
The main KD carries the product designation (ГОСТ Р 2.102-2023, §5.5).
Counts come from the installed native hierarchy; the regional box is a
separate reference sheet, not a purchased-parts section of the product.
"""

from dataclasses import dataclass
from functools import partial

from atlas_catalog import MANUAL, XYKA, web_notes
from plates_eskd_font import drawing_font
from plates_eskd_frame import Sheet
from plates_eskd_positions import PREFIX, installed_bom


# Stable file stems. Titles in the stamp name the specified physical object.
DOCUMENTS = (
    ('000', 'product', 'Чаша электронная XKAH PRO'),
    ('100', 'upper', 'Часть верхняя'),
    ('200', 'lower', 'Часть нижняя'),
    ('220', 'pod', 'Чаша съёмная'),
    ('130', 'fascia', 'Кассета лицевая'),
    ('131', 'film', 'Накладка лицевая'),
    ('110', 'housing', 'Корпус верхний'),
    ('170', 'heater', 'Нагреватель'),
)
SPEC_CODES = {code for code, _, _ in DOCUMENTS}
DOC, ASSEMBLIES, DETAILS, OTHER = 'Документация', 'Сборочные единицы', 'Детали', 'Прочие изделия'
# Only actual documents of the specified object; NEVER its own specification,
# the child assembly's СБ, the physical PDF page number or a fictitious .180 СБ.
DRAWINGS = {
    '000': (('СБ', 'А3', 'Сборочный чертёж', '2 листа'), ('ГЧ', 'А3', 'Габаритный чертёж', ''),
            ('Д1', 'А4', 'Указатель листов комплекта', '')),
    '100': (('СБ', 'А3', 'Сборочный чертёж', '3 листа'),),
    '200': (('СБ', 'А3', 'Сборочный чертёж', ''),),
    '220': (('СБ', 'А3', 'Сборочный чертёж', ''),),
    '130': (('СБ', 'А3', 'Сборочный чертёж', ''),),
    '131': (('СБ', 'А3', 'Сборочный чертёж', ''),),
}
# A4 is the *specification* of a child, not the format of that child's СБ.
# The four drawn parts have their own document. Other details are БЧ; the
# reconstruction does not supply the unknown material, mass or shop data.
DRAWN_PARTS = {'171': 'А4', '221': 'А4', '222': 'А4', '223': 'А4'}
ELECTRONIC_GROUPS = {'111', '140', '160', '180', '190', '210'}

# Additions to the product name (not more counted items).
QUALIFIER = {
    '111': 'Неподвижный узел модели',
    '140': 'С рассеивателем',
    '150': 'Внешний вид: XKAH.43.150',
    '160': 'Группа модели',
    '180': 'GYS005-S-088-A4.3',
    '190': '20260305A, с дисплеем',
}
NOTES = {
    '100': 'С батареей', '200': 'С одной чашей',
    '110': 'С гнездом батареи', '130': 'Без плат', '131': 'Снимается целиком',
    '140': 'Защёлки на ободе', '150': 'Каталог XYKA', '160': '10 жил к плате; 4 к ободу',
    '170': 'Щиток внутри узла', '180': 'Деталь платы: XKAH.43.181',
    '190': 'Деталь платы: XKAH.43.191', '210': 'Группа модели', '220': 'Установлена одна',
    '101': 'Резьба не измерена', '102': 'Не винт', '103': 'Без типоразмера',
    '111': 'Не часть батареи', '112': 'Со знаком и проушинами', '114': 'Без оси',
    '115': 'С фактурой', '116': 'Без штырька', '117': 'Съёмное',
    '119': 'Под уплотнением', '120': 'Внутри основы',
    '132': 'Разделение наружного слоя в CAD условно', '133': 'В той же накладке; не стекло дисплея',
    '134': 'Под накладкой', '135': 'Между платами', '136': 'Отдельность условна',
    '137': 'Со знаком и пятой', '138': 'Со знаком и пятой', '139': 'Со знаком и пятой',
    '171': 'Со знаками', '172': 'С надписью', '173': 'С рисунком диска',
    '221': 'С маркировкой', '222': 'В корпусе чаши', '223': 'Со стороны шахты',
}


@dataclass(frozen=True)
class Record:
    paper: str
    pos: str
    designation: str
    name: str
    quantity: str = ''
    note: str = ''


def _records(code, resolved):
    groups = {key: [] for key in (DOC, ASSEMBLIES, DETAILS, OTHER)}
    for kind, paper, name, note in DRAWINGS.get(code, ()):
        groups[DOC].append(Record(paper, '', f'{PREFIX}{code} {kind}', name, note=note))
    for part, count in resolved:
        child = part.code
        name = part.name
        if child in QUALIFIER:
            name += '\n' + QUALIFIER[child]
        note = NOTES.get(child, '')
        designation = PREFIX + child
        if child == '150':
            # Table 4.1: format and designation MUST be empty in «Прочие изделия».
            # .150 is our view of a bought unit, not the maker's ordering code.
            section, paper, designation = OTHER, '', ''
        elif child in SPEC_CODES:
            section, paper = ASSEMBLIES, 'А4'
        elif child in ELECTRONIC_GROUPS:
            # No separately issued paper KD. 4.2.17.1: empty for electronic KD.
            section, paper = ASSEMBLIES, ''
        else:
            section, paper = DETAILS, DRAWN_PARTS.get(child, 'БЧ')
            if paper == 'БЧ':
                name += '\nМатериал не установлен'
                note = '\n'.join(filter(None, (note, 'Масса н/у')))
        groups[section].append(Record(paper, str(part.pos), designation, name, str(count), note))
    # §4.2.5: order within a section by designation. The local numbers of
    # the registered drawings remain unchanged (e.g. жгут .160 is pos. 8).
    for section in (ASSEMBLIES, DETAILS):
        groups[section].sort(key=lambda r: r.designation)
    return [(key, records) for key, records in groups.items() if records]


# Widths 6, 6, 8, 70, 63, 10, 22 = 185. The frame itself supplies the two
# outside edges, the very top and the bottom closure at the common stamp.
X = (20, 26, 32, 40, 110, 173, 183, 205)
TOP, HEAD_BASE = 292, 277
HEIGHTS = (2.5, 2.5, 3.5, 3.5, 3.5, 3.5, 2.5)
HEADER = ('Формат', 'Зона', 'Поз.', 'Обозначение', 'Наименование', 'Кол.', 'Приме-\nчание')
EMPTY = ('',) * 7


def _wrap(value, width, height):
    """Wrap at actual glyph advances; do not squeeze type or split an ID."""
    measure = drawing_font().metrics
    lines = []
    for paragraph in value.split('\n'):
        current = ''
        for word in paragraph.split():
            if measure(word)[0] * height > width:
                raise ValueError(f'{word!r}: wider than {width:g} mm at h={height:g}')
            candidate = f'{current} {word}' if current else word
            if current and measure(candidate)[0] * height > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def _record_lines(r):
    values = (r.paper, '', r.pos, r.designation, r.name, r.quantity, r.note)
    wrapped = [_wrap(value, x1 - x0 - (1 if i in (0, 1, 2, 5) else 2.4), height)
               for i, (value, x0, x1, height) in enumerate(zip(values, X, X[1:], HEIGHTS))]
    count = max(map(len, wrapped))
    return [tuple(col[i] if i < len(col) else '' for col in wrapped) for i in range(count)]


def _limits(ordinal):
    # 232 / 29 = 8 mm; 257 / 32 > 8 mm. No short final line at the stamp.
    return (45, 29) if ordinal == 1 else (20, 32)


def _paginate(groups):
    """Break at record boundaries; keep each heading with the first item."""
    pages = [[]]
    for section, records in groups:
        heading = (*EMPTY[:4], section, '', '')
        blocks = [_record_lines(r) for r in records]
        section_height = 2 + sum(map(len, blocks))
        for i, block in enumerate(blocks):
            page = pages[-1]
            cap = _limits(len(pages))[1]
            lead = ([EMPTY] if page else []) + [heading, EMPTY] if i == 0 else []
            # Do not strand a short last section across two sheets.
            fresh = i == 0 and page and section_height <= 10 and len(page) + 1 + section_height > cap
            if fresh or len(page) + len(lead) + len(block) > cap:
                pages.append([])
                page = pages[-1]
                lead = [heading, EMPTY]
            if len(lead) + len(block) > _limits(len(pages))[1]:
                raise ValueError('Single specification record does not fit a page')
            page.extend(lead)
            page.extend(block)
    return pages


def _text(s, x, y, text, h, ha='left', angle=0):
    """y is the ink centre (including descenders), in paper millimetres."""
    if not text:
        return
    _, ascent, descent = drawing_font().metrics(text)
    offset = (ascent - descent) * h / 2
    if angle == 90:
        x += offset
    else:
        y -= offset
    s.text(x, y, text, h=h, ha=ha, va='baseline', rotation=angle, rotation_mode='anchor')


def _spec_sheet(code, title, lines, number, sheets):
    s = Sheet(PREFIX + code, 'Спецификация', '', product=title, paper='A4',
              number=number, sheets=sheets, form='2' if number == 1 else '2a')
    bottom, cap = _limits(number)
    pitch = (HEAD_BASE - bottom) / cap
    for x in X[1:-1]:
        s.line([(x, bottom), (x, TOP)], width=.5)
    s.line([(X[0], HEAD_BASE), (X[-1], HEAD_BASE)], width=.7)
    for i in range(1, cap):
        y = HEAD_BASE - pitch * i
        s.line([(X[0], y), (X[-1], y)], width=.25)
    for i, label in enumerate(HEADER):
        x = (X[i] + X[i + 1]) / 2
        if i == 6:
            _text(s, x, 287.1, 'Приме-', 3.5, 'center')
            _text(s, x, 281.9, 'чание', 3.5, 'center')
        else:
            narrow = i in (0, 1, 2, 5)
            _text(s, x, (TOP + HEAD_BASE) / 2, label, 2.5 if narrow else 3.5,
                  'center', 90 if narrow else 0)
    for i, cells in enumerate(lines):
        y = HEAD_BASE - pitch * (i + .5)
        heading = cells[4] in (DOC, ASSEMBLIES, DETAILS, OTHER) and not cells[3]
        for j, value in enumerate(cells):
            if not value:
                continue
            center = j in (0, 1, 2, 5) or heading
            x = (X[j] + X[j + 1]) / 2 if center else X[j] + 1.2
            _text(s, x, y, value, HEIGHTS[j], 'center' if center else 'left')
            if heading:
                w, ascent, descent = drawing_font().metrics(value)
                half = w * HEIGHTS[j] / 2
                underline = y - (ascent + descent) * HEIGHTS[j] / 2 - .5
                s.line([(x - half, underline), (x + half, underline)], width=.25)
    return s


# One region, one product card. The NAMES and BOX quantities are shared with
# the atlas evidence catalogue; the CAD counts below are a separate axis.
# Key by name (not table ordinal), rejecting a changed/unknown catalogue.
KIT_ROLES = {
    'Устройство XYKA PRO': (None, 'Изделие в целом'),
    'Съёмный аккумулятор': ('150', 'Верхний блок, поз. 4'),
    'Многоразовая чаша': ('220', 'Нижний блок, поз. 2'),
    'Уплотнитель для установки на шахту': (None, 'Принадлежность'),
    'Щипцы для чаши': (None, 'Инструмент'),
    'Шило-вилка': (None, 'Инструмент'),
    'Зарядный кабель USB-C': (None, 'Принадлежность'),
    'Мешок для переноски': (None, 'Принадлежность'),
    'Руководство по быстрому старту': (None, 'Документация'),
    'Инструкция пользователя': (None, 'Документация'),
}


def _kit_rows(bom):
    region = web_notes()['kit']
    if len(region) != len(KIT_ROLES) or {row['label'] for row in region} != KIT_ROLES.keys():
        raise ValueError('Regional kit changed: reconcile its current evidence with the model')
    counts = {r.code: q for parent in ('100', '200') for r, q in bom[parent]}
    result = []
    for row in region:
        if row['url'] != XYKA + 'xyka-graphite':
            raise ValueError('Do not mix source regions or SKUs')
        name, box = row['label'], row['quantity']
        code, role = KIT_ROLES[name]
        installed = counts[code] if code else (None if name == 'Устройство XYKA PRO' else 0)
        if installed is not None and installed > box:
            raise ValueError(f'Installed quantity exceeds supplied: {name}')
        result.append((name, str(box), '—' if installed is None else str(installed), role))
    return result


def _kit_sheet(rows):
    s = Sheet('СПР-01', 'Справка о поставке', '', product='XYKA PRO, графит', paper='A4', form='2')
    _text(s, 24, 281, 'Поставка и установленное изделие', 5)
    _text(s, 24, 269, 'XYKA PRO, графит. Региональная комплектация для России.', 3.5)
    _text(s, 24, 261.5, 'SKU в карточке продавца: 700.954.29. Количества указаны в штуках.', 3)
    xs = (20, 100, 126, 150, 205)
    top, data_y, pitch = 253, 239, 8.6
    bottom = data_y - len(rows) * pitch
    for x in xs[1:-1]:
        s.line([(x, bottom), (x, top)], width=.35)
    for y in (top, data_y, bottom):
        s.line([(20, y), (205, y)], width=.5)
    for j, label in enumerate(('Наименование', 'В поставке', 'В сборке', 'Учёт')):
        _text(s, (xs[j] + xs[j + 1]) / 2, (top + data_y) / 2, label, 3, 'center')
    for i, cells in enumerate(rows):
        y = data_y - pitch * (i + .5)
        for j, value in enumerate(cells):
            center = j in (1, 2)
            x = (xs[j] + xs[j + 1]) / 2 if center else xs[j] + 1.4
            _text(s, x, y, value, 3, 'center' if center else 'left')
        if i + 1 < len(rows):
            s.line([(20, y - pitch / 2), (205, y - pitch / 2)], width=.25)
    _text(s, 24, 145, 'В поставке 2 чаши: 1 установлена, 1 запасная.', 3.5)
    _text(s, 24, 137, 'Аккумулятор также уже учтён в изделии. Строки таблицы не суммируют.', 3)
    _text(s, 24, 130, 'Кабель, инструменты и принадлежности не входят в установленную сборку.', 3)
    _text(s, 24, 119, 'Границы спецификаций', 3.5)
    _text(s, 24, 111, 'XKAH.43.000 описывает одно собранное изделие. Вложенные узлы', 3)
    _text(s, 24, 104.5, 'учтены по одному разу; группы CAD не являются артикулами продавца.', 3)
    _text(s, 24, 98, 'Рисунок, печать и наружная фактура остаются на своей детали. Платы', 3)
    _text(s, 24, 91.5, 'с деталями монтажа учтены как модули, а не как набор отдельных ЭРИ.', 3)
    _text(s, 24, 85, 'БЧ — без чертежа; н/у — не установлена. Данные не для изготовления.', 3)
    _text(s, 24, 74, 'Источники', 3.5)
    links = ((67.5, 'Карточка: ', XYKA + 'xyka-graphite'),
             (61.5, 'Руководство, распаковка: ', XYKA + 'manual#unpack'),
             (49.5, '', MANUAL))
    for y, label, url in links:
        s.text(24, y, label + url, h=2.5, va='center', url=url)
    _text(s, 24, 55.5, 'Для сравнения: XKAH Pro User Manual, с. 03 — две чаши, один адаптер. Перечни не объединены.', 2.5)
    return s


def spec_pages(a):
    """(stem, designation, index title, local sheet, total sheets, make_sheet).

    Validation and pagination happen once when indexing. Makers retain only
    the resolved cells, so do not reopen the FCStd or rebuild a release.
    """
    bom = installed_bom(a)
    result = []
    for code, stem, title in DOCUMENTS:
        pages = _paginate(_records(code, bom[code]))
        total = len(pages)
        for n, lines in enumerate(pages, 1):
            result.append((f'spec-{stem}-{n:02d}', PREFIX + code, 'Спецификация. ' + title,
                           n, total, partial(_spec_sheet, code, title, lines, n, total)))
    result.append(('kit-note', 'СПР-01', 'Комплект поставки. XYKA PRO, графит',
                   1, 1, partial(_kit_sheet, _kit_rows(bom))))
    return result
