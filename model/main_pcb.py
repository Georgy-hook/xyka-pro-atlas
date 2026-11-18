"""GYS005-S-088-A4.3 main board, in its unplaced component-side local frame.

u = towards B+ in upright AD206911; v = from the F/clear end to the crest;
w = towards the populated side from its soldermask face. Units are mm.
All photo-derived layouts can be rebuilt without OpenCV or external images.
"""
import json
from pathlib import Path

import FreeCAD as App
import Part

from pcb_packages import package
from pcb_profile import build_profile

_REG = json.loads(Path(__file__).with_name('pcb_registration.json').read_text(encoding='utf-8'))
W = _REG['nominal_mm']['BoardW']
L = _REG['nominal_mm']['BoardL']
T = _REG['nominal_mm']['BoardT']

PARAMS = [
    ('BoardW', W, 'QFN-28 4×4; IMG_8914 → 8915 → 8909/AD, projective reconstruction, pcb_registration.json', 2.0),
    ('BoardL', L, 'IMG_8908/8909/8915/AD/8921; actual crest to B/F edge in rectified plane', 4.0),
    ('BoardT', T, 'IMG_8914/8921/8908 exposed edge band + approximate camera tilt; not caliper', .45),
    ('BoardMountDia', 1.90, 'IMG_8909/8920/8921/AD; apparent bores relative to calibrated component face', .35),
]

ANCHORS = {key: (u / W, v / L, w) for key, (u, v, w) in _REG['wire_exit_mm'].items()}
HOLES = {key: (u / W, v / L) for key, (u, v) in _REG['mechanical_holes_mm'].items()}
RGB_COLORS = ('white', 'blue', 'black', 'red')
RGB_DIRECTION = (0, 1, 0)


def project(photo_id, x, y):
    """Original, unrotated pixel -> normalized point on the *mask plane*."""
    h = _REG['views'][str(photo_id)]['pixel_to_local_mm']
    den = h[2][0] * x + h[2][1] * y + h[2][2]
    return ((h[0][0] * x + h[0][1] * y + h[0][2]) / den / W,
            (h[1][0] * x + h[1][1] * y + h[1][2]) / den / L)


def position(c, obj, u_norm, v_norm, z_mm=0, rotation_deg=0):
    obj.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), rotation_deg))
    c.at(obj, f'Parameters.BoardW * ({u_norm:.10f})',
         f'Parameters.BoardL * ({v_norm:.10f})', z_mm)
    return obj


def build(c):
    # All support modules are native geometry constructors; App::FeaturePython
    # and GUI/Draft proxies are not used, including for physical lettering.
    from pcb_surface import build_copper_and_print, ink
    from pcb_connections import build_connections, drill_for
    from pcb_passives import build_passives
    from pcb_printmap import build_printmap

    root = c.groups['main']
    board = c.sub(root, 'PcSubstrate', '01  Контур, сердцевина и маска')
    joints = c.sub(root, 'PcTerminals', '02  Припаянные жилы · отдельные вводы')
    pads = c.sub(root, 'PcPrinted', '03  Площадки и шелкография')
    devices = c.sub(root, 'PcDevices', '04  Микросхемы, диод, излучатель')
    sockets = c.sub(root, 'PcConnect', '05  Подсветка · колодка и вилка')
    small = c.sub(root, 'PcDiscretes', '06  Двухвыводные компоненты')

    def locate(obj, u_norm, v_norm, z_mm=0, rotation_deg=0):
        return position(c, obj, u_norm, v_norm, z_mm, rotation_deg)

    def at_mm(obj, u, v, z=0, deg=0):
        return locate(obj, u / W, v / L, z, deg)

    holes = _REG['mechanical_holes_mm']
    power = _REG['wire_exit_mm']
    drills = [(u, v, drill_for(k)) for k, (u, v, _) in power.items() if not k.startswith('RGB')]
    build_profile(c, board, holes, drills, W, L)
    build_connections(c, joints, sockets, power, at_mm, ink)
    build_copper_and_print(c, pads, at_mm, _REG)
    build_printmap(c, pads, project, at_mm, W, L)

    def add(name, label, style, uv, rotation=0, mark='', **kw):
        obj = c.sub(devices, name, label)
        at_mm(obj, *uv, deg=rotation)
        package(c, obj, style, mark, **kw)

    def px(photo, x, y):
        u, v = project(photo, x, y)
        return u * W, v * L

    # Bodies/hole are placed at mounting centres, not the parallax-shifted cap
    # centres visible in oblique 8908/09. 8915 control/holdout IDs are stable.
    add('PcU3', 'U3 · Artery AT32F421G8U7', 'qfn28', (-7.98, 28.20), 180)
    add('PcFlash', 'HCT · HC25FQ128GSSIG / 2546', 'flash8', (-8.12, 33.10), -90)
    add('PcU5', 'U5 · 6209A / 2522/33', 'tab4', (9.20, 46.00), 180, '6209A\n2522/33')
    add('PcU7', 'U7 · 6209A · тип не установлен', 'tab4', (9.20, 39.20))
    add('PcD26', 'D26 · SS14 · полоса к гребню платы', 'ss14', (13.12, 38.45), 90)
    add('PcUnknownQFN20', 'UNKNOWN · 5 контактов на грань', 'qfn16', (.72, 29.05))
    add('PcBuzzer', 'Зуммер · отверстие и литой знак +', 'buzz', (7.77, 17.97), -103, D=11.74, H=8.3)
    # Eight leaded body by F+/B+. Marking/manufacturer/purpose not resolved.
    add('PcUnknownBF', 'UNKNOWN · корпус с 8 выводами у F+', 'sop8small', (6.18, 8.30), 90)
    for ref, x in (('Q5', 165), ('Q6', 260), ('Q7', 348)):
        add('Pc' + ref, ref + ' · Y1', 'sot23', px('8915', x, 931), 90, 'Y1')
    for ref, x, y, rotation, code in (
        ('Q11', 145, 697, 0, ''), ('Q12', 137, 568, 0, ''),
        ('BesideR13', 689, 847, 180, ''), ('Q4', 715, 723, 180, ''),
        ('NearC18', 514, 793, 180, '2301F'), ('J11', 793, 648, 180, ''),
    ):
        add('PcUnknown' + ref, ref + ' · тип UNKNOWN', 'sot23',
            px('8915', x, y), rotation, code)
    add('PcUnknownQ8', 'Q8 · тип UNKNOWN', 'sot23', px('8914', 797, 959), 90)
    build_passives(c, small, project, locate, ink)
    return root
