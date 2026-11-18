"""Installed BOM: one local number per physical occurrence, not per B-rep.

Drawings and specification sheets share position_by_id(parent, native_id, a=None).
Pass an Assets/Scene, or an actual Scene Item, to resolve any leaf by its native
ancestry. A bare ID suffices for the stable local identities (e.g. face keys).
No FreeCAD import is needed to import or query this catalogue.
"""

from collections import defaultdict
from dataclasses import dataclass


PREFIX = 'XKAH.43.'
RIM = tuple('MechServiceScrew' + end for end in ('TopL', 'TopR', 'SideR', 'Foot', 'SideL'))
EARS = tuple(n.replace('ServiceScrew', 'PanelEar') for n in RIM)
SEAL = tuple('MechServiceBaseSealScrew' + end for end in ('Left', 'Right', 'Rear'))
INNER = tuple('MechServiceBaseInnerScrew' + end for end in ('FrontL', 'FrontR', 'RearL', 'RearR'))


@dataclass(frozen=True)
class Part:
    pos: int
    code: str
    name: str
    # Each anchor is ONE physical instance or owner group. Skins/markings/feet
    # select the same position for a leader; they never increase the quantity.
    anchors: tuple
    skins: tuple = ()


def part(pos, code, name, anchors, skins=()):
    return Part(pos, code, name, (anchors,) if isinstance(anchors, str) else tuple(anchors), tuple(skins))


def key(pos, code, name, side):
    native = 'MechOuterKey' + side
    return part(pos, code, name, native, [native + suffix for suffix in ('Mark', 'Field', 'Foot')])


# Internal reconstruction designations, NOT article numbers or hardware standards.
# A parent has exactly one row for a child assembly, irrespective of its solids.
LEVELS = {
    '000': (
        part(1, '100', 'Часть верхняя', 'UpperUnit'),
        part(2, '200', 'Часть нижняя', 'LowerUnit'),
    ),
    '100': (
        part(1, '110', 'Корпус верхний', 'Housing'),
        part(2, '130', 'Кассета лицевая', 'Fascia'),
        part(3, '140', 'Обод световой', 'LightRing'),
        part(4, '150', 'Аккумулятор XYKA PRO', 'Battery'),
        part(5, '170', 'Нагреватель', 'Heater'),
        part(6, '180', 'Плата основная в сборе', 'MainPCB'),
        part(7, '190', 'Плата дисплея в сборе', 'DisplayPCB'),
        part(8, '160', 'Жгут проводов', 'Harness'),
        part(9, '101', 'Винт крепления кассеты', RIM),
        part(10, '102', 'Штырёк закрытия', 'MechClosurePin'),
        # Section fixture: Mounts. Revised model: already inside LowerBody.
        part(11, '103', 'Ось шарнира', 'MechHingeAxle'),
    ),
    '200': (
        part(1, '210', 'Основание с ложементом', 'LowerBody'),
        part(2, '220', 'Чаша съёмная', 'Pod'),
    ),
    '220': (
        part(1, '221', 'Корпус чаши', 'MechRemovablePod', ('MechPodWallMark',)),
        part(2, '222', 'Сетка чаши', 'MechPodScreen'),
        part(3, '223', 'Крышка чаши', 'MechPodLid'),
    ),
    '130': (
        part(1, '131', 'Накладка лицевая', 'MechFrontFilm'),
        part(2, '134', 'Носитель клавиш', 'MechKeyCarrier'),
        part(3, '135', 'Рамка межплатная', 'MechCartridgeFrame'),
        part(4, '136', 'Опора дисплейной платы', ('MechDisplaySeatL', 'MechDisplaySeatR')),
        key(5, '137', 'Клавиша левая', 'L'),
        key(6, '138', 'Клавиша центральная', 'C'),
        key(7, '139', 'Клавиша правая', 'R'),
    ),
    '131': (
        part(1, '132', 'Маска лицевой накладки', 'MechServiceCover'),
        part(2, '133', 'Участок оптический', 'MechCoverWindow'),
    ),
    '110': (
        # Section fixture has the well; final CAD adds the fixed contact faces.
        # None of these is part of the removable battery envelope.
        part(1, '111', 'Гнездо аккумулятора', 'MechPackWell',
             ('MechPackWellMouth', 'MechPackSeatCarrier', 'MechPackSeatSockets')),
        part(2, '112', 'Кожух верхний', 'MechUpperFairing', ('MechBrandMark', *EARS)),
        part(3, '113', 'Перекладина проёма', 'MechNoseBridge'),
        part(4, '114', 'Звено шарнира верхнее', 'MechRearHingeLeaf'),
        part(5, '115', 'Клавиша аккумулятора', 'MechPackReleaseKey', ('MechPackReleaseKeyField',)),
        part(6, '116', 'Направляющая штырька', 'MechClosurePinGuide'),
        part(7, '117', 'Уплотнение нагревателя', 'MechServiceBaseGasket'),
        part(8, '118', 'Вставка внутренняя', 'MechServiceBaseInsert'),
        part(9, '119', 'Винт под уплотнением', SEAL),
        part(10, '120', 'Винт внутренней основы', INNER),
    ),
    '170': (
        part(1, '171', 'Щиток теплозащитный', 'MechHeatGuard',
             ('MechHeatGuardHotSymbol', 'MechHeatGuardCaption', 'MechHeatGuardFixingMarks',
              'MechHeatGuardCenterMark')),
        part(2, '172', 'Обод щитка', 'MechHeatGuardRim', ('MechHeatGuardRimLegend',)),
        part(3, '173', 'Диск нагревательный', 'MechHeaterPlate', ('MechHeaterFaceBands',)),
        part(4, '174', 'Обойма нагревателя', 'MechHeaterCarrier'),
    ),
}
# This mapping is local to ONE assembly; never flatten nested quantities.
SCOPE = {'000': 'Assembly', '100': 'UpperUnit', '200': 'LowerUnit', '220': 'Pod',
         '130': 'Fascia', '131': 'MechFrontFilm', '110': 'Housing', '170': 'Heater'}
