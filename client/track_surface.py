"""Native spatial leaf references to track surface quads (0x42e760/0x42eed0).

This identifies surfaces; vehicle collision response is a separate subsystem.
"""
from dataclasses import dataclass
import math
from .track_mesh import decode_mesh
from .track_spatial import decode_spatial
from .track_plane import surface_height, track_plane


def surface_quad_vertex_indices(block_index, descriptor_index, descriptors, quads):
    """Resolve one surface descriptor to its four vertex indices."""
    if (type(block_index) is not int or not 0 <= block_index <= 0xffff or
            type(descriptor_index) is not int or
            not 0 <= descriptor_index <= 0xffff or
            not isinstance(descriptors, (tuple, list)) or
            not isinstance(quads, (tuple, list))):
        raise ValueError('invalid surface descriptor lookup inputs')
    if descriptor_index >= len(descriptors):
        raise ValueError('surface descriptor index is outside the block')
    descriptor = descriptors[descriptor_index]
    if not isinstance(descriptor, (tuple, list)) or len(descriptor) < 4:
        raise ValueError('surface descriptor must include its quad index')
    quad_index = descriptor[3]
    if type(quad_index) is not int or not 0 <= quad_index < len(quads):
        raise ValueError('surface quad index is outside the block')
    indices = quads[quad_index]
    if (len(indices) != 4 or any(type(index) is not int or
                                 not 0 <= index <= 0xffff for index in indices)):
        raise ValueError('surface quad must contain four uint16 vertex indices')
    return tuple(indices)


def average_surface_vertex_color(block_index, descriptor, vertex_colors, quads):
    """Average the four packed colors referenced by one surface descriptor.

    ``descriptor`` stores the quad-table index at slot 3 and ``quads`` contains
    the corresponding four vertex indices. The original emits opaque gray when
    the descriptor pointer is absent; callers represent that case with None.
    """
    if descriptor is None:
        return 0xff7f7f7f
    if (type(block_index) is not int or not 0 <= block_index <= 0xffffffff or
            not isinstance(descriptor, (tuple, list)) or len(descriptor) < 4 or
            not isinstance(vertex_colors, (tuple, list)) or
            not isinstance(quads, (tuple, list))):
        raise ValueError('invalid surface color inputs')
    quad_index = descriptor[3]
    if type(quad_index) is not int or not 0 <= quad_index < len(quads):
        raise ValueError('surface descriptor quad index is outside the table')
    indices = quads[quad_index]
    if (len(indices) != 4 or any(type(index) is not int or
                                 not 0 <= index < len(vertex_colors)
                                 for index in indices)):
        raise ValueError('surface quad must reference four supplied vertex colors')
    colors = [vertex_colors[index] for index in indices]
    if any(type(color) is not int or not 0 <= color <= 0xffffffff
           for color in colors):
        raise ValueError('vertex colors must be uint32 packed words')
    r = sum((color >> 16) & 0xff for color in colors) >> 2
    g = sum((color >> 8) & 0xff for color in colors) >> 2
    b = sum(color & 0xff for color in colors) >> 2
    return 0xff000000 | (r << 16) | (g << 8) | b


