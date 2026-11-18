"""Small native-design helpers for the XKAH shell (world X right, Y inward, Z up).

Master contours are in millimetres at W/H/D = 78/154/98. Part::Scale retains
independent spreadsheet edits in the saved document. Other standard operations
(cut, cylinders, extrusion, etc.) can then reference those scaled features.
Only registered end features, not hidden feature-history operands, are parts.
"""

import math

import FreeCAD as App
import Part


V = App.Vector
Z = V(0, 0, 1)
Y = V(0, 1, 0)
W, D, H = 78.0, 98.0, 154.0
CY = 45.3  # axis from exterior UI datum (top plan of manual, printed p. 04)
WX = 'Parameters.BodyW / 78 mm'
DY = 'Parameters.BodyD / 98 mm'
HZ = 'Parameters.BodyH / 154 mm'
AXIS_Y = 'Parameters.BodyD * 0.462244898'

CASE = (0.156, 0.172, 0.185)
MOLD = (0.109, 0.121, 0.133)
INK = (0.055, 0.063, 0.074)
SEAL = (0.199, 0.209, 0.218)
STEEL = (0.701, 0.718, 0.725)
ALLOY = (0.422, 0.455, 0.470)
PALE = (0.839, 0.851, 0.839)

PHOTO = 'IMG_AD206911-3187-4C31-BC25-74C98D584C6D.jpeg; IMG_8916; IMG_8920'
MAN = 'XKAH Pro User Manual, printed pp.03–04 (PDF pp.6–7), https://www.animashop.cz/user/related_files/xkah_user_manual.pdf'
XYKA = 'https://xyka.pro/'
OPEN_PHOTO = 'XYKA product image https://static.tildacdn.com/tild3734-6137-4364-a166-633334636230/2.jpg'
BACK_PHOTO = 'XYKA rear/underside image https://static.tildacdn.com/tild6433-3632-4761-b132-623036633939/6.jpg'
PACK_PHOTO = 'XYKA removable pack https://static.tildacdn.com/tild6333-3139-4932-b232-376530333934/5.jpg'
RETAIL = 'https://hookahministry.com/products/xkah-pro-graphite'
PODS = 'https://smokaz.de/xkah-pro-ersatz-pod-2er-pack'
CN = 'https://patents.google.com/patent/CN309108835S/en'
US_FAMILY = ('CN309108835S 立体图1, https://eureka.patsnap.com/patent/CN309108835S ; '
             'USD1105588S1 Figs.1–8, https://www.surechembl.org/api/patent/pdf/US-D1105588-S1')
WO1 = 'https://patents.google.com/patent/WO2025223381A1/en'
WO5 = 'https://patents.google.com/patent/WO2025223385A1/en'
OBS = 'OWNER PHOTO / ESTIMATE'
EXT = 'PRODUCT VIEW / ESTIMATE; A4.3 not dimensioned'
EST = 'CONCEPTUAL FIT / UNVERIFIED'


def at_ratio(name, n, d):
    return f'Parameters.{name} * {n / d:.10f}'


def body_pos(x, y, z):
    return (at_ratio('BodyW', x, W), at_ratio('BodyD', y, D), at_ratio('BodyH', z, H))


def feature(c, parent, type_id, name, label):
    obj = c.doc.addObject(type_id, 'Mech' + name)
    parent.addObject(obj)
    obj.Label = label
    return obj


def hidden(obj):
    obj.Visibility = False
    if obj.ViewObject:
        obj.ViewObject.Visibility = False
    return obj


def scaled(c, parent, name, label, shape, ratios=(WX, DY, HZ), origin=(0, 0, 0)):
    """A local, editable profile master and a native scale/placement; no proxy."""
    master = feature(c, parent, 'Part::Feature', name + 'Contour', 'Контур · ' + label)
    # Part::Scale works in its Base's local axes and ignores the Base placement.
    # Preserve any pre-rotation/translation *inside* the topology; leaving it
    # on the master would collapse fasteners and controls onto the origin.
    master.Shape = Part.makeCompound([shape]) if not shape.Placement.isIdentity() else shape
    obj = feature(c, parent, 'Part::Scale', name, label)
    obj.Base = master
    obj.Uniform = False
    for key, value in zip(('XScale', 'YScale', 'ZScale'), ratios):
        if isinstance(value, str):
            obj.setExpression(key, value)
        else:
            setattr(obj, key, float(value))
    # For equal factors the similarity transform keeps circles/cylinders exact.
    # Only truly independent edits need OCCT's general affine transformation.
    obj.setExpression('Uniform', 'XScale == YScale ? (XScale == ZScale ? 1 : 0) : 0')
    obj.setExpression('UniformScale', 'XScale')
    c.at(obj, *origin)
    hidden(master)
    return obj


