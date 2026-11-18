"""Tessellate a *placed* FreeCAD B-rep, preserving OCCT face normals and winding."""

import numpy as np
import FreeCAD  # Load the same OCCT runtime as the saved document before Part.
import Part
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepLib import BRepLib_ToolTriangulatedShape
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepTools import breptools
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import topods


MM_TO_M = 0.001
ANGULAR_DEFLECTION = 0.52  # radians; OCCT also enforces the absolute chord error below


def gltf_axes(xyz):
    """Rotation only: CAD right/in/up -> glTF right/up/back. Determinant +1."""
    return np.asarray(xyz)[..., [0, 2, 1]] * [1, 1, -1]


def gltf_metres(xyz_mm):
    return gltf_axes(xyz_mm) * MM_TO_M


def _face_mesh(face):
    location = TopLoc_Location()
    tri = BRep_Tool.Triangulation(face, location)
    if tri is None or not tri.NbTriangles():
        raise ValueError('OCCT did not triangulate a B-rep face')
    # OCCT evaluates normals on the underlying surface at mesh UVs. Caps and
    # sidewalls have separate vertex streams; cylinders stay smooth across 2π.
    BRepLib_ToolTriangulatedShape.ComputeNormals(face, tri)
    count = tri.NbNodes()
    p = np.array([tri.Node(i).Coord() for i in range(1, count + 1)])
    n = np.array([tri.Normal(i).Coord() for i in range(1, count + 1)])
    indices = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)],
                       dtype=np.int32) - 1  # OCCT counts from 1, glTF from 0

    # This is the triangulation's own location inside Item.shape, not the
    # document object's Placement (Scene has already applied its ancestors).
    mirrored = False
    if not location.IsIdentity():
        transform = location.Transformation()
        m = np.array([[transform.Value(i, j) for j in range(1, 5)] for i in range(1, 4)])
        mirrored = np.linalg.det(m[:, :3]) < 0
        p = p @ m[:, :3].T + m[:, 3]
        n = n @ m[:, :3].T  # TopLoc transformations are similarities; normalize below.
    reverse = face.Orientation() == TopAbs_REVERSED
    if reverse:
        n = -n
    if reverse != mirrored:
        indices = indices[:, [0, 2, 1]]
    return p, n, indices


def tessellate(item):
    """One indexed TRIANGLES primitive per registered leaf; no LOD/no face deletion."""
    # Absolute 8–50 µm chord error, scaled to the size of the feature, not
    # the enclosure. The angular cap also applies to round holes in thin masks.
    chord_mm = float(np.clip(np.max(item.box[1] - item.box[0]) * 0.003, 0.008, 0.05))
    shape = Part.__toPythonOCC__(item.shape)
    breptools.Clean(shape)  # ignore cached display triangulations on Scene's shape copy
    mesher = BRepMesh_IncrementalMesh(shape, chord_mm, False, ANGULAR_DEFLECTION, False)
    if not mesher.IsDone():
        raise ValueError(f'{item.name}: OCCT meshing failed')

    positions, normals, indices = [], [], []
    offset = 0
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    while faces.More():
        p, n, ix = _face_mesh(topods.Face(faces.Current()))
        positions.append(p)
        normals.append(n)
        indices.append(ix + offset)
        offset += len(p)
        faces.Next()
    if not indices:
        raise ValueError(f'{item.name}: no physical surface')
    p = gltf_metres(np.concatenate(positions)).astype('<f4')
    n = gltf_axes(np.concatenate(normals))
    ix = np.concatenate(indices)
    lengths = np.linalg.norm(n, axis=1)
    if not (np.isfinite(p).all() and np.isfinite(lengths).all() and (lengths > 0).all()):
        raise ValueError(f'{item.name}: invalid position or normal')
    n = (n / lengths[:, None]).astype('<f4')

    # A seam/pole may collapse to one float32 point. Discard only triangles
    # with exactly zero area in the delivered precision; never decimate solids.
    a, b, c = p[ix].astype(np.float64).transpose(1, 0, 2)
    cross = np.cross(b - a, c - a)
    keep = np.any(cross != 0, axis=1)
    if not keep.all():
        ix, cross = ix[keep], cross[keep]
        if not len(ix):
            raise ValueError(f'{item.name}: only zero-area triangles')

    # At a tight loft fold an analytic tangent can face behind the *chord*.
    # Never flip an isolated triangle: adjacent triangles must retain opposite
    # edge traversal even at such a fold. Split just the offending shading
    # corners and use the oriented facet normal there. No positions are moved.
    rows, corners = np.nonzero(np.einsum('ij,ikj->ik', cross, n[ix]) <= 0)
    if len(rows):
        facet_n = cross[rows] / np.linalg.norm(cross[rows], axis=1)[:, None]
        first = len(p)
        p = np.concatenate((p, p[ix[rows, corners]]))
        n = np.concatenate((n, facet_n.astype('<f4')))
        ix[rows, corners] = first + np.arange(len(rows))
    if len(rows) or not keep.all():
        used, idx = np.unique(ix, return_inverse=True)
        p, n, ix = p[used], n[used], idx.reshape(-1, 3)
    # 65535 is reserved in glTF even for TRIANGLES (primitive restart).
    ix = ix.astype('<u2' if len(p) <= 65535 else '<u4')
    return p, n, ix
