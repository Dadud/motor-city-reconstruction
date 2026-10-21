"""Path-change state machine from original owner reset helper 0x43f090."""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class PathResetGlobals:
    path_count: int
    wrap_reference: int
    secondary_reference: int
    multi_segment: int
    step_threshold: int
    designated_mode: int
    environment_mode: int

    def __post_init__(self):
        values = (self.path_count, self.wrap_reference,
                  self.secondary_reference, self.multi_segment,
                  self.step_threshold, self.designated_mode,
                  self.environment_mode)
        if any(type(value) is not int for value in values):
            raise ValueError('reset globals must be integer observations')
        if self.path_count <= 0:
            raise ValueError('path count must be positive')


def advance_reset_axis(record):
    """Port child 0x468cc0: toggle the two path/reset direction flags."""
    if not isinstance(record, bytearray) or len(record) < 0xdf8:
        raise ValueError('mutable owner image through +0xdf7 is required')
    flags = struct.unpack_from('<I', record, 0xdf4)[0]
    struct.pack_into('<I', record, 0xdf4, flags ^ 0xc00)
    return record


def update_path_reset_state(record, *, globals_, interface_query,
                            notify_track_change, advance_state):
    """Port 0x43f090 with its interface and stateful children explicit.

    ``interface_query`` observes the original virtual (0x16, owner) gate;
    ``notify_track_change`` represents 0x406a50 and ``advance_state`` 0x468cc0.
    Their mutations are not guessed by this state-machine port.
    """
    if not isinstance(record, bytearray) or len(record) < 0x1c98:
        raise ValueError('a mutable owner image through +0x1c97 is required')
    if not isinstance(globals_, PathResetGlobals):
        raise ValueError('observed path-reset globals are required')
    if not all(callable(fn) for fn in
               (interface_query, notify_track_change, advance_state)):
        raise ValueError('all three 0x43f090 child callbacks are required')

    old_index = struct.unpack_from('<i', record, 0x364)[0]
    new_index = struct.unpack_from('<i', record, 0x370)[0]
    if interface_query(0x16, record) != 0:
        return record
    if new_index == old_index:
        return record

    third = globals_.path_count // 3
    designated = struct.unpack_from('<i', record, 0x464)[0] == globals_.designated_mode
    struct.pack_into('<i', record, 0x364, new_index)
    if designated and globals_.environment_mode == 0:
        notify_track_change(new_index, struct.unpack_from('<i', record, 0x47c)[0])

    next_primary = new_index - globals_.wrap_reference
    prior_primary = old_index - globals_.wrap_reference
    if next_primary < 0:
        next_primary += globals_.path_count
    if prior_primary < 0:
        prior_primary += globals_.path_count
    if next_primary < third and third * 2 < prior_primary:
        direction_primary = 1
    elif third * 2 < next_primary and prior_primary < third:
        direction_primary = -1
    else:
        direction_primary = 0

    flags = struct.unpack_from('<I', record, 0xdf4)[0]
    if flags & 0x800:
        direction_primary = -direction_primary
    direction = direction_primary

    if globals_.wrap_reference != globals_.secondary_reference:
        next_secondary = new_index - globals_.secondary_reference
        prior_secondary = old_index - globals_.secondary_reference
        if next_secondary < 0:
            next_secondary += globals_.path_count
        if prior_secondary < 0:
            prior_secondary += globals_.path_count
        direction = 0
        if next_secondary < third and third * 2 < prior_secondary:
            direction = 1
        elif third * 2 < next_secondary and prior_secondary < third:
            direction = -1
        if flags & 0x800:
            direction = -direction

    if direction_primary == 0 and direction == 0:
        return record

    current = struct.unpack_from('<i', record, 0x480)[0]
    counter = struct.unpack_from('<i', record, 0x47c)[0]
    if globals_.multi_segment != 0:
        counter_direction = direction_primary
        if flags & 0x400:
            counter_direction, direction = direction, direction_primary
        if current == 0:
            if direction > 0:
                counter += 1
                struct.pack_into('<i', record, 0x47c, counter)
                if globals_.step_threshold <= counter:
                    struct.pack_into('<I', record, 0xdf4, flags | 0x1000)
                    return record
                struct.pack_into('<i', record, 0x480, 1)
                advance_reset_axis(record)
                advance_state(record)
                return record
            if counter_direction >= 0:
                return record
            struct.pack_into('<i', record, 0x480, 1)
            return record
        if counter_direction < 0:
            struct.pack_into('<i', record, 0x480, current + 1)
            return record
        if counter_direction < 1:
            return record
        struct.pack_into('<i', record, 0x480, current - 1)
        return record

    if direction_primary < 0:
        current += 1
    elif direction_primary > 0:
        if current == 0:
            counter += 1
            struct.pack_into('<i', record, 0x47c, counter)
            if globals_.step_threshold <= counter:
                struct.pack_into('<I', record, 0xdf4, flags | 0x1000)
        else:
            current -= 1
    struct.pack_into('<i', record, 0x480, current)
    if (direction > 0 and
            globals_.wrap_reference != globals_.secondary_reference and
            counter - current == globals_.step_threshold - 1):
        updated_flags = struct.unpack_from('<I', record, 0xdf4)[0]
        struct.pack_into('<I', record, 0xdf4, updated_flags | 0x1000)
    return record
