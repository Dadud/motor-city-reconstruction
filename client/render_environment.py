"""Small state transitions for the legacy environment renderer."""


def set_environment_activity(primary, secondary, *, primary_enabled=True):
    """Write the active flags at +0x3c of the two optional scene objects.

    This models the complete body of 0x478950. The global-to-object pointer
    selection remains the caller's responsibility.
    """
    for pointer in (primary, secondary):
        if type(pointer) is not int or pointer < 0:
            raise ValueError('environment object addresses must be nonnegative integers')
    return ((primary, int(bool(primary_enabled))) if primary else None,
            (secondary, 0) if secondary else None)


def release_environment_objects(objects):
    """Return non-null frees and zeroed globals for the 0x478980 cleanup."""
    if not isinstance(objects,(tuple,list)) or len(objects)!=4:
        raise ValueError('environment cleanup requires four object pointers')
    if any(type(pointer) is not int or not 0<=pointer<=0xffffffff
           for pointer in objects):
        raise ValueError('environment pointers must be unsigned words')
    return tuple(pointer for pointer in objects if pointer), (0,0,0,0)
