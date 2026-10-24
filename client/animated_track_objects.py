"""State updates performed by native routine 0x42d780."""
import math
import struct

from .track_object_animation import evaluate_track_object_animation


RECORD_SIZE = 0x78
ANIMATION_POINTER = 0x74
DELTA_OFFSET = 0x58


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', float(value)))[0]


def update_animated_track_objects(records, delta_scale, transform_position):
    """Transform animated records and store scaled XYZ position deltas.

    ``transform_position(index, record)`` supplies the output position of the
    called native transform helper. Nonanimated records remain byte-identical.
    The helper's broader animation behavior is intentionally outside this
    routine's contract.
    """
    if not isinstance(records, (tuple, list)):
        raise ValueError('records must be an ordered sequence')
    if not callable(transform_position):
        raise ValueError('a transform-position callback is required')
    scale = _f32(delta_scale)
    if not math.isfinite(scale):
        raise ValueError('delta scale must be finite')
    result = []
    for index, image in enumerate(records):
        if not isinstance(image, (bytes, bytearray)) or len(image) != RECORD_SIZE:
            raise ValueError('each object must be a 0x78-byte record')
        record = bytearray(image)
        animation = struct.unpack_from('<I', record, ANIMATION_POINTER)[0]
        if animation:
            before = struct.unpack_from('<3f', record, 0)
            transformed = transform_position(index, bytes(record))
            matrix = None
            if (isinstance(transformed, (tuple, list)) and len(transformed) == 2
                    and isinstance(transformed[0], (tuple, list))):
                after, matrix = transformed
                if not isinstance(matrix, (tuple, list)) or len(matrix) != 9:
                    raise ValueError('transform callback matrix must contain nine values')
                matrix = tuple(_f32(value) for value in matrix)
                struct.pack_into('<9f', record, 0x0C, *matrix)
            else:
                after = transformed
            if not isinstance(after, (tuple, list)) or len(after) != 3:
                raise ValueError('transform callback must return XYZ or (XYZ, matrix)')
            after = tuple(_f32(value) for value in after)
            struct.pack_into('<3f', record, 0, *after)
            # The original computes with x87 extended precision and rounds on
            # each final store; Python binary64 retains the exact float inputs.
            delta = tuple(_f32((new - old) * scale)
                          for old, new in zip(before, after))
            struct.pack_into('<3f', record, DELTA_OFFSET, *delta)
        result.append(bytes(record))
    return tuple(result)


def update_animated_track_objects_from_tracks(records, animations, time_value,
                                              delta_scale):
    """Compose the mode-1 0x407940 child with the 0x42d780 caller."""
    if not isinstance(animations, dict):
        raise ValueError('animations must map original pointer values to byte views')

    def transform(_index, record):
        pointer = struct.unpack_from('<I', record, ANIMATION_POINTER)[0]
        try:
            animation = animations[pointer]
        except KeyError as error:
            raise ValueError(f'missing animation bytes for pointer {pointer:#x}') from error
        pose = evaluate_track_object_animation(animation, time_value, mode=1)
        return pose.translation, pose.rotation

    return update_animated_track_objects(records, delta_scale, transform)
