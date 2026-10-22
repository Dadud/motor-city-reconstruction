"""Build runtime collision bounds for decoded track scenery objects."""
from dataclasses import dataclass
import struct

from client.collision_pair_candidate import (DynamicCandidateTable,
                                             build_dynamic_candidate_table)
from client.track_mesh import TrackObjectGroup


@dataclass(frozen=True)
class TrackObjectBounds:
    """The 0x427f50 table and mutated runtime rows for one FRD object group."""

    candidates: DynamicCandidateTable
    source_rows: bytes
    vertex_arrays: tuple[tuple[int, bytes], ...]


def build_track_object_bounds(group: TrackObjectGroup, *, source_address,
                              table_address, payload_address):
    """Translate decoded FRD objects into runtime rows and their bounds.

    The loader's 0x428680 layout gives each runtime row the same 0x38-byte
    footprint as the 56-byte on-disk descriptor. Vertex arrays contain packed
    XYZ triples followed by separate four-byte attributes in memory; only the
    triples are consumed by the 0x427f50 bounds producer.
    """
    for label, value in (('source', source_address), ('table', table_address),
                         ('payload', payload_address)):
        if type(value) is not int or not 0 < value <= 0xffffffff:
            raise ValueError(f'{label} address must be a non-null uint32')
    rows = bytearray()
    arrays = []
    cursor = payload_address
    for obj in group.objects:
        if len(obj.descriptor) != 0x38:
            raise ValueError('track object descriptor must be 0x38 bytes')
        row = bytearray(obj.descriptor)
        count, = struct.unpack_from('<I', row, 0x24)
        if count != len(obj.vertex_records):
            raise ValueError('descriptor vertex count disagrees with decoded payload')
        animation_size, = struct.unpack_from('<I', row, 0x1c)
        face_count, = struct.unpack_from('<I', row, 0x30)
        if animation_size != len(obj.animation):
            raise ValueError('descriptor animation size disagrees with decoded payload')
        if face_count != len(obj.faces):
            raise ValueError('descriptor face count disagrees with decoded payload')
        if animation_size:
            struct.pack_into('<I', row, 0x20, cursor)
            cursor += animation_size
        else:
            struct.pack_into('<I', row, 0x20, 0)
        points = b''.join(obj.vertex_records)
        if count and len(points) != count * 12:
            raise ValueError('decoded object vertex records are malformed')
        struct.pack_into('<I', row, 0x28, cursor)
        arrays.append((cursor, points))
        cursor += count * 12
        struct.pack_into('<I', row, 0x2c, cursor)
        cursor += count * 4
        struct.pack_into('<I', row, 0x34, cursor)
        cursor += face_count * 30
        if face_count & 1:
            cursor += 2
        if cursor > 0xffffffff:
            raise ValueError('track object vertex layout overflows uint32')
        rows.extend(row)
    vertices = dict(arrays)
    source_rows = bytes(rows)
    candidates = build_dynamic_candidate_table(
        source_rows, vertices, source_address=source_address,
        table_address=table_address)
    return TrackObjectBounds(candidates, source_rows, tuple(arrays))
