"""Offscreen orthographic rasterization of already-global FreeCAD physical leaves.

The rows of ``frame`` are screen right, screen up and direction *toward* the
viewer. No traversal of a document, placement composition or file I/O is done.
Use on the process main thread (one shared offscreen context; Cocoa requires it).
"""

import atexit
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from numbers import Real
from operator import index
import re
from threading import current_thread, main_thread

import FreeCAD  # Load the application before its Part extension.
import Part
import numpy as np
from PIL import Image
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkCleanPolyData, vtkPolyDataNormals
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkLight, vtkPolyDataMapper, vtkRenderer, vtkRenderWindow,
    vtkWindowToImageFilter,
)
from vtkmodules.vtkRenderingOpenGL2 import vtkDepthPeelingPass, vtkOpenGLFXAAPass, vtkRenderStepsPass


@dataclass(frozen=True)
class Render:
    """RGB image and (umin, vmin, umax, vmax) in world mm, at the *outer edges*.

    For a point at (u,v), PIL edge coordinates from the top left are
    x = width*(u-umin)/(umax-umin), y = height*(vmax-v)/(vmax-vmin).
    Subtract 0.5 from each if working in integer pixel-center coordinates.
    """

    image: Image.Image
    extent: tuple[float, float, float, float]


@dataclass
class _Mesh:
    xyz: np.ndarray
    triangles: np.ndarray
    normals: np.ndarray


@dataclass
class _Scene:
    layers: list[tuple[float, vtkPolyData]]  # (opacity, surface) in a common camera frame
    extent: tuple[float, float, float, float]
    depth: float
    labels: list[str]


# Cache model-space meshes, not views, colors, names or exploded placements.
# The OCC snapshot also keeps its TShape alive; a recycled address/32-bit
# hash collision cannot silently substitute another part's triangles.
_mesh_cache = OrderedDict()
_cache_bytes = 0
_MAX_BYTES = 384 * 1024**2
_MAX_LEAVES = 4096


def _polydata(xyz, triangles):
    # Give VTK ownership. In particular, vtkCellArray may shallow-copy an
    # intermediate connectivity wrapper rather than retaining its Python owner.
    points = vtkPoints()
    points.SetData(numpy_to_vtk(np.ascontiguousarray(xyz), deep=True))
    cells = vtkCellArray()
    cells.SetData(3, numpy_to_vtk(np.ascontiguousarray(triangles).ravel(), deep=True))
    data = vtkPolyData()
    data.SetPoints(points)
    data.SetPolys(cells)
    return data


def _tessellate(shape):
    vertices, facets = shape.tessellate(0.025)
    if not facets:
        return None
    raw = _polydata(np.asarray(vertices, dtype=np.float64), np.asarray(facets, dtype=np.int32))

    # Weld face-boundary/seam duplicates within this leaf only. Split the
    # normals again at actual creases: flat lands stay flat next to roundovers.
    weld = vtkCleanPolyData()
    weld.SetInputData(raw)
    weld.ToleranceIsAbsoluteOn()
    weld.SetAbsoluteTolerance(1e-7)  # mm; not a visual gap-closing tolerance
    weld.ConvertPolysToLinesOff()
    normals = vtkPolyDataNormals()
    normals.SetInputConnection(weld.GetOutputPort())
    normals.SetFeatureAngle(42.0)
    normals.SplittingOn()
    normals.ConsistencyOff()  # Use the oriented OCC triangles, including cavities.
    normals.ComputeCellNormalsOff()
    normals.ComputePointNormalsOn()
    normals.Update()
    out = normals.GetOutput()
    if not out.GetNumberOfPolys():
        return None
    return _Mesh(
        vtk_to_numpy(out.GetPoints().GetData()),
        vtk_to_numpy(out.GetPolys().GetConnectivityArray()).reshape(-1, 3).astype(np.int32, copy=False),
        vtk_to_numpy(out.GetPointData().GetNormals()),
    )


def _mesh(shape):
    global _cache_bytes
    if shape.isNull():
        return None
    key = (shape.hashCode(), shape.Orientation)
    entry = _mesh_cache.get(key)
    if entry is not None and entry[0].isEqual(shape):
        _mesh_cache.move_to_end(key)
        return entry[1]
    mesh = _tessellate(shape)
    size = 0 if mesh is None else mesh.xyz.nbytes + mesh.triangles.nbytes + mesh.normals.nbytes
    if size <= _MAX_BYTES:
        if entry is not None:
            _cache_bytes -= _mesh_cache.pop(key)[2]
        while _mesh_cache and (len(_mesh_cache) >= _MAX_LEAVES or _cache_bytes + size > _MAX_BYTES):
            _cache_bytes -= _mesh_cache.popitem(last=False)[1][2]
        _mesh_cache[key] = (Part.Shape(shape), mesh, size)
        _cache_bytes += size
    return mesh


