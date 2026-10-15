"""Original 0x51ed40 body samples: eight corners, six faces, eight edges.

Shape selectors are original internal values, not the catalogue body selectors.
The rounded corner adjustment happens AFTER face/edge sample construction.
"""
import math
from client.tire_response import f32


def body_samples(shape, half_extents):
    if type(shape) is not int or not 0 <= shape <= 4:
        raise ValueError('original body shape must be 0..4')
    values = tuple(map(f32, half_extents))
    if len(values) != 3 or not all(math.isfinite(v) and abs(v) <= 1e6 for v in values):
        raise ValueError('three finite bounded half extents required')
    x, y, z = values
    nx, ny, nz = -x, -y, -z
    corners = [(nx, ny, z), (x, ny, z), (x, ny, nz), (nx, ny, nz)]
    if shape == 1:
        upper = [(0., y, 0.)] * 4
    elif shape == 2 and x <= z:
        upper = [(0., y, z), (0., y, z), (0., y, nz), (0., y, nz)]
    elif shape == 2:
        upper = [(nx, y, 0.), (x, y, 0.), (x, y, 0.), (nx, y, 0.)]
    else:
        upper = [(nx, y, z), (x, y, z), (x, y, nz), (nx, y, nz)]
    corners += upper
    # The original retains several sums in x87 registers until their final store.
    a, b, c, d = upper
    rear_x = c[0] + d[0]
    rear_y = d[1] + c[1]
    rear_z = c[2] + d[2]
    bottom_x, bottom_y = nx + x, ny + ny
    faces = [
        ((b[0]+a[0]+nx+x)*.25, (ny+ny+a[1]+b[1])*.25, (z+z+b[2]+a[2])*.25),
        ((rear_x+nx+x)*.25, (ny+ny+rear_y)*.25, (nz+nz+rear_z)*.25),
        ((nx+nx+d[0]+a[0])*.25, (ny+ny+d[1]+a[1])*.25, (nz+d[2]+a[2]+z)*.25),
        ((x+x+c[0]+b[0])*.25, (ny+ny+c[1]+b[1])*.25, (nz+c[2]+b[2]+z)*.25),
        ((rear_x+b[0]+a[0])*.25, (rear_y+a[1]+b[1])*.25, (rear_z+b[2]+a[2])*.25),
        ((nx+bottom_x+x)*.25, (ny+ny+bottom_y)*.25, (z+z+nz+nz)*.25),
    ]
    edges = [
        ((b[0]+a[0])*.5, (a[1]+b[1])*.5, (b[2]+a[2])*.5),
        ((c[0]+b[0])*.5, (c[1]+b[1])*.5, (c[2]+b[2])*.5),
        ((d[0]+a[0])*.5, (d[1]+a[1])*.5, (d[2]+a[2])*.5),
        (rear_x*.5, rear_y*.5, rear_z*.5),
        (bottom_x*.5, bottom_y*.5, (z+z)*.5),
        ((x+x)*.5, bottom_y*.5, (nz+z)*.5),
        ((nx+nx)*.5, bottom_y*.5, (nz+z)*.5),
        (bottom_x*.5, bottom_y*.5, (nz+nz)*.5),
    ]
    # Original array contains 22 samples (eight corners, six faces, eight edges).
    # Four vertical edge midpoints are not present in this particular helper.
    samples = [tuple(map(f32, p)) for p in corners + faces + edges]
    if shape in (3, 4):
        scale = f32(.707)
        for i in range(8):
            samples[i] = tuple(f32(v*scale) if shape == 4 or axis != 1 else v
                               for axis, v in enumerate(samples[i]))
        if shape == 4:
            for i in range(14, 22):
                p = samples[i]
                samples[i] = (p[0], f32(p[1]*scale), p[2])
    return tuple(samples)


def customize_body_samples(selector, samples):
    """Complete 0x43a240 catalogue-shape adjustment of the live sample array."""
    if type(selector) is not int or not 0 <= selector <= 7:
        raise ValueError('catalogue body selector must be 0..7')
    if len(samples) != 22 or any(len(p) != 3 for p in samples):
        raise ValueError('22 original body samples required')
    values = [f32(v) for p in samples for v in p]
    if not all(math.isfinite(v) and abs(v) <= 1e6 for v in values):
        raise ValueError('bounded finite sample coordinates required')
    def scale(indices, factor):
        for i in indices: values[i] = f32(values[i]*f32(factor))
    if selector == 1:
        scale((22,19,52),.3); scale((13,16,43),.5); scale((2,5,56,14,17,44),.9)
    elif selector in (2,4):
        if selector == 2:
            scale((20,53,23),.8); scale((29,),.95)
        scale((17,14),.8); scale((44,),.9); scale((22,19),.3)
        scale((52,43),.4); scale((13,16),.3)
    elif selector == 5:
        scale((22,19,52),.3); scale((13,16,43),.4)
    elif selector == 6:
        scale((3,0,46,45,48,49,15,12,18,21,11,8),.8)
        scale((17,14,44),.85); scale((9,6,65),.9)
        scale((22,19,52),.7); scale((13,16),.3); scale((43,),.4)
    elif selector == 7:
        scale((13,16,43),.3)
    return tuple(tuple(values[i:i+3]) for i in range(0,66,3))
