"""Exploded illustration of the documented XKAH service states, built from installed IDs.

Translations are display space, not prescribed extraction strokes. Each step records
only its incremental changes; the final native links and the mesh use their sum.
"""

from collections import defaultdict


MANUAL = 'https://www.animashop.cz/user/related_files/xkah_user_manual.pdf'
ALBUM = 'https://www.reddit.com/r/hookah/comments/1walb9l/'
XYKA = 'https://xyka.pro/xyka-graphite'


def metres(vector):
    x, y, z = vector
    return [round(x / 1000, 8), round(z / 1000, 8), round(-y / 1000, 8)]


class Layout:
    def __init__(self, context):
        self.steps = []
        self.by_module = defaultdict(set)
        self.by_unit = defaultdict(set)
        self.parts = {o.Name: o for o in context.physical}
        self.xyz = {name: (0., 0., 0.) for name in self.parts}
        self.role = {name: 'installed' for name in self.parts}
        modules = {o.Name for o in context.groups.values()}
        units = set(context.units)
        for name, obj in self.parts.items():
            lineage = {p.Name for p in context.lineage(obj)}
            module, = modules & lineage
            unit, = units & lineage
            self.by_module[module].add(name)
            self.by_unit[unit].add(name)

    def select(self, *prefixes):
        return {name for name in self.parts if name.startswith(prefixes)}

    def place(self, key, title, text, source, view, placements, focus=()):
        moves = []
        seen = set()
        for names, target in placements:
            overlap = seen & names
            if overlap:
                raise ValueError(f'{key}: multiple destinations for {overlap}')
            seen.update(names)
            grouped = defaultdict(list)
            for name in sorted(names):
                old = self.xyz[name]
                delta = tuple(b - a for a, b in zip(old, target))
                if any(delta):
                    grouped[delta].append(name)
                    self.role[name] = key
                self.xyz[name] = target
            moves.extend(dict(ids=ids, d=metres(delta)) for delta, ids in grouped.items())
        if not moves:
            raise ValueError(f'No physical movement for teardown state {key}')
        self.steps.append(dict(id=key, title=title, text=text, source=source, view=view,
                               moves=moves, focusIds=sorted(focus)))


