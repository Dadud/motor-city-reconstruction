"""Translation of native render/effect parameter normalizer 0x494dc0."""
import math
import struct


BLOCK_SIZE = 0xC138
_FLOAT32 = struct.Struct('<f')
_RADIUS_SCALE = _FLOAT32.unpack(bytes.fromhex('82a8fb37'))[0]  # mcity.exe:0x83c7d0
_DEGREES_TO_TURN = _FLOAT32.unpack(bytes.fromhex('610b363b'))[0]  # 0x83c7d4
_TURN_RADIANS = struct.unpack('<d', bytes.fromhex('00000060fb211940'))[0]  # 0x84a198


def _f32(value):
    return _FLOAT32.unpack(_FLOAT32.pack(value))[0]


def prepare_track_effect_params(block):
    """Mutate a writable native-layout image using the 0x494dc0 field offsets.

    Offsets are preserved from the native record because its complete semantic
    layout has not been recovered. The function updates only the fields written
    by the original routine.
    """
    if not isinstance(block, bytearray):
        raise TypeError('track effect block must be a bytearray')
    if len(block) < BLOCK_SIZE:
        raise ValueError(f'track effect block must be at least {BLOCK_SIZE:#x} bytes')

    count, = struct.unpack_from('<i', block, 0xC0D8)
    if count != 0:
        struct.pack_into('<f', block, 0xC0DC, _f32(1.0 / count))

    limit, = struct.unpack_from('<i', block, 0xC0C8)
    current, = struct.unpack_from('<i', block, 0xC0D0)
    if current > limit:
        struct.pack_into('<i', block, 0xC0D0, limit)

    for offset in (0xC118, 0xC11C):
        value, = struct.unpack_from('<f', block, offset)
        if value == 0.0 or math.isnan(value):
            struct.pack_into('<f', block, offset, 1.0)

    phase_degrees, = struct.unpack_from('<i', block, 0xC134)
    radius_scale, = struct.unpack_from('<i', block, 0xC130)
    phase_turns = _f32(phase_degrees * _DEGREES_TO_TURN)
    amplitude = _f32(radius_scale * _RADIUS_SCALE)
    radians = phase_turns * _TURN_RADIANS
    struct.pack_into('<f', block, 0xC0E0, _f32(math.cos(radians) * amplitude))
    struct.pack_into('<f', block, 0xC0E4, _f32(math.sin(radians) * amplitude))
    return block
