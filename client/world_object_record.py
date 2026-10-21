"""Byte-image adapters for the original 0x4f8-byte world-object array."""
import struct

from .world_object_array import WORLD_OBJECT_STRIDE
from .world_object_update import WorldObjectUpdate, update_world_object
from .world_object_damping import WorldObjectMotion
from .world_object_maintenance import (WorldObjectMaintenance,
                                       maintain_world_object)


RECORD_SIZE = WORLD_OBJECT_STRIDE


def update_object_record(record, *, object_phase):
    """Run the recovered 0x520250 update directly on one native-layout image.

    The executable callback receives an owner pointer and writes the owner's
    position, rotation, transpose, projections and transformed 22-point array.
    This adapter connects that callback to the full record instead of requiring
    callers to manufacture a detached ``WorldObjectUpdate`` value.
    """
    if not isinstance(record, bytearray) or len(record) < RECORD_SIZE:
        raise ValueError('mutable 0x4f8-byte world-object image required')
    if record[4] == 0:
        return record

    def vector(offset, count):
        return struct.unpack_from(f'<{count}f', record, offset)

    state = WorldObjectUpdate(
        object_id=struct.unpack_from('<I', record, 0)[0],
        active=True,
        position=vector(0x08, 3),
        linear_velocity=vector(0x14, 3),
        center_of_mass=vector(0x5c, 3),
        rotation=vector(0x78, 9),
        angular_velocity=vector(0x38, 3),
        projection_vectors=vector(0x328, 3),
        local_vertices=vector(0xe0, 66),
        world_vertices=vector(0x1e8, 66),
    )
    updated, _ = update_world_object(state, object_phase=object_phase)
    struct.pack_into('<3f', record, 0x08, *updated.position)
    struct.pack_into('<9f', record, 0x78, *updated.rotation)
    struct.pack_into('<9f', record, 0x9c, *updated.transposed_rotation)
    struct.pack_into('<3f', record, 0xc0, *updated.projected)
    struct.pack_into('<66f', record, 0x1e8, *updated.world_vertices)
    return record


def update_object_array(records, *, object_phase):
    """Apply 0x520250 to active array entries in original storage order."""
    if not isinstance(records, bytearray) or len(records) % RECORD_SIZE:
        raise ValueError('world-object array must be a whole number of 0x4f8-byte rows')
    for offset in range(0, len(records), RECORD_SIZE):
        row = bytearray(records[offset:offset + RECORD_SIZE])
        update_object_record(row, object_phase=object_phase)
        records[offset:offset + RECORD_SIZE] = row
    return records


def maintain_object_record(record, *, update_physics):
    """Run the recovered 0x4265f0 post-physics maintenance on one owner image.

    ``update_physics`` is the required 0x520c20 child boundary and receives the
    same mutable byte image. It must implement the selected runtime's real
    environment and contact stages; this adapter only owns the parent's
    active-row gate and post-child velocity fields.
    """
    if not isinstance(record, bytearray) or len(record) < RECORD_SIZE:
        raise ValueError('mutable 0x4f8-byte world-object image required')
    if not callable(update_physics):
        raise ValueError('the 0x520c20 physics callback is required')
    if record[4] == 0:
        return record

    update_physics(record)
    motion = WorldObjectMotion(
        struct.unpack_from('<h', record, 0x3bc)[0],
        struct.unpack_from('<3f', record, 0x14),
        struct.unpack_from('<3f', record, 0x38),
    )
    state = WorldObjectMaintenance(
        motion, True,
        struct.unpack_from('<f', record, 0x350)[0],
        struct.unpack_from('<f', record, 0xd8)[0],
    )
    result = maintain_world_object(state, lambda _motion: motion)
    struct.pack_into('<3f', record, 0x14, *result.motion.linear_velocity)
    struct.pack_into('<3f', record, 0x38, *result.motion.angular_velocity)
    return record


def maintain_object_array(records, *, update_physics):
    """Apply 0x4265f0 to active records in array order in place."""
    if not isinstance(records, bytearray) or len(records) % RECORD_SIZE:
        raise ValueError('world-object array must be a whole number of 0x4f8-byte rows')
    for offset in range(0, len(records), RECORD_SIZE):
        row = bytearray(records[offset:offset + RECORD_SIZE])
        maintain_object_record(row, update_physics=update_physics)
        records[offset:offset + RECORD_SIZE] = row
    return records