def scaled_part(c, parent, name, label, shape, color, source, confidence, notes='', **opts):
    obj = scaled(c, parent, name, label, shape, **opts)
    return c.register(obj, parent, color, source, confidence, notes)


def cut_native(c, parent, name, label, base, tool):
    obj = feature(c, parent, 'Part::Cut', name, label)
    obj.Base = base
    obj.Tool = tool
    obj.Refine = True
    hidden(base)
    hidden(tool)
    return obj


def circle(radius, height, x=0, y=0, z=0, direction=Z):
    return Part.makeCylinder(radius, height, V(x, y, z), direction)


def ring(ro, ri, height, x=0, y=0, z=0):
    return circle(ro, height, x, y, z).cut(circle(ri, height + 0.2, x, y, z - 0.1))


def polygon(points):
    return Part.makePolygon(list(points) + [points[0]])


def turned(points, cy=0):
    """A closed r,z lathe profile; vertices describe the actual hollow section."""
    wire = polygon([V(r, cy, z) for r, z in points])
    return Part.Face(wire).revolve(V(0, cy, 0), Z, 360)


def bezier(*points):
    curve = Part.BezierCurve()
    curve.setPoles(list(points))
    return curve.toShape()


def u_wire(y, width, tip, top):
    """Flat-topped U with a true, tangent semicircular lower end, in world XZ."""
    r = width / 2
    ul, ur = V(-r, y, top), V(r, y, top)
    ll, lr = V(-r, y, tip + r), V(r, y, tip + r)
    return Part.Wire([Part.makeLine(ul, ll), Part.Arc(ll, V(0, y, tip), lr).toShape(),
                      Part.makeLine(lr, ur), Part.makeLine(ur, ul)])


def rounded_rect(width, length, r, y=0):
    """Centered XZ outline, circular quarter-arcs, for lens, sockets and keys."""
    a, b = width / 2, length / 2
    r = min(r, a * .999, b * .999)
    q = r / math.sqrt(2)
    pts = [V(a-r, y, b), V(-a+r, y, b), V(-a, y, b-r), V(-a, y, -b+r),
           V(-a+r, y, -b), V(a-r, y, -b), V(a, y, -b+r), V(a, y, b-r)]
    mid = [V(-a+r-q, y, b-r+q), V(-a+r-q, y, -b+r-q),
           V(a-r+q, y, -b+r-q), V(a-r+q, y, b-r+q)]
    edges = []
    for j in range(4):
        i = 2 * j
        edges.append(Part.makeLine(pts[i], pts[i+1]))
        edges.append(Part.Arc(pts[i+1], mid[j], pts[(i+2) % 8]).toShape())
    return Part.Wire(edges)


def side_key(direction, factor=1.0, y=0):
    """Soft triangular left/right key. A web image does not fix the corner radii."""
    def p(x, z):
        return V(direction * x * factor, y, z * factor)
    return Part.Wire([
        bezier(p(-2.95, 2.35), p(-2.94, 4.53), p(-1.30, 4.25), p(-.40, 3.72)),
        Part.makeLine(p(-.40, 3.72), p(2.16, 1.70)),
        bezier(p(2.16, 1.70), p(3.62, .82), p(3.62, -.85), p(2.16, -1.72)),
        Part.makeLine(p(2.16, -1.72), p(-.40, -3.72)),
        bezier(p(-.40, -3.72), p(-1.3, -4.25), p(-2.94, -4.53), p(-2.95, -2.35)),
        Part.makeLine(p(-2.95, -2.35), p(-2.95, 2.35)),
    ])


def z_box(base, height):
    return Part.makeBox(180, 190, height, V(-90, -40, base))


def trim(base, tools):
    if not tools:
        return base
    return base.cut(Part.makeCompound(tools)).removeSplitter()


def rotated(shape, center, angle):
    result = shape.copy()
    result.rotate(center, Z, angle)
    return result


def moved(shape, x, y, z):
    result = shape.copy()
    result.translate(V(x, y, z))
    return result
