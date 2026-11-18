"""External key skins, not switches. Local X right, Z up, Y into the cap.

HookahCat's 1200 x 800 five-screw photo, rotated 90° clockwise (no mirror):
central field ~71 x 80 px inside ~94 x 125 px; lightning ~29 x 52 px.
The two ends of the chevrons are NOT arrowheads pointing at the next key.
The diagonal facets also show on the regional circular and rear releases.
Photos constrain proportions, not the sign of each facet or a tooling depth.
"""

from math import ceil

import Part

from mech_shapes import EXT, STEEL, V, bezier, moved, polygon, scaled_part


_CAT = 'https://hookahcat.com.ua/image/catalog/Blog-images/blog/xkln/'
PANEL_PHOTOS = (_CAT + 'elektronna-chasha-xkah-pro.jpg; ' + _CAT +
                'xkah-pro-5-gvyntiv-pid-nakladkoyu.jpg; XYKA Graphite ' +
                'https://static.tildacdn.com/tild6433-6633-4037-a431-643161373334/1.webp')
UNLOCK_PHOTO = 'XYKA Silver https://static.tildacdn.com/tild3034-3031-4664-a339-313765633031/28.jpg'
REAR_PHOTO = 'XYKA Silver https://static.tildacdn.com/tild6435-3364-4230-b430-623433646666/23.jpg'
HINGE_PHOTO = 'XYKA Silver https://static.tildacdn.com/tild3738-3535-4738-b864-643863386330/25.jpg'

# All levels measured IN from the original outer face (mm). Even the highest
# marking stays inside that envelope. The field is a backed, removable CAD
# subdivision for picking/export, not a claim about separate manufactured parts.
PITCH = .74                  # same-row repeat; alternate rows offset by half
LAND = .115                  # field below smooth rim
DEPTH = .095                 # blind facet below land
BED = .28                    # base of field; continuous cap behind it
_FIELD_COLOR = (.615, .637, .648)
_MARK_COLOR = (.215, .228, .238)
_ESTIMATE = ('Шаг, глубина и материал оценочны. Цвет условный, передаёт контраст, '
             'не установленный химсостав. Разбиение поверхностей для выбора в CAD.')


def cushion(width, height):
    """Bowed ends and short straight sides visible on the inset (XZ plane)."""
    def p(x, z):
        return V(x * width / 2, 0, z * height / 2)

    return Part.Wire([
        bezier(p(-1, .58), p(-1, .87), p(-.55, 1), p(0, 1)),
        bezier(p(0, 1), p(.55, 1), p(1, .87), p(1, .58)),
        Part.makeLine(p(1, .58), p(1, -.58)),
        bezier(p(1, -.58), p(1, -.87), p(.55, -1), p(0, -1)),
        bezier(p(0, -1), p(-.55, -1), p(-1, -.87), p(-1, -.58)),
        Part.makeLine(p(-1, -.58), p(-1, .58)),
    ])


def _side_field(hand):
    """Rounded wedge: tall inboard edge, shorter blunt outboard end."""
    def p(x, z):
        return V(hand * x, 0, z)

    return Part.Wire([
        bezier(p(-2.12, 1.96), p(-2.12, 2.72), p(-1.66, 3.01), p(-1.02, 2.73)),
        Part.makeLine(p(-1.02, 2.73), p(1.10, 1.77)),
        bezier(p(1.10, 1.77), p(1.82, 1.44), p(2.20, 1.05), p(2.20, .49)),
        Part.makeLine(p(2.20, .49), p(2.20, -.49)),
        bezier(p(2.20, -.49), p(2.20, -1.05), p(1.82, -1.44), p(1.10, -1.77)),
        Part.makeLine(p(1.10, -1.77), p(-1.02, -2.73)),
        bezier(p(-1.02, -2.73), p(-1.66, -3.01), p(-2.12, -2.72), p(-2.12, -1.96)),
        Part.makeLine(p(-2.12, -1.96), p(-2.12, 1.96)),
    ])


