"""Private room settings selection from original 0x450830.

Cache lookup is supplied explicitly; this module neither enumerates live rooms
nor authenticates. Original unsafe string overflow is outside its boundary.
"""
from dataclasses import dataclass
import struct

from client.room_settings import ROOM_SETTINGS_MIN_SIZE, apply_room_settings


def initialize_room_settings(image: bytes) -> bytes:
    """Original 0x44a460 writes, preserving unspecified padding and extra bytes."""
    if not isinstance(image, bytes) or not ROOM_SETTINGS_MIN_SIZE <= len(image) <= 65536:
        raise ValueError('expected bounded settings image')
    result = bytearray(image)
    for offset, size in ((0, 32), (0x30, 16), (0x54, 256), (0x20, 12),
                         (0x154, 4), (0x42, 2), (0x4c, 2), (0x158, 2),
                         (0x46, 2), (0x48, 4), (0x50, 4)):
        result[offset:offset + size] = bytes(size)
    struct.pack_into('<I', result, 0x2c, 0x21)
    struct.pack_into('<H', result, 0x40, 2)
    result[0x44] = 1
    return bytes(result)


@dataclass(frozen=True)
class RoomSelection:
    room_image: bytes
    result: int
    source: str


def select_room(room_image: bytes, name: bytes, *, cached_settings: bytes | None = None) -> RoomSelection:
    """Select settings after a supplied cache lookup, or preserve active state.

    Cached settings are an observed successful lookup result, not a fabricated
    server reply. Connected or pending rooms do not perform the lookup. A new
    selection clears the connected short even on a cache hit. No join task is scheduled.
    """
    if not isinstance(room_image, bytes) or not 0x3ac <= len(room_image) <= 65536:
        raise ValueError('expected bounded complete room image')
    if not isinstance(name, bytes) or len(name) > 31 or b'\0' in name:
        raise ValueError('room name must contain at most 31 bytes without NUL')
    current = room_image[0xa0:0xc0]
    end = current.find(b'\0')
    if end < 0:
        raise ValueError('current room name requires bounded NUL')
    active = (struct.unpack_from('<H', room_image, 0xec)[0] != 0 or
              struct.unpack_from('<I', room_image, 0x3a8)[0] != 0)
    if active:
        return RoomSelection(room_image, int(name == current[:end]), 'active')
    if cached_settings is None:
        settings = bytearray(initialize_room_settings(bytes(ROOM_SETTINGS_MIN_SIZE)))
        settings[:len(name) + 1] = name + b'\0'
        source = 'defaults'
    else:
        if not isinstance(cached_settings, bytes) or not ROOM_SETTINGS_MIN_SIZE <= len(cached_settings) <= 65536:
            raise ValueError('expected bounded cached settings image')
        settings = bytearray(cached_settings)
        source = 'cache'
    struct.pack_into('<H', settings, 0x4c, 0)
    return RoomSelection(apply_room_settings(room_image, bytes(settings)), 1, source)
