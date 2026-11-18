"""XKAH / XYKA PRO A4.3 — exterior and provisional mechanical assembly.

Integration contract: Sheet aliases below plus BoardW/L/T and Ui* from the two
PCB modules. Global X is right looking at the display, global Y increases into
the barrel, Z is up from the lower socket mouth. The inclined exterior datum
crosses the old Y=0 reference at Z=84 mm nominal. PCB depth and board-bottom
height are local cassette coordinates; see mech_profiles.cassette_frame.
All lengths in mm. Native FreeCAD 1.1;
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
from mech_modules import base_interface
from mech_mounts import board_carrier, closure, external_keys, hinge
from retail_battery import battery
from retail_clips import rim_hardware
from retail_clips_base import add_service_base
from retail_pod import chamber, heater
from mech_shapes import MAN, OPEN_PHOTO, PACK_PHOTO, PHOTO, PODS, RETAIL, US_FAMILY, WO1, WO5, XYKA


SMOKEDEX = 'https://smokedex.info/en/p/H8PEDkC54u6/xkah-pro-hookah-e-hmd'


PARAMS = [
    ('BodyW', 78.0, MAN+' p.04: max width/height ≈134/259. '+SMOKEDEX+' lists WIDTH 75 mm; '+RETAIL+' lists DIAMETER 70 mm. Different datums; neither is a maximum calliper width of A4.3.', 7.0),
    ('BodyD', 98.0, MAN+' p.04, master chassis depth from Y=0 reference to rear hinge; inclined U-tip projects past this datum. '+US_FAMILY, 9.0),
    ('BodyH', 154.0, MAN+' p.04; '+RETAIL+' and '+SMOKEDEX+' both list 16 cm rounded, without datums. That falls in the photo estimate; do not rescale the unmeasured PCB seating.', 9.0),
    ('PanelBase', 68.0, PHOTO+'; lower edge of seated main PCB, height along inclined cassette, not global Z.', 6.0),
    ('MainDepth', 8.0, 'IMG_8919 / IMG_AD206911: inward distance normal to the inclined panel, to main PCB component face.', 1.65),
    ('UiBase', 77.0, MAN+' p.04 c,d,e; IMG_8917/8918. Lower UI board edge, height along inclined cassette.', 5.0),
    ('UiDepth', 3.5, 'IMG_8917, IMG_8918, IMG_8919: inward distance along panel normal to UI soldermask, not global Y.', .65),
    ('BatteryOD', 45.4, MAN+' pp.03–04 iii,a; '+PACK_PHOTO+'; whole cartridge outer envelope only.', 3.3),
    ('BatteryL', 80.0, 'https://xyka.pro/akkumulyator-xyka ; '+MAN+' p.03 iii. Axial envelope excluding the loose cable, estimated L/OD ≈1.77–1.82 in side views; no physical measurement.', 8.0),
    ('PodOD', 42.0, PODS+' retailer replacement pod, width 42 mm; not measured on owner unit.', 1.6),
    ('PodH', 23.3, PODS+' replacement pod height 23.3 mm; '+OPEN_PHOTO+'; revision fit unknown.', 1.3),
    ('HeatFaceD', 45.8, OPEN_PHOTO+' plate-to-pod apparent width; '+WO5+' Figs.3–8. Heater and sheet are an estimate.', 4.0),
    ('HeatPlateT', 1.5, WO5+' Figs.4–8; open Pro photo https://hookahx.de/wp-content/uploads/xkah-innenaufbau-heizspiralen-platte-v1.jpg shows a perforated disk, not its thickness or layer stack.', .8),
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
    add_service_base(c, upper)
    battery(c, upper)
    chamber(c, lower)
    heater(c)
