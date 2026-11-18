"""Mechanical interface of the 20260305A module (local millimetres).

These are v0.1 estimates, not tolerances, active LCD dimensions or a pinout.
All values refer to the unmirrored, buttons-down front, before cassette placement.
"""

from pathlib import Path


FACE = 'IMG_8917 / IMG_8918 — 20260305A, two original macro views'
TRACE = 'IMG_8918, rectified on round contacts and PCB rails; IMG_8917 independent view'
SCALE = TRACE + '; estimated from ~3 × 4 mm tactile case, type UNKNOWN'
STACK = 'IMG_8917 / 18 oblique layer edges; IMG_8919 confirms closely stacked boards'
CROP = 'IMG_8908 / 09 / 19 silhouette against main carrier; far LCD/PCB ends cropped in 8917/18'
EST = 'OBSERVED / physical dimensions ESTIMATE'
LOW = 'ESTIMATE / obscured extent or height UNKNOWN'

# alias, nominal mm, basis, estimated plus/minus mm (not a statistical interval).
PARAMS = [
    ('UiW', 28.2, SCALE, 3.5),
    ('UiL', 50.4, CROP, 6.0),
    ('UiT', 0.8, 'IMG_8918: exposed laminate edge; not caliper measured', 0.25),
    ('UiHoleD', 1.25, 'Clear diameter of two visibly open bores; screw type UNKNOWN', 0.30),
    ('UiHoleLU', -7.9, TRACE, 0.95),
    ('UiHoleRU', 8.25, TRACE, 0.95),
    ('UiHoleV', 1.25, TRACE, 0.30),
    ('UiReliefR', 1.85, TRACE + '; side scallop radius', 0.45),
    ('UiReliefBite', 0.95, TRACE + '; inward bite of side scallop', 0.35),
    ('UiSwLU', -8.9, TRACE + '; estimated footprint centre under moving cap', 1.0),
    ('UiSwCU', 0.3, TRACE + '; estimated footprint centre under moving cap', 0.5),
    ('UiSwRU', 9.4, TRACE + '; estimated footprint centre under moving cap', 1.0),
    ('UiSwV', 6.8, TRACE + '; estimated footprint centre under moving caps', 0.9),
    ('UiCapW', 2.2, 'IMG_8917 / 18: cream actuator upper face, not external key', 0.35),
    ('UiCapL', 2.65, 'IMG_8917 / 18: cream actuator upper face, not external key', 0.40),
    ('UiPlungerTop', 2.0, STACK + '; extended cream actuator top from mask', 0.55),
    ('UiGlassW', 29.2, SCALE + '; visible lower tangencies adjusted for parallax', 2.8),
    ('UiGlassL', 33.0, CROP + '; panel edge seen under long side of main carrier', 4.5),
    ('UiGlassR', 5.2, TRACE + '; lower corners visible, upper corners assumed alike', 1.2),
    ('UiGlassU', 0.15, TRACE + '; centreline of glass', 0.75),
    ('UiGlassV', 17.4, TRACE + '; lower glass edge, not centre ordinate', 1.4),
    ('UiGlassTop', 2.2, STACK + '; exterior glass surface from soldermask', 0.7),
    ('UiGlassT', 0.43, STACK + '; lens/cover subdivision UNKNOWN', 0.16),
    ('UiBackT', 0.66, STACK + '; polymer backing and seating combined', 0.28),
]

NOMINAL = {name: float(value) for name, value, _, _ in PARAMS}
CONTACTS = (
    (-11.65, 3.67), (-4.37, 2.10), (-1.04, 2.06),
    (2.36, 2.05), (5.38, 2.07), (12.07, 3.51),
)
EDGE_PADS = ((11.88, 7.15), (11.77, 9.67), (11.76, 12.15), (11.69, 14.82))
HOLES = ((-7.9, 1.25), (8.25, 1.25))
BUTTONS = ((-8.9, 6.8), (0.3, 6.8), (9.4, 6.8))

INTERFACE = {
    'frame': 'u=0 board centre, +u global X; v=0 lower edge, +v global Z; w=0 mask, +w global -Y',
    'substrate': 'UiSubstrate',
    'board_mm': {'width': 28.2, 'length': 50.4, 'thickness': 0.8},
    'pcb_bounds_uvw_mm': ((-14.1, 14.1), (0.0, 50.4), (-0.8, 0.0)),
    'holes_mm': dict(zip(('UiHoleL', 'UiHoleR'), HOLES)),
    'hole_diameter_mm': 1.25,
    'plungers_mm': dict(zip(('UiPlungerL', 'UiPlungerC', 'UiPlungerR'), BUTTONS)),
    'plunger_face_wh_mm': (2.2, 2.65),
    'plunger_top_mm': 2.0,
    'glass': {
        'object': 'UiGlass', 'center_uv_mm': (0.15, 33.9), 'uv_size_mm': (29.2, 33.0),
        'radius_mm': 5.2, 'bottom_v_mm': 17.4, 'face_w_mm': 2.2,
        'bounds_uv_mm': ((-14.45, 14.75), (17.4, 50.4)), 'active_area': 'UNKNOWN',
    },
    'contacts_mm': {f'UiContact{i:02d}': uv for i, uv in enumerate(CONTACTS, 1)},
    'edge_pads_mm': {f'UiEdgePad{i:02d}': uv for i, uv in enumerate(EDGE_PADS, 1)},
    'registration_file': Path(__file__).with_name('display_registration.json').name,
    'uncertainty': '± values in PARAMS are engineering estimates; no dimension measured on specimen.',
    'mounting': 'Same frontal cassette; IMG_8919 does not show the inter-board connection or separation directly.',
}
