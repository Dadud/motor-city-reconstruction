"""Portable scene-node and face traversal for the startup raster producer."""
from dataclasses import dataclass
import math

from .fce import Model as FceModel
from .raster_fill import RASTER_HEIGHT, RASTER_WIDTH, rasterize_projected_triangle
from .render_list import RenderList
from .tire_response import f32

_MIRROR_X_TYPES = frozenset((5, 6, 9, 10, 13))


@dataclass(frozen=True)
class RasterMesh:
    """One already selected surface from an original scene-list node."""

    vertices: tuple[tuple[float, float, float], ...]
    triangles: tuple[tuple[int, int, int], ...]
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    mesh_type: int = 0
    has_model: bool = True
    surface_id: int = 0
    vertex_base: int = 0
    face_base: int = 0


@dataclass(frozen=True)
class RasterSceneNode:
    """Decoded form of a linked render node used by 0x483450."""

    model: FceModel | None
    surface_id: int
    mesh_type: int
    vertex_base: int = 0
    face_base: int = 0


def raster_nodes_from_render_list(models, render_list):
    """Adapt recovered render-list model/surface/type words into area nodes.

    Portable render records store a model index in word 1, surface index in
    word 3 and native mesh-type selector in word 5. The original stores a
    model pointer in word 1; ``models`` is the caller-owned pointer table
    equivalent. Ordering and selected list head remain caller inputs.
    """
    models = tuple(models)
    if not isinstance(render_list, RenderList):
        raise TypeError('render list must be a recovered RenderList')
    nodes = []
    for index, record in enumerate(render_list.records):
        model_index, surface_id, mesh_type = (
            record.words[1], record.words[3], record.words[5])
        if model_index >= len(models):
            raise ValueError(f'render record {index} references an unknown model')
        model = models[model_index]
        if model is not None and not isinstance(model, FceModel):
            raise TypeError(f'render record {index} model is not a decoded FCE')
        if model is not None and mesh_type < 16 and not 0 <= surface_id < len(model.parts):
            raise ValueError(f'render record {index} surface is outside its model')
        nodes.append(RasterSceneNode(model, surface_id, mesh_type))
    return tuple(nodes)


def raster_meshes_from_nodes(nodes):
    """Adapt linked scene nodes and decoded FCEs to the portable raster path.

    The original node's model pointer is at +4, signed surface id at +0xc and
    mesh type at +0x14. Each selected FCE part supplies its origin, vertices
    and triangles. A null model and types >=16 are retained as skipped nodes.
    """
    meshes = []
    for node in nodes:
        if not isinstance(node.mesh_type, int):
            raise TypeError('mesh type must be an integer')
        if node.model is None or node.mesh_type >= 16:
            meshes.append(RasterMesh((), (), mesh_type=node.mesh_type,
                                     has_model=node.model is not None,
                                     surface_id=node.surface_id))
            continue
        if not isinstance(node.model, FceModel):
            raise TypeError('scene node model must be a decoded FCE model')
        if type(node.surface_id) is not int or not 0 <= node.surface_id < len(node.model.parts):
            raise ValueError('scene surface ID outside decoded FCE parts')
        part = node.model.parts[node.surface_id]
        meshes.append(RasterMesh(
            vertices=part.vertices,
            triangles=tuple(face.indices for face in part.triangles),
            position=part.origin,
            mesh_type=node.mesh_type,
            surface_id=node.surface_id))
    return tuple(meshes)


def _transformed_triangles(meshes):
    for mesh in meshes:
        if not isinstance(mesh.mesh_type, int):
            raise TypeError('mesh type must be an integer')
        if (not isinstance(mesh.surface_id, int) or mesh.surface_id < 0 or
                mesh.surface_id > 0x7fff):
            raise ValueError('surface ID must be a nonnegative int16 value')
        if (type(mesh.vertex_base) is not int or mesh.vertex_base < 0 or
                type(mesh.face_base) is not int or mesh.face_base < 0):
            raise ValueError('surface buffer bases must be nonnegative integers')
        if not mesh.has_model or mesh.mesh_type >= 16:
            continue
        if len(mesh.position) != 3 or any(not math.isfinite(f32(v)) for v in mesh.position):
            raise ValueError('mesh position must contain three finite values')
        position = tuple(f32(v) for v in mesh.position)
        vertices = tuple(tuple(f32(v) for v in vertex) for vertex in mesh.vertices)
        if any(len(vertex) != 3 for vertex in vertices):
            raise ValueError('mesh vertices must be three-dimensional')
        if any(not math.isfinite(v) for vertex in vertices for v in vertex):
            raise ValueError('mesh vertices must be finite')
        mirror_x = mesh.mesh_type in _MIRROR_X_TYPES
        for face in mesh.triangles:
            if len(face) != 3 or any(type(index) is not int or
                                     index < 0 or mesh.vertex_base + index >= len(vertices)
                                     for index in face):
                raise ValueError('face indices must select three existing vertices')
            transformed = []
            for index in face:
                x, y, _ = vertices[mesh.vertex_base + index]
                if mirror_x:
                    x = f32(x * -1.0)
                transformed.append((f32(position[0] + x), f32(position[1] + y)))
            yield tuple(transformed)


def rasterize_scene_geometry(meshes, x_bounds, y_bounds):
    """Rasterize eligible decoded surface records into an occupancy mask."""
    if len(x_bounds) != 2 or len(y_bounds) != 2:
        raise ValueError('each raster bound must contain a minimum and maximum')
    xmin, xmax = (f32(value) for value in x_bounds)
    ymin, ymax = (f32(value) for value in y_bounds)
    if not all(math.isfinite(v) for v in (xmin, xmax, ymin, ymax)):
        raise ValueError('finite float32 bounds required')
    if xmin == xmax or ymin == ymax:
        raise ValueError('projection bounds must have nonzero extents')
    bitmap = bytearray(RASTER_WIDTH * RASTER_HEIGHT)
    for triangle in _transformed_triangles(meshes):
        face_mask = rasterize_projected_triangle(
            triangle, (xmin, xmax), (ymin, ymax))
        for pixel, occupied in enumerate(face_mask):
            if occupied:
                bitmap[pixel] = 1
    return bytes(bitmap)
