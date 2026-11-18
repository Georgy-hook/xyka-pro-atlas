"""Observed finishes and dimensional comparisons for the PRO atlas (not material tests).

The web and the FreeCAD palette use this one catalogue. An empty material is
intentional: an unverified material is preferable to a guessed datasheet.
"""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
XYKA = 'https://xyka.pro/'
MANUAL = 'https://www.animashop.cz/user/related_files/xkah_user_manual.pdf'
WIDTH = 'https://smokedex.info/en/p/H8PEDkC54u6/xkah-pro-hookah-e-hmd'
DIAMETER = 'https://hookahministry.com/products/xkah-pro-graphite'
PRODUCT = 'https://xkah.us/products/xkah-pro'
POD = 'https://smokaz.de/xkah-pro-ersatz-pod-2er-pack'
METAL = 'https://hookain.eu/electric-bowls-hmds/xkah-pro-e-hmd-smokebox-graphite'
RED = 'https://www.reddit.com/r/hookah/comments/1walb9l/'
OPEN = 'https://hookahx.de/en/xkah-pro-innenaufbau-zerlegen/'
EARLIER = 'https://hookahcat.com.ua/ru/xkah-pro-electronic-hookah-bowl-review'
BLUE_DISK = 'https://hookahx.de/wp-content/uploads/xkah-innenaufbau-heizspiralen-platte-v1.jpg'
A43 = 'https://hookahx.de/wp-content/uploads/xkah-innenaufbau-hauptplatine-v1.jpg'
A1 = 'https://hookahcat.com.ua/image/catalog/Blog-images/blog/xkln/xkah-pro-plata-upravlinnya.jpg'
KEYS = 'https://hookahcat.com.ua/image/catalog/Blog-images/blog/xkln/xkah-pro-5-gvyntiv-pid-nakladkoyu.jpg'
BACK = 'https://static.tildacdn.com/tild6433-3632-4761-b132-623036633939/6.jpg'
QFN = 'https://www.arterychip.com/download/DS/DS_AT32F421_V2.02_EN.pdf'


def finish(slug, name, body, lower_edge):
    # Only skins documented in colour in the side, rear and bottom views.
    # The silver controls, window, encapsulated battery and boards stay fixed.
    return dict(id=slug, label=name, swatch=body, source=XYKA+'xyka-'+slug, colors={
        'MechUpperFairing': body,
        'MechLowerShroud': body,
        'MechRearClevis': body,
        'MechRearHingeLeaf': body,
        'MechBevelGrip': lower_edge,
    })


FINISHES = [
    finish('graphite', 'Графит', '#525457', '#393B3E'),
    finish('silver', 'Серебро', '#C0C2C5', '#A3A5A7'),
    finish('blue', 'Синий', '#8D9DD4', '#7987BC'),
    finish('pink', 'Розовый', '#CD9AC4', '#B582A9'),
]


def observation(title, status, text, source, url, *parts):
    return dict(title=title, status=status, text=text, source=source, url=url, parts=list(parts))