MODULE_UNIT = {p.anchors[0]: 'UpperUnit' for p in LEVELS['100'] if p.pos <= 8}
MODULE_UNIT.update(LowerBody='LowerUnit', Pod='LowerUnit', Mounts='UpperUnit')


def _catalog(rows):
    table = {}
    if len({r.pos for r in rows}) != len(rows) or len({r.code for r in rows}) != len(rows):
        raise ValueError('Repeated local position or designation')
    for r in rows:
        for name in (*r.anchors, *r.skins):
            if name in table:
                raise ValueError(f'Repeated native ID in one specification: {name}')
            table[name] = r
    return table


_LOCAL = {k: _catalog(rows) for k, rows in LEVELS.items()}


def _direct(parent, item):
    """Use the real installed path, not prefix matching or the exploded links."""
    if SCOPE[parent] not in item.chain:
        raise KeyError(f'{item.name}: outside {PREFIX}{parent}')
    matches = {_LOCAL[parent][n] for n in (item.name, *item.chain) if n in _LOCAL[parent]}
    if len(matches) != 1:
        raise KeyError(f'{PREFIX}{parent}: no unique position for {item.name} in {item.chain}')
    return matches.pop()


def position_by_id(parent, native_id, a=None):
    """Local number for a CAD ID or Scene Item. Unknown/wrong scope -> KeyError.

    parent: '130' or 'XKAH.43.130' (also accepts 'XKAH.43.130 СБ').
    For the hinge axle, whose parent changed, pass the scene or its Item.
    Example: position_by_id('130', 'MechOuterKeyRMark') == 7.
    """
    parent = str(parent).strip().partition(' ')[0].removeprefix(PREFIX)
    local = _LOCAL[parent]
    if not isinstance(native_id, str):
        return _direct(parent, native_id).pos
    if a is not None:
        sc = getattr(a, 'scene', a)
        if native_id in sc.named:
            return _direct(parent, sc.named[native_id]).pos
        # Project a container (e.g. MechFrontFilm in .100) onto this level.
        # Never assign a single balloon to Mounts if it contains different rows.
        numbers = set()
        for item in sc.items:
            chain = item.chain
            if SCOPE[parent] in chain and native_id in chain[chain.index(SCOPE[parent]) + 1:]:
                numbers.add(_direct(parent, item).pos)
        if len(numbers) == 1:
            return numbers.pop()
        raise KeyError(f'{PREFIX}{parent}: no unique installed position for {native_id}')
    if native_id == 'MechHingeAxle':
        raise KeyError('MechHingeAxle changed owner; pass its Scene Item or a=Assets/Scene')
    if native_id in local:
        return local[native_id].pos
    # A housing/film/guard surface also has an unambiguous *ancestor* number.
    for row in LEVELS[parent]:
        if row.code in LEVELS:
            try:
                position_by_id(row.code, native_id)
            except KeyError:
                continue
            return row.pos
    raise KeyError(f'{PREFIX}{parent}: unknown ID {native_id}; pass a=Assets/Scene for leaf lookup')


