"""Fallback action dispatch used when the controller mouse path is inactive."""
from dataclasses import dataclass


UINT32_MASK = 0xffffffff


@dataclass(frozen=True)
class MouseFallbackOutputs:
    cursor_delta: int
    button_state_0: int
    button_state_1: int
    transition_flags: int
    dispatch_trace: tuple


def _signed32(value):
    value &= UINT32_MASK
    return value - 0x100000000 if value & 0x80000000 else value


def build_fallback_mouse_outputs(action_words, *, dispatch_action):
    """Port the inactive branch at 0x4adc28..0x4add65.

    The first four configured actions dispatch unconditionally. The remaining
    four dispatch only when their low type byte is nonzero. The first pair
    produce the signed half-difference byte; outputs three/four are truncated
    to bytes. Callback implementation remains the caller's boundary.
    """
    if not isinstance(action_words, (bytes, bytearray, memoryview)) \
            or len(action_words) < 32:
        raise ValueError('fallback action image must contain eight dwords')
    if not callable(dispatch_action):
        raise ValueError('fallback action dispatcher is required')
    words = tuple(int.from_bytes(action_words[offset:offset + 4], 'little')
                  for offset in range(0, 32, 4))
    results = []
    trace = []
    for index, word in enumerate(words):
        if index >= 4 and (word & 0xff) == 0:
            results.append(0)
            continue
        result = dispatch_action(word)
        if type(result) is not int or not 0 <= result <= UINT32_MASK:
            raise ValueError('fallback dispatch result must be uint32')
        trace.append(word)
        results.append(result)

    flags = 0
    if (words[0] & 0xff) != 1:
        flags = 2
    if (words[1] & 0xff) != 1:
        flags |= 2
    if (words[2] & 0xff) != 1:
        flags |= 4
    if (words[3] & 0xff) != 1:
        flags |= 1
    if (words[4] & 0xff) != 0 and results[4] != 0:
        flags |= 8
    if (words[5] & 0xff) != 0 and results[5] != 0:
        flags |= 0x10
    if (words[6] & 0xff) != 0 and results[6] != 0:
        flags |= 0x20
    if (words[7] & 0xff) != 0 and results[7] != 0:
        flags |= 0x40

    difference = _signed32(results[1]) - _signed32(results[0])
    difference = _signed32(difference) >> 1
    return MouseFallbackOutputs(
        cursor_delta=difference & 0xff,
        button_state_0=results[2] & 0xff,
        button_state_1=results[3] & 0xff,
        transition_flags=flags,
        dispatch_trace=tuple(trace))
