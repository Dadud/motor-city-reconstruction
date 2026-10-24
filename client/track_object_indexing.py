"""Initial track-row assignment for world objects in native 0x42d5b0."""
import struct

from .track_object_animation import evaluate_track_object_animation
from .track_surface_query import nearest_track_initialization_point


OBJECT_SIZE = 0x78
TRACK_ROW_SIZE = 0x54


def assign_track_object_indices(objects, track_rows, animations):
    """Initialize object poses and assign nearest quarter-stride track rows.

    Animation pointers in object records resolve through the supplied mapping
    to bounded animation byte views. Animations use the native mode-1 pose at
    time zero. The track table and object array are explicit ordered views.
    """
    if not isinstance(objects, (tuple, list)):
        raise ValueError('objects must be an ordered sequence')
    if not isinstance(track_rows, (tuple, list)) or not track_rows:
        raise ValueError('track rows must be a nonempty ordered sequence')
    if any(not isinstance(row, (bytes, bytearray)) or len(row) != TRACK_ROW_SIZE
           for row in track_rows):
        raise ValueError('each track row must contain 0x54 bytes')
    if not isinstance(animations, dict):
        raise ValueError('animations must map native pointers to animation byte views')
    result = []
    for object_index, image in enumerate(objects):
        if not isinstance(image, (bytes, bytearray)) or len(image) != OBJECT_SIZE:
            raise ValueError('each object must contain 0x78 bytes')
        record = bytearray(image)
        animation_pointer = struct.unpack_from('<I', record, 0x74)[0]
        if animation_pointer:
            try:
                animation = animations[animation_pointer]
            except KeyError as error:
                raise ValueError(
                    f'missing animation data for pointer {animation_pointer:#x}') from error
            pose = evaluate_track_object_animation(animation, 0, mode=1)
            struct.pack_into('<3f', record, 0, *pose.translation)
            struct.pack_into('<9f', record, 0x0C, *pose.rotation)
        struct.pack_into('<3f', record, 0x58, 0.0, 0.0, 0.0)
        position = struct.unpack_from('<3f', record, 0)
        selected = nearest_track_initialization_point(position, track_rows)
        struct.pack_into('<ii', record, 0x34, selected, selected >> 3)
        result.append(bytes(record))
    return tuple(result)
