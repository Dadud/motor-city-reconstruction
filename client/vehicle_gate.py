"""Original 0x55cfc0 result from explicit interface operation-5 observations.

The virtual-interface producer and current-counter scheduler remain external.
No invariant across repeated calls is implied by this pure helper.
"""


def _signed(value):
    if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
        raise ValueError('signed int32 counter observation required')
    return value


def vehicle_gate_result(owner_present: bool, current_counter: int, interface_result=None):
    if type(owner_present) is not bool:
        raise ValueError('boolean owner-presence observation required')
    current_counter = _signed(current_counter)
    if not owner_present:
        return False
    return current_counter >= _signed(interface_result)
