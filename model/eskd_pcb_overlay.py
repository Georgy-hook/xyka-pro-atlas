"""Add native vector copper to a single landscape A3 Matplotlib PDF/SVG pair.

All placement matrices act on absolute board mm, including B.Cu. The clip is
in *paper* mm, before the board transform. Neither side is implicitly mirrored.
Only the added SVG groups pass through librsvg/Cairo; the base is never replotted.

``add_copper(pdf_path, svg_path, placements, *, verify_python=None)`` runs the
worker with /usr/bin/python3 by default. The caller needs only the stdlib; the
worker needs PyMuPDF, Pillow and librsvg >= 2.46 with Cairo PDF (FreeCAD ships
the dylib on macOS). No display, Qt application, installation or shell required.
CLI: ``python3 eskd_pcb_overlay.py --check`` exercises both vector and clipping;
``python3 eskd_pcb_overlay.py BASE.pdf BASE.svg [placements.json]`` also works
(JSON group values are serialized <g> elements; stdin if no manifest is given).
"""

import argparse
import ctypes as C
import ctypes.util
from contextlib import ExitStack
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from xml.parsers import expat


SVG = "{http://www.w3.org/2000/svg}"
PAPER = (420, 297)
PT = 72 / 25.4
PX = 4  # pixels / printed mm, used *only* for visibility tests
# Cairo quantizes its clip to fractional points and MuPDF rounds the PDF
# rectangular scissor outwards to device pixels. At an exact pixel boundary,
# even a 0.001 mm rounding can therefore show one entire extra boundary row.
PDF_EDGE_MM = 0.002
SHAPES = {"path", "circle", "rect", "line", "polyline", "polygon", "ellipse"}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"


