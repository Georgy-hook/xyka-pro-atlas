"""Attach source-qualified surface descriptions and an optional palette to FCStd."""

import json

from atlas_catalog import FINISHES, MATERIALS, MATERIAL_SOURCES
from context import text_property


def annotate(doc, evidence):
    text_property(evidence, 'FinishCatalog', json.dumps(FINISHES, ensure_ascii=False), 'Presentation')
    text_property(evidence, 'ActiveFinish', 'graphite', 'Presentation')
    text_property(evidence, 'FinishNote', 'Палитра студийных видов XYKA PRO. Цвета экранные, не RAL. '
                  'Видимые оболочки переключает XKAH_Finish.FCMacro; геометрия не меняется.', 'Presentation')
    for name, note in MATERIALS.items():
        part = doc.getObject(name)
        if part is None:
            raise ValueError(f'Unknown surface ID: {name}')
        text_property(part, 'SurfaceMaterialNote', note, 'Surface')
        text_property(part, 'SurfaceMaterialSource', MATERIAL_SOURCES[name], 'Surface')
    for name, tint in FINISHES[0]['colors'].items():
        part = doc.getObject(name)
        rgb = tuple(int(tint[i:i+2], 16) / 255.0 for i in (1, 3, 5))
        part.ColorHex = tint
        if part.ViewObject:
            part.ViewObject.ShapeColor = rgb
            part.ViewObject.LineColor = tuple(max(.04, v*.4) for v in rgb)
