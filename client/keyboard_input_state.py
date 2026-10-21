"""Keyboard mapping/state pass used by the cursor update handler."""
from dataclasses import dataclass
import struct


KEY_LIMIT = 0x80
KEY_RECORD_SIZE = 0x84
KEY_RECORD_COUNT = KEY_LIMIT
KEY_RECORDS_SIZE = KEY_RECORD_SIZE * KEY_RECORD_COUNT


@dataclass
class KeyboardInputState:
    """Bounded views of the keyboard globals consumed by 0x4606b0."""

    key_map: bytes
    records: bytearray
    input_mode: int
    environment_mode: int
    suppression_key_state: int
    direction_flags: int = 0


def update_keyboard_direction_flags(state, *, lookup_record):
    """Port 0x4606b0, with the original record resolver as an explicit bridge.

    ``lookup_record(key, record_view)`` corresponds to the game's record lookup
    path. It returns truthy when the record was populated and available. A
    missing record is cleared and receives eight 0x7f defaults at +0x50.
    """
    if not isinstance(state, KeyboardInputState):
        raise ValueError('KeyboardInputState is required')
    if not isinstance(state.key_map, (bytes, bytearray, memoryview)):
        raise ValueError('key map must be a byte view')
    if len(state.key_map) == 0 or not any(key >= KEY_LIMIT for key in state.key_map):
        raise ValueError('key map must contain an unsigned sentinel at or above 0x80')
    if not isinstance(state.records, bytearray) or len(state.records) < KEY_RECORDS_SIZE:
        raise ValueError('record table must contain 128 records of 0x84 bytes')
    for value in (state.input_mode, state.environment_mode,
                  state.suppression_key_state):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('keyboard globals must be uint32 values')
    if not callable(lookup_record):
        raise ValueError('record lookup bridge is required')

    flags = 0
    state.direction_flags = 0
    mode_uses_keyboard = state.input_mode in (5, 6)
    for key in state.key_map:
        if key >= KEY_LIMIT:
            break
        offset = key * KEY_RECORD_SIZE
        row = memoryview(state.records)[offset:offset + KEY_RECORD_SIZE]
        available = bool(lookup_record(key, row))
        if not available:
            row[:] = b'\0' * KEY_RECORD_SIZE
            for slot in range(8):
                struct.pack_into('<I', row, 0x50 + slot * 4, 0x7f)
            continue

        if (mode_uses_keyboard or state.environment_mode != 0) and flags == 0 \
                and state.suppression_key_state == 0:
            first, second = struct.unpack_from('<ii', row, 0)
            third = struct.unpack_from('<i', row, 0x70)[0]
            if first < 0x7f:
                flags |= 4
            elif first > 0x17d:
                flags |= 8
            if second < 0x7f:
                flags |= 1
            elif second > 0x7f:
                flags |= 2
            if third != 0:
                flags |= 0x10

    state.direction_flags = flags
    return flags
