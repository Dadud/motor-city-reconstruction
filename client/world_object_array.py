"""Active world-object array dispatch at original callback entry 0x426730."""
WORLD_OBJECT_STRIDE = 0x4f8


def update_active_world_objects(base_address, active_flags, update_object):
    """Walk the 0x4f8-byte object array and call 0x520250 for active rows."""
    if type(base_address) is not int or not 0 < base_address <= 0xffffffff:
        raise ValueError('world-object base must be a non-null uint32')
    if not callable(update_object):
        raise ValueError('the 0x520250 object callback is required')
    for index, active in enumerate(active_flags):
        if type(active) is not bool:
            raise ValueError('world-object active flag must be boolean')
        address = base_address + index * WORLD_OBJECT_STRIDE
        if address > 0xffffffff:
            raise ValueError('world-object row address overflows uint32')
        if active:
            update_object(address)
