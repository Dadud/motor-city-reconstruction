"""Observed MCO string comparison primitives."""


def _fold_config_byte(value):
    wrapped = (value + 0xbf) & 0xff
    return (wrapped + (0x20 if wrapped < 0x1a else 0) + 0x41) & 0xff


def compare_config_names(left, right):
    """Compare NUL-terminated names using 0x6aa840's default MCO mode.

    The original's other mode delegates case conversion to locale state. This
    function represents the observed default mode only and returns -1, 0, or 1.
    """
    if not isinstance(left, (bytes, bytearray, memoryview)) or not isinstance(
            right, (bytes, bytearray, memoryview)):
        raise TypeError('byte strings required')
    left, right = bytes(left), bytes(right)
    if b'\0' not in left or b'\0' not in right:
        raise ValueError('NUL-terminated byte strings required')

    index = 0
    while True:
        first, second = left[index], right[index]
        if first == second:
            if first == 0:
                return 0
            index += 1
            continue
        first_folded = _fold_config_byte(first)
        second_folded = _fold_config_byte(second)
        if first_folded != second_folded:
            return -1 if first_folded < second_folded else 1
        index += 1