def _sign(ident):
    # Hand trace scaled to the existing cap, not a font or a billboard.
    if ident == 'C':
        name = 'молния'
        detail = 'Верхнее остриё справа, нижнее слева; ширина ~0.40 и высота ~0.65 поля.'
        points = [(.96, 2.26), (1.04, 2.23), (.50, .43), (.53, .25), (1.24, -.12),
                  (1.27, -.23), (-.94, -2.26), (-1.00, -2.19), (-.49, -.38),
                  (-.53, -.24), (-1.23, .14), (-1.27, .27)]
    else:
        # Left is a valley, right a peak when the screen is ABOVE the keys.
        up = 1 if ident == 'R' else -1
        name = 'шеврон вверх' if up == 1 else 'шеврон вниз'
        detail = 'Экран сверху: вершина шеврона ' + ('выше' if up == 1 else 'ниже') + ' концов.'
        stroke = [(-1.33, -.38), (-.09, .67), (.09, .67), (1.33, -.38),
                  (1.16, -.68), (0, .26), (-1.16, -.68)]
        points = [(x, up * z) for x, z in stroke]
    # Sink into a matching seat below the lowest facet; no overlapping paint
    # solids. The sign's visible face is slightly proud of the field, not the rim.
    top = .055
    face = Part.Face(polygon([V(x, top, z) for x, z in points]))
    return face.extrude(V(0, LAND + DEPTH + .025 - top, 0)), name, detail


def _die():
    """One six-plane, flat-bottomed diamond cutter (no cone/pin tessellation)."""
    r = .46 * PITCH
    mouth = [V(x, LAND - .012, z) for x, z in ((r, 0), (0, r), (-r, 0), (0, -r))]
    floor = [V(p.x * .23, LAND + DEPTH, p.z * .23) for p in mouth]
    loops = [mouth, floor[::-1]]
    for i in range(4):
        j = (i + 1) % 4
        loops.append([mouth[i], floor[i], floor[j], mouth[j]])
    return Part.makeSolid(Part.makeShell([Part.Face(polygon(loop)) for loop in loops]))


def _field(profile):
    face = Part.Face(profile)
    blank = moved(face.extrude(V(0, BED - LAND, 0)), 0, LAND, 0)
    box = face.BoundBox
    nx = ceil(max(-box.XMin, box.XMax) / PITCH) + 1
    nz = ceil(max(-box.ZMin, box.ZMax) / (.5 * PITCH)) + 1
    die = _die()
    # Staggered rows, trimmed by the actual field perimeter. A small phase
    # offset avoids a stamp vertex coinciding with a symmetry/seam vertex.
    dies = [moved(die, (col + .11 + .5 * (row % 2)) * PITCH, 0,
                  (row + .17) * .5 * PITCH)
            for row in range(-nz, nz + 1) for col in range(-nx, nx + 1)]
    return blank.cut(Part.makeCompound(dies))  # one boolean, one backed solid


def grip_key(c, parent, ident, label, blank, profile, source, note, *, pose=None,
             sign=None, **scale):
    """Recess only the exposed face. Apply the *same* datum to every registered leaf."""
    def add(name, text, shape, color, evidence):
        if pose is not None:
            shape.Placement = pose.multiply(shape.Placement)
        return scaled_part(c, parent, name, text, shape, color, source, EXT,
                           evidence + ' ' + _ESTIMATE, **scale)

    mouth = profile.copy()
    mouth.scale(1.048)
    pocket = Part.makeLoft([moved(mouth, 0, -.025, 0), moved(profile, 0, LAND, 0),
                            moved(profile, 0, BED, 0)], True, True)
    add(ident, label, blank.cut(pocket), STEEL, note + ' Гладкий светлый кант вокруг глухого поля.')
    field = _field(profile)
    if sign:
        mark, name, detail = sign
        field = field.cut(mark)
        add(ident + 'Mark', label + ' · ' + name, mark, _MARK_COLOR,
            detail + ' Тональная вставка по фото HookahCat; на региональном графите блик светлый.')
    obj = add(ident + 'Field', label + ' · гранёное поле', field, _FIELD_COLOR,
              f'Диагональные ряды: повтор {PITCH:g} мм, дно ячейки на {DEPTH:g} мм ниже '
              f'площадки, площадка на {LAND:g} мм ниже канта. Не сквозное сверление.')
    if obj.ViewObject:
        obj.ViewObject.DisplayMode = 'Shaded'  # avoid black wire outlines on microfacets


def panel_key(c, cover, ident, cap, **scale):
    field = cushion(6.42, 6.98) if ident == 'C' else _side_field(-1 if ident == 'L' else 1)
    grip_key(c, cover, 'OuterKey' + ident, 'Наружная клавиша ' + ident, cap, field,
             PANEL_PHOTOS, 'Наружный колпачок, не кремовый толкатель 20260305A. '
             'Ось, шток и посадочный контур оставлены на привязках UiSw.',
             sign=_sign(ident), **scale)