OBSERVATIONS = [
    observation('Клавиатура, не три гладких колпачка', 'Видно на фото',
                'На наружной панели три светлых обода. Внутри — фактурные поля: слева шеврон вниз, '
                'в центре молния, справа шеврон вверх. CAD передаёт поверхностный рельеф. '
                'Ни сквозное сверление, ни сплав колпачков фотографией не доказаны.',
                'Макро снятой рамки · HookahCat', KEYS, 'MechOuterKeyCField', 'MechOuterKeyLMark',
                'MechOuterKeyCMark', 'MechOuterKeyRMark'),
    observation('Прорези корпуса и рельеф замка', 'Видно на фото',
                'Рядом с шарниром виден ряд из пяти щелей разной высоты. На скосе основания — '
                'чередование глухих граней и тёмных окон. На кнопке шарнира видна мелкая сетка, '
                'а не такие же сквозные окна. Оборотные фотографии четырёх цветов сохраняют светлые кнопки.',
                'XYKA · крупный план основания', BACK, 'MechRearEjectKey', 'MechBevelGrip', 'MechUpperFairing'),
    observation('Две платы, две ревизии', 'Не взаимозаменять',
                'На разборке с чёрной маской читаются A4.3 и 20260204; совпадают форма и '
                'положение зуммера и белой колодки. В отдельной разборке HookahCat плата зелёная, '
                'с маркировкой A1 и 20250617. Цвет платы, её компоненты и проводку A1 не переносили.',
                'Макро чёрной платы · u/Glad-Way8509, через HookahX', A43, 'PcMaskFace', 'PcBuzzer_Body'),
    observation('Под наружной клавишей', 'Фото владельца',
                'IMG_8917/8918 показывают три кремовых толкателя и отдельную прямоугольную '
                'перфорированную металлическую область на 20260305A. Это не фактура наружных клавиш. '
                'На другом серийном аппарате также видны отдельный дисплейный модуль и шлейф.',
                'Разборка Pro · раздел о дисплее', OPEN, 'UiPerforatedLand', 'UiPlungerC', 'UiFlexReturn'),
    observation('Нагревательный диск с обратной стороны', 'Другой разобранный Pro',
                'Вместо прежнего сплошного условного цилиндра показана синяя перфорированная '
                'сторона с контрастными дугами. Отверстия за выводами не дорисованы. '
                'Положение по углу, толщина и невидимый пакет слоёв остаются оценкой. Рисунок не электрическая схема.',
                'Фотография диска · u/Glad-Way8509, через HookahX', BLUE_DISK, 'MechHeaterPlate', 'MechHeaterFaceBands'),
    observation('Четыре каталожных покрытия', 'Серия XYKA PRO',
                'Окрашены обе половины кожуха, внешний шарнир и нижний скос. Кассета экрана, '
                'аккумулятор, контакты, светлые клавиши и изоляция проводов не меняют цвета вместе с ними. '
                'Образцы sRGB подобраны по боковым студийным кадрам при рассеянном свете; это не RAL и не спектрометрия.',
                'Официальный региональный каталог', XYKA+'catalog', 'MechUpperFairing', 'MechLowerShroud'),
    observation('У деталей одного цвета разный материал', 'Документация и оговорки',
                'XYKA указывает нержавеющую сталь для съёмной чашки и силикон для ложемента. '
                'Для наружного кожуха дилер указывает алюминий. Эти утверждения не распространяются '
                'на кнопки, шарнир, крышку батареи или все блестящие детали.', 'XYKA · вопросы и ответы', XYKA,
                'MechRemovablePod', 'MechChamberInsert'),
]


def dim(name, cad, reference, status, url):
    return dict(name=name, cad=cad, reference=reference, status=status, url=url)


DIMENSIONS = [
    dim('Высота закрытого корпуса · Z', '154 ± 9 мм', '160 мм — SmokeDex и HookahMinistry, округлено',
        'Оценка CAD согласуется с каталогами. Крайние точки размера не заданы.', WIDTH),
    dim('Поперечный габарит · X', '78 ± 7 мм', '75 мм — ширина (SmokeDex)',
        'Не заменяет обмер максимальной ширины A4.3.', WIDTH),
    dim('Диаметр из карточки продавца', 'Не отдельный габарит CAD', '≈70 мм — диаметр, сечение не указано',
        'Не приравнивать ни к ширине 75 мм, ни к глубине с шарниром.', DIAMETER),
    dim('Глубина с шарниром · Y', '98 ± 9 мм', 'На боковом фото Y/Z ≈504/788. При Z=154…160 мм получаем ≈99…102 мм.',
        'Перекрёстная оценка по силуэту. Вид спереди даёт X/Z ≈383/787. Глубина не опубликована как паспортный размер.', PRODUCT),
    dim('Порт снизу / у горла', '21,5 ± 1 / 16 ± 1 мм', 'Ø21,5 → Ø16 мм внутри (FAQ); «21 мм» — краткое описание',
        'Справка по серии; не наружный диаметр. Проверить на конкретном экземпляре.', XYKA),
    dim('Сменная чашка · ширина × высота', '42 ± 1,6 × 23,3 ± 1,3 мм', '42 × 23,3 мм у сменного pod',
        'Размер аксессуара по продавцу, не корпуса и не нагревательного диска.', POD),
    dim('Основная PCB · Ш × Д × Т', '29,3 × 64,2 × 1,45 мм', '±2 / ±4 / ±0,45 мм',
        'Оценка по фото A4.3 и номиналу корпуса U3; не измерено.', QFN),
    dim('Дисплейная PCB · Ш × Д × Т', '28,2 × 50,4 × 0,8 мм', '±3,5 / ±6 / ±0,25 мм',
        'Оценка по IMG_8917/18. Верх обрезан; масштаб слабее, чем у основной PCB.', None),
    dim('Фактура клавиш · шаг / глубина', '0,74 / 0,095 мм', 'На центральной клавише поле ≈71 × 80 px внутри ≈94 × 125 px',
        'Параметры визуальной модели; глубину текстуры по фотографии измерить нельзя.', KEYS),
]