def _rgb(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError(f'Expected #rrggbb, got {value!r}')
    return tuple(bytes.fromhex(value[1:]))


def _size(width, height):
    width, height = index(width), index(height)
    if min(width, height) < 1:
        raise ValueError('Image dimensions must be positive')
    return width, height


def _opacity(item):
    # A saved CAD property, not a name, ViewObject setting or material guess.
    percent = getattr(getattr(item, 'obj', None), 'OpticalTransparency', None)
    if isinstance(percent, Real) and not isinstance(percent, bool) and 0 <= percent <= 100:
        return (100.0 - float(percent)) / 100.0
    return 1.0


def _scene(items, frame, width, height, padding, offsets, *, id_key=None, opaque_only=False):
    """Project material batches (or flat pick IDs), fit ALL leaves, then recenter once."""
    if current_thread() is not main_thread():
        raise RuntimeError('Call the offscreen renderer on the process main thread')
    basis = np.asarray(frame, dtype=np.float64)
    if basis.shape != (3, 3) or not np.allclose(basis @ basis.T, np.eye(3), atol=1e-6, rtol=0):
        raise ValueError('frame must have orthonormal rows [right, up, unit eye]')
    if not np.isfinite(padding) or padding < 0:
        raise ValueError('padding must be finite and non-negative')
    shifts = {}
    for name, offset in (offsets or {}).items():
        delta = np.asarray(offset, dtype=np.float64)
        if delta.shape != (3,) or not np.isfinite(delta).all():
            raise ValueError(f'Expected a finite world-mm offset for {name}')
        shifts[name] = basis @ delta

    labels, groups = {}, {}
    for item in items:
        mesh = _mesh(item.shape)
        if mesh is None:
            continue  # Null/wire-only leaves have no surface to rasterize.
        if id_key is not None:
            # Sequential exact IDs; 0 is the background, not the first leaf.
            i = labels.setdefault(getattr(item, id_key), len(labels) + 1)
            if i > 0xffffff:
                raise ValueError('Too many leaves for a 24-bit ID pass')
            rgb = (i & 255, (i >> 8) & 255, i >> 16)
            # Anchors pick physical sheets; the opaque HLR prepass sees through them.
            opacity = 0.0 if opaque_only and _opacity(item) < 1.0 else 1.0
        else:
            rgb = _rgb(item.color)
            opacity = _opacity(item)
        # Each physical leaf can have its own service motion. Prefer its total
        # world translation; never add the legacy group shift on top of it.
        shift = shifts.get(item.name, shifts.get(item.root))
        groups.setdefault(opacity, []).append((mesh, shift, rgb))
    if not groups:
        return None

    batches = {alpha: _project(blocks, basis, lit=id_key is None) for alpha, blocks in groups.items()}
    low = np.min([xyz.min(axis=0) for xyz, _, _, _ in batches.values()], axis=0)
    high = np.max([xyz.max(axis=0) for xyz, _, _, _ in batches.values()], axis=0)
    center = (low + high) * 0.5
    du, dv, depth = high - low
    pitch = max(du / width, dv / height, 1e-12) * (1.0 + 2.0 * padding)
    hu, hv = 0.5 * width * pitch, 0.5 * height * pitch
    extent = (center[0] - hu, center[1] - hv, center[0] + hu, center[1] + hv)

    reflected = np.linalg.det(basis) < 0
    layers = []
    for opacity, (uvw, triangles, colors, normals) in batches.items():
        if opacity == 0.0:
            continue  # A clear leaf contributes bounds but neither color nor depth.
        uvw -= center  # Recenter in double before upload to the GPU.
        if reflected:
            triangles = triangles[:, ::-1]  # Preserve front faces in a reflected frame.
        surface = _polydata(uvw.astype(np.float32), triangles)
        surface.GetPointData().SetScalars(numpy_to_vtk(colors, deep=True))
        if normals is not None:
            surface.GetPointData().SetNormals(numpy_to_vtk(normals, deep=True))
        layers.append((opacity, surface))
    return _Scene(layers, tuple(map(float, extent)), float(depth), list(labels))


def _project(blocks, basis, *, lit):
    """Pack one draw's vertices, indices, CAD colors and optional normals."""
    nv = sum(len(m.xyz) for m, _, _ in blocks)
    nt = sum(len(m.triangles) for m, _, _ in blocks)
    uvw = np.empty((nv, 3), dtype=np.float64)
    triangles = np.empty((nt, 3), dtype=np.int32)
    colors = np.empty((nv, 3), dtype=np.uint8)
    normals = np.empty((nv, 3), dtype=np.float32) if lit else None
    rotation = basis.T.astype(np.float32)
    v0 = t0 = 0
    for mesh, shift, rgb in blocks:
        v1, t1 = v0 + len(mesh.xyz), t0 + len(mesh.triangles)
        uvw[v0:v1] = mesh.xyz @ basis.T
        if shift is not None:
            uvw[v0:v1] += shift
        triangles[t0:t1] = mesh.triangles + v0
        colors[v0:v1] = rgb
        if normals is not None:
            normals[v0:v1] = mesh.normals @ rotation
        v0, t0 = v1, t1

    return uvw, triangles, colors, normals


def _studio_lights(renderer):
    # Neutral, broad key/fill and a grazing light. No ground plane, black
    # outlines or material guesses based on a label or a group's identity.
    for direction, intensity in (
        ((-0.95, 0.58, 1.15), 0.94),
        ((0.96, -0.10, 0.75), 0.31),
        ((0.15, 0.96, -0.40), 0.32),
    ):
        light = vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*direction)
        light.SetFocalPoint(0, 0, 0)
        light.SetPositional(False)
        light.SetIntensity(intensity)
        renderer.AddLight(light)


