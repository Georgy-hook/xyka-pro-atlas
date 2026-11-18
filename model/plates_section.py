"""Presentation roles for real, located section bodies. Never edit the native graph."""

from dataclasses import dataclass

from shapely.geometry import box

from plates_scene import RIGHT


@dataclass(frozen=True)
class _CutBody:
    name: str
    shape: object
    root: str  # The cut projector unions newly exposed material by this key.


POD_LAYERS = {'MechRemovablePod': 'PodBody', 'MechPodLid': 'PodLid', 'MechPodScreen': 'PodScreen'}


def _role(item, structured, mount):
    root = item.root
    if not structured:
        # The old file already has these physical leaves, but not the newer
        # functional roots. Use its *actual* parentage, not inferred solids.
        if 'MechPodAssembly' in item.chain and root == 'Heater':
            root = 'Pod'
        elif root == 'Housing':
            if 'MechLowerShellGroup' in item.chain:
                root = 'LowerBody'
            elif 'MechServicePanelGroup' in item.chain:
                root = 'Fascia'
            elif item.name == 'MechLightRing':
                root = 'LightRing'
    if root == 'Pod':
        return POD_LAYERS.get(item.name, root)
    if root == 'Heater' and item.name == 'MechHeatGuard':
        return 'HeatGuard'
    if mount is not None:
        if item is mount:
            return 'DisplaySeat'
        if root == 'DisplayPCB':
            if item.name == 'UiGlass':
                return 'Glass'
            if 'UiKeyMembrane' in (item.name, *item.chain):
                return 'KeyMembrane'
        if root == 'Fascia':
            if item.name.startswith('MechOuterKey'):
                return 'OuterKey'
            if item.name == 'MechCoverWindow':
                return 'FilmWindow'
    return root


def section(a, items, depth, frame=RIGHT, mount=None):
    """Same B-reps, clipping plane and HLR; only the hatch grouping changes.

    Include the presentation role in the temporary name for retagged leaves:
    Assets keys its cache by ordered names, frame and depth, not hatch keys.
    """
    bodies = []
    for item in items:
        role = _role(item, a.scene.structured, mount)
        bodies.append(item if role == item.root else _CutBody(f'{item.name}:{role}', item.shape, role))
    return a.section(bodies, depth, frame)


def cap_point(cap, bounds=None):
    """Anchor inside actual hatched material, never in a bore or outside the crop."""
    if cap is None:
        return None
    visible = cap if bounds is None else cap.intersection(box(*bounds))
    def polygons(area):
        if area.geom_type == 'Polygon':
            yield area
        elif hasattr(area, 'geoms'):
            for part in area.geoms:
                yield from polygons(part)

    piece = max((p for p in polygons(visible) if p.area > 0), key=lambda p: p.area, default=None)
    if piece is None:
        return None
    point = piece.representative_point()
    return point.x, point.y


def crop_view(s, proj, bounds, available, *, cap, weight):
    """Clip to exactly the model-space window marked in its parent view."""
    from plates_graphics import LINE, fit_scale  # legacy plate only, never part of the ESKD master
    x, y, w, h = available
    scale = fit_scale(bounds, available, cap=cap)
    cw = (bounds[2] - bounds[0]) * scale
    ch = (bounds[3] - bounds[1]) * scale
    rect = (x + (w-cw)/2, y + (h-ch)/2, cw, ch)
    m = s.geometry(proj, rect, bounds=bounds, scale=scale, weight=weight)
    s.rect(*rect, edge=LINE, lw=.19, z=8)
    return m


def window(s, mapping, bounds, tag):
    from plates_graphics import TEAL  # legacy plate only
    left, bottom, right, top = mapping.uvbox(bounds)
    s.rect(left, bottom, right-left, top-bottom, edge=TEAL, style='dashed', lw=.22, z=8)
    s.label(right+1.4, top, tag, 8.0, bold=True, color=TEAL, bg='white')
