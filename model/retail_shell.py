"""Retail outer mould line, rear air slots and bottom bevel. Nominal mm, EST.

No image texture replaces a hole or a fitted face. Section readings refer to
XKAH US closed views 1, 5, 6 and 7 of https://xkah.us/products/xkah-pro and
XYKA Graphite https://static.tildacdn.com/tild6266-3464-4239-a239-646538633937/4.webp .
Hidden returns provide dark sight-lines, not a proposed internal airflow path.
"""
import math

import Part

from mech_shapes import CY, V, circle, polygon, rotated, trim, turned
from retail_shell_rear import PACK_KEY, key_socket

# Central bright rim y1218..1328 on the 1515 px tall graphite silhouette.
# Shared by the bore, bezel and knob, independent of the existing diameter.
UNLOCK_Z = 24.70


def parting_mask(dz=0.):
    """Below the mould line. Keep the original inboard land for bowl and pin.

    Only the external 4 mm or so of the rim changes height. The overlap is a
    concealed step, not a counterfeit movement of the heat-seat or switch pin.
    The .28 mm half-gap at the old case line becomes .11 mm at the outer skin.
    """
    def block(stations):
        ys = [(-30., -5.), (128., -5.), *stations]
        return Part.Face(polygon([V(-75, y, z) for y, z in ys])).extrude(V(150, 0, 0))
    old = [(128., 45.45 + dz)]
    for i in range(9):
        t = i / 8
        u = 1 - t
        old.append((36*u**3 + 63*u*u*t + 34.5*u*t*t + t**3,
                    45.45*(u**3 + 3*u*u*t) + 34.65*(3*u*t*t + t**3) + dz))
    old.append((-30., 34.65 + dz))
    # Saturate the correction for the deeper land stations; distinct .276 and
    # .28 inputs must still have distinct faces for the existing inner step.
    abs_d = abs(dz)
    d = math.copysign(.40 * min(abs_d, .35) + max(0., abs_d - .35), dz)
    new = [(128., 47.45 + d)]
    for i in range(17):
        t = 1. - i/16
        y = 6.8 + 26.6*t
        bend = t*t*(3 - 2*t)
        new.append((y, 37.95 + 9.50*bend + d))
    new.append((-30., 37.95 + d))
    core = circle(33.86, 120, 0, CY, -6)
    return block(new).cut(core).fuse(block(old).common(core)).removeSplitter()


def _bank_return(sign):
    # Offset wall only behind the visible slits. Air space remains on the
    # sides/top; the interior of the bowl does not appear through the bank.
    section = [(31.66, 46.50), (32.30, 46.50), (32.30, 60.70), (31.66, 60.70)]
    face = Part.Face(polygon([V(0, CY + r, z) for r, z in section]))
    band = face.revolve(V(0, CY, 0), V(0, 0, 1), 36.2)
    return rotated(band, V(0, CY, 0), 28.4 if sign > 0 else -64.6)


def _rounded_polygon(points, tangent=.24):
    """Tangency-distance round corners of a convex, planar aperture polygon."""
    starts, ends, mids = [], [], []
    for i, v in enumerate(points):
        a, b = points[i - 1] - v, points[(i + 1) % len(points)] - v
        a.normalize()
        b.normalize()
        theta = a.getAngle(b) / 2
        center_dir = a + b
        center_dir.normalize()
        center_dist = tangent / math.cos(theta)
        radius = tangent * math.tan(theta)
        starts.append(v + a*tangent)
        ends.append(v + b*tangent)
        mids.append(v + center_dir*(center_dist - radius))
    edges = []
    for i, a in enumerate(starts):
        edges.append(Part.Arc(a, mids[i], ends[i]).toShape())
        edges.append(Part.makeLine(ends[i], starts[(i + 1) % len(points)]))
    return Part.Wire(edges)


def rear_features(upper):
    """Apply both real banks and the closed-supported rear battery control."""
    slots = []
    for sign in (-1, 1):
        for angle, height in zip((34.4, 40.4, 46.7, 53.4, 60.4), (9.70, 8.48, 7.20, 5.88, 4.55)):
            # Viewed tangentially the tips lean a little toward the hinge; the
            # openings are not a row of round-ended drilled tubes.
            # The straight rear photo puts the lowest edges about 3 mm
            # above the seam under both groups, not coincident with it.
            base, w = 50.45, 2.00
            def slot_wire(radial, spread):
                yr = CY + radial
                shift = sign * .09 * height
                return _rounded_polygon([V(-w/2-spread, yr, base-spread), V(w/2+spread, yr, base-spread),
                                         V(w/2+shift+spread, yr, base+height+spread),
                                         V(-w/2+shift-spread, yr, base+height+spread)], .31)
            tool = Part.makeLoft([slot_wire(30.3, -.10), slot_wire(35.65, -.10), slot_wire(37.25, .19),
                                  slot_wire(40.0, .19)], True, True)
            slots.append(rotated(tool, V(0, CY, 0), sign * angle))
    shell = trim(upper, slots + [key_socket(PACK_KEY)])
    for side in (-1, 1):
        shell = shell.fuse(_bank_return(side))
    return shell.removeSplitter()


def _skirt_outline(width0, width1, z0, z1, depth):
    # The cutter floor follows the bevel in section. Taper alternates like the
    # large/small trapezoids on either side of the front and rear centerlines.
    def y(z):
        return CY + 33.05 + (38.48 - 33.05)*(z - .55)/(7.20 - .55) + depth
    return _rounded_polygon([V(-width0/2, y(z0), z0), V(width0/2, y(z0), z0),
                             V(width1/2, y(z1), z1), V(-width1/2, y(z1), z1)], .42)


def bevel_grip():
    body = turned([(27.92, .12), (32.05, .12), (32.68, .26), (33.05, .55), (38.48, 7.20),
                   (38.73, 7.79), (36.55, 7.79), (31.48, 1.73), (27.92, 1.73)], CY)
    dies = []
    for wb, wt in [(3.64, 6.50), (5.94, 4.45)]:
        dies.append(Part.makeLoft([_skirt_outline(wb - .32, wt - .32, 1.35, 6.49, -.61),
                                   _skirt_outline(wb, wt, 1.15, 6.70, -.13),
                                   _skirt_outline(wb, wt, 1.15, 6.70, 2.2)], True, True))
    pockets = [rotated(dies[i % 2], V(0, CY, 0), i*10.) for i in range(36)]
    # Black mouths occur twice symmetrically on the front/rear, NOT on either
    # centreline. The separate annular return behind them prevents see-through.
    port = Part.Face(_skirt_outline(4.40, 4.43, 1.42, 2.33, -5.15)).extrude(V(0, 9, 0))
    outlets = [rotated(port, V(0, CY, 0), angle) for angle in range(30, 360, 60)]
    return trim(trim(body, pockets), outlets)
