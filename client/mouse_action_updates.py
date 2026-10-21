"""Action edges and the 32-frame input transition ring from 0x4ad6f0.

The caller supplies the existing game's action-state resolver and the three
device-mapping values. This keeps configured action callbacks explicit while
recovering the deterministic game-side edge, priority, and ring behavior.
"""
from dataclasses import dataclass


UINT32_MASK = 0xffffffff
RING_MASK = 0x1f
ACTION_WORD_COUNT = 32
EDGE_ACTION_COUNT = 12


@dataclass
class MouseActionUpdateState:
    """Persistent action-edge and transition-ring globals used by the handler."""

    edge_latches: bytearray
    ring_words: list
    ring_counter: int = 0
    notification_suppressed: int = 0
    notification_payload: bytes = b''
    button_transition_flags: int = 0


def update_priority_edges(action_words, edge_latches, *, dispatch_action):
    """Update the 12 priority-ordered rising-edge latches.

    Returns the first newly-pressed slot (1..12), or zero. Action zero skips
    its callback and leaves that slot's latch unchanged, matching the native
    loop. Nonzero actions clear a latch when inactive and set it when active.
    """
    if not isinstance(action_words, (bytes, bytearray, memoryview)) \
            or len(action_words) < EDGE_ACTION_COUNT * 4:
        raise ValueError('priority action image must contain twelve dwords')
    if not isinstance(edge_latches, bytearray) or len(edge_latches) < 13:
        raise ValueError('edge latch image must contain indices zero through twelve')
    if not callable(dispatch_action):
        raise ValueError('priority action dispatcher is required')

    for index in range(1, EDGE_ACTION_COUNT + 1):
        offset = (index - 1) * 4
        action = int.from_bytes(action_words[offset:offset + 4], 'little')
        if action == 0:
            continue
        result = dispatch_action(action)
        if type(result) is not int or not 0 <= result <= UINT32_MASK:
            raise ValueError('priority callback result must be uint32')
        if result < 0x80000000 and result != 0:
            if edge_latches[index] == 0:
                edge_latches[index] = 1
                return index
        else:
            edge_latches[index] = 0
    return 0


def update_special_action_edges(edge_latches, *, direction_enabled,
                                direction_codes, direction_values):
    """Update the type-5/type-6 rising edges before priority key scanning.

    Type 5 wins when both are newly pressed; in that case type 6 is not
    sampled during this pass, matching the native early branch. The two
    latches are bytes 1 and 2 of the shared edge-latch image.
    """
    if not isinstance(edge_latches, bytearray) or len(edge_latches) < 3:
        raise ValueError('edge latch image must contain indices one and two')
    if type(direction_enabled) is not bool:
        raise ValueError('direction_enabled must be bool')
    if len(direction_codes) != 3 or len(direction_values) != 3:
        raise ValueError('three mapped direction records are required')

    def active(value):
        return direction_enabled and any(
            enabled and mapped == value
            for enabled, mapped in zip(direction_codes, direction_values))

    type_five = active(5)
    if type_five:
        if edge_latches[1] == 0:
            edge_latches[1] = 1
            return 1
    else:
        edge_latches[1] = 0

    type_six = active(6)
    if type_six:
        if edge_latches[2] == 0:
            edge_latches[2] = 1
            return 2
    else:
        edge_latches[2] = 0
    return 0


