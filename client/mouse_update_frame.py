"""Connected selector-six, cursor-motion, mapping, and action-frame update."""
from dataclasses import dataclass

from .mouse_action_updates import MouseActionUpdateState, apply_transition_frame
from .mouse_cursor_motion import MouseCursorMotionParameters, update_mouse_cursor_motion
from .mouse_mapping_snapshot import MouseMappingSource, publish_mouse_mapping_snapshot
from .mouse_fallback_state import build_fallback_mouse_outputs
from .mouse_state_get import MouseGetStateContext, get_mouse_state


@dataclass(frozen=True)
class MouseInputFrameResult:
    cursor: object
    motion: object
    mapping: object
    action_edge: int
    transition_word: int
    ring_slot: int


def update_mouse_input_frame(context, action_state, priority_actions,
                             transition_actions, *, motion_parameters,
                             mapping_words, action_active,
                             priority_action_active, query_absolute_cursor,
                             ensure_device_acquired, read_device_state,
                             report_error, set_mouse_state, notify=None):
    """Run the recovered active mouse-frame pipeline in original call order.

    Selector-six access feeds the existing 0x6f0a30/DirectInput bridge or the
    absolute cursor branch. The returned X sample then feeds the recovered
    motion calculation, button bytes feed the controller-mapping globals, and
    those globals feed the type-5/type-6/action transition ring.

    Device acquisition/read, cursor positioning, action callbacks and notify
    remain injected host/game boundaries. A null selector-six result stops the
    pipeline, matching the native prelude's null-state branch.
    """
    if not isinstance(context, MouseGetStateContext):
        raise ValueError('MouseGetStateContext is required')
    if not isinstance(action_state, MouseActionUpdateState):
        raise ValueError('MouseActionUpdateState is required')
    if not isinstance(motion_parameters, MouseCursorMotionParameters):
        raise ValueError('MouseCursorMotionParameters is required')
    if not callable(set_mouse_state):
        raise ValueError('mouse state setter is required')
    if len(action_state.notification_payload) < 5:
        raise ValueError('action notification payload must contain five bytes')
    if not isinstance(mapping_words, (tuple, list)) or len(mapping_words) != 4:
        raise ValueError('four mapped action words are required')

    cursor = get_mouse_state(
        6, context,
        query_device_info=lambda _buffer: 0,
        query_absolute_cursor=query_absolute_cursor,
        ensure_device_acquired=ensure_device_acquired,
        read_device_state=read_device_state,
        report_error=report_error)
    if cursor is None:
        return None

    motion = update_mouse_cursor_motion(cursor.x, motion_parameters)
    for selector, value in motion.setter_calls:
        set_mouse_state(selector, value)

    state_record = bytearray(0x13)
    state_record[0x10] = cursor.button0 & 0xff
    state_record[0x11] = cursor.button1 & 0xff
    state_record[0x12] = cursor.button2 & 0xff
    mapping = publish_mouse_mapping_snapshot(
        MouseMappingSource(bytes(state_record), *mapping_words))
    direction_codes = (bool(mapping.value_9e1654),
                       bool(mapping.value_9e165c),
                       bool(mapping.value_9e1658))
    direction_values = (mapping.value_9e1648,
                        mapping.value_9e1650,
                        mapping.value_9e164c)
    edge, word, slot = apply_transition_frame(
        action_state, priority_actions, transition_actions,
        action_active=action_active,
        priority_action_active=priority_action_active,
        direction_enabled=True, direction_codes=direction_codes,
        direction_values=direction_values, notify=notify)
    return MouseInputFrameResult(cursor, motion, mapping, edge, word, slot)


def update_mouse_fallback_frame(action_state, priority_actions,
                                transition_actions, fallback_actions, *,
                                fallback_action_dispatch, action_active,
                                priority_action_active, notify=None):
    """Run the no-controller/no-mouse path and then the shared action tail.

    This branch does not acquire selector six or overwrite the last mouse
    mapping globals. Its four output bytes are rebuilt from the configured
    fallback actions; direction overlays are gated off before the shared
    priority-edge and transition-ring pass.
    """
    if not isinstance(action_state, MouseActionUpdateState):
        raise ValueError('MouseActionUpdateState is required')
    if len(action_state.notification_payload) < 5:
        raise ValueError('action notification payload must contain five bytes')
    fallback = build_fallback_mouse_outputs(
        fallback_actions, dispatch_action=fallback_action_dispatch)
    action_state.button_transition_flags = fallback.transition_flags
    payload = bytearray(action_state.notification_payload)
    if len(payload) >= 5:
        payload[0] = fallback.cursor_delta
        payload[1] = fallback.button_state_0
        payload[2] = fallback.button_state_1
        action_state.notification_payload = bytes(payload)
    edge, word, slot = apply_transition_frame(
        action_state, priority_actions, transition_actions,
        action_active=action_active,
        priority_action_active=priority_action_active,
        direction_enabled=False, notify=notify)
    return fallback, edge, word, slot
