"""Fixed-angle heading lookup recovered from 0x6f2cc0."""
import struct

# 257 endpoint values at 0x8c8d10; 16-bit turn units, first quadrant.
_HEADING_TABLE = struct.unpack('<257I', bytes.fromhex(
    '0000000029000000510000007a000000a3000000cc000000f40000001d010000460100006f01000097010000c0010000e9010000110200003a02000062020000' \
    '8b020000b4020000dc020000050300002d030000560300007e030000a7030000cf030000f703000020040000480400007004000099040000c1040000e9040000' \
    '11050000390500006105000089050000b1050000d905000001060000290600005106000078060000a0060000c8060000ef060000170700003e07000066070000' \
    '8d070000b5070000dc070000030800002a08000051080000780800009f080000c6080000ed080000140900003b0900006109000088090000ae090000d5090000' \
    'fb090000220a0000480a00006e0a0000940a0000ba0a0000e00a0000060b00002c0b0000510b0000770b00009d0b0000c20b0000e70b00000d0c0000320c0000' \
    '570c00007c0c0000a10c0000c60c0000eb0c0000100d0000340d0000590d00007d0d0000a20d0000c60d0000ea0d00000f0e0000330e0000560e00007a0e0000' \
    '9e0e0000c20e0000e50e0000090f00002c0f0000500f0000730f0000960f0000b90f0000dc0f0000ff0f000021100000441000006710000089100000ab100000' \
    'ce100000f01000001211000034110000561100007711000099110000bb110000dc110000fd1100001f120000401200006112000082120000a3120000c3120000' \
    'e41200000513000025130000451300006613000086130000a6130000c6130000e61300000514000025140000441400006414000083140000a2140000c1140000' \
    'e0140000ff1400001e1500003d1500005b1500007a15000098150000b7150000d5150000f3150000111600002f1600004c1600006a16000088160000a5160000' \
    'c2160000e0160000fd1600001a1700003717000054170000701700008d170000aa170000c6170000e2170000fe1700001b18000037180000531800006e180000' \
    '8a180000a6180000c1180000dd180000f8180000131900002e19000049190000641900007f1900009a190000b4190000cf190000e9190000041a00001e1a0000' \
    '381a0000521a00006c1a0000861a00009f1a0000b91a0000d31a0000ec1a0000051b00001f1b0000381b0000511b00006a1b0000831b00009c1b0000b41b0000' \
    'cd1b0000e51b0000fe1b0000161c00002e1c0000461c00005e1c0000761c00008e1c0000a61c0000be1c0000d51c0000ed1c0000041d00001b1d0000331d0000' \
    '4a1d0000611d0000781d00008e1d0000a51d0000bc1d0000d31d0000e91d0000ff1d0000161e00002c1e0000421e0000581e00006e1e0000841e00009a1e0000' \
    'b01e0000c51e0000db1e0000f01e0000061f00001b1f0000301f0000451f00005a1f00006f1f0000841f0000991f0000ae1f0000c31f0000d71f0000ec1f0000' \
    '00200000'
))


def _signed32(value):
    value &= 0xffffffff
    return value - 0x100000000 if value & 0x80000000 else value


def heading_angle(param_1, param_2):
    """Match the integer fixed-angle atan2 helper at 0x6f2cc0.

    Inputs are signed coordinate integers. The result uses 0x10000 units per
    turn and preserves the executable's Q32 ratio, table interpolation and
    octant reflection arithmetic.
    """
    if type(param_1) is not int or type(param_2) is not int:
        raise ValueError('heading coordinates must be integers')
    if not -0x80000000 <= param_1 <= 0x7fffffff or not -0x80000000 <= param_2 <= 0x7fffffff:
        raise ValueError('heading coordinates must fit signed 32-bit integers')
    flags = 0
    if param_2 < 0:
        flags |= 2
        param_2 = _signed32(-param_2)
    if param_1 < 0:
        flags |= 4
        param_1 = _signed32(-param_1)
    if param_2 == param_1:
        angle = 0x2000
    else:
        minor = param_1
        if param_2 < param_1:
            flags |= 1
            minor, param_2 = param_2, param_1
        denominator = param_2 & 0xffffffff
        if denominator == 0:
            raise ValueError('heading ratio denominator is zero after signed wrapping')
        ratio = (((minor & 0xffffffff) << 32) // denominator) & 0xffffffff
        index = ratio >> 24
        fraction = (ratio >> 8) & 0xffff
        start = _HEADING_TABLE[index]
        angle = start + (((_HEADING_TABLE[index + 1] - start) * fraction) >> 16)
    if flags == 1:
        return 0x4000 - angle
    if flags == 2:
        return 0x8000 - angle
    if flags == 3:
        return angle + 0x4000
    if flags == 4:
        return -angle
    if flags == 5:
        return angle - 0x4000
    if flags == 6:
        return angle - 0x8000
    if flags == 7:
        return -0x4000 - angle
    return angle


def heading_byte_for_world_coordinates(x, z):
    """Quantize body float coordinates as 0x42d9f0 does, then return AH."""
    x_fixed = int(round(float(x) * 65536.0)) >> 8
    z_fixed = int(round(float(z) * 65536.0)) >> 8
    return (heading_angle(x_fixed, z_fixed) >> 8) & 0xff