@lru_cache(maxsize=1)
def _window():
    # Recreating Cocoa GL contexts per view leaks driver resources in long
    # publisher runs. Keep one offscreen context, never a previous scene.
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetMultiSamples(0)
    window.SetUseSRGBColorSpace(False)
    atexit.register(window.Finalize)
    return window


def _actor(surface, opacity, *, ids):
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(surface)
    mapper.SetScalarModeToUsePointData()
    mapper.SetColorModeToDirectScalars()
    mapper.InterpolateScalarsBeforeMappingOff()
    actor = vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.EdgeVisibilityOff()
    if ids:
        prop.LightingOff()
        prop.SetInterpolationToFlat()
    else:
        prop.SetInterpolationToPhong()
        prop.SetAmbient(0.37)
        prop.SetDiffuse(0.69)
        prop.SetSpecular(0.16)
        prop.SetSpecularPower(11.0)
        if opacity < 1.0:
            prop.SetOpacity(opacity)
            # Closed thin glazing: apply the sheet tint once, not again at the exit face.
            prop.BackfaceCullingOn()
    return actor


def _optical_pass(fxaa):
    # Use classic per-pixel peeling after the opaque pass. The bundled Cocoa
    # backend's automatic dual-peeling path can blend in actor insertion order.
    steps = vtkRenderStepsPass()
    peel = vtkDepthPeelingPass()
    peel.SetTranslucentPass(steps.GetTranslucentPass())
    peel.SetMaximumNumberOfPeels(0)  # until no translucent fragments remain
    peel.SetOcclusionRatio(0.0)
    steps.SetTranslucentPass(peel)
    if fxaa:
        aa = vtkOpenGLFXAAPass()
        aa.SetDelegatePass(steps)
        return aa
    return steps


def _capture(scene, width, height, background, *, ids, fxaa=False):
    renderer = vtkRenderer()
    renderer.AutomaticLightCreationOff()
    renderer.SetBackground(*(c / 255.0 for c in background))
    renderer.SetUseFXAA(fxaa)
    for opacity, surface in scene.layers:
        renderer.AddActor(_actor(surface, opacity, ids=ids))
    if not ids:
        _studio_lights(renderer)
    if any(opacity < 1.0 for opacity, _ in scene.layers):
        renderer.SetPass(_optical_pass(fxaa))

    camera = renderer.GetActiveCamera()
    camera.ParallelProjectionOn()
    umin, vmin, umax, vmax = scene.extent
    # Size is set only by ParallelScale. Put the eye well back so that even
    # VTK's view-dependent specular term is nearly parallel over a thin PCB.
    distance = max(1.0, scene.depth, 8 * max(umax - umin, vmax - vmin))
    camera.SetPosition(0, 0, distance)
    camera.SetFocalPoint(0, 0, 0)
    camera.SetViewUp(0, 1, 0)
    camera.SetParallelScale((vmax - vmin) * 0.5)
    # Tight, but don't put the silkscreen or the front skin on a clip plane.
    dz = scene.depth * 0.5 + max(0.0001, scene.depth * 0.001, distance * 1e-6)
    camera.SetClippingRange(distance - dz, distance + dz)

    window = _window()
    window.SetSize(width, height)
    window.AddRenderer(renderer)
    try:
        window.Render()
        read = vtkWindowToImageFilter()
        read.SetInput(window)
        read.SetInputBufferTypeToRGB()
        read.ReadFrontBufferOff()
        read.ShouldRerenderOff()
        read.Update()
        image = read.GetOutput()
        if image.GetDimensions()[:2] != (width, height):
            raise RuntimeError(f'Unexpected VTK framebuffer size {image.GetDimensions()}')
        pixels = vtk_to_numpy(image.GetPointData().GetScalars()).reshape(height, width, 3)
        return pixels[::-1].copy()  # GL bottom-left -> PIL top-left; own the bytes.
    finally:
        window.RemoveRenderer(renderer)


