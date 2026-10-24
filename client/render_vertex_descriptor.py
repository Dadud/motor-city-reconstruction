"""Shared renderer vertex-format query wrapper recovered from the client."""


def query_render_vertex_descriptor(input_word, temporary_mode, output_mask, *,
                                   set_mode, dispatch):
    """Translate 0x6f3090 around its renderer mode and callback dependencies.

    ``set_mode(word)`` returns the previous cached mode. ``dispatch(mode, 1,
    input_word, scratch)`` models the downstream 0x6f28f0 callback, which fills
    four words. ``output_mask`` selects which optional native output pointers
    are present; returned writes are ``(slot, value)`` pairs.
    """
    if type(input_word) is not int or not 0 <= input_word <= 0xffffffff:
        raise ValueError('input_word must be an unsigned 32-bit word')
    if type(temporary_mode) is not int or not 0 <= temporary_mode <= 0xffffffff:
        raise ValueError('temporary_mode must be an unsigned 32-bit word')
    if type(output_mask) is not int or not 0 <= output_mask < 16:
        raise ValueError('output_mask must select four optional output words')
    if not callable(set_mode) or not callable(dispatch):
        raise ValueError('mode and dispatch callbacks are required')

    previous_mode = set_mode(temporary_mode) if temporary_mode else 0
    render_mode = 0x10008 if temporary_mode else 8
    scratch = [None, None, None, None]
    dispatch(render_mode, 1, input_word, scratch)
    if any(type(value) is not int or not 0 <= value <= 0xffffffff
           for value in scratch):
        raise ValueError('dispatch must fill all four scratch words')
    writes = tuple((index, scratch[index]) for index in range(4)
                   if output_mask & (1 << index))
    if previous_mode:
        set_mode(previous_mode)
    return tuple(scratch), writes, render_mode
