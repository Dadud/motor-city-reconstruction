"""Float-to-integer scanline bounds used by the startup scene rasterizer."""
import math

from .tire_response import f32


def _bounded_float(value):
    value = f32(value)
    if not math.isfinite(value) or value < -2147483648.0 or value >= 2147483648.0:
        raise ValueError('finite float32 value with int32-rounded result required')
    return value


def raster_ceil(value):
    """Translate 0x483f00's x87 ROUND plus positive-fraction correction."""
    return math.ceil(_bounded_float(value))


def raster_floor(value):
    """Translate 0x483f30's x87 ROUND plus negative-fraction correction."""
    return math.floor(_bounded_float(value))
