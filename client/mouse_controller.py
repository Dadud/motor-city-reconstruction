"""Small cursor-control state machine used by the game reset path."""


def clamp_i32(value, minimum, maximum):
    """Port 0x6f1380's ordered signed comparisons, including inverted bounds."""
    if any(type(item) is not int or not -(1 << 31) <= item < (1 << 31)
           for item in (value, minimum, maximum)):
        raise ValueError('clamp inputs must be signed 32-bit integers')
    if value < minimum:
        value = minimum
    if maximum < value:
        value = maximum
    return value


def cursor_control_ready(enabled, initialized):
    """Port 0x4ad6a0's readiness predicate."""
    return bool(enabled and initialized)


def cursor_reset_action(*, enabled, initialized, input_mode, environment_mode,
                        x, y, set_state):
    """Port 0x4ad4a0, with selector 3/4 routed to the mouse setter."""
    if not cursor_control_ready(enabled, initialized):
        return False
    if environment_mode != 0:
        return False
    if input_mode in (4, 5):
        return False
    if set_state(3, x) is False:
        return False
    if set_state(4, y) is False:
        return False
    return True
