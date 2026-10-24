"""Homogeneous vertex clip-code helper recovered from the MCO renderer."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderClipBounds:
    """Signed 32-bit limits consumed by the original 0x6cb810 helper."""
    x_lower: int
    x_upper: int
    y_lower: int
    y_upper: int
    w_upper: int
    z_lower: int

    def __post_init__(self):
        for value in (self.x_lower, self.x_upper, self.y_lower,
                      self.y_upper, self.w_upper, self.z_lower):
            if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
                raise ValueError('clip bounds must be signed 32-bit integers')


def render_clip_code(vertex, bounds):
    """Return the byte written by 0x6cb810 for one signed XYZW vertex.

    Bound order and bit behavior follow the original comparisons, including
    the XOR mask used when W is negative.
    """
    if len(vertex) != 4 or any(type(value) is not int or
                               not -(1 << 31) <= value < (1 << 31)
                               for value in vertex):
        raise ValueError('clip vertices require four signed 32-bit integers')
    if not isinstance(bounds, RenderClipBounds):
        raise TypeError('bounds must be RenderClipBounds')

    x, y, z, w = vertex
    code = 0
    if x < bounds.x_lower:
        code = 0x10
    elif x > bounds.x_upper:
        code = 0x20
    if y < bounds.y_lower:
        code |= 0x04
    elif y > bounds.y_upper:
        code |= 0x08
    if w < 0:
        code ^= 0x3d
    elif w > bounds.w_upper:
        code |= 0x01
    elif z >= bounds.z_lower:
        code |= 0x02
    return code
