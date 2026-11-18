"""Nonphysical retail LCD evidence, registered against the assembled native faces.

`presentation_descriptor(doc)` is called by the CAD builder after recompute. Its
JSON result belongs in Evidence.PresentationJSON, never in the physical tree.
A reader of the saved document needs no artwork source files or photographs.
"""

import json
import math
import re

import FreeCAD as App
import Part
import numpy as np

from plates_scene import global_shape


def _unit(vector):
    return vector / np.linalg.norm(vector)


def _gltf(xyz):
    x, y, z = xyz
    return [float(x), float(z), float(-y)]


def _normal(face):
    u0, u1, v0, v1 = face.ParameterRange
    return np.array(tuple(face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)))


def _outward_faces(shape, outward):
    for face in shape.Faces:
        n = _normal(face)
        if n @ outward > 0.99 and face.findPlane(1e-6) is not None:
            yield face, _unit(n)


def _uv_bounds(shape, to_local):
    # Exact CAD extent in the optical plane, not the projected *world* AABB
    # (incorrect on the raked fascia), nor just vertices of a curved outline.
    copy = shape.copy()
    copy.Placement = to_local.multiply(copy.Placement)
    b = copy.optimalBoundingBox(False, False)
    return np.array([[b.XMin, b.YMin], [b.XMax, b.YMax]])


