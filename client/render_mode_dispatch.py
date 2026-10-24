"""Explicit state model for the client's shared render-mode dispatcher."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RenderDispatchState:
    cached_mode: int
    capability_bit_4: int
    capability_bit_2: int
    capability_bit_0x10000: int
    capability_bit_0x20000_a: int
    capability_bit_0x20000_b: int
    capability_both_0x30000: int
    capability_bit0: int
    callback_context_b: int
    vertex_stride: int
    vertex_format: int
    primary_callbacks: tuple[int, ...]
    secondary_callbacks: tuple[int, ...]
    render_flags: int = 0
    primary_callback: int = 0
    secondary_callback: int = 0
    draw_context_a: int = 0
    draw_context_b: int = 0
    draw_param3: int = 0
    draw_param4: int = 0

    def __post_init__(self):
        scalar_names = (
            'cached_mode', 'capability_bit_4', 'capability_bit_2',
            'capability_bit_0x10000', 'capability_bit_0x20000_a',
            'capability_bit_0x20000_b', 'capability_both_0x30000',
            'capability_bit0',
            'callback_context_b', 'vertex_stride',
            'vertex_format', 'render_flags', 'primary_callback',
            'secondary_callback', 'draw_context_a', 'draw_context_b',
            'draw_param3', 'draw_param4')
        for name in scalar_names:
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 0xffffffff:
                raise ValueError(f'{name} must be an unsigned 32-bit word')
        for name, size in (('primary_callbacks', 32), ('secondary_callbacks', 8)):
            values = tuple(getattr(self, name))
            if len(values) != size or any(type(v) is not int or not 0 <= v <= 0xffffffff
                                          for v in values):
                raise ValueError(f'{name} must contain {size} unsigned words')
            object.__setattr__(self, name, values)


def dispatch_render_mode(state, mode, vertex_count, vertices, indices):
    """Translate 0x6f28f0's flag filtering, table selection and draw dispatch.

    Return ``(result, updated_state, callback_events)``. Callback events preserve
    the original argument order and are kept explicit instead of running a GPU.
    """
    if not isinstance(state, RenderDispatchState):
        raise TypeError('state must be a RenderDispatchState')
    words = (mode, vertex_count, vertices, indices)
    if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in words):
        raise ValueError('dispatch arguments must be unsigned 32-bit words')
    current = state
    active_mode = mode
    if state.cached_mode != mode:
        if state.capability_bit_4 == 0:
            active_mode &= 0xfffffffb
        if state.capability_bit_2 == 0:
            active_mode &= 0xfffffffd
        if state.capability_bit_0x10000 == 0:
            active_mode &= 0xfffeffff
        stride = state.vertex_stride or 0x0c
        vertex_format = state.vertex_format or 0x20
        if state.capability_bit_0x20000_a == 0 or state.capability_bit_0x20000_b == 0:
            active_mode &= 0xfffdffff
        if (active_mode & 0x30000) == 0x30000 and state.capability_both_0x30000 == 0:
            active_mode &= 0xfffdffff
        if (active_mode & 1) and (active_mode & 0x20000):
            active_mode &= 0xfffdffff
        if state.capability_bit0 == 0:
            active_mode &= 0xfffffffe
        primary = state.primary_callbacks[active_mode & 0x1f]
        secondary_index = ((active_mode >> 15) & 7) | (active_mode & 1)
        secondary = (state.secondary_callbacks[secondary_index]
                     if active_mode & 0x30000 else 0)
        current = replace(state, cached_mode=active_mode, vertex_stride=stride,
                          vertex_format=vertex_format,
                          render_flags=active_mode & 0x10000000,
                          primary_callback=primary, secondary_callback=secondary)
    events = []
    if vertex_count > 0 and vertices != 0 and indices != 0:
        if current.primary_callback:
            current = replace(current, draw_context_a=current.capability_bit0,
                              draw_context_b=current.callback_context_b,
                              draw_param3=vertices, draw_param4=indices)
            events.append(('primary', vertex_count, vertices, indices))
        if current.secondary_callback:
            events.append(('secondary', vertex_count, indices))
        return active_mode, current, tuple(events)
    return 0, current, ()

