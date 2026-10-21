"""Keyboard action thresholds and direction-key predicates."""
import struct


ACTION_TABLE_SIZE = 0x7FC
KEY_STATE_COUNT = 0x80
ACTIVE = 0xff


def action_progress_value(action, action_table):
    """Port 0x460890's signed action-progress threshold calculation."""
    if type(action) is not int or not 0 <= action <= 0xffffffff:
        raise ValueError('action word must be uint32')
    if not isinstance(action_table, (bytes, bytearray, memoryview)) \
            or len(action_table) < ACTION_TABLE_SIZE:
        raise ValueError('action table must expose 511 dwords')

    record_index = (action >> 28) * 0x21 + ((action >> 24) & 0x0f)
    record = struct.unpack_from('<i', action_table, record_index * 4)[0]
    current = record >> 8
    lower = (action >> 16) & 0xff
    upper = (action >> 8) & 0xff

    if lower < upper:
        if lower <= current:
            if upper < current:
                return ACTIVE
            if lower == 0:
                return current
            return (current - lower) * 2
    elif upper < lower:
        if current < upper:
            return ACTIVE
        if current <= lower:
            if lower == 0xff:
                return 0xff - current
            return (lower - current) * 2
    return 0


def is_keyboard_action_active(action, *, key_states, direction_flags,
                              action_table, query_other_action=None):
    """Port 0x460950's local key/direction cases and threshold subcall.

    Non-type-1/4 action words dispatch through an external input-state table;
    that path is an explicit callback and is required only for those words.
    """
    if type(action) is not int or not 0 <= action <= 0xffffffff:
        raise ValueError('action word must be uint32')
    if not isinstance(key_states, (bytes, bytearray, memoryview)) \
            or len(key_states) < KEY_STATE_COUNT:
        raise ValueError('keyboard state must contain 128 bytes')
    if type(direction_flags) is not int or not 0 <= direction_flags <= 0xffffffff:
        raise ValueError('direction mask must be uint32')

    action_type = action & 0xff
    if action_type == 4:
        key = (action >> 8) & 0xff
        if key_states[key & 0x7f] != 0:
            return ACTIVE
        if direction_flags == 0:
            return 0
        key_flag = {
            0xcb: 0x04, 0xcd: 0x08, 0xc8: 0x01,
            0xd0: 0x02, 0x1c: 0x10,
        }.get(key, 0)
        return ACTIVE if direction_flags & key_flag else 0

    if action_type == 1:
        return ACTIVE if action_progress_value(action, action_table) > 0x80 else 0

    if not callable(query_other_action):
        raise ValueError('other action-state callback is required')
    return query_other_action(action)