def _optical_plane(doc, anchor):
    if anchor != 'UiGlass':
        raise ValueError('The boot state belongs to the LCD, not to the removable film')
    board, glass = doc.getObject('DisplayPCB'), doc.getObject(anchor)
    if board is None or glass is None or 'ColorHex' not in glass.PropertiesList:
        raise ValueError(f'LCD optical anchor {anchor!r} is not a registered physical leaf')
    rotation = board.getGlobalPlacement().Rotation
    right = np.array(tuple(rotation.multVec(App.Vector(1, 0, 0))))
    outward = np.array(tuple(rotation.multVec(App.Vector(0, 0, 1))))
    candidates = list(_outward_faces(global_shape(glass), outward))
    if not candidates:
        raise ValueError(f'{anchor}: missing planar outward optical face')
    face, normal = max(candidates, key=lambda pair: pair[0].Area)
    u = _unit(right - normal * (right @ normal))
    v = np.cross(normal, u)
    axes = np.stack([u, v, normal])
    frame = App.Placement(App.Vector(), App.Rotation(*(App.Vector(*a) for a in axes), 'ZXY'))
    to_local = frame.inverse()
    depth = np.array(tuple(face.CenterOfMass)) @ normal
    # The optical window can be larger than the internal rear LCD slab or
    # offset from its centre. Register the design to the *window footprint*
    # projected onto the LCD plane. Verify the ink itself against both faces.
    pane = doc.getObject('MechCoverWindow')
    windows = [(face, depth)]
    if pane is not None:
        fronts = list(_outward_faces(global_shape(pane), normal))
        if not fronts:
            raise ValueError('MechCoverWindow has no planar outward optical surface')
        optical, pane_n = max(fronts, key=lambda pair: pair[0].Area)
        if not np.allclose(pane_n, normal, rtol=0., atol=1e-6):
            raise ValueError('MechCoverWindow is not parallel to the installed LCD')
        bounds = _uv_bounds(optical, to_local)
        pane_depth = np.array(tuple(optical.CenterOfMass)) @ normal
        if pane_depth < depth - 1e-5:
            raise ValueError('The removable optical window is behind the LCD')
        windows.append((optical, pane_depth))
    else:
        if doc.getObject('UpperUnit') is not None:
            raise ValueError('Missing optical zone of the retail face film: MechCoverWindow')
        bounds = _uv_bounds(face, to_local)
    center_uv = bounds.mean(axis=0)
    # A mask can crop the front of a larger LCD. Take the actual aperture
    # containing the optical centre; never select an adjacent button/tool or
    # infer a screen width from the housing/raster resolution.
    for name in ('MechServiceCover', 'MechKeyCarrier'):
        mask = doc.getObject(name)
        if mask is None or name == anchor:
            continue
        open_at_center = False
        for panel, n in _outward_faces(global_shape(mask), normal):
            panel_depth = np.array(tuple(panel.CenterOfMass)) @ normal
            if len(panel.Wires) < 2 or n @ normal < 0.99999:
                continue
            projected = App.Vector(*((center_uv[0], center_uv[1], panel_depth) @ axes))
            for wire in panel.Wires:
                if wire.isSame(panel.OuterWire):
                    continue
                opening = Part.Face(wire)
                if opening.isInside(projected, 1e-5, True):
                    open_at_center = True
                    if pane is None:
                        aperture = _uv_bounds(wire, to_local)
                        bounds[0] = np.maximum(bounds[0], aperture[0])
                        bounds[1] = np.minimum(bounds[1], aperture[1])
                    windows.append((opening, panel_depth))
        if pane is not None and not open_at_center:
            raise ValueError(f'{name}: no optical opening at the registered LCD centre')
    size = bounds[1] - bounds[0]
    if not np.isfinite(bounds).all() or np.any(size <= 0):
        raise ValueError(f'{anchor}: empty optical aperture')
    center_uv = bounds.mean(axis=0)
    origin = np.r_[center_uv, depth] @ axes
    (x0, y0), (x1, y1) = bounds
    corners = [_gltf((np.array([x, y, depth]) @ axes) * .001)
               for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    lcd = {'anchor': anchor, 'origin': _gltf(origin * .001), 'u': _gltf(u), 'v': _gltf(v),
           'normal': _gltf(normal), 'corners': corners}
    if pane is not None:
        lcd['windowId'] = pane.Name
    return lcd, size, center_uv, axes, windows


def _check_trace(art, size, center_uv, axes, windows):
    if (not isinstance(art, dict) or art.get('kind') != 'presentation'
            or art.get('state') != 'regional-boot-reference' or art.get('units') != 'mm'
            or art.get('emissive') is not True or art.get('center') != [0, 0]
            or not re.fullmatch(r'#[\da-fA-F]{6}', str(art.get('color', '')))
            or not isinstance(art.get('polygons'), list) or not art['polygons']):
        raise ValueError('Missing or invalid source-traced LCD artwork')
    for polygon in art['polygons']:
        if not isinstance(polygon, dict) or not isinstance(polygon.get('holes'), list):
            raise ValueError('Bad LCD polygon/holes')
        for ring in [polygon.get('points'), *polygon['holes']]:
            if not isinstance(ring, list) or len(ring) < 3:
                raise ValueError('Empty LCD contour')
            for pt in ring:
                if (not isinstance(pt, (list, tuple)) or len(pt) != 2
                        or any(type(x) not in (int, float) or not math.isfinite(x) for x in pt)):
                    raise ValueError('Nonfinite or malformed LCD contour point')
                if np.any(np.abs(pt) > size / 2 + 1e-5):
                    raise ValueError('LCD artwork lies outside optical bounds')
                for region, depth in windows:
                    xyz = np.r_[center_uv + pt, depth] @ axes
                    if not region.isInside(App.Vector(*xyz), 1e-5, True):
                        raise ValueError('LCD artwork clips against actual optical face/seat')
            points = np.asarray(ring)
            if abs(np.sum(np.cross(points, np.roll(points, -1, axis=0)))) < 1e-11:
                raise ValueError('Zero-area LCD artwork contour')


def presentation_descriptor(doc):
    """Build once from the *actual* native optical face and the traced regional art."""
    from retail_marks import BOOT_SOURCE, boot_artwork

    lcd, size, center, axes, windows = _optical_plane(doc, 'UiGlass')
    art = boot_artwork(*map(float, size))
    _check_trace(art, size, center, axes, windows)
    return {'lcd': {**lcd, 'artwork': art, 'source': BOOT_SOURCE}}


def saved_presentation(doc, physical_ids):
    """Read the native evidence verbatim; check its placement against the reopened glass."""
    evidence = doc.getObject('Evidence')
    if (evidence is None or 'PresentationJSON' not in evidence.PropertiesList
            or evidence.getTypeIdOfProperty('PresentationJSON') != 'App::PropertyString'):
        raise ValueError('Missing saved Evidence.PresentationJSON')
    pres = json.loads(evidence.PresentationJSON)
    lcd = pres.get('lcd') if isinstance(pres, dict) else None
    if not isinstance(lcd, dict) or not isinstance(lcd.get('anchor'), str) or lcd['anchor'] not in physical_ids:
        raise ValueError('LCD anchor is not a physical leaf in this assembly')
    if not isinstance(lcd.get('source'), str) or not lcd['source'].strip():
        raise ValueError('LCD presentation needs its optical reference source')
    optical, size, center, axes, windows = _optical_plane(doc, lcd['anchor'])
    if lcd.get('windowId') != optical.get('windowId') or (lcd.get('windowId') and lcd['windowId'] not in physical_ids):
        raise ValueError('LCD optical window ID does not match its physical carrier')
    for k in ('origin', 'u', 'v', 'normal', 'corners'):
        expected = np.asarray(optical[k])
        given = np.asarray(lcd.get(k))
        if (given.shape != expected.shape or given.dtype.kind not in 'fiu'
                or not np.allclose(given, expected, rtol=0., atol=1e-7)):
            raise ValueError(f'{lcd["anchor"]}: stale/invalid LCD {k} vs saved optical face')
    _check_trace(lcd.get('artwork'), size, center, axes, windows)
    return pres
