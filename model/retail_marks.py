"""Traced exterior XYKA print and a separate optical boot-state presentation.

No images, fonts or remote resources are required. All contours below were
redrawn from observed pixel corners. Importing this module for SVG/JSON does
not load FreeCAD. Only the two physical ink builders import CAD lazily.

Coordinates: body +X is right from outside, +Y inward, +Z up. The mark is
on the FRONT of the upper fairing, ABOVE its wave seam, NOT on the U-cover.
The rear, cap and stem underside do not show a brand. The small framed Pro
on regional carton art is not a second mark on this device. The US front
reads XKAH, with materially different letters: it fixes the approximate
location but is NOT the source of the owner's XYKA paths. The removable pod
has a separate dark mark in a regional retail image, not proven on A4.3.
"""

from math import isfinite


BODY_SOURCE = (
    'Owner IMG_AD206911-3187-4C31-BC25-74C98D584C6D.jpeg, x401–653, '
    'y1274–1419: actual XYKA / triangular A; graphite and silver regional '
    'front views 01 (1500²): '
    'https://static.tildacdn.com/tild6433-6633-4037-a431-643161373334/1.webp ; '
    'https://static.tildacdn.com/tild6637-3737-4665-b333-373331623631/22.jpg'
)
BOOT_SOURCE = (
    'Regional XYKA graphite/silver front 01, lit artwork on glass; '
    'mech_xy05 crop (x358..452, y81..102); mech_xy11 oblique boot. '
    'This graphic describes one photographed state, not a live display or circuit.'
)
POD_SOURCE = (
    'Regional XYKA mech_xy01: black XYKA on the near side of the metal pod '
    'below the rolled rim; mech_xy05 shows a DIFFERENT side/orientation. '
    'Exact clocking, finish and identity of the owner’s pod are UNKNOWN.'
)

# These are appearance swatches, not measured printing materials. The owner
# mark is silver/grey against graphite; in the silver retail finish it is dark.
BODY_INK = (0.52, 0.54, 0.56)
POD_INK = (0.16, 0.17, 0.18)
BOOT_COLOR = '#2787E5'  # emissive presentation swatch; glass/reflection vary by shot.
COAT_DEPTH = 0.065     # representational depth in mm for CAD/STEP visibility only.

# Original full-resolution regional FRONT image axes, x right, y down. Separate
# paths are intentional: the X has two long tips *on the left*, the Y has a
# diagonal descender, and the K has a discrete upright. The angle of the short
# K/A run and the triangular counter agree with the owner's oblique closeup.
# Subpixel contact at the counter's lower left is ambiguous. A very small web
# keeps the negative space a real hole (never a tiny filled triangle).
# Each item is (exterior, tuple_of_counters). No pre-existing vector file used.
_BODY = (
    (((615.0, 934.8), (632.0, 937.0), (669.4, 986.7), (681.3, 974.1),
      (700.0, 975.2), (678.8, 998.8), (699.3, 1024.8), (679.8, 1024.0),
      (668.1, 1009.1), (626.4, 1053.7), (608.1, 1052.3), (659.5, 997.3)), ()),
    (((708.0, 975.6), (727.1, 976.1), (739.4, 990.0), (751.6, 976.3),
      (771.4, 976.1), (726.8, 1025.3), (707.2, 1025.2), (729.2, 1000.8)), ()),
    (((772.1, 976.2), (789.2, 975.8), (789.4, 1025.4), (772.1, 1025.7)), ()),
    (((790.1, 1000.3), (811.2, 975.4), (830.0, 974.4), (808.8, 999.8),
      (825.4, 1019.5), (861.5, 972.2), (882.1, 970.8), (884.0, 1022.1),
      (858.8, 1023.1), (850.1, 1013.6), (840.5, 1024.7), (811.3, 1024.8)),
     (((869.0, 986.8), (870.0, 1012.0), (851.6, 1012.2)),)),
)

