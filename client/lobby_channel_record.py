"""Private research boundary for original room argument -> channel record.

Reproduces bounded field writes, preserving an explicitly supplied allocation
image wherever the original constructor does not initialize bytes. No sockets,
host callbacks, original object pointers, or inferred room defaults are used.
"""
import struct

from client.lobby_channel_codec import ChannelJoinRecord

CHANNEL_ARGUMENT_SIZE = 0x15c
CHANNEL_ALLOCATION_SIZE = 0x3bc


def initialize_channel_image(argument: bytes, allocated_image: bytes) -> bytes:
    """0x743d50 plus data defaults from 0x7440c0; excludes host lock/vtable."""
    if not isinstance(argument, bytes) or len(argument) != CHANNEL_ARGUMENT_SIZE:
        raise ValueError('expected exact native channel argument')
    if not isinstance(allocated_image, bytes) or len(allocated_image) != CHANNEL_ALLOCATION_SIZE:
        raise ValueError('expected explicit channel allocation image')
    image = bytearray(allocated_image)
    def put(offset, width, value):
        image[offset:offset + width] = value.to_bytes(width, 'little')
    for start, end in ((0x38, 0x58), (0x70, 0x81), (0x90, 0x190)):
        image[start:end] = bytes(end - start)
    for offset in (8, 0x2c, 0x30, 0x58, 0x60, 0x88, 0x190, 0x194, 0x19c):
        put(offset, 4, 0)
    for offset in (0x64, 0x66, 0x6a, 0x6c, 0x82, 0x86, 0x198):
        put(offset, 2, 0)
    put(0x34, 4, 0xffffffff)
    put(0x68, 2, 1)
    put(0x84, 1, 1)
    # Defaults subsequently overwritten by the constructor's supplied values.
    flags = struct.unpack_from('<I', argument, 0xc)[0]
    put(0x6e, 2, (flags & 1) or (flags & 4) or 2)
    put(0x6a, 2, flags & 0x20)
    put(0x82, 2, flags & 0x4000)
    for source, target, width in ((0, 4, 4), (4, 0x5c, 4), (8, 8, 4),
                                  (0xc, 0x190, 4), (0x34, 0x70, 17),
                                  (0x48, 0x88, 4), (0x4c, 0x8c, 4),
                                  (0x50, 0x90, 256), (0x150, 0x86, 2)):
        image[target:target + width] = argument[source:source + width]
    # strncpy(..., 30) pads after NUL but does not touch the final two bytes.
    name = argument[0x10:0x2e].split(b'\0', 1)[0]
    image[0xc:0x2a] = name.ljust(30, b'\0')
    return bytes(image)


def materialize_channel_record(channel_image: bytes) -> ChannelJoinRecord:
    """Field-copy range 0x7398a7..0x739a0e, before wire serialization.

    Input includes caller/connection overrides. Preserve untouched record holes
    from this exact image; zeroing them is not an observed original behavior.
    """
    if not isinstance(channel_image, bytes) or len(channel_image) != CHANNEL_ALLOCATION_SIZE:
        raise ValueError('expected complete channel image')
    image = bytearray(channel_image)
    for source, target, width in (
        (8, 0x1a0, 4), (0x2c, 0x1c4, 4), (0x30, 0x1c8, 4),
        (0x34, 0x1cc, 4), (0x58, 0x1f0, 4), (0x5c, 0x1f4, 4),
        (0x60, 0x1f8, 4), (0x64, 0x1fc, 2), (0x66, 0x1fe, 2),
        (0x68, 0x200, 2), (0x6a, 0x202, 2), (0x6c, 0x204, 2),
        (0x6e, 0x206, 2), (0x82, 0x226, 2), (0x84, 0x228, 1),
        (0x86, 0x22c, 2), (0x88, 0x230, 4), (0x8c, 0x234, 4),
        (0x190, 0x340, 4), (0x198, 0x346, 2), (0xc, 0x1a4, 32),
        (0x38, 0x1d0, 16), (0x48, 0x1e0, 16), (0x90, 0x240, 256),
        (0x70, 0x214, 17),
    ):
        image[target:target + width] = image[source:source + width]
    return ChannelJoinRecord(bytes(image[0x1a0:0x344]))
