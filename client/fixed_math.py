"""Fixed-point integer helpers recovered from the MCO client math library."""


def _truncating_division(numerator, denominator):
    """Integer division with the x86/C truncation-toward-zero rule."""
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def signed_ratio_16_16(numerator, denominator):
    """Translate 0x6f2c50's signed quotient to wrapped 16.16 fixed point.

    The native implementation divides the whole part and the remainder
    separately, then combines both at 16 fractional bits. This avoids
    overflowing a direct ``numerator * 65536`` intermediate.
    """
    if (type(numerator) is not int or type(denominator) is not int or
            not -(1 << 31) <= numerator < (1 << 31) or
            not -(1 << 31) <= denominator < (1 << 31)):
        raise ValueError('fixed-point ratio operands must be signed int32 values')
    if denominator == 0:
        raise ValueError('fixed-point ratio denominator must be nonzero')
    if numerator == -(1 << 31) and denominator == -1:
        raise ValueError('native signed division overflows for INT_MIN / -1')
    whole = _truncating_division(numerator, denominator)
    remainder = numerator - whole * denominator
    fractional = _truncating_division(remainder * 0x10000, denominator)
    result = whole * 0x10000 + fractional
    return ((result + (1 << 31)) & 0xffffffff) - (1 << 31)
