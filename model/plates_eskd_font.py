"""The drawing face used by plates_eskd_frame; no system font installation.

osifont is an ISO-style engineering face, not a certified GOST 2.304 font.
Upstream: https://github.com/hikikomori82/osifont . The FreeCAD TechDraw
copy is accompanied by osifont.license; we use the LGPLv3 + Font Exception
option. ESKD_FONT_PATH can point to a local copy on a machine without FreeCAD.
"""

import base64
import os
from functools import cached_property, lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath


PT_PER_MM = 72 / 25.4
SOURCE = "https://github.com/hikikomori82/osifont"
LICENSE = "GNU LGPL v3 with GPL Font Exception"
FILENAME = "osifont-lgpl3fe.ttf"


def drawing_font():
    """Resolve only the agreed face. Never silently change a drawing's metrics."""
    override = os.environ.get("ESKD_FONT_PATH")
    if override:
        return _load(Path(override).expanduser().resolve())
    relative = Path("Mod/TechDraw/Resources/fonts") / FILENAME
    for root in (
        Path("/Applications/FreeCAD.app/Contents/Resources/share"),
        Path("/usr/share/freecad"),
        Path("/usr/local/share/freecad"),
    ):
        candidate = root / relative
        if candidate.is_file():
            return _load(candidate)
    raise FileNotFoundError(f"Set ESKD_FONT_PATH to TechDraw's {FILENAME}")


@lru_cache(maxsize=4)
def _load(path):
    return _DrawingFont(path)


class _DrawingFont:
    def __init__(self, path):
        self.path = path
        with TTFont(path) as tt:
            names = tt["name"]
            self.family = names.getDebugName(1) or ""
            self.version = (names.getDebugName(5) or "").strip()
            notice = " ".join(names.getDebugName(i) or "" for i in (0, 13)).lower()
            if (self.family.lower() != "osifont" or "lgpl" not in notice
                    or "font exception" not in notice or tt["OS/2"].fsType != 0):
                raise ValueError(f"Expected embeddable osifont (LGPLv3 + Font Exception): {path}")
            cmap = tt.getBestCmap()
            self.codepoints = frozenset(cmap)
            # This TechDraw face has no OS/2.sCapHeight. The actual straight
            # cap H is 1510 units on a 2048-unit em (not the line/em height).
            cap = tt["glyf"][cmap[ord("H")]]
            self.cap_fraction = (cap.yMax - cap.yMin) / tt["head"].unitsPerEm
        self.credit = (f"Font only: {self.family}, {self.version}, by Zefram Cochrane; "
                       f"{LICENSE}; {SOURCE}; https://www.gnu.org/licenses/lgpl-3.0.html")
        self._measure_at = FontProperties(family=self.family, fname=str(path), size=100,
                                          style="normal", weight="normal", stretch="normal",
                                          variant="normal")
        self._ruler = TextToPath()

    def properties(self, h):
        prop = self._measure_at.copy()
        prop.set_size(h * PT_PER_MM / self.cap_fraction)
        return prop

    @lru_cache(maxsize=2048)
    def metrics(self, text):
        """Advance, ascent and descent in mm when the nominal cap is 1 mm."""
        width, height, descent = self._ruler.get_text_width_height_descent(
            text, self._measure_at, ismath=False
        )
        unit = 100 * self.cap_fraction
        return width / unit, (height - descent) / unit, descent / unit

    def check_glyphs(self, text):
        missing = {c for c in text if c != "\n" and ord(c) not in self.codepoints}
        if missing:
            chars = ", ".join(f"{c!r} (U+{ord(c):04X})" for c in sorted(missing))
            raise ValueError(f"osifont lacks {chars}; use an available drawing symbol")

    @cached_property
    def svg_face(self):
        # Embed the original, unmodified TTF. Browser SVG remains editable and
        # searchable, and has no dependency on fonts installed on the reader.
        data = base64.b64encode(self.path.read_bytes()).decode("ascii")
        return ("<style type=\"text/css\">@font-face { font-family: 'osifont'; "
                f"src: url('data:font/ttf;base64,{data}') format('truetype'); "
                "}</style>")