def build_transition_mask(action_words, *, action_active, direction_enabled,
                          direction_codes, direction_values):
    """Build one 32-action transition word, preserving native bit ordering.

    ``action_words`` are read in increasing address order. The first becomes
    output bit zero and the last becomes bit 31. Four final slots additionally
    test mapped direction values 12, 11, 10, and 9 when direction input is
    enabled. Action resolution remains a callback because configuration may
    dispatch to game or platform-specific handlers.
    """
    if not isinstance(action_words, (bytes, bytearray, memoryview)) \
            or len(action_words) < ACTION_WORD_COUNT * 4:
        raise ValueError('transition action image must contain 32 dwords')
    if type(direction_enabled) is not bool:
        raise ValueError('direction_enabled must be bool')
    if not isinstance(direction_codes, (tuple, list)) or len(direction_codes) != 3:
        raise ValueError('three direction-action enable values are required')
    if not isinstance(direction_values, (tuple, list)) or len(direction_values) != 3:
        raise ValueError('three mapped direction values are required')
    if not callable(action_active):
        raise ValueError('action-state resolver is required')

    result = 0
    for index in range(ACTION_WORD_COUNT):
        result >>= 1
        offset = index * 4
        action = int.from_bytes(action_words[offset:offset + 4], 'little')
        if action != 0 and action_active(action) != 0:
            result |= 0x80000000

    # The native loop's switch cases map direction values 12, 9, 10, 11
    # to mask bits 27, 28, 29, 30 respectively.
    if direction_enabled:
        for slot, mapped_value in enumerate((12, 9, 10, 11)):
            if any(enabled and value == mapped_value
                   for enabled, value in zip(direction_codes, direction_values)):
                result |= 1 << (27 + slot)
    return result & UINT32_MASK


def apply_transition_frame(state, priority_action_words, transition_action_words, *, action_active,
                           direction_enabled=False, direction_codes=(False, False, False),
                           direction_values=(0, 0, 0), notify=None,
                           update_edges=True, priority_action_active=None):
    """Insert the next transition word and issue the optional native notify.

    The native counter increments before selecting its 32-entry slot. Its
    unsigned increment wraps at 32 bits; the slot uses only the low five bits.
    Notification is skipped whenever the environment suppression byte is set.
    """
    if not isinstance(state, MouseActionUpdateState):
        raise ValueError('MouseActionUpdateState is required')
    if not isinstance(state.edge_latches, bytearray) or len(state.edge_latches) < 13:
        raise ValueError('edge latch image must contain indices zero through twelve')
    if not isinstance(state.ring_words, list) or len(state.ring_words) < 32:
        raise ValueError('transition ring must contain 32 dwords')
    if type(state.ring_counter) is not int or not 0 <= state.ring_counter <= UINT32_MASK:
        raise ValueError('ring counter must be uint32')
    if type(state.notification_suppressed) is not int or not 0 <= state.notification_suppressed <= 255:
        raise ValueError('notification suppression must be a byte')

    if type(state.button_transition_flags) is not int or not 0 <= state.button_transition_flags <= 255:
        raise ValueError('button transition flags must be a byte')
    if type(update_edges) is not bool:
        raise ValueError('update_edges must be bool')
    edge = 0
    if update_edges:
        if direction_enabled:
            edge = update_special_action_edges(
                state.edge_latches, direction_enabled=True,
                direction_codes=direction_codes, direction_values=direction_values)
        if edge == 0:
            has_priority_actions = any(priority_action_words[:EDGE_ACTION_COUNT * 4])
            if has_priority_actions and not callable(priority_action_active):
                raise ValueError('priority action dispatcher is required for nonzero actions')
            if callable(priority_action_active):
                edge = update_priority_edges(priority_action_words, state.edge_latches,
                                             dispatch_action=priority_action_active)
    word = build_transition_mask(
        transition_action_words, action_active=action_active,
        direction_enabled=direction_enabled,
        direction_codes=direction_codes, direction_values=direction_values)
    next_counter = (state.ring_counter + 1) & UINT32_MASK
    slot = next_counter & RING_MASK
    state.ring_words[slot] = word
    state.ring_counter = next_counter
    if len(state.notification_payload) >= 5:
        payload = bytearray(state.notification_payload)
        payload[3] = state.button_transition_flags
        payload[4] = edge
        state.notification_payload = bytes(payload)
    if not state.notification_suppressed:
        if notify is not None:
            if not callable(notify):
                raise ValueError('notify must be callable')
            notify(bytes(state.notification_payload))
    return edge, word, slot
