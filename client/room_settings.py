"""Private bounded room-settings assignment recovered from 0x44db80/44a9d0.

Inputs are separate immutable images. This copies observed fields only and
preserves untouched destination bytes, including tails after string terminators.
No source defaults, authenticated selection or pointer ownership is inferred.
"""

ROOM_SETTINGS_MIN_SIZE = 0x15a
ROOM_SETTINGS_OFFSET = 0xa0
_FIELDS = ((0x24, 4), (0x2c, 4), (0x20, 4), (0x40, 2),
           (0x154, 4), (0x42, 2), (0x4c, 2), (0x158, 2),
           (0x46, 2), (0x48, 4), (0x44, 1), (0x28, 4), (0x50, 4))


def apply_room_settings(room_image: bytes, settings_image: bytes) -> bytes:
    """Copy settings into room +0xa0 while preserving its server selector.

    Original string copies are unbounded. The authored boundary requires NUL
    within the 32-byte name and 16-byte secondary string fields, and rejects
    invalid images before any write. Aliasing/overflow behavior is excluded.
    """
    for image, minimum in ((room_image, ROOM_SETTINGS_OFFSET + ROOM_SETTINGS_MIN_SIZE),
                           (settings_image, ROOM_SETTINGS_MIN_SIZE)):
        if not isinstance(image, bytes) or not minimum <= len(image) <= 65536:
            raise ValueError('expected bounded immutable room/settings image')
    strings = []
    for offset, capacity in ((0, 32), (0x30, 16)):
        end = settings_image.find(b'\0', offset, offset + capacity)
        if end < 0:
            raise ValueError('settings string requires NUL inside its field')
        strings.append((offset, end + 1 - offset))
    result = bytearray(room_image)
    # Original order: name, opaque data, secondary string, scalar fields.
    for offset, size in (strings[0], (0x54, 256), strings[1], *_FIELDS):
        destination = ROOM_SETTINGS_OFFSET + offset
        result[destination:destination + size] = settings_image[offset:offset + size]
    return bytes(result)
