"""Collect and (optionally) cache derived views; no edits to the input FCStd."""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import gzip
import json
import os
import tempfile

import FreeCAD  # Initialise the Part extension before use.
import Part
import numpy as np
from PIL import Image
from shapely import from_wkb

import plates_render as studio
import plates_vector as vector
from plates_scene import RIGHT, board_layers, camera
from plates_service import ServiceViews


def progress(text):
    print('=== ' + str(text), flush=True)


def digest(path):
    h = sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class Cut:
    x: float
    mount: object
    mount_point: np.ndarray
    seat_frame: np.ndarray
    seat_depth: float


class Assets:
    def __init__(self, scene, cache=None, quick=False):
        self.scene = scene
        self.service = ServiceViews(scene)
        self.service.check()
        self.cache = None
        self.memo = {}
        self.quick = quick
        self.fingerprint = digest(scene.src)
        if cache is not None:
            inputs = [Path(__file__), Path(studio.__file__), Path(vector.__file__),
                      Path(__file__).with_name('plates_scene.py'), Path(__file__).with_name('plates_service.py')]
            key = sha256((self.fingerprint + ''.join(digest(p) for p in inputs)).encode()).hexdigest()[:20]
            self.cache = Path(cache) / key
            self.cache.mkdir(parents=True, exist_ok=True)

    def derived(self, mode, items, frame, value=None):
        # A leaf may also appear in an exploded, locally aligned or cropped
        # B-rep projection. The installed and displaced poses are not interchangeable.
        def identity(i):
            p = i.shape.Placement
            return (i.name, i.root, tuple(round(v, 8) for v in (*p.Base, *p.Rotation.Q)))

        key = [mode, [identity(i) for i in items], np.asarray(frame).round(7).tolist(), value]
        name = sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:20]
        if name in self.memo:
            return self.memo[name]
        path = self.cache / f'{name}.json.gz' if self.cache else None
        if path and path.exists():
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            p = SimpleNamespace(lines=[np.asarray(l) for l in data['lines']],
                                light=[np.asarray(l) for l in data['light']],
                                fills=[(from_wkb(bytes.fromhex(poly)), c) for poly, c in data['fills']],
                                hatches=[(from_wkb(bytes.fromhex(poly)), c) for poly, c in data['hatches']],
                                bounds=tuple(data['bounds']))
        else:
            progress(f'{mode}: {len(items)} features, eye={np.array(frame[2]).round(2)}')
            if mode == 'color':
                p = vector.colour_view(items, frame)
            elif mode == 'section':
                p = vector.cut_view(items, frame, value)
            else:
                # The window stays installed. Its two transmitting optical
                # surfaces should not hide the LCD edges in an exterior
                # line drawing. Keep the actual thickness/rim faces in HLR.
                windows = [i for i in items if i.name == 'MechCoverWindow'
                           and float(getattr(i.obj, 'OpticalTransparency', 0)) > 0]
                opaque = [i for i in items if i not in windows]
                visible = studio.visible_names(opaque, frame, width=1380)
                keep = [i for i in opaque if i.name in visible]
                for item in windows:
                    normal = self.scene.board_frame('DisplayPCB')[2]
                    walls = []
                    for face in item.shape.Faces:
                        plane = face.findPlane(1e-6)
                        if plane is None or abs(normal @ tuple(plane.Axis)) < .99999:
                            walls.append(face)
                    if not walls:
                        raise ValueError(f'Cannot identify native window rim: {item.name}')
                    keep.append(replace(item, shape=Part.makeCompound(walls)))
                if not keep:
                    raise ValueError('No visible leaves in hidden-line view')
                p = vector.line_view(keep, frame)
            if not (p.lines or p.light or p.hatches or p.fills):
                raise ValueError('Empty generated CAD projection')
            if path:
                data = dict(lines=[np.asarray(l).round(5).tolist() for l in p.lines],
                            light=[np.asarray(l).round(5).tolist() for l in p.light],
                            fills=[(poly.wkb_hex, c) for poly, c in p.fills],
                            hatches=[(poly.wkb_hex, c) for poly, c in p.hatches],
                            bounds=[float(n) for n in p.bounds])
                # Distinct paper-proof processes may produce the same view.
                # Readers only ever see completed, source-keyed geometry.
                fd, name_tmp = tempfile.mkstemp(dir=path.parent, prefix='.hlr-', suffix='.partial')
                os.close(fd)
                tmp = Path(name_tmp)
                try:
                    with gzip.open(tmp, 'wt', encoding='utf-8', compresslevel=4) as f:
                        json.dump(data, f, separators=(',', ':'))
                    tmp.replace(path)
                finally:
                    tmp.unlink(missing_ok=True)
        self.memo[name] = p
        return p

    def line(self, items, frame):
        return self.derived('lines', items, frame)

    def colors(self, root):
        return self.derived('color', self.scene.by[root], self.scene.board_frame(root))

    def plan_points(self, root, items):
        """Interior visible points, not projected 3-D box centres (holes/occlusion)."""
        key = 'plan-labels:' + root
        if key not in self.memo:
            self.memo[key] = studio.root_anchors(self.scene.by[root], self.scene.board_frame(root),
                                                 name_mode=True, width=1300)
        anchors = self.memo[key]
        return [(n, anchors[i.name]) for n, i in enumerate(items, 1) if i.name in anchors]

    def section(self, items, depth, frame=RIGHT):
        """Retain w <= depth with w and the plane marker in the SAME world frame."""
        return self.derived('section', items, frame, float(depth))

    def raster(self, mode):
        views = self.service.specs()
        if mode not in views:
            raise ValueError(mode)
        items, frame, offsets, size = views[mode]
        if self.quick:
            size = tuple(round(v*.45) for v in size)
        key = f'{mode}-{size[0]}-{size[1]}'
        if key in self.memo:
            return self.memo[key]
        path = self.cache / f'{key}.png' if self.cache else None
        if path and path.exists() and path.with_suffix('.json').exists():
            img = Image.open(path).convert('RGB')
            r = SimpleNamespace(image=img, extent=tuple(json.loads(path.with_suffix('.json').read_text())))
        else:
            progress(f'Studio: {mode} | {size[0]} × {size[1]}')
            r = studio.render(items, frame, width=size[0], height=size[1], offsets=offsets,
                              bgcolor='#f1f4f1', padding=.075)
            # A neutral black lift for print prevents adjacent dark housing parts
            # from closing up. It changes no geometry; the paper white is fixed.
            if mode in ('assembled', 'exploded', 'upper-unit', 'lower-unit', 'film-service', 'key-service'):
                lut = [round(white*(n/white)**.76) if n < white else n
                       for white in (241, 244, 241) for n in range(256)]
                r = SimpleNamespace(image=r.image.point(lut), extent=r.extent)
            if path:
                r.image.save(path)
                path.with_suffix('.json').write_text(json.dumps([float(n) for n in r.extent]))
        self.memo[key] = r
        return r

    def anchors(self, mode, names=False):
        """Pick on precisely the same registered leaves and poses as the image."""
        key = f'anchors:{mode}:{names}'
        if key not in self.memo:
            items, frame, offsets, _ = self.service.specs()[mode]
            self.memo[key] = studio.root_anchors(items, frame, offsets=offsets, width=1250, name_mode=names)
        return self.memo[key]

    def cuts(self):
        """Cut B crosses an actual post centre, not the middle of an unrelated gap."""
        s = self.scene
        housing = s.by['Housing'] + s.by.get('LowerBody', [])
        x = (min(i.box[0, 0] for i in housing) + max(i.box[1, 0] for i in housing)) / 2
        # Never take a general-purpose base boss or arbitrary fastening leaf:
        # the B–B locator must pass through the *actual display mounting seat*.
        target_roots = ('Fascia', 'Mounts', 'Housing')
        targets = {i.name: i for root in target_roots for i in s.by.get(root, [])}
        seat_ids = ('MechDisplaySeatL', 'MechDisplaySeatR', 'UiDisplaySeatL', 'UiDisplaySeatR',
                    'MechUiSeatL', 'MechUiSeatR', 'DisplaySeatL', 'DisplaySeatR')
        mount = next((targets[k] for k in seat_ids if k in targets), None)
        if mount is None:
            raise ValueError('No known display seat in Fascia, Mounts or Housing; do not issue an invented section B')
        # In locator B1 the observer looks along local +w. A plane normal to
        # local u therefore appears edge-on at this u, even after yaw or roll.
        # The side view B2 retains gravity vertical where geometrically possible.
        u, v, _ = s.board_frame('DisplayPCB')
        up = (0, 0, 1) if abs(u[2]) < .98 else v
        seat_frame = camera(u, up)
        # A registered mounting leaf can be a one-solid Compound (Part::Scale).
        # Use a point on the axis of a real fastening body, not the empty space
        # between bodies of a compound, nor the centre of its world AABB.
        principal = max(mount.shape.Solids, key=lambda solid: solid.Volume)
        origin = np.array(principal.CenterOfMass)
        return Cut(x, mount, origin, seat_frame, float(u @ origin))

    def cut_items(self, mounting=False):
        scene = self.scene
        structural = ('Housing', 'LowerBody', 'Fascia', 'LightRing', 'Mounts')
        items = [i for root in structural for i in scene.by.get(root, [])]
        if not mounting:
            items.extend(i for root in ('Battery', 'Heater', 'Pod') for i in scene.by.get(root, []))
        for root in ('MainPCB', 'DisplayPCB'):
            items.extend(board_layers(scene, root))
        # Show the actual glass plane and supporting LCD stack in section.
        items.extend(i for i in scene.by['DisplayPCB'] if i.name in ('UiBacking', 'UiCell', 'UiRim', 'UiGlass'))
        items.extend(i for i in scene.by['DisplayPCB'] if 'UiKeyMembrane' in (i.name, *i.chain))
        return items
