"""Raw reflected CRC-32 accumulator shared by native checksum call sites."""
import zlib


def crc32_raw(data):
    """Match 0x658280: initial 0xffffffff, standard table, no final XOR."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError('CRC input must be bytes-like')
    return zlib.crc32(data) ^ 0xffffffff
