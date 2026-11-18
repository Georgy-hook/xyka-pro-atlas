"""XKAH Pro service retention. Nominal master geometry in millimetres, not tooling.

Face axes are LOCAL to the -7.5 degree cassette; cap and upper deck are WORLD
masters. Apply the cuts before native scaling. Four rim stations are visible on the owner's
specimen. A fifth is registered ONLY from the open comparison A4.3; board
holes and the shell's blind optical routes are not screw locations.

The crown with its lugs is *one* removable moulding; the complementary teeth
are part of the fixed deck. Do not make four loose screws at the light band.
"""

import FreeCAD as App
import Part

from mech_profiles import cassette_frame, in_cassette
from mech_shapes import CY, MOLD, V, Y, Z, circle, moved, polygon, rotated, rounded_rect, scaled_part, turned


SEPTEMBER = 'https://www.reddit.com/r/hookah/comments/1walb9l/'
OCTOBER = 'https://www.reddit.com/r/hookah/comments/1xat220/'
UA_FACE = ('https://hookahcat.com.ua/image/catalog/Blog-images/blog/xkln/'
           'xkah-pro-5-gvyntiv-pid-nakladkoyu.jpg')
OWNER_RIM = 'IMG_AD206911-3187-4C31-BC25-74C98D584C6D.jpeg; IMG_8916/8917/8919/8920/8921'
RIM_SOURCE = OWNER_RIM + '; ' + SEPTEMBER + ' #1; ' + OCTOBER + ' #7–8; ' + UA_FACE
LIGHT_SOURCE = SEPTEMBER + ' steps 3–4, photos #1/#8/#12 (one album); ' + OCTOBER + ' #3, #7'
LIGHT_NOTE = ('Четыре зацепа накладки подсветки по рассказу; на фото видны снятый чёрный '
              'обод с белой вставкой и ушки, не четыре измеренных профиля. Окна язычков, '
              'клинья, часы и зазоры EST. Не отдельные винты или светодиоды.')

# ID, x, z. The lower two axes were moved WITH their original bored ears:
# d1f4b00 put them <1.25 mm from the skin edge; a recessed round head and its
# seat would clip through the continuous face. The asymmetry remains deliberate.
RIM_STATIONS = (('TopL', -15.25, 142.90), ('TopR', 15.25, 142.90),
                ('SideR', 17.20, 82.90), ('Foot', -1.90, 71.00),
                ('SideL', -16.70, 82.80))
HEAD_CLEAR_R = 1.40
SHANK_CLEAR_R = .90
BEARING_Y = .70
EAR_FACE_Y = 1.50


def rim_seat_tool():
    """Five coaxial *stepped* cuts (4 owner + 1 comparator). No cut in the removable overlay (y=.07–.25)."""
    tools = []
    for _, x, z in RIM_STATIONS:
        head = circle(HEAD_CLEAR_R, BEARING_Y + 1., x, -1., z, Y)
        bore = circle(SHANK_CLEAR_R, 4.5, x, BEARING_Y - .01, z, Y)
        tools.append(head.fuse(bore).removeSplitter())
    return Part.makeCompound(tools)


def cut_rim_seats(blank, add_pads=True):
    """Use on the unscaled rigid face carrier only. The optional backs of the
    seats extend to y=1.50 and bear against the captive housing ears;
    no new loose washer/seat, no cutter added to the physical parts list.
    """
    if add_pads:
        pads = [circle(1.72, EAR_FACE_Y - .55, x, .55, z, Y) for _, x, z in RIM_STATIONS]
        blank = blank.fuse(Part.makeCompound(pads))
    return blank.cut(rim_seat_tool()).removeSplitter()


def rim_screw(x, z):
    """Schematic recessed drive depression; not a bit selection or thread spec."""
    # Actual bearing at y=.70, top at .36 below the removable film; shank is
    # supported by the original clear bore. Only the drive envelope is known.
    profile = [(0., .49), (.39, .49), (.51, .36), (1.02, .36), (1.21, .40),
               (1.28, .48), (1.28, .65), (1.23, .70), (.74, .70),
               (.74, 3.98), (.61, 4.18), (0., 4.18)]
    solid = turned(profile)
    solid.rotate(V(), V(1, 0, 0), -90)
    return moved(solid, x, 0, z)


def rim_ear(ident, x, z, shell_local):
    """Keep the shell-contacting web and a true open Ø1.80 bore after the screw is removed."""
    radius = 1.98 if ident.startswith('Top') else 1.90
    # The cartridge frame starts at n=4.72; after moving its axis inward,
    # a side ear must not use the original deep top-ear web (formerly 4.94).
    depth = {'Foot': 3.05, 'SideR': 2.94, 'SideL': 2.94}.get(ident, 3.44)
    ring = circle(radius, depth, x, EAR_FACE_Y, z, Y)
    if ident.startswith('Top'):
        strap = Part.makeBox(radius * 2, depth, 5.35, V(x - radius, EAR_FACE_Y, z))
    elif ident in ('SideL', 'SideR'):
        x0 = x - 5.5 if ident == 'SideL' else x
        strap = Part.makeBox(5.5, depth, 2 * radius, V(x0, EAR_FACE_Y, z - radius))
    else:
        strap = Part.makeBox(2 * radius, depth, 5.55, V(x - radius, EAR_FACE_Y, z - 5.55))
    hole = circle(SHANK_CLEAR_R, depth + .50, x, EAR_FACE_Y - .25, z, Y)
    blank = ring.fuse(strap).cut(hole).removeSplitter()
    witness = V(x - 1.40, EAR_FACE_Y + depth / 2, z)
    pieces = blank.cut(shell_local).removeSplitter().Solids
    seated = [s for s in pieces if s.isInside(witness, 1e-6, False)]
    if len(seated) != 1:
        raise ValueError(f'{ident}: no unique seated shell ear at the retained bore')
    return seated[0]