def find_surface_quad_candidate(x, z, candidates, blocks):
    """Return the first containing ``(block, descriptor)`` candidate.

    ``candidates`` is the ordered identifier list emitted by the spatial
    lookup. Each decoded block is ``(vertices, quads, descriptors)`` as
    returned by ``decode_surface``. The edge products retain the native order
    and have no tolerance or height/normal filtering.
    """
    if not math.isfinite(x) or not math.isfinite(z):
        raise ValueError('surface query coordinates must be finite')
    if not isinstance(candidates, (tuple, list)):
        raise ValueError('surface candidates must be ordered')
    if not isinstance(blocks, (tuple, list)):
        raise ValueError('surface blocks must be ordered')
    for candidate in candidates:
        if (not isinstance(candidate, (tuple, list)) or len(candidate) != 2 or
                any(type(value) is not int or not 0 <= value <= 0xffff
                    for value in candidate)):
            raise ValueError('each candidate must contain uint16 block and descriptor IDs')
        block_index, descriptor_index = candidate
        if block_index >= len(blocks):
            raise ValueError('candidate block is outside the supplied blocks')
        vertices, quads, descriptors = blocks[block_index]
        if descriptor_index >= len(descriptors):
            raise ValueError('candidate descriptor is outside its block')
        polygon_index = descriptors[descriptor_index][3] & 0xffff
        if polygon_index >= len(quads):
            raise ValueError('descriptor polygon is outside its block quad table')
        indices = quads[polygon_index]
        if len(indices) != 4 or any(index >= len(vertices) for index in indices):
            raise ValueError('surface quad must reference four supplied vertices')
        a, b, c, d = (vertices[index] for index in indices)
        if (((a[0] - b[0]) * (z - b[2]) <= (x - b[0]) * (a[2] - b[2])) and
            ((b[0] - c[0]) * (z - c[2]) <= (b[2] - c[2]) * (x - c[0])) and
            ((c[0] - d[0]) * (z - d[2]) <= (x - d[0]) * (c[2] - d[2])) and
            ((d[0] - a[0]) * (z - a[2]) <= (d[2] - a[2]) * (x - a[0]))):
            return (block_index, descriptor_index)
    return None


@dataclass(frozen=True)
class SurfaceHit:
    block: int
    descriptor: int
    vertices: tuple
    raw_descriptor: tuple

    def sample(self, x, z):
        """Return height and unit normal using native 0x42dc50/0x4b71a0."""
        if not math.isfinite(x) or not math.isfinite(z):
            raise ValueError('non-finite surface sample')
        a,b,c,d = self.vertices
        reference, normal = track_plane(x, z, (a, b, c, d))
        if not any(normal) or abs(normal[1]) <= 1e-12:
            raise ValueError('degenerate or vertical surface plane')
        height=surface_height(normal, reference, (x, 0.0, z))
        return height,normal


@dataclass(frozen=True)
class TrackSurface:
    spatial: object
    blocks: tuple

    def lookup(self, x, z, upward_only=True, reference_height=None, tolerance=0):
        """Query surfaces, optionally select the height nearest wheel contact.

        Default behavior preserves native candidate order and exact containment.
        Height selection and edge tolerance are authored compatibility behavior.
        Tolerance is a distance in track units, not an unscaled cross-product.
        """
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError('invalid surface edge tolerance')
        if reference_height is not None and not math.isfinite(reference_height):
            raise ValueError('non-finite surface reference height')
        best=None
        best_distance=math.inf
        for identifier in self.spatial.candidates(x,z):
            block, record = identifier & 0xffff, identifier >> 16
            vertices,quads,descriptors = self.blocks[block]
            descriptor = descriptors[record]
            if upward_only and descriptor[5] <= 0:
                continue
            quad = tuple(vertices[i] for i in quads[descriptor[3] & 0xffff])
            if all((a[0]-b[0])*(z-b[2]) <= (x-b[0])*(a[2]-b[2]) + tolerance*math.hypot(a[0]-b[0],a[2]-b[2])
                   for a,b in zip(quad,quad[1:]+quad[:1])):
                hit=SurfaceHit(block,record,quad,descriptor)
                if reference_height is None:
                    return hit
                try:
                    height,_=hit.sample(x,z)
                except ValueError:
                    continue
                distance=abs(height-reference_height)
                if distance < best_distance:
                    best,best_distance=hit,distance
        return best


def decode_surface(data):
    blocks=[]
    _,offset=decode_mesh(data,materials=True,surface_records=blocks)
    spatial,end=decode_spatial(data,offset)
    if end != len(data):
        raise ValueError('unexpected FRD trailing spatial data')
    def validate(node):
        if node.identifiers is not None:
            for identifier in node.identifiers:
                block,record=identifier & 0xffff,identifier >> 16
                if block >= len(blocks) or record >= len(blocks[block][2]):
                    raise ValueError('FRD spatial surface reference outside block')
        else:
            for child in node.children:
                if child is not None:
                    validate(child)
    for cell in spatial.cells:
        validate(cell)
    return TrackSurface(spatial,tuple(blocks))