def _check_same_shape(sc, row):
    """These particular screw/seat stations use the same oriented profile.

    Do not rely on matching labels, polygon counts, bounds or volume alone:
    compare the translated solids themselves. Fail closed on a changed part.
    """
    reference = sc.named[row.anchors[0]].shape
    if len(reference.Solids) != 1 or reference.Volume <= 0:
        raise ValueError(f'{row.code}: expected a single installed solid')
    centre = reference.Solids[0].CenterOfMass
    for name in row.anchors[1:]:
        other = sc.named[name].shape.copy()
        if len(other.Solids) != 1:
            raise ValueError(f'{name}: expected a single solid in {row.code}')
        other.translate(centre - other.Solids[0].CenterOfMass)
        common = reference.common(other).Volume
        difference = abs(reference.Volume - common) + abs(other.Volume - common)
        if not difference <= max(1e-6, reference.Volume * 1e-6):
            raise ValueError(f'{name}: distinct B-rep cannot be counted with {row.anchors[0]}')


def installed_bom(a):
    """Validate all represented levels and return {parent: [(Part, quantity), ...]}.

    Physical presence of anchors is mandatory. Unknown leaves in a detailed
    level, or misplaced cross-module parts, stop the issue rather than quietly
    changing totals. At a black-box boundary the real group counts just once.
    """
    sc = getattr(a, 'scene', a)
    if not sc.structured or set(sc.units) != {'UpperUnit', 'LowerUnit'}:
        raise ValueError('Specification requires a native two-unit installed assembly')
    if set(sc.roots) != set(MODULE_UNIT):
        raise ValueError(f'Unexpected native functional groups: {set(sc.roots) ^ set(MODULE_UNIT)}')
    for item in sc.items:
        if item.unit != MODULE_UNIT[item.root]:
            raise ValueError(f'Wrong unit: {item.name} / {item.chain}')
    # Key witnesses at black-box boundaries. A printed PCB representation must
    # have a board; the removable bowl must not absorb its fixed receiver.
    for name, root in (('MechChamberInsert', 'LowerBody'), ('MechLightRing', 'LightRing'),
                       ('MechTopBridge', 'LightRing'), ('MechBatteryEnvelope', 'Battery'),
                       ('PcLaminateCore', 'MainPCB'), ('UiSubstrate', 'DisplayPCB'),
                       ('UiKeyMembrane', 'DisplayPCB')):
        if name not in sc.named or sc.named[name].root != root:
            raise ValueError(f'Missing or misplaced {root}/{name}')
    # Distinguish revised native ownership from a simply missing fastener.
    axle = sc.named.get('MechHingeAxle')
    if axle is None or axle.root not in ('Mounts', 'LowerBody'):
        raise ValueError('Missing/misplaced hinge axle')
    result = {}
    for parent, scope in SCOPE.items():
        seen = defaultdict(set)
        covered = set()
        for item in sc.items:
            if scope not in item.chain:
                continue
            row = _direct(parent, item)
            seen[row].update(set(row.anchors).intersection((item.name, *item.chain)))
            if item.name in covered:
                raise ValueError(f'{parent}: repeated installed leaf {item.name}')
            covered.add(item.name)
        resolved = []
        for row in LEVELS[parent]:
            if parent == '100' and row.anchors == ('MechHingeAxle',) and axle.root == 'LowerBody':
                continue
            missing = set(row.anchors) - seen[row]
            if missing:
                raise ValueError(f'{PREFIX}{parent}, pos. {row.pos}: missing installed {sorted(missing)}')
            if len(row.anchors) > 1:
                _check_same_shape(sc, row)
            resolved.append((row, len(seen[row])))
        result[parent] = resolved
    return result
