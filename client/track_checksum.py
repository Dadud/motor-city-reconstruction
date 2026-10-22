"""The raw CRC-32 accumulator used by native MCO track loading."""
from .crc32 import crc32_raw


def track_checksum(data):
    """Return 0x658280's 32-bit result for a complete loaded byte image.

    The native loop starts at ``0xffffffff``, uses the standard reflected
    0xedb88320 lookup table, and returns that accumulator without a final XOR.
    This is therefore the complement of ``zlib.crc32(data)``.
    """
    return crc32_raw(data)
