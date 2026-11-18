"""Installed retail film, opaque return and LCD. Areas are normal projections, not pixels."""

import numpy as np
import Part

from assembly_units import UNITS
from fit_frames import Frame
from fit_geometry import DEFLECTION, EPS, bounds, box_hits, extents, vec, xyz
from fit_keymask import NativeRays

__all__ = ('retail_window',)

MASK, PANE, CARRIER, LCD = 'MechServiceCover', 'MechCoverWindow', 'MechKeyCarrier', 'UiGlass'


def _lift(shape, w):
    return shape.translated(vec((0, 0, w)))


def _union(faces):
    faces = list(faces)
    if not faces:
        return Part.makeCompound([])
    return faces[0].fuse(faces[1:]).removeSplitter() if len(faces) > 1 else faces[0]


def _flat(face):
    lo, hi = bounds(face, True)
    return hi[2] - lo[2] <= EPS


def _end(solid, front, name):
    """Actual end material, including all trims/islands. Never flatten a skew part's box."""
    limit = solid.box[int(front), 2]
    faces = [f for f in solid.shape.Faces if abs(f.CenterOfMass.z - limit) <= EPS and _flat(f)]
    if not faces:
        raise ValueError(f'{name}: no planar {"outer" if front else "inner"} face parallel to the LCD at the material end')
    return faces[0].CenterOfMass.z, _union(_lift(f, -f.CenterOfMass.z) for f in faces)


def _holes(skin, targets):
    # Only inner wires of a real material face, never the U silhouette. Register
    # by overlap, not a shared centre, a box, or the largest of the key holes.
    holes = [Part.Face(wire) for f in skin.Faces for wire in f.Wires if not wire.isSame(f.OuterWire)]
    for target in targets:  # pane first; LCD fallback only for a completely displaced pane
        selected = [hole for hole in holes if hole.common(target).Faces]
        if selected:
            return selected
    return []


def _centroid(region):
    faces = region.Faces
    return np.average([xyz(f.CenterOfMass) for f in faces], axis=0, weights=[f.Area for f in faces])


def _point(region):
    """Strict interior station; the centroid of a crescent or perforated pane need not be in it."""
    faces = region.Faces
    if not faces:
        raise ValueError('No trimmed face at the proposed witness plane')
    p = _centroid(region)
    if any(f.isInside(vec(p), EPS, False) for f in faces):
        return p
    face = max(faces, key=lambda f: f.Area)
    points, triangles = face.tessellate(DEFLECTION)
    coords = np.array([xyz(p) for p in points])
    for triangle in triangles:
        p = coords[list(triangle)].mean(axis=0)
        if face.isInside(vec(p), EPS, False):
            return p
    raise ValueError('Could not resolve an interior witness on a nonempty trimmed face')


def _station(frame, uv, w):
    return frame.point((*uv[:2], w))


def _extent(face):
    lo, hi = bounds(face, True)
    return f'{hi[0]-lo[0]:.4f} × {hi[1]-lo[1]:.4f}'


def _contour(frame, end, mask, pane, glass, emit):
    wm, skin = mask
    wp, film = pane
    loops = _holes(skin, (film, glass))
    if not loops:
        raise ValueError(f'No bounded optical cut in {MASK} at its {end} face overlapping pane or LCD')
    hole = _union(loops).cut(skin)  # retain disconnected mask material inside an outer hole wire
    du, dv = (_centroid(film) - _centroid(hole))[:2]
    missing, excess = hole.cut(film), film.cut(hole)
    note = (f'{len(loops)} bounded cut(s); actual cut/pane areas {hole.Area:.5f}/{film.Area:.5f} mm², '
            f'u × v spans {_extent(hole)} / {_extent(film)} mm; pane minus cut centroid '
            f'(u,v)=({du:+.4f},{dv:+.4f}) mm. Full planar trims, including internal holes.')
    check = 'retail film / ' + end + ' contour'
    if not (missing.Faces or excess.Faces):
        emit('CHECKED', check, MASK, PANE, _station(frame, _point(film), wp), metric='unmatched area mm²',
             value=0., detail=note)
    for region, other, w, metric in ((missing, film, wm, 'unfilled cut mm²'),
                                      (excess, hole, wp, 'pane outside cut mm²')):
        if region.Faces:
            p = _point(region)
            gap = Part.Vertex(vec(p)).distToShape(Part.makeCompound(other.Edges))[0]
            emit('REVIEW', check, MASK, PANE, _station(frame, p, w), metric=metric, value=region.Area,
                 detail=note + f' In-plane distance from this unmatched station to the other trim: {gap:.5f} mm. '
                 'Projected mismatch, not a common volume.')
    return hole


