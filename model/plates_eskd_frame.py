"""A single physical, monochrome master for ESKD drawing and text sheets.

All geometry is in millimetres from the paper's lower left, not from the
frame. Title blocks: GOST R 2.104-2023, Appendix Б.1–Б.3, September 2024
edition incorporating ИУС 7/2024 and 12/2024; field numbers in comments
refer to its Table 1. No assigned stage, mass, revision, signature or
organisation is inferred. Optional fields shown dashed in the standard
are omitted unless needed (Б.6); field 35 is provided for electronic KD.
"""

import math
from io import StringIO
from operator import index
from pathlib import Path
from xml.sax.saxutils import escape

from matplotlib import rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

if __package__:
    from .plates_eskd_font import PT_PER_MM, drawing_font
else:  # The existing command-line producers put model/ on sys.path.
    from plates_eskd_font import PT_PER_MM, drawing_font


_PAPER = {"A3": (420, 297), "A4": (210, 297)}
_HEIGHT = {"1": 55, "2": 40, "2а": 15}
_MAIN, _THIN = 0.7, 0.25
_SIZES = (7, 5, 3.5, 2.5, 1.8)
# Confirmed for this ESKD issue. Field 35 is the electronic document's
# version, not model A4.3; field 9 identifies the project, not a manufacturer.
_DOCUMENT_VERSION = "1"
_DEVELOPER_PROJECT = "XKAH PRO / реконструкция"


def _word_lines(value, measure, available, wrap):
    lines = []
    for paragraph in value.split("\n"):
        if not wrap:
            lines.append(paragraph)
            continue
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}" if line else word
            if line and measure(candidate)[0] > available:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


