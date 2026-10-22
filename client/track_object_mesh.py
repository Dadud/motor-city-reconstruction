"""Decode attached track-object quads into the shared local mesh model."""
import math
import struct

from client.fce import Model, Part, Triangle
from client.collision_palette import adjust_color_words
from client.track_mesh import TrackObjectGroup


def decode_track_object_group(group: TrackObjectGroup, uv_coordinates, *,
                              color_percentages=(100, 100, 100)):
    """Build one local-space mesh model from an FRD object group.

    Object transforms and animation are retained on the source records and are
    not applied here. Face records use the same 15-word quad/UV/page/flags
    layout as the track-block faces.
    """
    uv_coordinates = tuple(uv_coordinates)
    parts = []
    for object_index, obj in enumerate(group.objects):
        kind = obj.descriptor[2] & 0xf
        vertices = tuple(struct.unpack('<3f', record)
                         for record in obj.vertex_records)
        if any(not math.isfinite(value) for vertex in vertices for value in vertex):
            raise ValueError('track object has a non-finite vertex position')
        triangles = []
        normal_sums = [[0.0, 0.0, 0.0] for _ in vertices]
        for record in obj.faces:
            if len(record) != 15:
                raise ValueError('track object face record must contain 15 words')
            corners = record[:4]
            if any(index >= len(vertices) for index in corners):
                raise ValueError('track object face index outside vertex array')
            uv_indices = record[4:12]
            if any(index >= len(uv_coordinates) for index in uv_indices):
                raise ValueError('track object UV index outside shared UV table')
            for triangle_corners in ((0, 1, 2), (0, 2, 3)):
                indices = tuple(corners[index] for index in triangle_corners)
                if len(set(indices)) < 3:
                    continue
                a, b, c = (vertices[index] for index in indices)
                ab = tuple(b[axis] - a[axis] for axis in range(3))
                ac = tuple(c[axis] - a[axis] for axis in range(3))
                normal = (ab[1] * ac[2] - ab[2] * ac[1],
                          ab[2] * ac[0] - ab[0] * ac[2],
                          ab[0] * ac[1] - ab[1] * ac[0])
                for index in indices:
                    for axis in range(3):
                        normal_sums[index][axis] += normal[axis]
                uv_corners = tuple((1, 0, 3, 2)[index]
                                   for index in triangle_corners)
                uv = tuple(uv_coordinates[uv_indices[2 * corner]]
                           for corner in uv_corners) + tuple(
                           uv_coordinates[uv_indices[2 * corner + 1]]
                           for corner in uv_corners)
                triangles.append(Triangle(indices, uv, record[13], record[14]))
        normals = tuple(tuple(value for value in normal) for normal in normal_sums)
        if len(obj.vertex_attributes) != len(vertices):
            raise ValueError('track object color count disagrees with vertex array')
        colors = bytearray(b''.join(obj.vertex_attributes))
        adjust_color_words(colors, len(vertices), color_percentages)
        vertex_colors = struct.unpack('<' + 'I' * len(vertices), colors)
        origin = (struct.unpack_from('<3f', obj.descriptor, 0x10)
                  if kind in (2, 4) else (0.0, 0.0, 0.0))
        name = (f'Track object {group.block_index}:'
                f'{group.section_offset:#x}:{object_index}')
        parts.append(Part(name, origin, vertices,
                          normals, tuple(triangles), vertex_colors,
                          obj.descriptor[2] & 0xf0))
    return Model(tuple(parts), 0)
