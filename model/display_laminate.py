"""Native board outline, routed cutouts and rounded LCD laminations."""

from display_interface import CROP, EST, FACE, LOW, STACK, TRACE
from display_native import (
    BRASS, CORE, MASK, P, circle, constrained_polygon, pad, rounded_loop,
    scale_u, scale_v, sketch,
)


def body(c, parent, name, label):
    b = c.doc.addObject('PartDesign::Body', name)
    b.Label = label
    parent.addObject(b)
    return b


def hole_placement(side):
    return (f'{P}UiHole{side}U * {P}UiW / 28.2 mm', f'{P}UiHoleV * {P}UiL / 50.4 mm')


def board(c, parent):
    p = c.p
    pcb = body(c, parent, 'UiSubstrate', '20260305A · основание PCB / вырезы и сверления')
    contour = sketch(pcb, 'UiOutline', 'Контур платы · видимые нижние фаски; дальний край ESTIMATE')
    # Normalized fractions define the photo outline. The four points hidden
    # under the far end of the LCD close the envelope, not a traced rear edge.
    outline = [
        (-10.60, 0.0), (11.07, 0.0), (14.10, 4.09), (14.10, 46.95),
        (10.65, 50.4), (-10.65, 50.4), (-14.10, 46.95), (-14.10, 4.35),
    ]
    constrained_polygon(contour, [
        (u * p['UiW'] / 28.2, v * p['UiL'] / 50.4, scale_u(u), scale_v(v) if v else None)
        for u, v in outline
    ])
    laminate = pad(pcb, contour, 'UiBoardBlank', 'Ламинат и маска до фрезеровки',
                   p['UiT'], P + 'UiT', reverse=True)
    drill = sketch(pcb, 'UiBoresAndReliefs', 'Два сквозных отверстия и две краевые выборки')
    for side in ('L', 'R'):
        ux, vy = hole_placement(side)
        circle(drill, p[f'UiHole{side}U'] * p['UiW'] / 28.2, p['UiHoleV'] * p['UiL'] / 50.4,
               p['UiHoleD'] / 2 + 0.035, ux, vy, P + 'UiHoleD / 2 + 0.035 mm')
    for sign, along in ((-1, 11.18), (1, 11.15)):
        center = sign * (p['UiW'] / 2 + p['UiReliefR'] - p['UiReliefBite'])
        ex = f'({P}UiW / 2 + {P}UiReliefR - {P}UiReliefBite) * {sign}'
        circle(drill, center, along * p['UiL'] / 50.4, p['UiReliefR'], ex, scale_v(along), P + 'UiReliefR')
    through = pcb.newObject('PartDesign::Pocket', 'UiThroughCuts')
    through.Label = 'Фрезеровка и сверление насквозь'
    through.Profile = drill
    through.Length = p['UiT']
    through.setExpression('Length', P + 'UiT')
    for obj in (contour, laminate, drill):
        obj.Visibility = False
    c.register(pcb, parent, MASK, TRACE + '; ' + CROP, EST,
               'Face w=0; FR4/mask combined. Lower chamfers and twin reliefs traced. '
               'Rear outline is cropped: closed under the glass without inventing mounts or a connector.')
    # Separate native annular barrels both define the actual clear circular
    # bores and allow extraction of their axes by the integration/drawing code.
    for side in ('L', 'R'):
        hole_metal(c, parent, side)
    return pcb


def hole_metal(c, parent, side):
    p = c.p
    name = 'UiHole' + side
    ring = body(c, parent, name, 'Отверстие ' + side + ' · кромка и открытый просвет')
    barrel = sketch(ring, name + 'BarrelProfile', 'Профиль внутренней стенки')
    clear = p['UiHoleD'] / 2
    for delta in (0.035, 0.0):
        circle(barrel, 0, 0, clear + delta, er=f'{P}UiHoleD / 2 + {delta:g} mm')
    wall = pad(ring, barrel, name + 'Wall', 'Тонкая стенка отверстия', p['UiT'], P + 'UiT', True)
    land = sketch(ring, name + 'LipProfile', 'Тонкая кромка на стороне кнопок')
    for delta in (0.13, 0.0):
        circle(land, 0, 0, clear + delta, er=f'{P}UiHoleD / 2 + {delta:g} mm')
    pad(ring, land, name + 'Lip', 'Светлая кромка · материал UNKNOWN', 0.027, None)
    wall.Visibility = False
    c.at(ring, *hole_placement(side), 0.0)
    c.register(ring, parent, BRASS, FACE, EST,
               'The dark through bore and pale rim are visible; finish, wall plating and fastening method UNKNOWN. '
               'The bare PCB drill is enlarged by the provisional 0.035 mm wall on each side.')


