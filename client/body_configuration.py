"""Catalogue body configuration initialization, before assembly aggregation.

The numeric stores in original 0x54a390 are recovered. Original semantic
validation (0x542a00) and body quality (0x54a2b0) are separate boundaries.
"""
from dataclasses import dataclass
import math
import struct

from client.tire_response import f32


# Destination offset, one-based Physics Val ordinal. Unknown semantic names
# remain offsets rather than acquiring invented physical meanings.
_FLOATS = ((0,16),(4,17),(8,18),(0x10,20),(0x24,9),
    (0x2c,2),(0x30,3),(0x34,4),(0x38,5),(0x3c,6),(0x40,34),
    (0x58,10),(0xec,23),(0xf0,24),(0xf4,25),(0xf8,26),(0xfc,26),
    (0x100,27),(0x104,27),(0x108,28),(0x10c,29),(0x110,30),
    (0x114,30),(0x118,30),(0x11c,31),(0x120,32),(0x64,35),(0x68,36))
_NEAREST = ((0xc,19),(0x14,38),(0x18,39))
_TRUNCATE = ((0x44,33),(0x48,7),(0x4c,8),(0xe8,22))
_BYTES = ((0x60,12),(0x61,13),(0x62,14),(0x63,15),(0xe4,21))


@dataclass(frozen=True)
class BodyConfiguration:
    """A body-loader result; initial assembly mass is only the body's mass."""
    image: bytes
    part_type_id: int
    physics_ordinal: int

    def float_at(self, offset):
        return struct.unpack_from('<f',self.image,offset)[0]

    @property
    def body_mass(self): return self.float_at(0x1c)
    @property
    def wheelbase(self): return self.float_at(0x2c)
    @property
    def front_track(self): return self.float_at(0x30)
    @property
    def rear_track(self): return self.float_at(0x34)
    @property
    def body_front_weight_fraction(self): return self.float_at(0x40)
    @property
    def front_clearance_reference(self): return self.float_at(0x11c)
    @property
    def rear_clearance_reference(self): return self.float_at(0x120)


def initialize_body_configuration(record, *, initial_image=None):
    """Execute the validated-record numeric section, preserving other bytes.

    Shape/finite checks protect this public function; they do not reproduce the
    original semantic validator. Integer conversions match the original default
    x87 round-to-nearest-even and CRT truncation. No COM/inertia is supplied.
    """
    if len(record.values) != 39:
        raise ValueError('body initializer requires exactly 39 Physics values')
    values = tuple(f32(v) for v in record.values)
    mass = f32(record.mass)
    if not all(math.isfinite(v) for v in (*values,mass)) or mass < 0:
        raise ValueError('body record requires finite values and nonnegative mass')
    out = bytearray(0x820) if initial_image is None else bytearray(initial_image)
    if len(out) != 0x820:
        raise ValueError('body configuration must contain 0x820 bytes')
    def integer(value, nearest=False):
        result = round(value) if nearest else math.trunc(value)
        if nearest:
            return result if -0x80000000 <= result <= 0x7fffffff else -0x80000000
        # CRT uses FISTP int64 and the caller stores only EAX, so finite
        # out-of-int32 values wrap rather than saturating to int32 indefinite.
        result = result if -0x8000000000000000 <= result <= 0x7fffffffffffffff else -0x8000000000000000
        return ((result+0x80000000)&0xffffffff)-0x80000000
    for offset, ordinal in _FLOATS:
        struct.pack_into('<f',out,offset,values[ordinal-1])
    for offset, ordinal in _NEAREST:
        struct.pack_into('<i',out,offset,integer(values[ordinal-1],True))
    for offset, ordinal in _TRUNCATE:
        struct.pack_into('<i',out,offset,integer(values[ordinal-1]))
    for offset, ordinal in _BYTES:
        out[offset] = integer(values[ordinal-1]) & 255
    for offset, value in ((0x1c,mass),(0x20,mass),(0x28,0.),
                          (0x50,9.),(0x54,9.),(0x5c,0.)):
        struct.pack_into('<f',out,offset,value)
    return BodyConfiguration(bytes(out),record.part_type_id,record.ordinal)


def stock_body_configuration(catalogue, vehicle_id=101):
    """Join the actual stock body and original Physics_Select ordinal 1.

    Ordinal 1 is the recovered query behavior, independent of StockAssembly's
    PhysicsDefault flag. Inputs remain in the separately supplied database.
    """
    vehicle = catalogue.vehicle(vehicle_id)
    bodies = [p for p in vehicle.parts if p.abstract_type_id == 20001]
    if len(bodies) != 1:
        raise ValueError('stock vehicle requires exactly one body')
    part = bodies[0]
    try:
        record = catalogue.physics[(part.part_type_id,1)]
    except KeyError as error:
        raise ValueError('stock body lacks required Physics ordinal 1') from error
    return initialize_body_configuration(record)
