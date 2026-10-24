"""Direct vertex-format callbacks recovered from the MCO renderer tables."""
from .tire_response import f32

# Static defaults read by the mode-8 callback in the shipped executable.
_DEFAULT_VIEWPORT = (319.5, 319.5, 319.5, 239.5,
                     1.000100016593933, 3.9999998989515007e-5, 10000.0)


def transform_render_position(vertex, viewport=_DEFAULT_VIEWPORT):
    """Translate callback 0x6f1d60: project one world point to XYZW.

    The mode-8 table slot at 0x8c8a20 calls this body. XYZ inputs use the
    renderer's binary32 world point; all calculations retain x87-style
    intermediates until the four native float stores.
    """
    vertex=tuple(f32(value) for value in vertex)
    viewport=tuple(f32(value) for value in viewport)
    if len(vertex)!=3 or len(viewport)!=7:
        raise ValueError('renderer position requires XYZ and seven viewport words')
    x,y,z=vertex
    x_scale,y_scale,x_offset,y_offset,z_offset,z_scale,zero_z_factor=viewport
    reciprocal=zero_z_factor if z==0.0 else 1.0/z
    return (f32((x_scale*reciprocal)*x+x_offset),
            f32(y_offset-(y*y_scale)*reciprocal),
            f32((z-z_offset)*z_scale),f32(reciprocal))


def transform_render_positions(vertices, viewport=_DEFAULT_VIEWPORT):
    """Apply the native mode-8 callback to a sequence of XYZ vertices."""
    return tuple(transform_render_position(vertex,viewport) for vertex in vertices)
