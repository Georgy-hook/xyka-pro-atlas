"""Inclined fascia datums and tangent-runout master surfaces (millimetres).

Manufacturer: https://xkah.us/products/xkah-pro closed graphite views 1/2/5;
006-_4 side (source URL below). The approximately eight-degree line is visible
with respect to the barrel, not inferred from a camera orbit. Compare USD1105588S1
Figs.5–7 and the current product, which has an LCD where the design shows no
window. Tilt, radii, wall thickness and transition lengths are EST, not tooling.
"""

import math

import FreeCAD as App
import Part

from mech_shapes import CY, V, bezier, circle, polygon, u_wire, z_box


SIDE_SOURCE = ('https://xkah.us/cdn/shop/files/006-_4_3b9c23ec-76a4-4953-b255-'
               '6d5832382f9d.png?v=1779269809&width=1000')
TILT = 7.5                  # inward at the top, about -X from the old frame
PIVOT = 84.0                # at keypad height; no stretch of the PCB/keys/glass
SIN = math.sin(math.radians(TILT))
COS = math.cos(math.radians(TILT))
TAN = SIN / COS
ROT = App.Rotation(V(1, 0, 0), -TILT)
FASCIA = App.Placement(V(0, -PIVOT*SIN, PIVOT*(1-COS)), ROT)
CAP_TOP = 153.53
BODY_TOP = 146.60
COVER_END = 148.20          # local Z; blind joint below the rolled crown
FRONT_R = 20.88             # original service cover half-width 20.07
FRONT_TIP = 66.36           # body lip; lower point read on the current product
COVER_TIP = 67.73           # ~16 mm below the key centres, not the PCB bottom


def cassette_frame(c, obj, old_rot=None, depth_alias=None, base_alias=None):
    """Compose the same rigid cassette tilt with a panel or populated-board frame.

    depth_alias/base_alias are the ORIGINAL local y/z datums on the sheet. An
    App::Part containing the cover/service hardware uses their zero defaults.
    The pivot height follows BodyH. No scale or shear is applied to hardware.
    """
    depth = f'Parameters.{depth_alias}' if depth_alias else '0 mm'
    base = f'Parameters.{base_alias}' if base_alias else '0 mm'
    pivot = f'(Parameters.BodyH * {PIVOT/154:.12g})'
    turn = ROT if old_rot is None else ROT.multiply(old_rot)
    obj.Placement = App.Placement(V(), turn)
    c.at(obj, 0,
         f'({depth}) * {COS:.12g} + (({base}) - {pivot}) * {SIN:.12g}',
         f'({base}) * {COS:.12g} + {pivot} * {1-COS:.12g} - ({depth}) * {SIN:.12g}')
    return obj


def in_cassette(shape, inverse=False):
    out = shape.copy()
    pose = FASCIA.inverse() if inverse else FASCIA
    out.Placement = pose.multiply(out.Placement)
    return out


def face_y(z):
    """World Y of the inclined exterior's datum, not the optical LCD surface."""
    return TAN * (z - PIVOT)


def _radius(z):
    # Extend the known cone a little past the slice plane; crown has its own
    # circular back. A large overlap ONLY at the hidden closing face is safe.
    return 38.96 - (38.96-31.97) * (z-9.4) / (145.55-9.4)


def _curve(points):
    spline = Part.BSplineCurve()
    spline.interpolate(points)
    return spline.toShape()


def _ring(s, back_plane=False):
    """U-isoline on the skin. At the outer runout it follows the conical barrel.

    Unlike a family of planar U extrusions, each point across the shoulder has
    its own depth. At the junction a quadratic falloff makes the fairing run
    into the barrel at a shallow angle; the concealed overlap avoids coincident
    boolean faces. Inclined mask and vertical cone remain undeformed.
    """
    growth = s**1.45
    r = FRONT_R + 6.95*growth
    local_tip = FRONT_TIP - 18.75*growth
    tip = PIVOT + (local_tip-PIVOT)*COS
    arc_h = r * COS
    tangent_z = tip + arc_h
    top = 162.0
    weight = (1-s)**2.5

    def point(x, z):
        rb = _radius(z)
        base_y = CY - math.sqrt(rb*rb - x*x)
        y = base_y + .12 - (base_y + .12 - face_y(z)) * weight
        return V(x, 37.3 if back_plane else y, z)

    right = [point(r, top+(tangent_z-top)*i/5) for i in range(6)]
    arc = []
    for i in range(21):
        angle = math.pi*i/20
        # Keep material outside the lower PCB corners, not along the centre
        # of the chin. Both the mask edge and the conical runout stay fixed.
        cheek = 9.20 * math.sin(math.pi*s) * math.sin(2*angle)**2
        arc.append(point(r*math.cos(angle), tip+arc_h*(1-math.sin(angle))-cheek))
    left = [point(-r, tangent_z+(top-tangent_z)*i/5) for i in range(6)]
    across_top = [point(-r+2*r*i/12, top) for i in range(13)]
    return Part.Wire([_curve(right), _curve(arc), _curve(left), _curve(across_top)])


