"""Complete bounded 0x51f440 construction of the original base owner image."""
import math
import struct
from client.body_geometry import body_samples
from client.tire_response import f32


def _ieee_div(numerator, denominator):
    """Return an IEEE single-compatible quotient, including zero divisors."""
    if denominator == 0.0:
        if numerator == 0.0:
            return float('nan')
        return math.copysign(float('inf'), numerator * math.copysign(1.0, denominator))
    return numerator / denominator


def construct_body(owner, identity, mass, half_extents, shape, material):
    if len(owner) != 0x2000:
        raise ValueError('expected full startup observation image')
    if type(identity) is not int or not 0 <= identity <= 0xffffffff:
        raise ValueError('original identity must be a uint32')
    if type(material) is not int or not 0 <= material <= 0xffffffff:
        raise ValueError('original material must be a uint32')
    dimensions = tuple(map(f32, half_extents))
    mass = f32(mass)
    if (len(dimensions) != 3 or not math.isfinite(mass) or not 0 <= mass <= 1e6
            or not all(math.isfinite(v) and abs(v) <= 1e3 for v in dimensions)):
        raise ValueError('bounded nonnegative mass and finite model half extents required')
    if type(shape) is not int or not 0 <= shape <= 4:
        raise ValueError('original body shape must be 0..4')
    if shape == 4:
        dimensions = (max(dimensions),)*3
    x, y, z = dimensions
    out = bytearray(owner)
    out[:0x418] = bytes(0x418)
    def word(offset, value): struct.pack_into('<I', out, offset, value)
    def put(offset, value):
        value = float(value)
        struct.pack_into('<f', out, offset,
                         f32(value) if math.isfinite(value) else value)
    word(0, identity); word(0x58, material); word(0xdc, shape)
    for offset, value in zip((0xcc, 0xd0, 0xd4), dimensions): put(offset, value)
    put(0xd8, math.sqrt(z*z+y*y+x*x))
    put(0x30, struct.unpack('<f', struct.pack('<I', 0xc11cf5c3))[0])
    mass = mass if mass != 0 else 1000.
    put(0x50, mass); put(0x54, 1./mass)
    sx, sy, sz = (f32(v*v*4.) for v in dimensions)
    double_x, double_y, double_z = (f32(v+v) for v in dimensions)
    box_factor, taper_factor = f32(1/12), f32(.0125)
    response = [f32(.31), 1., 1., 1.]
    if shape == 0:
        inertia = ((sz+sy)*mass*box_factor, (sz+sx)*mass*box_factor, (sy+sx)*mass*box_factor)
        volume = double_z*double_y*double_x
    elif shape == 1:
        response[1:] = [.5, 1., .5]
        inertia = ((sz*4.+sy*8.)*mass*taper_factor, (sz+sx)*mass*f32(.05),
                   (sx*4.+sy*8.)*mass*taper_factor)
        volume = double_z*double_x*double_y*.25
    elif shape == 2:
        if x <= z:
            response[1:] = [.5, 1., 1.]
            inertia = ((sy*8.+sz*4.)*mass*taper_factor, (sz+sx)*mass*box_factor, (sy+sx)*mass*box_factor)
        else:
            response[1:] = [1., 1., .5]
            inertia = ((sz+sy)*mass*box_factor, (sz+sx)*mass*box_factor, (sx*4.+sy*8.)*mass*taper_factor)
        volume = double_z*double_x*double_y*.5
    elif shape == 3:
        response[2] = struct.unpack('<f', struct.pack('<I', 0x3f34fdf4))[0]
        radius = f32(math.sqrt(x*x+z*z))
        inertia = ((sz+sy)*mass*box_factor, radius*radius*mass*.5, (sy+sx)*mass*box_factor)
        volume = radius*radius*double_y*f32(math.pi)
    else:
        response[1:] = [struct.unpack('<f', struct.pack('<I', 0x3f34fdf4))[0]]*3
        inertia = (x*mass*f32(.4),)*3
        volume = f32(x*x)*x*f32(4.188790321350098)
    volume = f32(volume)
    put(0x74, volume); put(0x70, _ieee_div(mass, volume))
    for axis, value in enumerate(inertia):
        put(0x2f0+axis*4, value)
        put(0x2fc+axis*4, _ieee_div(1., f32(value)))
    for axis, value in enumerate(response): put(0x308+axis*4, value)
    points = body_samples(shape, dimensions)
    packed = struct.pack('<66f', *(v for p in points for v in p))
    out[0xe0:0x1e8] = packed; out[0x1e8:0x2f0] = packed
    put(0x408, .875); word(0x40c, 0x3eaaa64c)
    coefficients = {1:(.15,.35), 2:(.2,.5), 3:(.05,.1), 4:(.35,1.), 5:(.05,.7), 6:(.25,.5)}
    restitution, friction = coefficients.get(material, (.1,.45))
    put(0x68, restitution); put(0x318, friction)
    if material == 6: put(0x308, .37)
    for offset in (0x78, 0x9c):
        struct.pack_into('<9f', out, offset, 1.,0.,0.,0.,1.,0.,0.,0.,1.)
    put(0xc4, 1.); word(0x400, 1); word(0x404, 1); out[4] = 1
    return bytes(out)
