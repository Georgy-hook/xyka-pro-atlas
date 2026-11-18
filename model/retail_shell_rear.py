"""Closed retail back: tapered hinge, concealed axle ends and blind key reveals.

Nominal mm, derived from the standing graphite views (not A4.3 metrology).
The exposed lower hinge is widest at its two roots; the upper spine narrows
upwards. The dark contour in side view follows the knuckle, not a pin head.
"""
import FreeCAD as App
import Part

from mech_keyfaces import cushion, grip_key
from mech_shapes import ALLOY, CASE, EST, EXT, MAN, V, WO1, Z, bezier, circle, moved, polygon, scaled_part

REAR = 'XKAH Pro US gallery 7, https://xkah.us/products/xkah-pro; XYKA Graphite https://static.tildacdn.com/tild6163-6264-4461-b536-636339346634/2.webp'
OBLIQUE = 'XKAH Pro US gallery 6; XYKA Graphite https://static.tildacdn.com/tild6266-3464-4239-a239-646538633937/4.webp'
SIDE = 'XYKA left profile https://static.tildacdn.com/tild6166-6135-4635-a233-616664376262/3.webp'
# width, length in the tilted face, outward Y/Z of visible centre, pitch about X
PACK_KEY = (11.05, 11.95, 80.17, 111.85, 2.94)
BASE_KEY = (12.55, 9.70, 90.39, 28.84, -32.8)
AXLE_Y = 92.45
AXLE_Z = 47.95


def _key_pose(spec):
    _, _, y, z, pitch = spec
    rot = App.Rotation(V(1, 0, 0), pitch).multiply(App.Rotation(Z, 180))
    return App.Placement(V(0, y, z), rot)


def _key_section(w, h, d):
    return moved(cushion(w, h), 0, d, 0)


def key_socket(spec):
    """Key mouth and hidden rebate for the overlapping skirt, in actual pose."""
    w, h, _, _, _ = spec
    aperture = Part.Face(_key_section(w + .32, h + .34, -2)).extrude(V(0, 9.5, 0))
    rebate = Part.Face(_key_section(w + 1.38, h + 1.40, 1.85)).extrude(V(0, 6.0, 0))
    tool = aperture.fuse(rebate).removeSplitter()
    tool.Placement = _key_pose(spec).multiply(tool.Placement)
    return tool


def retail_key(c, parent, name, label, spec, source):
    w, h, _, _, _ = spec
    # The return laps behind the narrow visible key seam without plugging the
    # face of the key or revealing a view of the interior electronics beside it.
    levels = [(-.54, -.58, 0.), (-.16, -.18, .22), (0., 0., .62),
              (0., 0., 1.91), (1.04, 1.07, 2.10), (1.04, 1.07, 2.48)]
    blank = Part.makeLoft([_key_section(w + dw, h + dh, d) for dw, dh, d in levels], True, True)
    grip_key(c, parent, name, label, blank, cushion(.765 * w, .69 * h), source,
             'Видимая клавиша с выпуклыми торцами, утопленным рифлёным полем и глухим нахлёстом. '
             'Зазор, скрытая ступень и ход оценочны, маркировка не считывается.', pose=_key_pose(spec))


def _width_fence():
    # At nominal z=16, 48 and 79: 41.5, 34.7 and 30.5 mm total width.
    samples = [(21.45, 8.0), (20.75, 16.), (17.35, 48.), (15.25, 79.), (15.1, 82.)]
    outline = [V(-w, 62., z) for w, z in samples] + [V(w, 62., z) for w, z in reversed(samples)]
    return Part.Face(polygon(outline)).extrude(V(0, 42, 0))


def _ramp_section(z, y, drop):
    # A gently bowed surface, not a flat ledge hacked off horizontally. Its
    # intersection with the conical drum supplies the arched lower hinge line.
    a, b = V(-23, y - drop, z), V(23, y - drop, z)
    edges = [bezier(a, V(0, y + drop, z), b)] if drop else [Part.makeLine(a, b)]
    c, d = V(23, 65, z), V(-23, 65, z)
    return Part.Wire(edges + [Part.makeLine(b, c), Part.makeLine(c, d), Part.makeLine(d, a)])


def _joint_crown(extra=0.):
    """Full-width cheek head, or slightly larger clearance tool for the return."""
    def p(y, z):
        return V(-23, y, z)
    r = 5.48 + extra
    a = p(65, 39.0)
    b = p(96.11 + extra, 39.0)
    c = p(AXLE_Y + r, 44.12)
    d = p(AXLE_Y + r, AXLE_Z)
    e = p(AXLE_Y - r, AXLE_Z)
    f = p(85.25 - extra, 47.45 + extra)
    g = p(65, 47.45 + extra)
    boundary = [Part.makeLine(a, b), bezier(b, p(97.0 + extra, 40.37), p(AXLE_Y + r, 41.80), c),
                Part.makeLine(c, d), Part.Arc(d, p(AXLE_Y, AXLE_Z + r), e).toShape(),
                Part.makeLine(e, f), Part.makeLine(f, g), Part.makeLine(g, a)]
    return Part.Face(Part.Wire(boundary)).extrude(V(46, 0, 0))


