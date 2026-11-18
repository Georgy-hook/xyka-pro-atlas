"""XKAH / XYKA PRO A4.3 — exterior and provisional mechanical assembly.

Integration contract: Sheet aliases below plus BoardW/L/T and Ui* from the two
PCB modules. X is right looking at the display, Y inward from the face (Y=0),
Z up from the lower socket mouth. All dimensions in mm. Native FreeCAD 1.1;
no FeaturePython or saved-document proxy. The build does not create any PCB.

Exterior stations follow the printed user manual p.04 and the actual regional
product views; not a mesh, decal, or legacy STEP template. CN309108835S front
perspective and USD1105588S1 priority-family Figs.1–8 support the fairing and
hinge silhouette; they do NOT show the present owner's exposed LCD, marking,
or a dimensional scale. Later WO sections are architectural alternatives only.
"""

import FreeCAD as App
import Part

from mech_case import housing
from mech_modules import base_interface, battery, chamber, heater
from mech_mounts import board_carrier, closure, external_keys, hinge, rim_hardware
from mech_shapes import MAN, OPEN_PHOTO, PACK_PHOTO, PHOTO, PODS, RETAIL, US_FAMILY, WO1, WO5, XYKA


PARAMS = [
    ('BodyW', 78.0, MAN+' p.04: max width/height ≈134/259. '+RETAIL+' lists 7 cm nominal, not a maximum-width measurement.', 7.0),
    ('BodyD', 98.0, MAN+' p.04: depth/width ≈169/134 across face and rear attachment hinge. '+US_FAMILY, 9.0),
    ('BodyH', 154.0, MAN+' p.04; '+RETAIL+' lists 16 cm. Scale reconciled with front silhouette, not measured on A4.3.', 9.0),
    ('PanelBase', 68.0, PHOTO+'; provisional seated lower edge of main PCB above U-tip, not pose of board pulled forward in photograph.', 6.0),
    ('MainDepth', 8.0, 'IMG_8919 / IMG_AD206911: estimated component-face Y leaving room for board backs and service frame.', 1.65),
    ('UiBase', 77.0, MAN+' p.04 c,d,e; IMG_8917/8918. Estimated keypad registration in exterior front outline.', 5.0),
    ('UiDepth', 3.5, 'IMG_8917, IMG_8918, IMG_8919: mask depth allowing recessed glass and exterior cap over bare plunger.', .65),
    ('BatteryOD', 45.4, MAN+' pp.03–04 iii,a; '+PACK_PHOTO+'; whole cartridge outer envelope only.', 3.3),
    ('BatteryL', 86.0, MAN+' p.03 iii; '+WO1+' Figs.8–12; cap-to-base envelope of a removable pack, internals unknown.', 8.0),
    ('PodOD', 42.0, PODS+' retailer replacement pod, width 42 mm; not measured on owner unit.', 1.6),
    ('PodH', 23.3, PODS+' replacement pod height 23.3 mm; '+OPEN_PHOTO+'; revision fit unknown.', 1.3),
    ('HeatFaceD', 45.8, OPEN_PHOTO+' plate-to-pod apparent width; '+WO5+' Figs.3–8. Heater and sheet are an estimate.', 4.0),
    ('HeatPlateT', 1.5, WO5+' Figs.4–8: flat plate envelope only; no measured or verified layer stack.', .8),
    ('StemMouthD', 21.5, XYKA+' regional FAQ: female lower opening 21.5 mm; compatible family, not a caliper reading of this unit.', 1.0),
    ('StemThroatD', 16.0, XYKA+' regional FAQ: female upper end 16 mm, A4.3 unverified.', 1.0),
    ('StemSocketL', 18.5, MAN+' p.04 j; '+WO1+' Figs.8,9,23: axial socket envelope, no measured engagement length.', 4.0),
]


def build(c):
    """Build only the mechanical physical leaves into the shared identity groups."""
    upper, lower, cover, outer, upper_shape, lower_shape = housing(c)
    rim_hardware(c, upper, upper_shape)
    board_carrier(c, cover)
    external_keys(c, upper, lower)
    hinge(c, upper, lower, outer)
    closure(c, upper, lower)
    base_interface(c, lower)
    battery(c, upper)
    chamber(c, lower)
    heater(c)
