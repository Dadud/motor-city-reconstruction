"""Bounded original FCE preparation primitives; no attachment producer substitutes.

Addresses refer only to mcity.exe SHA256 28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164.
Images retain FCE header, original/damaged vertex streams and dummy positions.
"""
import math
import struct
from client.tire_response import f32


def _u32(image, offset):
    return struct.unpack_from('<I', image, offset)[0]


def _count(image):
    if len(image) < 0x2038:
        raise ValueError('complete FCE header required')
    count = _u32(image, 0x11c)
    if count > 64 or _u32(image, 0x58) > 16:
        raise ValueError('bounded FCE part/dummy counts required')
    return count


def _point(image, offset):
    point = struct.unpack_from('<3f', image, offset)
    if not all(math.isfinite(v) for v in point):
        raise ValueError('finite FCE vectors required')
    return point


def _vertices(image, part, stream=0x14):
    count = _count(image)
    if not 0 <= part < count:
        return None
    size = _u32(image, 0x520 + part*4)
    start = 0x2038 + _u32(image, stream) + _u32(image, 0x420 + part*4)*12
    if size > 1_000_000 or start + size*12 > len(image):
        raise ValueError('bounded FCE geometry stream required')
    return start, size


def part_half_extents(image, part):
    """Original 0x4c4050. Local-space half-extents, ignoring part origin."""
    table = _vertices(image, part)
    if table is None or table[1] == 0:
        return None
    start, size = table
    low = high = _point(image, start)
    for index in range(1, size):
        point = _point(image, start + index*12)
        low = tuple(min(a,b) for a,b in zip(low,point))
        high = tuple(max(a,b) for a,b in zip(high,point))
    return tuple(f32(abs(a-b)*0.5) for a,b in zip(high,low))


def scale_part_streams(image, part, scales):
    """Original 0x4c42d0. Mutate the three observed vector streams.

    Original stream order 0x14,0x34,0x2c is significant if ranges alias.
    """
    if len(scales) != 3 or not all(math.isfinite(v) for v in scales):
        raise ValueError('three finite scales required')
    scales = tuple(map(f32, scales))
    tables = [_vertices(image,part,stream) for stream in (0x14,0x34,0x2c)]
    for table in tables:
        if table is None:
            continue
        start,size = table
        for index in range(size):
            point = _point(image,start+index*12)
            struct.pack_into('<3f',image,start+index*12,
                             *(f32(v*s) for v,s in zip(point,scales)))


def align_secondary_model(secondary, reference, reference_part):
    """Original 0x52bc60 after linked-list selection of the first type0x11.

    None secondary/part represent original missing model/node gates. A missing
    reference image is rejected safely by this adapter; original selected nodes
    require a valid model pointer. Names use the
    original case-sensitive substring `_W`. All part and dummy origins move.
    Returns whether alignment occurred (original function returns void).
    """
    if secondary is None or reference is None or reference_part is None:
        return False
    count = _count(secondary)
    if not 0 <= reference_part < _count(reference):
        raise ValueError('valid reference part required')
    target = _point(reference,0x120+reference_part*12)
    for index in range(count):
        raw = bytes(secondary[0xe28+index*64:0xe28+(index+1)*64])
        end = raw.find(b'\0')
        if end < 0:
            raise ValueError('terminated FCE name required')
        if b'_W' not in raw[:end]:
            continue
        source = _point(secondary,0x120+index*12)
        delta = [f32(a-b) for a,b in zip(target,source)]
        delta[1] = f32(delta[1]+f32(.05))
        for start,size in ((0x120,count),(0x5c,_u32(secondary,0x58))):
            for part in range(size):
                point = _point(secondary,start+part*12)
                struct.pack_into('<3f',secondary,start+part*12,
                                 *(f32(a+b) for a,b in zip(point,delta)))
        return True
    return False