def add_copper(pdf_path, svg_path, placements, *, verify_python=None):
    """Append and verify the groups, returning JSON-able dimensions/ink evidence."""
    records = []
    for item in placements:
        if not ET.iselement(item["group"]):
            raise TypeError("placement group must be an ElementTree element")
        records.append({"id": item["id"], "clip": item["clip"], "transform": item["transform"],
                        "group": ET.tostring(item["group"], encoding="unicode")})
    # -E ignores FreeCAD's Python paths but, unlike -I, retains user-site fitz.
    cmd = [verify_python or "/usr/bin/python3", "-E", "-B", Path(__file__).resolve(), "--",
           Path(pdf_path).resolve(strict=True), Path(svg_path).resolve(strict=True)]
    result = subprocess.run(cmd, input=json.dumps(records, allow_nan=False),
                            capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode:
        raise RuntimeError(f"copper compositor exited {result.returncode}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _length_mm(value):
    match = re.fullmatch(rf"\s*({NUMBER})\s*(mm|cm|in|pt|px|pc)?\s*", value or "")
    if not match:
        raise ValueError(f"expected physical SVG length, got {value!r}")
    units = {"mm": 1, "cm": 10, "in": 25.4, "pt": 1 / PT, "pc": 12 / PT,
             "px": 25.4 / 96, None: 25.4 / 96}
    return float(match[1]) * units[match[2]]


def _numbers(value, n):
    words = re.split(r"[\s,]+", value.strip())
    if len(words) != n or not all(re.fullmatch(NUMBER, word) for word in words):
        raise ValueError(f"expected {n} SVG numbers: {value!r}")
    nums = tuple(map(float, words))
    if not all(map(math.isfinite, nums)):
        raise ValueError("nonfinite SVG coordinate")
    return nums


def _check_a3(width, height):
    if not all(abs(a - b) < 0.02 for a, b in zip((width, height), PAPER)):
        raise ValueError(f"expected uncropped landscape A3; got {width:g} × {height:g} mm")
    return [round(width, 5), round(height, 5)]


def _sheet(raw):
    root = ET.fromstring(raw)
    if root.tag != SVG + "svg":
        raise ValueError("expected a namespaced Matplotlib SVG")
    w, h = (_length_mm(root.get(k)) for k in ("width", "height"))
    paper = _check_a3(w, h)
    x, y, vw, vh = _numbers(root.attrib["viewBox"], 4)
    if vw <= 0 or vh <= 0 or abs(vw / vh * h - w) > 0.02:
        raise ValueError("SVG viewBox does not have the physical A3 aspect ratio")
    # Use the base's actual viewport (usually pt), including any nonzero origin.
    matrix = f"matrix({vw / w:.15g} 0 0 {vh / h:.15g} {x:.15g} {y:.15g})"
    attrs = {k: root.attrib[k] for k in ("width", "height", "viewBox", "preserveAspectRatio")
             if k in root.attrib}
    return attrs, matrix, paper, {n.get("id") for n in root.iter() if "id" in n.attrib}


def _append_svg(raw, layers):
    # Insert at the root's real closing tag. Preserve the original bytes, e.g.
    # Matplotlib's DOCTYPE, style, text, metadata, links, and trailing comments.
    parser = expat.ParserCreate()
    end = None

    def on_end(name):
        nonlocal end
        end = (parser.CurrentByteIndex, name.encode("utf-8"))

    parser.EndElementHandler = on_end
    parser.Parse(raw, True)
    index, tag = end  # root closes last
    fragment = b"\n" + b"\n".join(ET.tostring(layer, encoding="utf-8") for layer in layers)
    if raw[index:index + 2] == b"</":
        return raw[:index] + fragment + b"\n" + raw[index:]
    if raw[index - 2:index] == b"/>":  # also allow a minimal, empty SVG base
        return raw[:index - 2] + b">" + fragment + b"\n</" + tag + b">" + raw[index:]
    raise ValueError("unsupported SVG base encoding; expected UTF-8")


def _placement(item, sheet_matrix, used):
    name = item["id"]
    if not re.fullmatch(r"[A-Za-z_][\w.-]*", name) or name in used:
        raise ValueError(f"invalid or duplicate SVG placement id: {name!r}")
    used.add(name)
    transform = item["transform"].strip()
    match = re.fullmatch(r"matrix\s*\(([^()]*)\)", transform)
    if not match:
        raise ValueError(f"{name}: expected an SVG matrix")
    a, b, c, d, _, _ = _numbers(match[1], 6)
    if a * d == b * c:
        raise ValueError(f"{name}: singular board transform")
    layer = ET.Element(SVG + "g", id=name, transform=sheet_matrix)
    clip = item["clip"]
    window = {}
    if clip is not None:
        x, y, w, h = clip = tuple(map(float, clip))
        if not (all(map(math.isfinite, clip)) and w > 0 and h > 0 and
                x >= 0 and y >= 0 and x + w <= PAPER[0] + 1e-8 and y + h <= PAPER[1] + 1e-8):
            raise ValueError(f"{name}: invalid paper clip {clip}")
        cid = _unique(used, name + "--window")
        defs = ET.SubElement(layer, SVG + "defs")
        cp = ET.SubElement(defs, SVG + "clipPath", id=cid, clipPathUnits="userSpaceOnUse")
        ET.SubElement(cp, SVG + "rect", dict(zip(("x", "y", "width", "height"), map(str, clip))))
        window["clip-path"] = f"url(#{cid})"
    crop = ET.SubElement(layer, SVG + "g", window)
    board = ET.SubElement(crop, SVG + "g", transform=transform,
                          style="stroke-linecap:butt;stroke-linejoin:miter")
    group = ET.fromstring(item["group"])
    count = 0
    for node in group.iter():
        tag = node.tag[len(SVG):] if node.tag.startswith(SVG) else node.tag
        if tag not in SHAPES | {"g", "title", "desc"} or (node is group and tag != "g"):
            raise ValueError(f"{name}: not a self-contained native vector group: {tag}")
        if any("url(" in v.lower() or k.endswith("href") for k, v in node.attrib.items()):
            raise ValueError(f"{name}: native copper must not depend on external definitions")
        node.tag = SVG + tag
        if "id" in node.attrib:
            node.set("id", _unique(used, name + "--" + node.get("id")))
        # MPL's universal *{stroke-linejoin:round;stroke-linecap:butt} beats
        # presentation attributes AND inheritance. Restore native SVG cascade
        # inside the group without changing the base stylesheet or any path d.
        style = "".join(f"{k}:{node.get(k, 'inherit')};" for k in ("stroke-linecap", "stroke-linejoin"))
        node.set("style", style + node.get("style", ""))
        count += tag in SHAPES
    if not count:
        raise ValueError(f"{name}: empty copper group")
    board.append(group)
    return layer, clip, count


def _unique(ids, stem):
    name = stem
    suffix = 1
    while name in ids:
        name = f"{stem}-{suffix}"
        suffix += 1
    ids.add(name)
    return name


class _Viewport(C.Structure):
    _fields_ = [(k, C.c_double) for k in ("x", "y", "width", "height")]


class _Renderer:
    """Tiny binding to the same high-level librsvg renderer as rsvg-convert."""

    def __init__(self):
        bundled = Path("/Applications/FreeCAD.app/Contents/Resources/lib/librsvg-2.dylib")
        name = str(bundled) if bundled.is_file() else ctypes.util.find_library("rsvg-2")
        if not name:
            raise RuntimeError("librsvg with Cairo PDF support not found")
        self.lib = lib = C.CDLL(name)
        ptr, dbl = C.c_void_p, C.c_double
        self.write_fn = C.CFUNCTYPE(C.c_int, ptr, ptr, C.c_uint)
        functions = {
            "rsvg_handle_new_from_data": (ptr, C.c_char_p, C.c_size_t, ptr),
            "rsvg_handle_set_dpi": (None, ptr, dbl),
            "rsvg_handle_render_document": (C.c_int, ptr, ptr, C.POINTER(_Viewport), ptr),
            "g_object_unref": (None, ptr),
            "cairo_pdf_surface_create_for_stream": (ptr, self.write_fn, ptr, dbl, dbl),
            "cairo_image_surface_create": (ptr, C.c_int, C.c_int, C.c_int),
            "cairo_image_surface_get_data": (ptr, ptr),
            "cairo_image_surface_get_stride": (C.c_int, ptr),
            "cairo_surface_flush": (None, ptr),
            "cairo_surface_finish": (None, ptr),
            "cairo_surface_status": (C.c_int, ptr),
            "cairo_surface_destroy": (None, ptr),
            "cairo_create": (ptr, ptr),
            "cairo_destroy": (None, ptr),
            "cairo_status": (C.c_int, ptr),
            "cairo_status_to_string": (C.c_char_p, C.c_int),
            "cairo_version_string": (C.c_char_p,),
        }
        for symbol, (result, *args) in functions.items():
            func = getattr(lib, symbol)
            func.argtypes = args
            func.restype = result
        version = [C.c_uint.in_dll(lib, f"rsvg_{s}_version").value for s in ("major", "minor", "micro")]
        self.info = {"librsvg": ".".join(map(str, version)), "cairo": lib.cairo_version_string().decode()}

    def render(self, svg, *, pdf):
        from PIL import Image

        lib = self.lib
        with ExitStack() as clean:
            handle = lib.rsvg_handle_new_from_data(svg, len(svg), None)
            if not handle:
                raise ValueError("librsvg could not open the overlay")
            clean.callback(lib.g_object_unref, handle)
            lib.rsvg_handle_set_dpi(handle, 72)
            if pdf:
                data = bytearray()

                @self.write_fn
                def write(_closure, start, size):
                    data.extend(C.string_at(start, size))
                    return 0  # CAIRO_STATUS_SUCCESS

                w, h = (mm * PT for mm in PAPER)
                surface = lib.cairo_pdf_surface_create_for_stream(write, None, w, h)
            else:
                w, h = (mm * PX for mm in PAPER)
                surface = lib.cairo_image_surface_create(0, w, h)  # native-endian ARGB32, premultiplied
            clean.callback(lib.cairo_surface_destroy, surface)
            cr = lib.cairo_create(surface)
            clean.callback(lib.cairo_destroy, cr)
            if not lib.rsvg_handle_render_document(handle, cr, C.byref(_Viewport(0, 0, w, h)), None):
                raise ValueError("librsvg could not render the overlay")
            if pdf:
                lib.cairo_surface_finish(surface)
            else:
                lib.cairo_surface_flush(surface)
            status = lib.cairo_status(cr) or lib.cairo_surface_status(surface)
            if status:
                raise RuntimeError(lib.cairo_status_to_string(status).decode())
            if pdf:
                return bytes(data)
            stride = lib.cairo_image_surface_get_stride(surface)
            buf = C.string_at(lib.cairo_image_surface_get_data(surface), h * stride)
            order = "BGRA" if sys.byteorder == "little" else "ARGB"
            return Image.frombytes("RGBA", (w, h), buf, "raw", order, stride)


def _dark_plane(rgba):
    # Both rasterizers deliver premultiplied RGBA; on white, darkness = A - L.
    from PIL import ImageChops

    return ImageChops.subtract(rgba.getchannel("A"), rgba.convert("RGB").convert("L"))


def _mask(dark):
    return dark.point(lambda v: 255 if v >= 12 else 0)


def _pixels(mask):
    return mask.histogram()[255]


def _pixel_box(clip, tolerance=0):
    x, y, w, h = clip
    return (math.floor((x - tolerance) * PX), math.floor((y - tolerance) * PX),
            math.ceil((x + w + tolerance) * PX), math.ceil((y + h + tolerance) * PX))


def _outside(mask, clip, tolerance=0):
    remaining = mask.copy()
    remaining.paste(0, _pixel_box(clip, tolerance))
    return _pixels(remaining)


def _vector_proof(blob, fitz):
    from PIL import Image

    with fitz.open("pdf", blob) as doc:
        page = doc[0]
        _check_a3(page.rect.width / PT, page.rect.height / PT)
        paths = len(page.get_cdrawings())
        if not paths or page.get_image_info() or page.get_images() or page.get_fonts():
            raise ValueError("expected painted PDF vectors only")
        pix = page.get_pixmap(matrix=fitz.Matrix(PX / PT, PX / PT), colorspace=fitz.csRGB, alpha=True)
        return Image.frombytes("RGBA", (pix.width, pix.height), pix.samples), paths


def _probe_layer(attrs, layer, clip, vector_count, renderer, fitz):
    from PIL import ImageChops, ImageFilter

    def serialize():
        root = ET.Element(SVG + "svg", attrs)
        root.append(layer)
        return ET.tostring(root, encoding="utf-8")

    svg = serialize()
    svg_rgba = renderer.render(svg, pdf=False)
    blob = renderer.render(svg, pdf=True)
    pdf_rgba, paths = _vector_proof(blob, fitz)
    dark = [_dark_plane(im) for im in (svg_rgba, pdf_rgba)]
    masks = [_mask(im) for im in dark]
    evidence = {"id": layer.get("id"), "svg_vector_elements": vector_count, "pdf_vector_paths": paths}
    for i, (fmt, rgba, mask) in enumerate(zip(("svg", "pdf"), (svg_rgba, pdf_rgba), masks)):
        bbox = mask.getbbox()
        alpha = rgba.getchannel("A")
        if not bbox or alpha.getextrema()[0] != 0:
            raise ValueError(f"{layer.get('id')}: missing {fmt} ink or opaque sheet background")
        # A white knockout over grid/annotation ink is not a transparent hole.
        if ImageChops.subtract(alpha.point(lambda v: v // 128), dark[i]).getbbox():
            raise ValueError(f"{layer.get('id')}: white cover in native artwork; supply transparent holes")
        # Different antialiasers can disagree on a marginal pixel. Look for
        # missing or displaced *features* beyond one pixel in either direction.
        far = ImageChops.subtract(mask, masks[1 - i].filter(ImageFilter.MaxFilter(3)))
        count = _pixels(mask)
        if _pixels(far) > max(2, 0.01 * count):
            raise ValueError(f"{layer.get('id')}: SVG / vector PDF ink mismatch")
        evidence[fmt] = {"ink_pixels": count, "ink_bbox_mm": [v / PX for v in bbox]}
    common = ImageChops.darker(*dark)
    peak = common.getextrema()[1]
    if peak < 12:
        raise ValueError("no common rendered ink witness")
    peaks = common.point(lambda v: 255 if v == peak else 0)
    y = peaks.getbbox()[1]
    x = peaks.crop((0, y, peaks.width, y + 1)).getbbox()[0]
    evidence["witness_mm"] = [(x + 0.5) / PX, (y + 0.5) / PX]
    if clip is not None:
        crop = layer.find(SVG + "g")
        ref = crop.attrib.pop("clip-path")  # actual (unclipped) native counterfactual
        try:
            uncropped = _mask(_dark_plane(renderer.render(serialize(), pdf=False)))
        finally:
            crop.set("clip-path", ref)
        pdf_mask = _mask(pdf_rgba.getchannel("A"))
        outside = [_outside(_mask(svg_rgba.getchannel("A")), clip), _outside(pdf_mask, clip, PDF_EDGE_MM)]
        if any(outside):
            raise ValueError(f"{layer.get('id')}: visible paint outside inspection clip: {outside}")
        rejected = _outside(uncropped, clip)
        if not rejected:
            # Vacuous negative control: the native drawing fits inside the ROI.
            # In a proof-only copy of this layer, challenge the SAME clip with a
            # solid sheet. Nothing from this probe goes to either deliverable.
            board = crop[0]
            crop.remove(board)
            test = ET.SubElement(crop, SVG + "rect", width=str(PAPER[0]), height=str(PAPER[1]))
            try:
                probe_svg = serialize()
                probe_pdf, _ = _vector_proof(renderer.render(probe_svg, pdf=True), fitz)
                for image, tol in ((renderer.render(probe_svg, pdf=False), 0), (probe_pdf, PDF_EDGE_MM)):
                    mask = _mask(image.getchannel("A"))
                    bounds = mask.getbbox()
                    if (not bounds or _outside(mask, clip, tol) or
                            max(abs(a - b) for a, b in zip(bounds, _pixel_box(clip))) > 1):
                        raise ValueError("inspection clip failed the independent full-sheet control")
            finally:
                crop.remove(test)
                crop.append(board)
        evidence["clip"] = {"rect_mm": clip, "svg_outside_pixels": outside[0], "pdf_outside_pixels": outside[1],
                            "unclipped_outside_ink_pixels": rejected, "pdf_edge_tolerance_mm": PDF_EDGE_MM,
                            "pdf_boundary_rounding_pixels": _outside(pdf_mask, clip) - outside[1],
                            "control": "unclipped native ink" if rejected else "solid sheet challenge"}
    return blob, evidence


def _pdf_page(doc):
    if not doc.is_pdf or doc.needs_pass or len(doc) != 1:
        raise ValueError("expected one accessible A3 PDF page")
    page = doc[0]
    if page.rotation or page.cropbox != page.mediabox or page.mediabox.top_left != (0, 0):
        raise ValueError("expected a full, unrotated Matplotlib page")
    _check_a3(page.rect.width / PT, page.rect.height / PT)
    return page


def _compose(pdf, svg, items):
    import fitz

    if not items:
        raise ValueError("no copper placements")
    if os.path.samefile(pdf, svg):
        raise ValueError("PDF and SVG must be distinct files")
    old_pdf, old_svg = pdf.read_bytes(), svg.read_bytes()
    attrs, matrix, svg_mm, used = _sheet(old_svg)
    placements = [_placement(item, matrix, used) for item in items]
    svg_bytes = _append_svg(old_svg, (p[0] for p in placements))
    # Render the exact subtrees parsed back from the *composed* SVG, not an
    # approximation, the base artwork, or fitz's clip-blind SVG importer.
    layers = list(ET.fromstring(svg_bytes))[-len(items):]
    renderer = _Renderer()
    reports = []
    with fitz.open("pdf", old_pdf) as base, ExitStack() as sources:
        pg = _pdf_page(base)
        words, fonts = pg.get_text("words"), pg.get_fonts()
        streams = {ref: base.xref_stream(ref) for ref in pg.get_contents()}
        paths, images = len(pg.get_cdrawings()), len(pg.get_image_info())
        for layer, (_, clip, count) in zip(layers, placements):
            blob, evidence = _probe_layer(attrs, layer, clip, count, renderer, fitz)
            source = sources.enter_context(fitz.open("pdf", blob))
            pg.show_pdf_page(pg.rect, source, 0, keep_proportion=False, overlay=True)
            reports.append(evidence)
        pdf_bytes = base.tobytes(deflate=True)  # keep original resource and content xrefs
    with fitz.open("pdf", pdf_bytes) as final:
        pg = _pdf_page(final)
        pdf_mm = _check_a3(pg.rect.width / PT, pg.rect.height / PT)
        refs = pg.get_contents()
        if ([r for r in refs if r in streams] != list(streams) or
                any(final.xref_stream(r) != data for r, data in streams.items()) or
                words != pg.get_text("words") or fonts != pg.get_fonts()):
            raise ValueError("base artwork, searchable text or font resources changed")
        total = len(pg.get_cdrawings())
        if total != paths + sum(r["pdf_vector_paths"] for r in reports) or len(pg.get_image_info()) != images:
            raise ValueError("merged PDF lost vectors or added images")
        for report in reports:
            x, y = report["witness_mm"]
            tile = fitz.Rect((x - .5) * PT, (y - .5) * PT, (x + .5) * PT, (y + .5) * PT)
            patch = pg.get_pixmap(matrix=fitz.Matrix(PX / PT, PX / PT), clip=tile, colorspace=fitz.csGRAY)
            if not patch.width or min(patch.samples) >= 244:
                raise ValueError(f"{report['id']}: ink witness missing on final PDF")
    result = {"pdf_page_mm": pdf_mm, "svg_page_mm": svg_mm, "page_count": 1, "px_per_mm": PX,
              "base_pdf_paths": paths, "final_pdf_paths": total, "added_images": 0,
              "base_words_preserved": len(words), "base_fonts_preserved": len(fonts),
              "renderer": {**renderer.info, "PyMuPDF": fitz.VersionBind}, "placements": reports}
    _replace_pair(pdf, svg, old_pdf, old_svg, pdf_bytes, svg_bytes)
    return result


def _replace_pair(pdf, svg, old_pdf, old_svg, new_pdf, new_svg):
    # No writing until BOTH in-memory products validate. Atomic per-file sibling
    # renames (the OS has no two-file rename); restore PDF if the second fails.
    with ExitStack() as clean:
        def stage(path, data):
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix="." + path.name + ".", delete=False) as f:
                tmp = Path(f.name)
                clean.callback(tmp.unlink, missing_ok=True)
                os.fchmod(f.fileno(), stat.S_IMODE(path.stat().st_mode))
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            return tmp

        pdf_tmp, svg_tmp, undo = stage(pdf, new_pdf), stage(svg, new_svg), stage(pdf, old_pdf)
        if pdf.read_bytes() != old_pdf or svg.read_bytes() != old_svg:
            raise RuntimeError("base changed during composition; refusing replacement")
        os.replace(pdf_tmp, pdf)
        try:
            os.replace(svg_tmp, svg)
        except BaseException:
            os.replace(undo, pdf)
            raise


def _check():
    import fitz

    renderer = _Renderer()
    attrs = {"width": "420mm", "height": "297mm", "viewBox": "0 0 420 297"}
    test = {"id": "Probe", "transform": "matrix(-1 0 0 1 40 0)", "clip": [10, 10, 10, 10],
            "group": '<g><path stroke="black" stroke-width="2" d="M10 15H26"/></g>'}
    layer, clip, count = _placement(test, "matrix(1 0 0 1 0 0)", set())
    _, report = _probe_layer(attrs, layer, clip, count, renderer, fitz)
    if not report["clip"]["unclipped_outside_ink_pixels"] or report["svg"]["ink_bbox_mm"] != [14, 14, 20, 16]:
        raise ValueError("known reflected stroke or rectangular clipping failed")
    return {**renderer.info, "PyMuPDF": fitz.VersionBind, "check": report}


def _main():
    ET.register_namespace("", SVG[1:-1])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run a vector/reflection/crop canary; no files written")
    parser.add_argument("pdf", type=Path, nargs="?")
    parser.add_argument("svg", type=Path, nargs="?")
    parser.add_argument("manifest", type=Path, nargs="?")
    args = parser.parse_args()
    if args.check:
        result = _check()
    elif args.pdf and args.svg:
        items = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else json.load(sys.stdin)
        result = _compose(args.pdf, args.svg, items)
    else:
        parser.error("supply BASE.pdf BASE.svg [placements.json], or --check")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    _main()
