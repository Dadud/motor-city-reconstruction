"""Renderer mode cache state translated from the client math/runtime library."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderCapabilityState:
    """Subset of renderer globals written by 0x6f19d0/1a00/1a70."""
    capability_4: int = 0
    capability_2: int = 0
    capability_4_dirty: int = 0
    capability_2_dirty: int = 0
    mode_cache: int = 0
    vertex_format_cache: int = 0

    def __post_init__(self):
        values = (self.capability_4, self.capability_2,
                  self.capability_4_dirty, self.capability_2_dirty,
                  self.mode_cache, self.vertex_format_cache)
        if any(type(value) is not int or not 0 <= value <= 0xffffffff
               for value in values):
            raise ValueError('renderer capability state requires uint32 words')


def set_capability_4(state, value):
    """Translate 0x6f19d0 and return the old value plus new global state."""
    return _set_capability(state, value, 4)


def set_capability_2(state, value):
    """Translate 0x6f1a00 and return the old value plus new global state."""
    return _set_capability(state, value, 2)


def _set_capability(state, value, bit):
    if not isinstance(state, RenderCapabilityState):
        raise TypeError('state must be RenderCapabilityState')
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('capability value must be uint32')
    if bit == 4:
        old = state.capability_4
        return old, RenderCapabilityState(
            value, state.capability_2,
            1 if value else state.capability_4_dirty,
            state.capability_2_dirty,
            0xffffffff if value == 0 else state.mode_cache,
            state.vertex_format_cache)
    old = state.capability_2
    return old, RenderCapabilityState(
        state.capability_4, value,
        state.capability_4_dirty,
        1 if value else state.capability_2_dirty,
        0xffffffff if value == 0 else state.mode_cache,
        state.vertex_format_cache)


def set_vertex_format_cache(state, value):
    """Translate 0x6f1a70 and return old vertex format plus new state."""
    if not isinstance(state, RenderCapabilityState):
        raise TypeError('state must be RenderCapabilityState')
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('vertex format cache must be uint32')
    return state.vertex_format_cache, RenderCapabilityState(
        state.capability_4, state.capability_2,
        state.capability_4_dirty, state.capability_2_dirty,
        0xffffffff if value == 0 else state.mode_cache,
        value)


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