def hinge_pieces(outer):
    fence = _width_fence()
    # Tapered rear ramp rounds into the axle. Its transverse curvature dies at
    # the hinge so the axis stays straight. A smooth lower intersection with
    # the barrel supplies the wrap seen especially on the pink underside view.
    ramp = Part.makeLoft([_ramp_section(9.60, 77.10, 4.75), _ramp_section(39., 96.11, 0.)], True, True)
    lower = ramp.fuse(_joint_crown()).common(fence).cut(outer).removeSplitter()
    centre_slot = Part.makeBox(26.78, 41., 21.4, V(-13.39, 64, 42.42))
    # Terminate the counterbores *inside* both ears; there is no uncovered
    # silver circle on either side of the closed retail hinge.
    bore = circle(1.94, 30.80, -15.40, AXLE_Y, AXLE_Z, V(1, 0, 0))
    lower = lower.cut(centre_slot).cut(bore).cut(key_socket(BASE_KEY)).removeSplitter()

    def p(y, z):
        return V(-23, y, z)
    a, b = p(65, 80.3), p(76.62, 80.3)
    c, d = p(85.25, 73.12), p(96.18, 50.80)
    e, f = p(88.38, 45.44), p(82.05, 46.14)
    g = p(65, 46.14)
    # Circumferential highlight along the rolled top only. The lower lug
    # returns INTO the clevis, with narrow slits at either side.
    top_fillet = [p(78.35, 80.04), p(80.05, 79.25), p(81.65, 78.14),
                  p(82.99, 76.74), p(84.18, 74.99), c]
    up_edges = [Part.makeLine(a, b)]
    for v in top_fillet:
        up_edges.append(Part.makeLine(b, v))
        b = v
    up_edges += [Part.makeLine(c, d), Part.Arc(d, p(92.45, 43.16), e).toShape(),
                 Part.makeLine(e, f), Part.makeLine(f, g), Part.makeLine(g, a)]
    leaf = Part.Face(Part.Wire(up_edges)).extrude(V(46, 0, 0)).common(fence).cut(outer)
    extended = _joint_crown(.19)
    # Allow the arch of BOTH side wings to follow the round ends. The centre
    # is a narrower lug and can therefore descend into the slot.
    wings = [extended.common(Part.makeBox(10.5, 44, 27, V(x, 63, 35))) for x in (-23.62, 13.12)]
    leaf = leaf.cut(Part.makeCompound(wings)).cut(bore).removeSplitter()
    # A plain axial gap between two flat knuckles exposes a vertical strip
    # of the otherwise hidden pin from behind. Give each cheek a concentric
    # shoulder entering a slightly relieved counterbore in the moving lug.
    for x0, xt in ((13.02, 12.88), (-13.58, -13.82)):
        shoulder = circle(3.14, .56, x0, AXLE_Y, AXLE_Z, V(1, 0, 0)).cut(bore)
        lower = lower.fuse(shoulder).removeSplitter()
        seat = circle(3.23, .94, xt, AXLE_Y, AXLE_Z, V(1, 0, 0))
        leaf = leaf.cut(seat).removeSplitter()
    axle = circle(1.80, 30.48, -15.24, AXLE_Y, AXLE_Z, V(1, 0, 0))
    return lower, leaf, axle


def hinge(c, upper, lower, outer):
    bracket, spine, axle = hinge_pieces(outer)
    scaled_part(c, lower, 'RearClevis', 'Основание шарнира · расширение и дуга вокруг корпуса',
                bracket, CASE, REAR + '; ' + OBLIQUE + '; ' + SIDE, EXT,
                'Две гладкие наружные щеки; ось снаружи не оголена. Обвод и положение по видам готового изделия, внутренний паз EST.')
    retail_key(c, lower, 'RearEjectKey', 'Задняя клавиша отделения основания', BASE_KEY,
               REAR + '; ' + OBLIQUE + '; ' + MAN + ' m')
    scaled_part(c, upper, 'RearHingeLeaf', 'Наклонная спинка · полная ширина плеч и узкий язык',
                spine, CASE, REAR + '; ' + SIDE + '; ' + WO1 + ' Figs.3–7', EXT,
                'Составная кромка в закрытом состоянии. Узкий носик продолжает внешнюю скруглённую спинку; ход не задан.')
    scaled_part(c, lower, 'HingeAxle', 'Поперечная скрытая ось шарнира · EST',
                axle, ALLOY, WO1 + ' Figs.5,6,8; ' + OBLIQUE, EST,
                'Оба конца утоплены внутри проушин. Фиксация и диаметр пальца не измерены.')
