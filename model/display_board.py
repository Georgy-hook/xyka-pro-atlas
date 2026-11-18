"""20260305A as photographed, in the integrator's local UI frame (u,v,w).

Public API: PARAMS, INTERFACE and build(c). Definitions of positional aliases,
uncertainty and sheet-driven housing datums are in display_interface.py. See
also display_registration.json for photo-plane fits and reserved check points.
The parent owns the cassette placement, external lens/bezel and external keys.
"""

import FreeCAD as App
import Part

from display_flex import flex
from display_gasket import build as key_membrane
from display_interface import INTERFACE, PARAMS
from display_laminate import board, color_exposed_core, display_stack
from display_lands import contacts, perforated_field, silkscreen, via_witnesses
from display_switches import switches


__all__ = ('PARAMS', 'INTERFACE', 'build')


def build(c):
    root = c.groups['display']
    pcb = c.sub(root, 'UiPrintedBoard', '20260305A · плата и маркировка')
    substrate = board(c, pcb)
    lands = c.sub(pcb, 'UiPads', 'Контактные площадки и металлография')
    contacts(c, lands)
    perforated_field(c, lands)
    via_witnesses(c, lands)
    ink = c.sub(pcb, 'UiSilk', 'Шелкография 20260305A')
    silkscreen(c, ink)
    controls = c.sub(root, 'UiTactiles', 'Три тактовые кнопки на PCB')
    switches(c, controls)
    key_membrane(c)
    lcd = c.sub(root, 'UiPanelStack', 'LCD · опорный пакет, обод и стекло')
    display_stack(c, lcd)
    flex(c, root)
    c.doc.recompute()
    color_exposed_core(substrate)