class Sheet:
    """A3 landscape / A4 portrait. Form '2a' is also accepted as '2а'.

    On form 2а, pass a nonempty scale for a graphical KD (field 26), or ''
    for a text KD (no field 26). `product`, if supplied, is part of field 1,
    never the name of an organisation. Figure and axes are not pyplot-owned.
    """

    def __init__(self, designation, title, scale, *, paper='A3', number=1,
                 sheets=1, form='1', material='', product=''):
        self.paper, self.form, self.scale = paper, form, scale
        self._paper = str(paper).strip().upper().replace("А", "A")
        self._form = str(form).strip().lower().replace("a", "а")
        self._scale_text = "" if scale is None else str(scale).strip()
        if self._paper not in _PAPER or self._form not in _HEIGHT:
            raise ValueError("Expected A3 or A4, and form 1, 2 or 2а")
        self.number, self.sheets = index(number), index(sheets)
        if not 1 <= self.number <= self.sheets:
            raise ValueError("Expected 1 <= number <= sheets")
        self.designation = str(designation)
        self.title = str(title)
        self.product, self.material = product or "", material or ""
        self.width, self.height = _PAPER[self._paper]
        self._face = drawing_font()
        self.fig = Figure(figsize=(self.width / 25.4, self.height / 25.4),
                          dpi=100, facecolor="white", layout="none")
        FigureCanvasAgg(self.fig)
        self.ax = self.fig.add_axes((0, 0, 1, 1), facecolor="white")
        self.finish()
        self._frame()
        _Stamp(self).draw()

    def text(self, x, y, text, h=3.5, **kwargs):
        """Place searchable text. h is the *ink height* of a flat capital in mm."""
        if not math.isfinite(h) or h <= 0:
            raise ValueError("h must be a positive cap height in mm")
        value = str(text)
        self._face.check_glyphs(value)
        if "c" not in kwargs:
            kwargs.setdefault("color", "black")
        return self.ax.text(x, y, value, fontproperties=self._face.properties(h),
                            parse_math=False, usetex=False, **kwargs)

    def line(self, points, *, width=.35, style='solid', **kwargs):
        """Add a polyline. width is a pen width in mm; style is a Line2D style."""
        if not math.isfinite(width) or width <= 0:
            raise ValueError("width must be a positive pen width in mm")
        xs, ys = zip(*points)
        if "c" not in kwargs:
            kwargs.setdefault("color", "black")
        kwargs.setdefault("solid_capstyle", "butt")
        kwargs.setdefault("solid_joinstyle", "miter")
        kwargs.setdefault("dash_capstyle", "butt")
        kwargs.setdefault("marker", "")
        return self.ax.add_line(Line2D(xs, ys, linewidth=width * PT_PER_MM,
                                       linestyle=style, **kwargs))

    def finish(self):
        """Restore the uncropped sheet and isotropic 1:1 data transform."""
        self.fig.set_size_inches(self.width / 25.4, self.height / 25.4, forward=False)
        self.ax.set_position((0, 0, 1, 1))
        self.ax.set_xlim(0, self.width)
        self.ax.set_ylim(0, self.height)
        self.ax.set_aspect("equal", adjustable="box", anchor="SW")
        self.ax.set_autoscale_on(False)
        self.ax.set_axis_off()
        return self

    def _box(self, x, y, width, height, value, *, size=2.5, wrap=False, angle=0):
        """Centre actual glyph ink vertically; do not truncate or distort a field."""
        if not value:
            return
        u, v = (height, width) if angle == 90 else (width, height)
        measure = self._face.metrics
        for h in _SIZES:
            if h > size:
                continue
            available = (u - 1.0) / h
            lines = _word_lines(str(value), measure, available, wrap)
            dims = [measure(s) for s in lines]
            lead = 1.65  # baseline distance in cap heights
            top = max(a - i * lead for i, (_, a, _) in enumerate(dims))
            bottom = min(-d - i * lead for i, (_, _, d) in enumerate(dims))
            if max(w for w, _, _ in dims) <= available and (top - bottom) * h <= v - .6:
                break
        else:
            raise ValueError(f"Text does not fit {width} × {height} mm field: {value!r}")
        theta = math.radians(angle)
        for i, s in enumerate(lines):
            dy = h * (-(top + bottom) / 2 - i * lead)
            self.text(x + width / 2 - math.sin(theta) * dy,
                      y + height / 2 + math.cos(theta) * dy,
                      s, h, ha="center", va="baseline", rotation=angle,
                      rotation_mode="anchor")

    def _frame(self):
        left, right, low, top = 20, self.width - 5, 5, self.height - 5
        self.line([(left, low), (right, low), (right, top), (left, top),
                   (left, low)], width=_MAIN)
        # Accounting strip (19–23), outside the frame on the binding edge.
        fields = ((25, "Инв. № подл."), (35, "Подп. и дата"), (25, "Взам. инв. №"),
                  (25, "Инв. № дубл."), (35, "Подп. и дата"))
        y = low
        for length, label in fields:
            self.line([(8, y), (left, y)], width=_MAIN)
            self._box(8, y, 5, length, label, angle=90)
            y += length
        self.line([(8, low), (8, y), (left, y)], width=_MAIN)
        self.line([(13, low), (13, y)], width=_MAIN)

        # Rotated designation (26), not a second title; both permitted paper
        # orientations here require 180° (Table 1). No such box on text KDs.
        if self._form == "1" or (self._form == "2а" and self._scale_text):
            self.line([(left, top - 14), (left + 70, top - 14),
                       (left + 70, top)], width=_MAIN)
            self._box(left, top - 14, 70, 14, self.designation, size=5, angle=180)

        # Fields 31/32 occupy the 5 mm strip BELOW the frame (Б.1–Б.3).
        self._box(right - 116, 0, 66, 5, "Копировал")
        self._box(right - 50, 0, 50, 5, f"Формат {self._paper}")