def _display_loop(profile, p, inset):
    """Centered about local u=0, referenced to the lower glass tangent v=0."""
    w = p['UiGlassW'] - 2 * inset
    l = p['UiGlassL'] - 2 * inset
    r = p['UiGlassR'] - inset
    bounds = (f'-{P}UiGlassW / 2 + {inset:g} mm', f'{inset:g} mm' if inset else None,
              f'{P}UiGlassW / 2 - {inset:g} mm', f'{P}UiGlassL - {inset:g} mm')
    rounded_loop(profile, -w / 2, inset, w, l, r, bounds, f'{P}UiGlassR - {inset:g} mm')


def display_stack(c, parent):
    p = c.p
    # The black backing seats directly on the board. A continuous slim rim
    # encloses the cell (a hollow frame, not another full intersecting slab).
    layers = [
        ('UiBacking', 'Опора LCD / тыльный носитель · материал UNKNOWN', (0.31,),
         0.0, p['UiBackT'], P + 'UiBackT', (0.115, 0.125, 0.135), LOW,
         'Bearing face w=0. Concealed seating/adhesive details unknown; no mounting screw inferred.'),
        ('UiRim', 'LCD · непрерывный металлический обод', (0.10, 0.34),
         P + 'UiBackT', p['UiGlassTop'] - p['UiGlassT'] - p['UiBackT'],
         f'{P}UiGlassTop - {P}UiGlassT - {P}UiBackT', (0.66, 0.68, 0.66), EST,
         'Thin hollow rim around cell; layer depths estimated from visible bright line.'),
        ('UiCell', 'LCD · тёмный пакет под стеклом', (0.34,),
         P + 'UiBackT', p['UiGlassTop'] - p['UiGlassT'] - p['UiBackT'],
         f'{P}UiGlassTop - {P}UiGlassT - {P}UiBackT', (0.15, 0.20, 0.26), EST,
         'Dark blue-grey laminate edge visible; optical/electrical layer construction UNKNOWN.'),
        ('UiGlass', 'LCD · покровное стекло, погашенный экран', (0.0,),
         f'{P}UiGlassTop - {P}UiGlassT', p['UiGlassT'], P + 'UiGlassT', (0.074, 0.088, 0.106), EST,
         'Dark face with curved lower corners, not an exterior faceplate. Active-pixel extent and controller UNKNOWN.'),
    ]
    for name, label, insets, zbase, thick, e_thick, rgb, confidence, note in layers:
        b = body(c, parent, name, label)
        profile = sketch(b, name + 'Profile', 'Замкнутый профиль · круглые касательные углы')
        for inset in insets:
            _display_loop(profile, p, inset)
        pad(b, profile, name + 'Layer', 'Слой LCD по профилю', thick, e_thick)
        c.at(b, f'{P}UiGlassU * {P}UiW / 28.2 mm', f'{P}UiGlassV * {P}UiL / 50.4 mm', zbase)
        c.register(b, parent, rgb, STACK + '; ' + CROP, confidence, note)


def color_exposed_core(pcb):
    """One physical substrate, not interpenetrating decorative mask copies."""
    if not pcb.ViewObject or pcb.Shape.isNull():
        return
    rgb = []
    for f in pcb.Shape.Faces:
        uv = f.ParameterRange
        normal = f.normalAt((uv[0] + uv[1]) / 2, (uv[2] + uv[3]) / 2)
        rgb.append(MASK if abs(normal.z) > 0.8 else CORE)
    pcb.ViewObject.DiffuseColor = rgb
