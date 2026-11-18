"""Collect and (optionally) cache derived views; no edits to the input FCStd."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import gzip
import json

import numpy as np
from PIL import Image
from shapely import from_wkb

import plates_render as studio
import plates_vector as vector
from plates_scene import FRONT, REAR, TOP, RIGHT, LEFT, BOTTOM, STUDIO, EXPLODED, ELEC, ELEC_BACK
from plates_scene import board_layers, choose


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
    seat_x: float
    mount: object


class Assets:
    def __init__(self, scene, cache=None, quick=False):
        self.scene = scene
        self.cache = None
        self.memo = {}
        self.quick = quick
        self.fingerprint = digest(scene.src)
        if cache is not None:
            inputs = [Path(__file__), Path(studio.__file__), Path(vector.__file__),
                      Path(__file__).with_name('plates_scene.py')]
            key = sha256((self.fingerprint + ''.join(digest(p) for p in inputs)).encode()).hexdigest()[:20]
            self.cache = Path(cache) / key
            self.cache.mkdir(parents=True, exist_ok=True)

    def derived(self, mode, items, frame, value=None):
        key = [mode, [i.name for i in items], np.asarray(frame).round(7).tolist(), value]
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
                visible = studio.visible_names(items, frame, width=1380)
                keep = [i for i in items if i.name in visible]
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
                tmp = path.with_suffix('.partial')
                with gzip.open(tmp, 'wt', encoding='utf-8', compresslevel=4) as f:
                    json.dump(data, f, separators=(',', ':'))
                tmp.replace(path)
        self.memo[name] = p
        return p

    def line(self, items, frame):
        return self.derived('lines', items, frame)

    def colors(self, root):
        return self.derived('color', self.scene.by[root], self.scene.board_frame(root))

    def section(self, items, x):
        return self.derived('section', items, RIGHT, float(x))

    def raster(self, mode):
        scene = self.scene
        views = {
            'assembled': (scene.items, STUDIO, None, (1380, 1510)),
            'exploded': (scene.items, EXPLODED, scene.offsets, (1990, 1500)),
            'electronics': (scene.subset('MainPCB', 'Harness', 'DisplayPCB'), ELEC, None, (1460, 1480)),
            'electronics-front': (scene.subset('MainPCB', 'Harness', 'DisplayPCB'), ELEC_BACK, None, (1060, 1380)),
        }
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
            if mode in ('assembled', 'exploded'):
                lut = [round(white*(n/white)**.76) if n < white else n
                       for white in (241, 244, 241) for n in range(256)]
                r = SimpleNamespace(image=r.image.point(lut), extent=r.extent)
            if path:
                r.image.save(path)
                path.with_suffix('.json').write_text(json.dumps([float(n) for n in r.extent]))
        self.memo[key] = r
        return r

    def cuts(self):
        """Cut B crosses an actual post centre, not the middle of an unrelated gap."""
        s = self.scene
        housing = s.by['Housing']
        x = (min(i.box[0, 0] for i in housing) + max(i.box[1, 0] for i in housing)) / 2
        targets = [*s.by['Mounts'], *housing]
        mount = choose(targets, 'DisplaySeatL', 'DisplaySeatR', 'panelboss', 'pcbpost', 'mainpost', 'uipost', 'boss', 'стойк',
                       'бобышк', 'standoff', 'опора', required=False)
        if mount is None:
            # Do not imply this is a post; use the actual first mounting leaf.
            mount = s.by['Mounts'][0]
        return Cut(x, mount.center[0], mount)

    def cut_items(self, mounting=False):
        scene = self.scene
        items = list(scene.by['Housing'])
        items.extend(scene.by['Mounts'])
        if not mounting:
            items.extend(scene.subset('Battery', 'Heater'))
        for root in ('MainPCB', 'DisplayPCB'):
            items.extend(board_layers(scene, root))
        return items