def fairing_master():
    """Closed fairing tool. Front and hidden closing planes are analytic caps."""
    rings = [_ring(s) for s in (0, .12, .26, .43, .61, .80, 1)]
    back = _ring(1, back_plane=True)
    skin = Part.makeLoft(rings, False, False, False, 3)
    return_side = Part.makeLoft([rings[-1], back], False, True)
    faces = [Part.Face(rings[0]), *skin.Faces, *return_side.Faces, Part.Face(back)]
    solid = Part.makeSolid(Part.makeShell(faces))
    if solid.Volume < 0:
        solid.reverse()
    return solid


def pocket_master():
    """Negative service cavity; its mouth and bores rotate with the UI module."""
    sections = [(-3.2, 40.6, 67.50), (1.0, 40.6, 67.50),
                (5.0, 40.92, 66.95), (10.5, 41.65, 64.80),
                (18, 44.10, 59.80), (33, 47.60, 54.5)]
    wires = [u_wire(y, width, tip, 163.5) for y, width, tip in sections]
    cavity = Part.makeLoft(wires, True, False)
    # Recess behind the mask only. PCB, its soldermask and the actual
    # chamfered backup carrier require this clearance at their lower corners.
    lower_clearance = [(-11.25, 67.08), (11.25, 67.08), (16.40, 73.10),
                       (16.40, 78.0), (-16.40, 78.0), (-16.40, 73.10)]
    relief = Part.Face(polygon([V(x, 4.26, z) for x, z in lower_clearance])).extrude(V(0, 12.5, 0))
    return in_cassette(cavity.fuse(relief).removeSplitter())


def roll_mask():
    """Rolling return from the rake to a near-tangent flat edge in top plan.

    Product side view fixes the inclined approach; the owner's family of
    end-on views shows a transverse rim just proud of the circle, not a shelf.
    https://i.redd.it/l3b6qbuzpmwh1.jpeg (different specimen, no scale).
    """
    zstart = 146.35
    ystart = face_y(zstart)
    def p(y, z):
        return V(-54, y, z)
    a = p(ystart, zstart)
    knuckle = p(11.66, 151.41)
    end = p(13.08, CAP_TOP)
    edges = [bezier(a, p(ystart + TAN*.83, zstart+.83), p(10.78, 149.95), knuckle),
             bezier(knuckle, p(12.10, 152.14), p(12.71, CAP_TOP), end),
             Part.makeLine(end, p(102, CAP_TOP)),
             Part.makeLine(p(102, CAP_TOP), p(102, 137)),
             Part.makeLine(p(102, 137), p(face_y(137), 137)),
             Part.makeLine(p(face_y(137), 137), a)]
    return Part.Face(Part.Wire(edges)).extrude(V(108, 0, 0))


def crown_and_bridge(nose):
    mask = roll_mask()
    crown_blank = circle(31.76, 2.70, 0, CY, 150.83)
    tongue = nose.common(z_box(150.83, 2.70)).common(mask)
    crown = crown_blank.fuse(tongue).cut(circle(25.10, 5.0, 0, CY, 149.8)).removeSplitter()
    # Geometry below the crown face: no through-slit at the side; not a solid
    # disk at ring height. Leave the indicator ring and both light routes free.
    sleeve = nose.common(z_box(BODY_TOP+.01, 150.83-BODY_TOP-.01)).common(mask)
    sleeve = sleeve.cut(circle(31.03, 6, 0, CY, 146))
    rebate = in_cassette(Part.Face(u_wire(-2.0, 40.7, 62.8, COVER_END+.045)).extrude(V(0, 2.95, 0)))
    return crown, sleeve.cut(rebate).removeSplitter()