def service_layout(c):
    plan = Layout(c)
    m = plan.by_module
    faces = {name for name, obj in plan.parts.items()
             if any(parent.Name == 'MechFrontFilm' for parent in c.lineage(obj))}
    screws = plan.select('MechServiceScrew')
    membrane = plan.select('UiKeyMembrane')
    lids = plan.select('MechPodLid')
    mesh = plan.select('MechPodScreen')
    collar = m['LightRing']
    heater_seal = {'MechServiceBaseGasket'}
    heater_fixings = plan.select('MechServiceBaseSealScrew')
    base_fixings = plan.select('MechServiceBaseInnerScrew')
    internal = plan.select('MechPackWell', 'MechPackSeat', 'MechServiceBaseInsert') - m['Battery']
    required = {'MechRemovablePod', 'MechPodLid', 'MechPodScreen', 'UiKeyMembrane', 'MechHeatGuard',
                'MechLightRing', 'MechServiceCover', 'MechCoverWindow', 'MechKeyCarrier', 'MechBrandMark',
                'MechServiceBaseInsert', 'MechServiceBaseGasket'}
    if required - plan.parts.keys():
        raise ValueError(f'Missing intended removable parts: {required - plan.parts.keys()}')
    if not {'MechServiceCover', 'MechCoverWindow'} <= faces or len(screws) != 5:
        raise ValueError('Detachable fascia or its observed fasteners missing')
    if len(heater_fixings) != 3 or len(base_fixings) != 4:
        raise ValueError('Two different sets of service-base fasteners are required: three and four')
    plan.place('battery', 'Съёмный аккумулятор',
               'Вынут аккумулятор целиком. Его USB-C, этикетка и нижние контакты уходят с блоком; ответная колодка остаётся в верхней части.',
               MANUAL, 'top', [(m['Battery'], (-50, -30, 112))], plan.select('MechPackCap', 'MechPackSeatSockets'))
    plan.place('halves', 'Верхняя и нижняя части',
               'Основание отделено по корпусному стыку. Табачная чаша пока в нижнем приёмнике; нагревательный щиток остаётся сверху.',
               MANUAL, 'right', [(plan.by_unit['LowerUnit'], (4, 82, -78))], ('MechLowerShroud', 'MechHeatGuard'))
    plan.place('pod', 'Чаша вне приёмника',
               'Из нижней половины вынута одна металлическая чаша. Приёмник остаётся в основании. Вторая чаша из комплекта не установлена.',
               XYKA, 'iso', [(m['Pod'], (88, 0, -42))], ('MechRemovablePod', 'MechChamberInsert'))
    plan.place('pod-parts', 'Корпус чаши, сетка и крышка',
               'В установленной ориентации крышка обращена вниз; за ней видна отдельная сетка. Сетка не является перфорированным щитком нагревателя.',
               MANUAL, 'iso', [(lids, (88, 0, -89)), (mesh, (109, -5, -75))], lids | mesh)
    plan.place('face-film', 'Лицевая плёнка и окно',
               'Наружная U-образная накладка отделена от носителя. Тонированное окно принадлежит накладке, а стекло LCD остаётся на плате.',
               ALBUM, 'iso', [(faces, (90, -45, 34))], faces)
    plan.place('face-screws', 'Винты под накладкой',
               'Три нижних винта и два верхних под клеевым слоем. На фото владельца различимы четыре места; нижнее слева закрыто платой и восстановлено по другому аппарату A4.3.',
               ALBUM, 'iso', [(screws, (60, -104, 0))], screws)
    plan.place('heat-seal', 'Уплотнение вокруг нагревателя',
               'Под снятым кольцевым уплотнением видны три винта верхней части. Это не силиконовая накладка кнопок.',
               ALBUM, 'bottom', [(heater_seal, (40, 5, -40))], heater_fixings)
    plan.place('heater-fasteners', 'Три винта под уплотнением',
               'Крепёж внутреннего модуля показан отдельно от корпусных винтов под лицевой плёнкой.',
               ALBUM, 'iso', [(heater_fixings, (-51, -23, -48))], heater_fixings)
    plan.place('light-ring', 'Световой обод и защёлки',
               'Снят световой обод с рассеивателем. Автор разбора насчитал четыре защёлки. Гнёзда в корпусе остаются на месте.',
               ALBUM, 'iso', [(collar, (72, 16, 50))], collar)
    cartridge = (m['Fascia'] - faces) | m['MainPCB'] | m['DisplayPCB'] | m['Harness']
    plan.place('cartridge', 'Кассета с электронными платами',
               'Лицевая кассета вынесена из проёма. Обе платы, наружные клавиши, силиконовая накладка и жгут пока вместе.',
               ALBUM, 'iso', [(cartridge, (-44, -75, 12))], ('MechCartridgeFrame', 'UiKeyMembrane'))
    plan.place('service-base', 'Внутреннее основание верхнего корпуса',
               'Внутренний носитель выходит из верхнего кожуха со стороны нагревателя. Его удерживающие выступы не являются замком штатно отсоединяемой нижней половины.',
               ALBUM, 'left', [(internal | (m['Heater'] - heater_fixings - heater_seal) | base_fixings, (-70, 2, -22))],
               plan.select('MechHeaterCarrier', 'MechPackWell', 'MechServiceBaseInsert'))
    plan.place('base-fasteners', 'Четыре винта внутреннего основания',
               'Эти четыре винта становятся видны после выхода внутреннего носителя. Они не относятся к патрубку нижней половины.',
               ALBUM, 'iso', [(base_fixings, (-110, -88, -14)), ({'MechServiceBaseInsert'}, (-110, -88, -52))], base_fixings)
    display = m['DisplayPCB'] - membrane
    fascia_rest = m['Fascia'] - faces
    plan.place('boards', 'Платы и три кнопки под силиконом',
               'Показаны плата A4.3, модуль 20260305A и отдельно снятая с него силиконовая накладка. На плате остаются три тактовые кнопки; наружные клавиши принадлежат кассете.',
               ALBUM, 'iso', [(display, (-100, -85, 42)), (membrane, (-90, -133, 51)),
                             (fascia_rest, (4, -105, 15))], membrane | {'UiPlungerC'})
    return plan