def _prism(region, w, travel):
    return _lift(region, w).extrude(vec((0, 0, travel)))


class _Sight:
    def __init__(self, leaves, frame, emit):
        self.rays = NativeRays(leaves)
        self.frame = frame
        self.inward = frame.direction((0, 0, -1))
        self.emit = emit

    def first(self, p, w):
        station = _station(self.frame, p, w)
        name, hit = self.rays.first(station, self.inward)
        return name, station if hit is None else hit

    def clear(self, region, w, target):
        """Prove normal visibility to a real trimmed face, not just hits on a grid.

        Screen the whole column above it. For an intrusion, coplanar cap shadows
        are exact if their extrusion contains the common. Curved residuals give
        only an upper bound on clear area and a strict finding, never clearance.
        """
        if not region.Faces:
            return region, True
        travel = self.rays.travel  # reaches outside the installed assembly in this frame
        column = _prism(region, w, travel)
        box = bounds(column, True)
        world = column.copy()
        world.Placement = self.frame.to_world.multiply(world.Placement)
        candidates = np.flatnonzero(box_hits(self.rays.boxes, bounds(world, True), EPS))
        shadows = []
        exact = True
        for i in candidates:
            leaf = self.rays.leaves[i]
            if float(getattr(leaf.obj, 'OpticalTransparency', 0)) > 0:
                continue  # same explicit policy as NativeRays; no opaque-leaf skip list
            s = self.frame.solid(leaf)
            if np.min(extents(s.box, box)) <= EPS:
                continue
            for common in s.shape.common(column).Solids:
                if not common.isValid() or common.Volume <= 0:
                    raise ValueError('Invalid optical-column common: ' + leaf.name)
                shadow = _union(_lift(f, -f.CenterOfMass.z) for f in common.Faces if _flat(f))
                if shadow.Faces:
                    shadows.append(shadow)
                residual = common.cut(_prism(shadow, w, travel)).Solids if shadow.Faces else [common]
                exact = exact and not residual
                # A thin off-axis blade/sphere can miss every regular ray grid.
                # Place the ray *inside* the actual clipped material in section.
                section_w = bounds(common, True)[:, 2].mean()
                section = common.common(_lift(region, section_w))
                p = _point(section)
                name, at = self.first(p, w)
                agrees = name != target or abs(self.frame.local_point(at)[2] - w) > EPS
                self.emit('BLOCKED_VIEW' if agrees else 'REVIEW', 'retail window / obstructed path',
                          target, name, at, self.inward, detail=f'{leaf.name} has material in front of the '
                          f'{target} target plane at this station. Witness = actual first hit (station if void).'
                          + (' Non-prismatic shadow not fully measured.' if residual else ''))
        clear = region.cut(_union(shadows)) if shadows else region
        for f in clear.Faces:
            name, at = self.first(_point(f), w)
            if name != target or abs(self.frame.local_point(at)[2] - w) > EPS:
                self.emit('BLOCKED_VIEW', 'retail window / first hit', target, name, at, self.inward,
                          detail='First surface is not the target at its measured depth (station for void).')
                exact = False
        return clear, exact