# A distinct plan-view trace of the illuminated graphic. Re-using the curved
# body's X contour here would reproduce cylindrical/perspective distortion.
_BOOT = (
    (((666.2, 365.5), (678.9, 365.5), (703.3, 394.1), (711.0, 386.2),
      (723.2, 386.2), (710.0, 401.7), (723.4, 418.1), (711.3, 418.0),
      (703.1, 408.8), (678.9, 438.6), (666.1, 438.6), (696.7, 402.0)), ()),
    (((726.5, 386.2), (739.0, 386.2), (746.5, 394.9), (754.4, 386.2),
      (765.5, 386.2), (739.7, 418.0), (726.5, 418.0), (740.6, 402.0)), ()),
    (((765.9, 386.2), (777.0, 386.2), (777.0, 418.1), (765.9, 418.1)), ()),
    (((777.4, 402.0), (790.1, 386.2), (802.4, 386.2), (789.4, 402.0),
      (799.8, 413.7), (822.5, 386.1), (836.5, 386.1), (836.5, 418.0),
      (819.5, 418.0), (814.5, 412.9), (808.7, 418.1), (790.0, 418.1)),
     (((825.9, 396.4), (825.9, 410.6), (815.4, 410.6)),)),
)

# mm at the nominal 78×98×154 envelope. The local front contour spans
# ≈275.9 px vs ≈644 px maximum body width and ≈609 px at the ink. Z is
# registered between the bright U-tip (y≈840) and centre seam (y≈1103),
# then checked with a front camera independently fitted to the complete case
# silhouette: the ink is closer to the lens than the flanks (≈8.9 vs ≈8.25
# px/mm), so the bounding-box ratio alone overestimates width. ±2 mm on ink size/location
# is reasonable for this reconstruction, NOT a manufacturing tolerance.
BODY_CENTER_XZ = (-0.28, 49.4)
BODY_SIZE_XZ = (31.1, 13.4)


def _ccw(loop, target):
    area = sum(x * b - a * y for (x, y), (a, b) in zip(loop, loop[1:] + loop[:1]))
    return loop if (area > 0) == target else list(reversed(loop))


def _artwork(trace, pixel_centre, scales, destination=(0.0, 0.0)):
    """Translate image points to up-positive coordinates and fix winding."""
    cx, cy = pixel_centre
    sx, sy = scales
    tx, ty = destination

    def path(points, ccw):
        return _ccw([[round(tx + (x - cx) * sx, 7), round(ty + (cy - y) * sy, 7)]
                     for x, y in points], ccw)

    return [{'points': path(border, True), 'holes': [path(h, False) for h in holes]}
            for border, holes in trace]


def _positive(value):
    if not isfinite(value) or value <= 0:
        raise ValueError('Artwork dimensions must be finite and positive')
    return float(value)


def boot_artwork(viewport_width, viewport_height):
    """Plain JSON-ready optical overlay; not a physical leaf, face or part.

    Pass clear VIEWPORT dimensions in mm, not pixel count or PCB size. Relative
    to its centre, +x goes right from the user's side and +y toward the upper
    end of the screen. No repeated closing vertex. Outer points are CCW, holes
    CW. Anchor the vertices to the glass's moving +u, +v plane at its visible
    face via the renderer; use polygon offset only to avoid depth fighting.
    Omit this entire return value when showing the off/unpowered state. Neither
    the dark screen rectangle nor new electronics are created here.
    """
    width, height = _positive(viewport_width), _positive(viewport_height)
    polygons = _artwork(_BOOT, (751.3, 402.05), (width / 242.0, height / 294.0))
    return dict(kind='presentation', state='regional-boot-reference', units='mm',
                center=[0.0, 0.0], color=BOOT_COLOR, emissive=True, polygons=polygons)


