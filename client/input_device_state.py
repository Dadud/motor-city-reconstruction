"""DirectInput device-state wrapper used by the mouse getter."""


def read_input_device_state(device, output, size, *, ensure_acquired,
                            get_state):
    """Port 0x6f0a30 around the device acquire/read services.

    Acquisition is attempted first. The read provider receives the original
    argument order ``(device, size, output)``; a nonzero status clears exactly
    the requested output range before returning that status.
    """
    if type(device) is not int or not 0 <= device <= 0xffffffff:
        raise ValueError('device identity must be uint32')
    if not isinstance(output, bytearray):
        raise ValueError('mutable device-state output is required')
    if type(size) is not int or not 0 <= size <= len(output):
        raise ValueError('state size must fit the output buffer')
    if not callable(ensure_acquired) or not callable(get_state):
        raise ValueError('device acquire and state-read services are required')

    ensure_acquired(device)
    status = get_state(device, size, memoryview(output)[:size])
    if type(status) is not int or not 0 <= status <= 0xffffffff:
        raise ValueError('device-state status must be uint32')
    if status != 0:
        output[:size] = bytes(size)
    return status
