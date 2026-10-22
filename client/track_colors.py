"""Track color operations recovered from the native client."""
import struct


_F32 = struct.Struct('<f')


def _f32(value):
    return _F32.unpack(_F32.pack(value))[0]


def blend_track_color(argb, base_argb, divisor, *, bypass=False):
    """Translate 0x4956e0's channel blend, preserving its native byte order.

    The high alpha byte is always 0xff on the blend path. The divisor is the
    native global blend divisor; a zero divisor follows the original x87
    floating-point path and is intentionally not special-cased.
    """
    if any(type(word) is not int or not 0 <= word <= 0xffffffff
           for word in (argb, base_argb)):
        raise ValueError('colors must be unsigned 32-bit ARGB words')
    if type(bypass) is not bool:
        raise ValueError('bypass must be a boolean')
    if bypass:
        return argb

    blend = _f32(1.0 / _f32(divisor))
    keep = _f32(1.0 - blend)
    half = 0.5
    base_channels = (base_argb & 0xff, (base_argb >> 8) & 0xff,
                     (base_argb >> 16) & 0xff)
    source_channels = (argb & 0xff, (argb >> 8) & 0xff,
                       (argb >> 16) & 0xff)
    output = []
    for base, source in zip(base_channels, source_channels):
        mixed = (base * blend + source * keep) * half
        # x87 stores the result to binary32 before FISTP (nearest-even).
        quantized = int(round(_f32(mixed)))
        output.append(min(0xff, max(0, quantized)))
    return 0xff000000 | (output[2] << 16) | (output[1] << 8) | output[0]
