"""Occupied-pixel bounds helper used by startup scene-area projection."""

RASTER_WIDTH = 0x141
RASTER_HEIGHT = 0xF1


def occupied_raster_bounds(bitmap):
    """Translate 0x483f60 over its fixed 321 by 241 byte raster.

    Returns ``(min_x, min_y, max_x, max_y, count)`` in the original output
parameter order. Empty masks retain the original sentinel bounds.
    """
    if not isinstance(bitmap, (bytes, bytearray, memoryview)):
        raise TypeError('raster must be a byte buffer')
    if len(bitmap) != RASTER_WIDTH * RASTER_HEIGHT:
        raise ValueError('startup occupancy raster must contain exactly 0x141*0xf1 bytes')

    min_x, min_y, max_x, max_y = 1_000_000, 1_000_000, -1_000_000, -1_000_000
    count = 0
    for y in range(RASTER_HEIGHT):
        start = y * RASTER_WIDTH
        for x, occupied in enumerate(bitmap[start:start + RASTER_WIDTH]):
            if occupied:
                if y < min_y:
                    min_y = y
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
                count += 1
    return min_x, min_y, max_x, max_y, count