def _inspect(leaves, emit):
    cover, pane, carrier, lcd = (leaves[n] for n in (MASK, PANE, CARRIER, LCD))
    frame = Frame(lcd.obj)  # one rigid frame for ALL installed BReps, +w towards viewer
    outward = frame.direction((0, 0, 1))
    for leaf in (cover, pane, carrier):
        if (float(getattr(leaf.obj, 'OpticalTransparency', 0)) > 0) != (leaf is pane):
            emit('REVIEW', 'retail window / optical material', leaf.name, point=xyz(leaf.shape.Vertexes[0].Point),
                 detail='Only the exterior pane of the three cassette members should transmit the sight ray.')
    film = cover.obj.Document.getObject('MechFrontFilm')
    if (film is None or pane.obj not in film.Group or cover.obj not in film.Group or carrier.obj in film.Group
            or lcd.group != 'DisplayPCB' or lcd.obj in film.Group):
        emit('REVIEW', 'retail window / service ownership', MASK, PANE, xyz(pane.shape.Vertexes[0].Point),
             detail='Expect mask and pane together in MechFrontFilm; carrier and DisplayPCB glass stay behind.')

    g, gface = _end(frame.solid(lcd), True, LCD)
    mask, window = frame.solid(cover), frame.solid(pane)
    outer, inner = _end(mask, True, MASK), _end(mask, False, MASK)
    front, back = _end(window, True, PANE), _end(window, False, PANE)
    pf, pane_face = front
    pb, pane_back = back
    p = _point(pane_face)
    step = pf - outer[0]
    rear_step = pb - inner[0]
    emit('CHECKED' if max(abs(step), abs(rear_step)) <= EPS else 'REVIEW', 'retail film / face flushness', MASK, PANE,
         _station(frame, p, pf), outward, 'pane proud of mask mm', step,
         detail=f'Actual outer planes along LCD +w. Rear-plane step {rear_step:+.5f} mm; '
         f'mask/pane thickness {outer[0]-inner[0]:.5f}/{pf-pb:.5f} mm. Same removable sheet, not stacked.')
    opening = _contour(frame, 'outer', outer, front, gface, emit)
    _contour(frame, 'inner', inner, back, gface, emit)

    sight = _Sight(leaves, frame, emit)
    cw, stop = _end(frame.solid(carrier), True, CARRIER)
    mouths = _holes(stop, (opening,))
    if len(mouths) != 1:
        name, at = sight.first(p, pf)
        emit('REVIEW', 'retail window / carrier mouth', CARRIER, name, at, sight.inward,
             detail=f'{len(mouths)} bounded carrier openings intersect the film cut; expected one LCD route.')
    # Only the measured opaque return OUTSIDE the mouth qualifies. An island
    # or ledge of the very same carrier inside the sight path is an obstruction.
    rim = opening.common(stop).cut(_union(mouths)) if mouths else Part.makeCompound([])
    if float(getattr(carrier.obj, 'OpticalTransparency', 0)) > 0:
        rim = Part.makeCompound([])
    contact = rim.common(pane_back) if rim.Faces else rim
    if contact.Faces:
        emit('GAP' if pb - cw >= -EPS else 'REVIEW', 'retail film / carrier separation', PANE, CARRIER,
             _station(frame, _point(contact), pb), sight.inward, 'signed axial separation mm', pb - cw,
             detail='Pane rear to actual opaque return under the removable film. Not a force or extraction allowance.')

    pane_field = pane_back.common(pane_face)
    overlap = pane_field.common(gface)
    if overlap.Faces:
        centre = _centroid(pane_face)
        at_centre = any(f.isInside(vec(centre), EPS, False) for f in overlap.Faces)
        q = centre if at_centre else _point(overlap)
        start = _station(frame, q, pf) - sight.inward * EPS
        first, _ = sight.rays.first_from(start, sight.inward, max(0., pf - g) + 2 * EPS)
        emit('GAP' if pb - g >= -EPS else 'REVIEW', 'retail window / centre depth', PANE, LCD,
             _station(frame, q, pf), sight.inward, 'outer pane to LCD face mm', pf - g,
             detail=('At pane area centroid' if at_centre else 'No common material at pane centroid; at measured overlap')
             + f'; inner pane to actual glass {pb-g:.5f} mm. First opaque hit on pane-to-LCD segment: {first}.')
    else:
        emit('REVIEW', 'retail window / centre depth', PANE, LCD, _station(frame, p, pf), sight.inward,
             detail='Pane and real LCD faces have no common footprint; no axial depth invented.')

    field = opening.cut(rim) if rim.Faces else opening
    unbacked = field.cut(gface)
    for f in unbacked.Faces:
        name, at = sight.first(_point(f), pf)
        emit('REVIEW' if name in (MASK, PANE, CARRIER, LCD) else 'EXPOSED_EDGE', 'retail window / unbacked opening',
             PANE, name, at, sight.inward, 'unbacked planar patch mm²', f.Area,
             detail='Outside both measured LCD face and opaque return. Named first hit at one interior station '
             '(window station for OPEN_VOID); not a claim that the whole patch sees that surface.')

    dark, dark_exact = sight.clear(rim.common(pane_field) if rim.Faces else rim, cw, CARRIER)
    if dark.Faces:
        emit('MASKED_EDGE' if dark_exact else 'REVIEW', 'retail window / cosmetic return', PANE, CARRIER,
             _station(frame, _point(dark), cw), sight.inward, 'return area mm²' if dark_exact else 'return upper bound mm²',
             dark.Area, detail='Normal footprint of the actual opaque return seen through the punched cut. '
             'Cosmetic backing, not LCD, active image or evidence of material interference.')
    free, exact = sight.clear(field.common(gface), g, LCD)
    visible = free.common(pane_field) if free.Faces else free
    if visible.Faces:
        c = _centroid(visible)
        df = c - _centroid(pane_face)
        dg = c - _centroid(gface)
        emit('OPEN' if exact else 'REVIEW', 'retail window / backed glass', PANE, LCD,
             _station(frame, _point(visible), g), sight.inward, 'visible glass mm²' if exact else 'visible upper bound mm²',
             visible.Area, detail=f'LCD-normal trimmed extent {_extent(visible)} mm (u × v); area-centroid offset '
             f'from pane ({df[0]:+.4f},{df[1]:+.4f}), from glass ({dg[0]:+.4f},{dg[1]:+.4f}) mm. '
             'Installed opaque solids checked from exterior to the glass face. No active-pixel or oblique-view claim.')
    else:
        name, at = sight.first(p, pf)
        emit('BLOCKED_VIEW', 'retail window / backed glass', PANE, name, at, sight.inward, 'visible glass mm²', 0.,
             detail='No clear common footprint of transmissive film and real LCD. First hit at pane station.')


def retail_window(leaves, emit):
    """Emit retail-only findings; return selected native material pairs to the distance pass."""
    if PANE not in leaves:
        root = next(iter(leaves.values())).obj.Document.getObject('Assembly') if leaves else None
        if root is None or not any(obj.Name in UNITS for obj in root.Group):
            return []  # pre-retail window has a separate check
    names = (MASK, PANE, CARRIER, LCD)
    pairs = [(leaves[a], leaves[b]) for i, a in enumerate(names) for b in names[i+1:] if a in leaves and b in leaves]
    missing = [name for name in names if name not in leaves]
    if missing:
        emit('REVIEW', 'retail window / inventory', detail='Missing installed material: ' + ', '.join(missing))
        return pairs
    try:
        _inspect(leaves, emit)
    except (Part.OCCError, ValueError, RuntimeError) as exc:
        emit('REVIEW', 'retail window / unresolved geometry', MASK, LCD, xyz(leaves[MASK].shape.Vertexes[0].Point),
             detail=f'{exc}. Witness is a cover vertex, not a verified optical hit.')
    return pairs
