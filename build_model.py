#!/usr/bin/env python3
"""Build the native reconstruction using FreeCAD's Python and standard workbenches."""

import argparse
import os
from pathlib import Path
import sys
import tempfile
import traceback

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'model'))


def build(out):
    import FreeCAD as App
    import FreeCADGui as Gui

    if not App.GuiUp:
        Gui.showMainWindow()
    import main_pcb
    import display_board
    import mechanics
    import harness
    from context import Context, PACKAGE_REFERENCES, text_property
    from export_step import export_sets
    from native_view import present
    from atlas_appearance import annotate

    doc = App.newDocument('XKAH_PRO_A43_rebuilt')
    doc.Label = 'XKAH PRO  /  A4.3  •  фотореконструкция'
    doc.Comment = ('Геометрия данного экземпляра реконструирована по фотографиям. '
                   'ESTIMATE: не выпускной чертёж, не заводской BOM и не схема подключения.')
    with tempfile.TemporaryDirectory(prefix='xkah-output-', dir=out) as tmp:
        c = Context(doc, tmp, [('Main PCB', main_pcb.PARAMS), ('Display PCB', display_board.PARAMS),
                               ('Mechanics', mechanics.PARAMS), ('Harness', harness.PARAMS),
                               ('Fixed packages / REF', PACKAGE_REFERENCES)])
        c.frames()
        evidence = doc.addObject('App::DocumentObjectGroup', 'Evidence')
        evidence.Label = 'C  •  Базисы и достоверность'
        for key, text in {
            'ReferenceSystem': 'X вправо при взгляде на экран; Y от панели внутрь; Z вверх. Единицы: мм.',
            'MainFrame': 'u поперёк от S± к B+, v вверх от торца F±, w наружу от маски на стороне компонентов; в закрытом корпусе w = +Y.',
            'DisplayFrame': 'u вправо, v от клавиш к стеклу; w от маски к пользователю (−Y).',
            'EvidenceOrder': '15 оригиналов владельца → корпусная документация IC → патенты как вариант → публичная схема только визуально.',
            'Interpretation': 'Сигналы S± и KEY+/GND не привязаны к конкретному датчику. Не показана неподтверждённая скрытая проводка.',
            'Editing': 'Жёлтые значения на листе Parameters — ESTIMATE. Внешний вид и разнос используют одни и те же физические тела.',
        }.items():
            text_property(evidence, key, text)
        for title, module in [('main PCB', main_pcb), ('display PCB', display_board),
                              ('mechanical assemblies', mechanics), ('fourteen conductors', harness)]:
            print(f'=== Build: {title}', flush=True)
            module.build(c)
            doc.recompute()
        annotate(doc, evidence)
        print('=== Validate leaf shapes', flush=True)
        for obj in c.physical:
            if obj.Shape.isNull() or not obj.Shape.isValid():
                raise ValueError(f'Invalid physical shape: {obj.Name} / {obj.Label}')
        c.make_exploded()
        doc.recompute()
        present()
        native = c.root / 'XKAH_PRO_A43_rebuilt.FCStd'
        print('=== Save native assembly', flush=True)
        doc.saveAs(str(native))
        c.registers()
        export_sets(c)
        App.closeDocument(doc.Name)
        for file in c.root.iterdir():
            if file.is_file():
                os.replace(file, out / file.name)
        print(f'=== Saved {len(c.physical)} physical features: {out}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=str(ROOT), type=Path)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    try:
        build(args.out.resolve())
    except BaseException:
        traceback.print_exc()
        code = 1
    else:
        code = 0
    # Embedded FreeCAD/Qt owns native process-global singletons; all documents are saved explicitly.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
