"""Renderer mode cache state translated from the client math/runtime library."""


def replace_render_mode(mode_cache, zero_mode_cache, requested_mode):
    """Translate 0x6f1a30's two-global render mode replacement.

    Returns ``(previous_mode, new_mode, zero_mode_cache)``. Setting the mode to
    zero invalidates the dependent cache with the native all-bits-one sentinel;
    nonzero modes preserve that cache word. Values are raw unsigned 32-bit words.
    """
    values = (mode_cache, zero_mode_cache, requested_mode)
    if any(type(value) is not int or not 0 <= value <= 0xffffffff
           for value in values):
        raise ValueError('render mode state requires unsigned 32-bit words')
    return (mode_cache, requested_mode,
            0xffffffff if requested_mode == 0 else zero_mode_cache)


def select_rectangle_texture_state(cached_texture_state):
    """Translate the 0x46abd0(0) state-selection call used by rectangles.

    A zero cache is already selected and produces no callback. Any other
    cached word invokes THRASH_settexture(0), then replaces the cache with 0.
    The function's nonzero texture-state branches are not covered here.
    Returns ``(new_cache, callback_arguments)``.
    """
    if (type(cached_texture_state) is not int or
            not 0<=cached_texture_state<=0xffffffff):
        raise ValueError('cached texture state must be an unsigned 32-bit word')
    if cached_texture_state==0:
        return 0,()
    return 0,(0,)
