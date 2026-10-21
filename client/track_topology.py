"""Track-path ordering and bounded index stepping recovered from the client."""
import struct

from .tire_response import f32


_U32 = 0xffffffff


def _u32(value):
    return value & _U32


def _s32(value):
    value &= _U32
    return value - 0x100000000 if value & 0x80000000 else value


def _signed_abs(value):
    value = _s32(value)
    return _s32(_u32((value ^ (value >> 31)) - (value >> 31)))


def _c_remainder(dividend, divisor):
    """C/x86 signed remainder, with quotient truncated toward zero."""
    dividend = _s32(dividend)
    divisor = _s32(divisor)
    if divisor == 0:
        raise ValueError('track path count must be nonzero')
    quotient = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        quotient = -quotient
    return _s32(dividend - quotient * divisor)


def reset_path_index(index, offset, *, primary_count, fallback_count,
                     primary_origin, secondary_origin, wrapped_mode,
                     reverse_mode):
    """Port 0x405930's path-coordinate calculation with x86 int semantics."""
    if any(type(value) is not int for value in
           (index, offset, primary_count, fallback_count, primary_origin,
            secondary_origin, wrapped_mode, reverse_mode)):
        raise ValueError('path reset inputs must be integers')
    count = _s32(primary_count)
    if count == 0:
        count = _s32(fallback_count)
    if count == 0:
        return 0
    offset = _s32(offset)
    index = _s32(index)
    primary_origin = _s32(primary_origin)
    secondary_origin = _s32(secondary_origin)
    adjusted = _u32(offset)
    if offset < 0:
        adjusted = _u32(adjusted + 1)
    base = _s32(_u32(adjusted * _u32(count)))

    if primary_origin == secondary_origin and wrapped_mode == 0:
        if reverse_mode == 0:
            if offset >= 0:
                numerator = _s32(_u32(_s32(count - primary_origin) + index))
                return _s32(_u32(base + _c_remainder(numerator, count)))
            numerator = _s32(_u32(_s32(primary_origin - index) + count))
            return _s32(_u32(base - _c_remainder(numerator, count)))
        if offset >= 0:
            numerator = _s32(_u32(_s32(primary_origin - index) + count))
            return _s32(_u32(base + _c_remainder(numerator, count)))
        numerator = _s32(_u32(_s32(count - primary_origin) + index))
        return _s32(_u32(base - _c_remainder(numerator, count)))

    if offset < 0:
        return (_s32(primary_origin - index) if secondary_origin <= primary_origin
                else _s32(index - primary_origin))
    if offset & 1:
        delta = (index - secondary_origin if secondary_origin <= primary_origin
                 else secondary_origin - index)
        return _s32(_u32(base + delta))
    delta = (primary_origin - index if secondary_origin <= primary_origin
             else index - primary_origin)
    return _s32(_u32(base + delta))


def path_index_is_forward(count, current, candidate, *, wrapped_ordering):
    """Port 0x406840's signed/wrapped path-index ordering predicate."""
    if any(type(value) is not int for value in (count, current, candidate)):
        raise ValueError('path indices and count must be integers')
    direct = _u32(current - candidate)
    if wrapped_ordering:
        if candidate < current:
            alternate = _u32(_u32(current - count) - candidate)
        else:
            alternate = _u32(_u32(count - candidate) + current)
        if _signed_abs(alternate) <= _signed_abs(direct):
            direct = alternate
    return _s32(direct) > 0


def step_path_index(index, offset, count, *, wrap_mode=True,
                    index_is_rejected=None):
    """Port 0x4066f0's single-step path index update.

    When ``wrap_mode`` is false, the game clamps to the path range and asks
    its separate validity helper (0x406960) before accepting the new index.
    """
    if any(type(value) is not int for value in (index, offset, count)):
        raise ValueError('path indices and count must be integers')
    if not wrap_mode:
        candidate = _s32(_u32(index + offset))
        candidate = min(max(candidate, 0), count - 1)
        if not callable(index_is_rejected):
            raise ValueError('clamped stepping requires the native rejection predicate')
        return index if index_is_rejected(candidate) else candidate

    stepped = _s32(_u32(index + offset))
    if offset < 0 and stepped < 0:
        return _s32(_u32(count + stepped))
    if offset >= 0 and count <= stepped:
        return _s32(_u32(_u32(index - count) + offset))
    return stepped