def rim_hardware(c, upper, shell):
    """Replacement for mech_mounts.rim_hardware, not an additional call.

    Both original top screw IDs and all four shell-ear IDs survive. Two more
    screws are at visible owner stations. SideL alone uses the comparable
    September specimen (not visible behind the board in the owner's photo).
    The fixed ears and the removable fasteners belong to different parents.
    """
    fasteners = c.sub(c.groups['mounts'], 'MechPanelFixings', 'Винты под съёмной облицовкой · 4 видимых места + 1 сравнительное')
    ears = c.sub(upper, 'MechRimEars', 'Неподвижные проушины передней кассеты')
    cassette_frame(c, fasteners)
    cassette_frame(c, ears)
    fixed = in_cassette(shell, inverse=True)
    for ident, x, z in RIM_STATIONS:
        comparison = ident == 'SideL'
        source = SEPTEMBER + ' #1, #7; ' + UA_FACE if comparison else OWNER_RIM
        evidence = ('СРАВНИТЕЛЬНЫЙ A4.3 / положение EST, на снимке владельца закрыто платой'
                    if comparison else 'OWNER PHOTO / SEEN BORE, POSITION EST')
        scaled_part(c, ears, 'PanelEar' + ident, 'Проушина корпуса ' + ident + ' · координаты EST',
                    rim_ear(ident, x, z, fixed), MOLD, source, evidence,
                    'Сквозной канал Ø1.80 EST; проушина остаётся с верхним кожухом, не отверстие PCB.')
        scaled_part(c, fasteners, 'ServiceScrew' + ident, 'Утопленный винт кассеты ' + ident + ' · EST',
                    rim_screw(x, z), (.245, .254, .259), RIM_SOURCE, evidence + ' / HARDWARE EST',
                    ('Пятая ось получена по левой стороне sep01 с поправкой на перспективу, без отражения правой. '
                     if comparison else 'Одна из четырёх позиций по видимому отверстию нашего корпуса. ') +
                    'Головка, длина, резьба и профиль привода не измерены; не винт платы.')


# Azimuth measured from front (-Y) about +Z. Profile/clocking are estimates,
# not four independently measured locations. Keep clear of the front wire exit.
LIGHT_ANGLES = (-136., -47., 47., 136.)


def _light_stations(local):
    # The retail diffuser is narrower than the issued master. Move the whole
    # mating pair inward, never just a tongue or just its window/receiver.
    # Before rotation local lies on the front (negative-Y) ray.
    local = moved(local, 0, 1.68, 0)
    return [rotated(local, V(0, CY, 0), a) for a in LIGHT_ANGLES]


def light_tongues():
    """Tapered axial blades with open windows for the complementary deck teeth."""
    r = 27.70
    profile = [(-1.35, 143.31), (1.35, 143.31), (1.90, 144.03), (1.90, 150.98),
               (-1.90, 150.98), (-1.90, 144.03)]
    blade = Part.Face(polygon([V(x, CY - r, z) for x, z in profile])).extrude(V(0, -.79, 0))
    slot = Part.Face(rounded_rect(2.48, 1.64, .27)).extrude(V(0, 2.0, 0))
    slot.translate(V(0, CY - 29.0, 145.59))
    return _light_stations(blade.cut(slot).removeSplitter())


def light_mouths():
    """Negative clearance in the existing top deck, not holes through its outer finish."""
    slot = Part.makeBox(4.16, 1.12, 6.0, V(-2.08, CY - 28.65, 142.60))
    return _light_stations(slot)


def light_teeth():
    """Fixed inward-facing ramps. Horizontal underside retains the tongue's bottom sill."""
    profile = [(28.91, 145.14), (27.97, 145.14), (27.97, 145.31),
               (28.66, 146.15), (28.91, 146.15)]
    section = polygon([V(-.79, CY - r, z) for r, z in profile])
    tooth = Part.Face(section).extrude(V(1.58, 0, 0))
    return _light_stations(tooth)


def crown_with_light_clips(crown):
    """Use instead of the bare MechTopBridge in the *removable* light group."""
    return crown.fuse(Part.makeCompound(light_tongues())).removeSplitter()


def cut_upper_for_light(upper):
    """Use on nominal WORLD upper B-rep, not the diffuser, lower shroud or PCB."""
    sockets = upper.cut(Part.makeCompound(light_mouths()))
    return sockets.fuse(Part.makeCompound(light_teeth())).removeSplitter()
