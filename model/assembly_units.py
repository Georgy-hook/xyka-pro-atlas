"""Installed hierarchy. The service split is across the body joint, not the PCBs."""

UNITS = {
    'UpperUnit': 'I  •  Верхняя часть: электроника, нагреватель и съёмный аккумулятор',
    'LowerUnit': 'II  •  Отсоединяемое основание с гнездом чаши',
}

# key, native document ID, label, mechanical parent, summary displacement (CAD mm).
# Actual presentation for every physical leaf is recorded in ServiceExplodeMM.
LAYOUT = (
    ('housing', 'Housing', '01  Верхний корпус и несущие элементы', 'UpperUnit', (0, 0, 0)),
    ('lower', 'LowerBody', '02  Нижняя часть и соединение с шахтой', 'LowerUnit', (4, 82, -78)),
    ('fascia', 'Fascia', '03  Передняя кассета и съёмная лицевая накладка', 'UpperUnit', (0, -66, 10)),
    ('light', 'LightRing', '04  Световое кольцо и его фиксаторы', 'UpperUnit', (72, 16, 50)),
    ('battery', 'Battery', '05  Съёмный аккумулятор', 'UpperUnit', (-50, -30, 112)),
    ('pod', 'Pod', '06  Съёмная чаша: корпус, сетка и крышка', 'LowerUnit', (92, 0, -45)),
    ('heater', 'Heater', '07  Нагреватель верхней части', 'UpperUnit', (-68, 0, -24)),
    ('main', 'MainPCB', '08  GYS005-S-088-A4.3 · основная плата', 'UpperUnit', (-40, -75, 15)),
    ('display', 'DisplayPCB', '09  20260305A · плата, силиконовая накладка и дисплей', 'UpperUnit', (-88, -75, 15)),
    ('wires', 'Harness', '10  Жгут · 10 припаянных жил и 4 жилы подсветки', 'UpperUnit', (-40, -75, 15)),
    ('mounts', 'Mounts', '11  Сервисный крепёж', 'UpperUnit', (0, -105, 10)),
)

MODULES = tuple(row[1] for row in LAYOUT)
SHORT_LABELS = dict(zip(MODULES, ('Верхний корпус', 'Основание', 'Лицевая кассета', 'Световой обод',
                                  'Аккумулятор', 'Табачная чаша', 'Нагреватель', 'Основная PCB',
                                  'Плата экрана', 'Жгут', 'Крепёж')))
GROUPS = {key: (name, label) for key, name, label, _, _ in LAYOUT}
PARENT = {key: unit for key, _, _, unit, _ in LAYOUT}
EXPLODE = {key: vector for key, _, _, _, vector in LAYOUT}
OUTER = ('housing', 'lower', 'fascia', 'light', 'mounts')