def render(
    items, frame, *, width=1600, height=1200, offsets=None, bgcolor='#f5f5f2', padding=0.06,
) -> Render:
    """Fit to the requested aspect, adding ``padding`` per side on the limiting axis.

    ``item.obj.OpticalTransparency`` is the percentage of backing color seen
    through a sheet (0..100). Other leaves are opaque; even clear leaves retain
    their fitted bounds. Offsets translate native leaf names (or legacy roots) in
    global mm. Empty/all-wire scenes have no surface extent and raise ValueError.
    """
    width, height = _size(width, height)
    background = _rgb(bgcolor)
    scene = _scene(items, frame, width, height, padding, offsets)
    if scene is None:
        raise ValueError('No surface triangles to render')
    # Predictable supersampling even in a single-sample Cocoa offscreen FBO.
    # For large print rasters avoid allocating a gigantic 4x-area framebuffer.
    scale = 2 if width * height <= 5_000_000 and max(width, height) <= 4096 else 1
    pixels = _capture(scene, width * scale, height * scale, background, ids=False, fxaa=scale == 1)
    image = Image.fromarray(pixels)
    if scale != 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return Render(image, scene.extent)


def _id_view(items, frame, width, offsets, key, *, opaque_only=False):
    width, height = _size(width, width)
    scene = _scene(items, frame, width, height, 0.06, offsets, id_key=key, opaque_only=opaque_only)
    if scene is None:
        return None
    pixels = _capture(scene, width, height, (0, 0, 0), ids=True)
    codes = pixels[:, :, 0].astype(np.int32)
    codes |= pixels[:, :, 1].astype(np.int32) << 8
    codes |= pixels[:, :, 2].astype(np.int32) << 16
    if codes.max() > len(scene.labels):
        raise RuntimeError('Unexpected color in flat ID buffer')
    return codes, scene.labels, scene.extent


def visible_names(items, frame, width=950) -> set[str]:
    """Opaque leaves owning >=1 depth-tested pixel in a square width-by-width view.

    Optical sheets are not opaque HLR blockers. They still contribute to the fit.
    This is sampled, not analytic HLR: raise width for tiny or grazing features.
    Exactly coincident faces have no unique depth winner.
    """
    view = _id_view(items, frame, width, None, 'name', opaque_only=True)
    if view is None:
        return set()
    codes, names, _ = view
    return {names[int(i) - 1] for i in np.unique(codes) if i}


def root_anchors(
    items, frame, *, offsets=None, width=900, name_mode=False,
) -> dict[str, tuple[float, float]]:
    """A visible pixel center (u,v) in world mm per root, or per internal name.

    Uses the deepest interior of each first-hit mask, not the center of a 3-D
    box (which could lie in a hole or under another part). This picks the physical
    surface of optical sheets, not an opaque obstruction. Hidden keys omitted.
    Use the same leaves, frame and offsets as the target render; its aspect
    ratio can differ. ``name_mode=True`` keeps leaves of a root separate.
    """
    from scipy.ndimage import distance_transform_edt, find_objects

    view = _id_view(items, frame, width, offsets, 'name' if name_mode else 'root')
    if view is None:
        return {}
    codes, labels, (umin, vmin, umax, vmax) = view
    height, width = codes.shape
    anchors = {}
    # Crop each distance transform to its own label's box, especially useful
    # for hundreds of tiny SMD/silkscreen leaves. Pad with real exterior.
    for i, box in enumerate(find_objects(codes, max_label=len(labels)), start=1):
        if box is None:
            continue
        mask = codes[box] == i
        distance = distance_transform_edt(np.pad(mask, 1))[1:-1, 1:-1]
        yy, xx = np.nonzero(distance == distance.max())
        # Long lands can have an entire ridge of maxima. Prefer a central one
        # without averaging two pixels and landing outside a concave mask.
        j = np.argmin((yy - yy.mean()) ** 2 + (xx - xx.mean()) ** 2)
        y, x = box[0].start + yy[j], box[1].start + xx[j]
        u = umin + (x + 0.5) * (umax - umin) / width
        v = vmax - (y + 0.5) * (vmax - vmin) / height
        anchors[labels[i - 1]] = (float(u), float(v))
    return anchors