class _Stamp:
    """Millimetre dimensions are local to the lower left of the 185 mm block."""

    def __init__(self, sheet):
        self.s = sheet
        self.left = sheet.width - 5 - 185
        self.form = sheet._form
        self.height = _HEIGHT[self.form]

    def h(self, y, x1, x2, pen=_MAIN):
        self.s.line([(self.left + x1, 5 + y), (self.left + x2, 5 + y)], width=pen)

    def v(self, x, y1, y2, pen=_MAIN):
        self.s.line([(self.left + x, 5 + y1), (self.left + x, 5 + y2)], width=pen)

    def label(self, x, y, w, h, value, **kwargs):
        self.s._box(self.left + x, 5 + y, w, h, value, **kwargs)

    def draw(self):
        s, height = self.s, self.height
        self.h(height, 0, 185)
        if self.left > 20:  # On A4 the binding-side frame IS the left border.
            self.v(0, 0, height)
        roles = {"1": ("Утв.", "Н. контр.", "", "Т. контр.", "Пров.", "Разраб."),
                 "2": ("Утв.", "Н. контр.", "", "Пров.", "Разраб."), "2а": ()}[self.form]
        change_y = 5 * len(roles)
        # Signature block (10–13) and changes (14–18) share a 65 mm grid.
        for x in (17, 40, 55, 65):
            self.v(x, 0, height)
        self.v(7, change_y, height)
        for y in range(5, height, 5):
            self.h(y, 0, 65, _MAIN if y in (change_y, change_y + 5) else _THIN)
        for i, role in enumerate(roles):
            self.label(0, 5 * i, 17, 5, role)
        for x, w, name in ((0, 7, "Изм."), (7, 10, "Лист"), (17, 23, "№ докум."),
                           (40, 15, "Подп."), (55, 10, "Дата")):
            self.label(x, change_y, w, 5, name)

        # The designation (2) and version (35) always form a 15 mm band.
        version_x = 165 if self.form == "2а" else 175
        self.v(version_x, height - 15, height)
        self.h(height - 5, version_x, 185)
        self.label(version_x, height - 5, 10, 5, "Вер.")
        self.label(version_x, height - 15, 10, 10, _DOCUMENT_VERSION, size=3.5)
        self.label(65, height - 15, version_x - 65, 15, s.designation, size=7)
        if self.form == "2а":
            self.v(175, 0, 15)
            self.label(175, 10, 10, 5, "Лист")
            self.label(175, 0, 10, 10, s.number, size=3.5)  # No total on 2а.
            return

        self.h(height - 15, 65, 185)
        self.v(135, 0, height - 15)
        self.h(15, 135, 185)
        self.label(135, 0, 50, 15, _DEVELOPER_PROJECT, size=3.5)  # 9
        name = "\n".join(filter(None, (s.product, s.title)))
        if self.form == "1":
            self.h(15, 65, 135)
            self.label(65, 15, 70, 25, name, size=5, wrap=True)  # 1
            self.label(65, 0, 70, 15, s.material, size=3.5, wrap=True)  # 3
            self.h(35, 135, 185)
            self.h(20, 135, 185)
            self.v(150, 20, 40)
            self.v(167, 20, 40)
            self.label(150, 35, 17, 5, "Масса")  # 5: no invented mass
            self.label(167, 35, 18, 5, "Масштаб")
            self.label(167, 20, 18, 15, s._scale_text, size=5)  # 6
            self.v(155, 15, 20)
            self.label(135, 15, 20, 5, f"Лист {s.number}")
            self.label(155, 15, 30, 5, f"Листов {s.sheets}")
            lit_y, lit_h = 20, 15
        else:  # Form 2: no material, mass or scale fields.
            self.label(65, 0, 70, 25, name, size=5, wrap=True)
            self.h(20, 135, 185)
            self.v(150, 15, 25)
            self.v(165, 15, 25)
            self.label(150, 20, 15, 5, "Лист")
            self.label(165, 20, 20, 5, "Листов")
            self.label(150, 15, 15, 5, s.number)
            self.label(165, 15, 20, 5, s.sheets)
            lit_y, lit_h = 15, 5
        # Field 4: three *separate* 5 mm sites for assigned stage letters.
        self.v(140, lit_y, lit_y + lit_h)
        self.v(145, lit_y, lit_y + lit_h)
        self.label(135, lit_y + lit_h, 15, 5, "Лит.")


def write_sheet(sheet, pdf_path, svg_path, source=''):
    """Write uncropped vector siblings; keep the supplied evidence string verbatim."""
    sheet.finish()
    face = sheet._face
    title = f"{sheet.designation} — {sheet.title}"
    svg = StringIO()
    # Never change the selected backend or pyplot's rcParams at import time.
    # These settings are temporary even when a writer raises an exception.
    with rc_context({"pdf.fonttype": 42, "pdf.use14corefonts": False,
                     "svg.fonttype": "none", "svg.hashsalt": "eskd-sheet",
                     "savefig.bbox": None, "savefig.transparent": False,
                     "path.simplify": False}):
        sheet.fig.savefig(svg, format="svg", facecolor="white", metadata={
            "Title": title, "Description": source, "Rights": face.credit, "Date": None})
        head, defs, body = svg.getvalue().partition("<defs>")
        if not defs:
            raise RuntimeError("SVG writer did not produce a definitions element")
        if "<image" in body:
            raise ValueError("The sheet contains a raster image or a rasterized artist")
        # Matplotlib writes Dublin Core dc:description; provide the equivalent
        # native SVG desc for viewers that only inspect the document root.
        document = f"{head}<desc>{escape(source)}</desc>\n{defs}{face.svg_face}\n{body}"
        sheet.fig.savefig(pdf_path, format="pdf", facecolor="white", metadata={
            "Title": title, "Subject": source, "Keywords": face.credit, "CreationDate": None})
    Path(svg_path).write_text(document, encoding="utf-8")
