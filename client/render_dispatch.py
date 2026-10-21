"""Portable state wrapper for the 0x6f1320 geometry handoff."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class RenderDispatchState:
    matrix_source: object = None
    position_source: object = None
    output_stride_bytes: int = 0x20
    matrix_dirty: bool = False
    position_dirty: bool = False
    dispatch_cache_valid: bool = True


def dispatch_object_geometry(state: RenderDispatchState, *, vertex_count: int,
                             local_vertices, world_vertices, matrix, position,
                             output_stride_bytes: int, draw: Callable):
    """Set the three global render inputs, dispatch mode 6, then restore them.

    The draw backend receives the original call shape used by 0x6f28f0.
    The source wrapper's temporary state changes are preserved even when an
    injected backend raises, which is a portability guard beyond its C ABI.
    """
    if not isinstance(state, RenderDispatchState):
        raise TypeError('RenderDispatchState required')
    if type(vertex_count) is not int or vertex_count < 0 or type(output_stride_bytes) is not int or output_stride_bytes < 0:
        raise ValueError('vertex count and output stride must be nonnegative integers')
    if not callable(draw):
        raise ValueError('the graphics draw callback is required')

    old_matrix, old_position, old_stride = (
        state.matrix_source, state.position_source, state.output_stride_bytes)

    def set_matrix(value):
        state.matrix_source = value
        if value is None:
            state.dispatch_cache_valid = False
        else:
            state.matrix_dirty = True

    def set_position(value):
        state.position_source = value
        if value is None:
            state.dispatch_cache_valid = False
        else:
            state.position_dirty = True

    try:
        set_matrix(matrix)
        set_position(position)
        state.output_stride_bytes = output_stride_bytes
        if output_stride_bytes == 0:
            state.dispatch_cache_valid = False
        return draw(6, vertex_count, local_vertices, world_vertices,
                    state.matrix_source, state.position_source,
                    state.output_stride_bytes)
    finally:
        set_matrix(old_matrix)
        set_position(old_position)
        state.output_stride_bytes = old_stride
        if old_stride == 0:
            state.dispatch_cache_valid = False
