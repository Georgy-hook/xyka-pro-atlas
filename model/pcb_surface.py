"""Mask-side lands and readable photo-registered screen printing (closed solids)."""
from functools import lru_cache
from pathlib import Path

import FreeCAD as App
import Part

V = App.Vector
INK = (.87, .87, .82)
TIN = (.63, .61, .55)
PAD_SRC = 'IMG_8914/8915, IMG_8908/8909/AD; rectified soldermask plane'
CONF = 'НАДПИСЬ / ФОРМА ПО ФОТО'
PRINT_H = .012


@lru_cache(maxsize=1)
def _font():
    paths = (Path(App.getResourceDir()) / 'Mod/TechDraw/Resources/fonts/osifont-lgpl3fe.ttf',
             Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
             Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
             Path('C:/Windows/Fonts/arial.ttf'))
    return next(p for p in paths if p.is_file())


@lru_cache(maxsize=200)
def _ink_master(text, cap_height):
    font = _font()
    glyphs = Part.makeWireString(text, str(font.parent) + '/', font.name, 1.0, .018)
    face = Part.makeCompound([Part.makeFace(g, 'Part::FaceMakerBullseye') for g in glyphs if g])
    face.scale(cap_height / face.BoundBox.YLength)
    bb = face.BoundBox
    face.translate(V(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, 0))
    return Part.makeCompound([g.extrude(V(0, 0, PRINT_H)) for g in face.Faces])


def ink(text, height_mm):
    """Centered XY text, +w from mask. Font outlines persist in native B-reps."""
    return _ink_master(str(text), float(height_mm)).copy()


def ring(outer, inner, h=PRINT_H):
    return Part.makeCylinder(outer, h).cut(Part.makeCylinder(inner, h))


def box_centre(xlen, ylen, h, cx=0, cy=0, z=0):
    return Part.makeBox(xlen, ylen, h, V(cx - xlen / 2, cy - ylen / 2, z))


def frame(xlen, ylen, border=.085):
    return box_centre(xlen, ylen, PRINT_H).cut(box_centre(xlen-2*border, ylen-2*border, PRINT_H))


def oval(xrad, yrad, h):
    wire = Part.Wire([Part.Ellipse(V(), max(xrad, yrad), min(xrad, yrad)).toShape()])
    solid = Part.Face(wire).extrude(V(0, 0, h))
    if yrad > xrad:
        solid.rotate(V(), V(0, 0, 1), 90)
    return solid


def label(c, parent, name, text, at_mm, u, v, size, angle=0, **kw):
    obj = c.solid(parent, name, text + ' · шелкография', ink(text, size), kw.get('color', INK),
                  kw.get('photo', PAD_SRC), CONF, kw.get('note', 'Оцифровка видимой надписи, шрифт приближён.'))
    return at_mm(obj, u, v, kw.get('z', 0), angle)


def build_copper_and_print(c, group, at_mm, reg):
    """Separate footprints and signal legends; no simulated buried routing."""
    def item(name, title, shp, uv, color=INK, note=''):
        obj = c.solid(group, name, title, shp, color, PAD_SRC, CONF, note)
        return at_mm(obj, *uv)

    labels = []
    controls = [d for d in reg['views']['8915']['landmarks'] if d['role'] == 'fit']
    for d in controls:
        key = d['label']
        u, v = d['uv_mm']
        edge = key in ('VCC', 'B1', 'G', 'R')
        radius = .79 if edge else .50
        item(d['internal_name'], 'Площадка ' + key, Part.makeCylinder(radius, .025), (u, v), TIN,
             'Функция контактной группы не проверена. Центр в pcb_registration.json.')
        if edge:
            # The crest shoulder is visibly close: a horseshoe rather than a
            # printed complete circle hanging in the air beyond the laminate.
            r = ring(1.05, .91).cut(Part.makeBox(4, 1.1, .05, V(-2, .64, -.01)))
            item(d['internal_name'] + 'Print', 'Дуга площадки ' + key, r, (u, v))
            labels.append((d['internal_name'] + 'Mark', key, u, v - 1.65, .86, 0))
    aux = [d['uv_mm'] for d in controls if d['internal_name'].startswith('PcAux')]
    au = sum(p[0] for p in aux)/len(aux)
    av = sum(p[1] for p in aux)/len(aux)
    item('PcAuxFrame', 'Контур GND / SDA / SCK / VDD', frame(1.61, 7.42, .11), (au, av))
    labels += [('PcAuxVDDMark', 'VDD', au, av + 4.24, .64, 0),
               ('PcAuxGNDMark', 'GND', au, av - 4.29, .64, 0),
               ('PcAuxSdaSckMark', 'SDA SCK', au + 1.28, av, .66, 90)]

    sw_u = -13.04
    for i, (key, v) in enumerate([('V',29.45),('DIO',27.51),('CLK',25.57),('G',23.63)]):
        item('PcDebug' + key, 'Площадка ' + key, Part.makeCylinder(.52, .025), (sw_u, v), TIN,
             'Порядок по фото, электрически не проверено.')
    item('PcDebugFrame', 'Четыре пятака · G / CLK / DIO / V', frame(1.54, 7.28, .10), (sw_u, 26.54))
    labels += [('PcDebugGMark','G',sw_u,22.57,.71,90),
               ('PcDebugVMark','V',sw_u,30.56,.68,90),
               ('PcDebugClkMark','CLK DIO',sw_u-.99,26.58,.61,90)]
    for key, uv in [('RX',(-4.30,26.67)),('TX',(-4.30,25.42))]:
        item('Pc' + key, 'Площадка ' + key, oval(.71,.37,.025), uv, TIN,
             'Фото IMG_8914; обозначение не подтверждает функцию или напряжение.')
        offset = .95 if key == 'RX' else -.97
        labels.append(('Pc'+key+'Mark', key, uv[0], uv[1]+offset, .67, 0))

    # Identifier/date occupy the narrow strip along the *right* routed edge.
    # Printed from the B/F end towards the crest (rotated 90° in upright AD).
    labels += [('PcBoardID','GYS005-S-088-A4.3',12.49,28.66,.90,90),
               ('PcBoardCode','20260204',13.70,29.33,.85,90),
               ('PcU3Print','U3',-10.84,26.84,.70,90),
               ('PcU5Print','U5',11.45,46.65,.72,90),
               ('PcU7Print','U7',7.48,41.74,.68,90),
               ('PcD26Print','D26',11.43,38.46,.70,90),
               ('PcD27Print','D27',13.67,47.10,.68,90),
               ('PcQ5Print','Q5',-.66,57.05,.52,90),
               ('PcQ6Print','Q6',-.64,53.75,.52,90),
               ('PcQ7Print','Q7',-.67,50.37,.52,90)]
    # Tiny laser/ink dot outside the body, independent of the IC's own dimple.
    item('PcU3IndexInk', 'U3 · точка ориентации корпуса', Part.makeCylinder(.13,PRINT_H), (-5.69,25.83))
    item('PcFlashIndexInk', 'HCT · точка ориентации корпуса', Part.makeCylinder(.15,PRINT_H), (-10.74,35.73))
    # Unpopulated diode pads and the bar between them are visible beside D26.
    for i, v in enumerate((42.35,44.67), 1):
        item('PcD27Foot'+str(i),'D27 · открытая площадка '+str(i),box_centre(.88,.95,.025), (13.66,v), TIN)
    item('PcD27Bar','D27 · контур полосы',frame(.94,.57,.08), (13.66,43.51))
    for name, text, u, v, h, a in labels:
        label(c,group,name,text,at_mm,u,v,h,a)
