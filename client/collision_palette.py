"""Palette-byte transforms used while loading collision/world records."""
import struct


def _percentages(values):
    values = tuple(values)
    if len(values) != 3 or any(type(value) is not int or not -(1 << 31) <= value < (1 << 31)
                               for value in values):
        raise ValueError('RGB scale percentages must be three signed int32 values')
    return values


def _signed32(value):
    value &= 0xffffffff
    return value if value < 0x80000000 else value - 0x100000000


def _trunc_div(numerator, denominator):
    quotient = abs(numerator) // denominator
    return -quotient if numerator < 0 else quotient


def _scale(component, percentage):
    if percentage == 100:
        return component
    if percentage <= 100:
        product = _signed32(percentage * component)
        return _trunc_div(product, 100) & 0xff
    product = _signed32((percentage - 100) * (255 - component))
    return (component + _trunc_div(product, 100)) & 0xff


def adjust_color_words(image, count, percentages):
    """Translate 0x428500 over a mutable array of packed ARGB color words.

    The original independently scales bytes at bits 16..23, 8..15 and 0..7;
    the high alpha byte is preserved exactly. Percentage order is red, green,
    blue and each operation uses integer truncation toward zero.
    """
    percentages = _percentages(percentages)
    if not isinstance(image, bytearray) or len(image) % 4:
        raise ValueError('color image must be mutable packed uint32 words')
    if type(count) is not int or count > len(image) // 4:
        raise ValueError('color count must fit the supplied word array')
    for index in range(max(0, count)):
        word, = struct.unpack_from('<I', image, index * 4)
        alpha = word & 0xff000000
        red = _scale((word >> 16) & 0xff, percentages[0])
        green = _scale((word >> 8) & 0xff, percentages[1])
        blue = _scale(word & 0xff, percentages[2])
        struct.pack_into('<I', image, index * 4,
                         alpha | ((red & 0xff) << 16) |
                         ((green & 0xff) << 8) | (blue & 0xff))
    return image


def adjust_color_records(records, percentages):
    """Apply the 0x428640 list walk to explicit ``(count, bytes)`` palettes."""
    records = tuple(records)
    for count, image in records:
        adjust_color_words(image, count, percentages)
    return records