def _coating(outer, shapes, depth):
    """Clip actual near-side OCC faces and extrude outward by a display-film depth.

    Restrict the punches to the near half. Clipping the whole body against a
    slightly displaced copy can emit internal slivers at almost tangent lofts
    or at the far wall. Here each usable surface is from the actual substrate:
    no analytic/conical guess, faceted projection, backing plate or floating
    flat sign. The inside of the ink exactly touches its support.
    """
    import FreeCAD as App
    import Part

    depth = _positive(depth)
    box = outer.BoundBox
    near = box.YMin - 1.0
    reach = 0.5 * box.YLength + 1.0
    outward = App.Vector(0, -depth, 0)
    letters = []
    for index, data in enumerate(shapes, 1):
        def wire(loop):
            pts = [App.Vector(x, near, z) for x, z in loop]
            return Part.makePolygon(pts + [pts[0]])

        face = Part.Face(wire(data['points']))
        for hole in data['holes']:
            face = face.cut(Part.Face(wire(hole)))
        clip = face.extrude(App.Vector(0, reach, 0))
        if not clip.isValid():
            raise ValueError(f'Invalid wordmark stencil at stroke {index}')
        cut = outer.common(clip)
        if not cut.Solids:
            raise ValueError(f'Mark stroke {index} does not contact its receiving body')
        # A finished, hollow upper housing may have a second, disconnected
        # intersection deeper in the body (the sloping seam's inner ledge).
        # Use the forward connected piece only. Box bounds with triangulation
        # disabled avoid misleading extrema on trimmed B-spline patches.
        front = min(cut.Solids, key=lambda s: s.optimalBoundingBox(False, False).YMin)
        films = []
        for f in front.Faces:
            u0, u1, v0, v1 = f.ParameterRange
            normal = f.normalAt((u0 + u1) * 0.5, (v0 + v1) * 0.5)
            if normal.y >= -0.30:
                continue  # Flat punch walls have n·Y = 0; rear/inside has n·Y > 0.
            film = f.extrude(outward)
            if film.Volume < 0:
                film.reverse()
            films.append(film)
        if not films:
            raise ValueError(f'No front-facing receiving surface at stroke {index}')
        letter = (films[0] if len(films) == 1 else films[0].multiFuse(films[1:])).removeSplitter()
        # Cavalieri's principle: for a surface extruded in -Y by t, V equals
        # its FRONT projection area times t. This catches missing tips, interior
        # duplicates, wrong booleans and punch clipping, independent of curvature.
        plane_area = face.Area
        if (not letter.isValid() or len(letter.Solids) != 1 or
                abs(letter.Volume / depth - plane_area) > max(0.015, 0.005 * plane_area)):
            raise ValueError(f'Stroke {index} is not a single complete outside ink film')
        letters.append(letter)
    return Part.makeCompound(letters)


def surface_mark(outer, *, width=BODY_SIZE_XZ[0], height=BODY_SIZE_XZ[1],
                 center_x=BODY_CENTER_XZ[0], center_z=BODY_CENTER_XZ[1], depth=COAT_DEPTH):
    """Drop-in for the former mech_case.surface_mark(outer), nominal world mm.

    Keep the existing MechBrandMark leaf and scale/parent it with the outer
    housing. Supply its nominal, unscaled receiving B-rep to this constructor.
    """
    shapes = _artwork(_BODY, (746.05, 994.25),
                      (_positive(width) / 275.9, _positive(height) / 118.9),
                      (center_x, center_z))
    return _coating(outer, shapes, depth)


def pod_mark(cup, *, width=20.5, center_z=9.8, depth=COAT_DEPTH):
    """Optional external print, local pod coordinates, nominal Ø42 × 23.3 mm.

    The input is the actual local cup B-rep, with its axis at x=y=0 and foot
    at z=0. Scale/position the returned native film EXACTLY like the pod. The
    face bearing the observed word points toward -Y here only as an estimated
    clocking; the lift-out pod can rotate. Do not put this print on its lid.
    """
    width = _positive(width)
    shapes = _artwork(_BOOT, (751.3, 402.05),
                      (width / 170.4, width / 170.4), (0, center_z))
    return _coating(cup, shapes, depth)
