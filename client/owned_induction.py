"""Recovered induction placeholder pruning at 0x66ed71..0x66f0b9.

This isolated tail of finalization 0x66ea20 does not perform the earlier
missing-part insertion/allocation. All retained records remain byte-identical.
"""
import struct


_PAIRS = ((340001, 340333, 340666), (350001, 360001, 350666))


def prune_owned_induction_placeholders(slots):
    """Prune first matches with the original swap-last-and-pop ordering.

    Ownership is a nonzero PartID at 0x5f8. Each pair's ownership tests occur
    before either of its removals. The second pair sees the first pair's output.
    Duplicate abstract types are not collapsed or removed together.
    """
    if not isinstance(slots, (tuple, list)):
        raise ValueError('expected an owned-part slot list or tuple')
    if any(not isinstance(slot, bytes) or len(slot) != 1596 for slot in slots):
        raise ValueError('expected 1596-byte owned-part slots')
    result = list(slots)

    def remove_first(abstract):
        for index, slot in enumerate(result):
            if struct.unpack_from('<i', slot)[0] == abstract:
                result[index] = result[-1]
                result.pop()
                break

    for first, second, third in _PAIRS:
        first_owned = second_owned = False
        for slot in result:
            abstract = struct.unpack_from('<i', slot)[0]
            if struct.unpack_from('<I', slot, 0x5f8)[0] != 0:
                first_owned |= abstract == first
                second_owned |= abstract == second
        if not first_owned:
            remove_first(first)
        if not second_owned:
            remove_first(second)
        if first_owned or second_owned:
            remove_first(third)
    return tuple(result)