def track_index_is_rejected(index, *, range_start, range_end,
                            lower_limit, upper_limit):
    """Port 0x406960's path-index rejection predicate."""
    if any(type(value) is not int for value in
           (index, range_start, range_end, lower_limit, upper_limit)):
        raise ValueError('track range values must be integers')
    low, high = sorted((range_start, range_end))
    no_lower_limit = lower_limit < 1
    has_upper_limit = upper_limit > 0
    if no_lower_limit and not has_upper_limit:
        return False
    if high == low:
        return False
    if low < high:
        if no_lower_limit or lower_limit <= low:
            if has_upper_limit and high < upper_limit:
                if no_lower_limit or lower_limit <= index:
                    return index > upper_limit
                return True
            if no_lower_limit:
                return False
        return index < lower_limit and has_upper_limit and upper_limit < index
    if not has_upper_limit:
        return False
    if lower_limit <= index or index <= upper_limit:
        return False
    return True


def bounded_path_index(index, offset, count, *, clamp):
    """Port 0x406770's one-adjustment wrap or bounded path index update."""
    if any(type(value) is not int for value in (index, offset, count)):
        raise ValueError('path indices and count must be integers')
    value = _s32(_u32(index + offset))
    if clamp:
        if count <= value:
            return count - 1
        return value if value >= 1 else 0
    if offset < 0:
        return _s32(_u32(count + value)) if value < 0 else value
    if count <= value:
        return _s32(_u32(_u32(index - count) + offset))
    return value




def collision_search_slot(row_left_step, row_right_step, offset):
    """Select one of the fourteen collision-search slots, from 0x4033b0."""
    row_left_step = f32(row_left_step)
    row_right_step = f32(row_right_step)
    offset = f32(offset)
    if offset >= 0.0:
        step = row_right_step
        slot = 7
        adjusted = offset - step * 0.5
    else:
        step = row_left_step
        slot = 6
        adjusted = step * 0.5 + offset
    if step == 0.0:
        raise ValueError('collision-search spacing must be nonzero')
    # 0x4033b0 stores the quotient to float32 before FISTP. The default
    # supported x87 mode rounds that stored value to nearest, ties to even.
    slot += round(f32(adjusted / step))
    return min(max(slot, 0), 13)


def collision_search_bit(mask, index):
    """Port 0x403320's clamped, high-bit-first search-mask test."""
    slot = min(max(index + 1, 0), 15)
    return (mask & 0xffffffff) & (1 << (15 - slot))


def reset_track_attribute(table, row_index, attribute, *, default_value):
    """Read the reset helper's per-row track byte from explicit table data.

    This is the memory behavior of 0x403000. ``attribute`` selects byte +0x18
    when zero and +0x19 otherwise; a null original table returns its global
    default byte. Rows are supplied as a bounded byte view, never as an
    original process pointer.
    """
    if type(row_index) is not int or type(attribute) is not int:
        raise ValueError('track row and attribute selector must be integers')
    if type(default_value) is not int or not 0 <= default_value <= 0xff:
        raise ValueError('default track attribute must be a byte')
    if table is None:
        return default_value
    view = memoryview(table).cast('B')
    offset = row_index * 0x1c + (0x18 if attribute == 0 else 0x19)
    if row_index < 0 or offset < 0 or offset >= len(view):
        raise ValueError('track attribute row is outside the supplied table')
    return view[offset]


def collision_fallback_offset(table, row_index, alternate_side):
    """Read the fallback search offset from original helper 0x403070.

    Rows are 0x1c bytes. The normal offset is a float at +0x10; the
    alternate-side offset is at +0x14. A null global table returns 0.0.
    """
    if type(row_index) is not int or not 0 <= row_index <= 0xffffffff:
        raise ValueError('fallback row index must be uint32')
    view = None if table is None else memoryview(table).cast('B')
    if view is None:
        return 0.0
    offset = row_index * 0x1c + (0x14 if alternate_side else 0x10)
    if offset + 4 > len(view):
        raise ValueError('fallback row is outside the supplied table')
    return struct.unpack_from('<f', view, offset)[0]
