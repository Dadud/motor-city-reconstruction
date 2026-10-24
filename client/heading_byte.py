"""Coarse fixed-angle lookup recovered from the MCO math library."""

# Original 257-byte first-octant table at 0x8c8c08.
_ANGLE_TABLE = bytes.fromhex(
    '0001010203030404050606070808090a0a0b0b0c0d0d0e0f0f101011121213141415161617171819191a1b1b1c1c1d1e' +
    '1e1f1f202121222223242425262627272829292a2a2b2c2c2d2d2e2e2f3030313132333334343535363737383839393a' +
    '3a3b3c3c3d3d3e3e3f3f4041414242434344444545464647474848494a4a4b4b4c4c4d4d4e4e4f4f5050515152525353' +
    '545454555556565757585859595a5a5b5b5b5c5c5d5d5e5e5f5f60606061616262636363646465656666666767686868' +
    '69696a6a6a6b6b6c6c6c6d6d6e6e6e6f6f707070717171727273737374747475757676767777777878787979797a7a7a' +
    '7b7b7b7c7c7c7d7d7d7e7e7e7f7f7f8080'
)


def heading_byte(x, y):
    """Return the 1/1024-turn heading used by original routine 0x6f2b90.

    The lookup spans one octant (0..128); signed quadrant reflection supplies
    offsets of 0x100 and 0x200. Coordinates are signed int32; INT_MIN is
    excluded because its wrapped absolute value follows a separate signed
    comparison path in the original.
    """
    if type(x) is not int or type(y) is not int:
        raise ValueError('heading coordinates must be integers')
    if not -0x80000000 <= x <= 0x7fffffff or not -0x80000000 <= y <= 0x7fffffff:
        raise ValueError('heading coordinates must fit signed 32-bit integers')
    if x == -0x80000000 or y == -0x80000000:
        raise ValueError('INT_MIN coordinates are outside the supported domain')

    x_abs, y_abs = abs(x), abs(y)
    offset = 0x200 if y < 0 else 0
    reflected = int(y < 0)
    if x < 0:
        reflected = 1 - reflected
        offset = -offset

    if y_abs < x_abs:
        offset += -0x100 if reflected else 0x100
        reflected = 1 - reflected
        minor, major = y_abs, x_abs
    else:
        minor, major = x_abs, y_abs

    if minor == major:
        angle = 0x80
    else:
        # The original rounds the ratio to the nearest of 257 table entries.
        index = (major // 2 + minor * 0x100) // major
        angle = _ANGLE_TABLE[index]
    return offset - angle if reflected else offset + angle