MATERIALS = {}
MATERIAL_SOURCES = {}


def material(ids, text, source):
    for part in ids.split():
        MATERIALS[part] = text
        MATERIAL_SOURCES[part] = source


material('MechUpperFairing MechLowerShroud', 'Кожух: алюминий по карточке дилера. Сплав и способ получения оттенка неизвестны.', METAL)
material('MechRemovablePod', 'Съёмная чаша: нержавеющая сталь по региональному описанию XYKA. Марка стали не указана.', XYKA)
material('MechChamberInsert', 'Нижний ложемент: силикон по описанию XYKA. Профиль и твёрдость не измерялись.', XYKA)
material('MechServiceCover', 'В фоторазборке накладка описана как пластиковая. Полимер и артикул не опубликованы.', OPEN)
material('MechHeatGuard', 'На опубликованной разборке Pro щиток описан как перфорированная нержавеющая сталь; марка неизвестна.', OPEN)
material('MechHeaterPlate MechHeaterFaceBands', 'Синяя сторона и светлые дуги видны на фото. Материал основы, покрытия и скрытых слоёв не установлен.', BLUE_DISK)
material('MechOuterKeyL MechOuterKeyC MechOuterKeyR MechFrontUnlockKey MechPackReleaseKey MechRearEjectKey '
         'MechOuterKeyLField MechOuterKeyCField MechOuterKeyRField MechRearEjectKeyField MechPackReleaseKeyField MechFrontUnlockKeyField',
         'Светлая отделка с металлическим блеском. По снимкам не отличить цельный металл от металлизированного пластика.', KEYS)
material('UiPerforatedLand', 'Светлая металлическая область у толкателя; сплав и функция неизвестны.', 'IMG_8917.jpg / IMG_8918.jpg')
material('UiPlungerL UiPlungerC UiPlungerR', 'Кремовая подвижная головка внутри штампованной рамки. Марка материала не установлена.', 'IMG_8917.jpg / IMG_8918.jpg')
material('MechBatteryEnvelope MechPackCap', 'Чёрная оболочка съёмного блока. Пластик по виду; состав, элементы и внутренние соединения не устанавливались.', XYKA+'akkumulyator-xyka')
material('UiFlexFoot UiFlexReturn', 'Янтарная гибкая лента с отдельными контактами; материал и пакет плёнок документально не подтверждены.', 'IMG_8917.jpg / IMG_8918.jpg')

SOURCES = [
    ('XYKA PRO: каталог четырёх расцветок', XYKA+'catalog'),
    ('XKAH: закрытый Pro, фронт и профиль для проверки пропорций', PRODUCT),
    ('Руководство XKAH Pro, печатные с. 03–04: фронт, тыл, низ и открытый узел', MANUAL),
    ('SmokeDex: Pro Graphite, серийные высота и ширина', WIDTH),
    ('HookahMinistry: отдельно названный диаметр и высота', DIAMETER),
    ('Smokaz: габарит сменной чашки', POD),
    ('Hookain: заявленный материал корпуса Pro', METAL),
    ('Первичная публикация разборки · u/Glad-Way8509', RED),
    ('HookahX: те же фотографии с атрибуцией; не второй независимый разбор', OPEN),
    ('HookahCat: собственный разбор аппарата с платой A1', EARLIER),
    ('HookahCat: маркировка и зелёная маска другой ревизии', A1),
    ('Artery AT32F421: размеры корпуса U3, §6.5, таблица 50', QFN),
]


def web_notes():
    return dict(finishes=FINISHES, observations=OBSERVATIONS, dimensions=DIMENSIONS,
                materials=MATERIALS, sources=[dict(title=t, url=u) for t, u in SOURCES])


def publish(out):
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(web_notes(), ensure_ascii=False, indent=2)
    out.write_text('// Generated by model/atlas_catalog.py.\nwindow.ATLAS_NOTES = '+data+';\n', encoding='utf-8')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out', type=Path, default=ROOT/'atlas'/'evidence.js')
    publish(cli.parse_args().out)
