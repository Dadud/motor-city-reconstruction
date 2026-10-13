"""Recovered owned-component counting, cost accumulation, and total price.

These are isolated original passes, not complete mechanical aggregation.
Existing cost fields are intentionally retained and accumulated again on each
visit. Out-of-range owned parent indexes are compared, never dereferenced.
"""
import struct

from .part_type_templates import _SPECIAL_TYPES


def _validate(slots):
    if not isinstance(slots, (tuple, list)) or len(slots) > 10000:
        raise ValueError('expected at most 10000 owned-part slots')
    if any(not isinstance(slot, bytes) or len(slot) != 1596 for slot in slots):
        raise ValueError('expected immutable 1596-byte owned-part slots')
    return tuple(slots)


def _unsigned(record, offset):
    return struct.unpack_from('<I', record, offset)[0]


def _children(slots, *, branded_only=False):
    children = [[] for _ in slots]
    for index, slot in enumerate(slots):
        parent = struct.unpack_from('<i', slot, 0x600)[0]
        if 0 <= parent < len(slots) and parent != index:
            if not branded_only or _unsigned(slot, 0x1e3) != 0:
                children[parent].append(index)
    return children


def apply_owned_component_counts(slots):
    """Apply recursive original 0x661370 counts at offset 0x638.

    Self contributes one only when branded and field 0x0c is zero; child
    traversal requires branding regardless of that child's self contribution.
    """
    slots = _validate(slots)
    children = _children(slots, branded_only=True)
    output = [bytearray(slot) for slot in slots]
    for root in range(len(slots)):
        # Each frame carries node, next child position, and running count.
        stack = [[root, 0, int(_unsigned(slots[root], 0x1e3) != 0 and
                              _unsigned(slots[root], 0xc) == 0)]]
        active = {root}
        while stack:
            node, cursor, count = stack[-1]
            if cursor < len(children[node]):
                child = children[node][cursor]
                stack[-1][1] += 1
                if child in active:
                    raise ValueError('cyclic branded component count traversal')
                active.add(child)
                stack.append([child, 0, int(_unsigned(slots[child], 0x1e3) != 0 and
                                           _unsigned(slots[child], 0xc) == 0)])
            else:
                stack.pop()
                active.remove(node)
                if stack:
                    stack[-1][2] = (stack[-1][2] + count) & 0xffffffff
                else:
                    struct.pack_into('<I', output[root], 0x638, count)
    return tuple(bytes(slot) for slot in output)


def apply_owned_repair_scrap_aggregates(slots):
    """Original 0x661d60/0x661cd0 modulo-32 cost accumulation.

    Eligible outer roots have offset 0x60c zero and a special abstract type.
    Recursive special children are processed afresh, including their existing
    totals; no reset or memoization is permitted by the original arithmetic.
    """
    slots = _validate(slots)
    output = [bytearray(slot) for slot in slots]
    children = _children(slots)
    special = [struct.unpack_from('<i', slot)[0] in _SPECIAL_TYPES for slot in slots]

    def add(parent, child):
        for offset in (0x62c, 0x630):
            total = (_unsigned(output[parent], offset) + _unsigned(output[child], offset)) & 0xffffffff
            struct.pack_into('<I', output[parent], offset, total)

    def recursive(start):
        # Resume a parent's addition after its special child completes.
        stack = [[start, 0, None]]
        active = {start}
        while stack:
            node, cursor, pending = stack[-1]
            if pending is not None:
                add(node, pending)
                stack[-1][2] = None
            elif cursor < len(children[node]):
                child = children[node][cursor]
                stack[-1][1] += 1
                if special[child]:
                    if child in active:
                        raise ValueError('cyclic special-component cost traversal')
                    stack[-1][2] = child
                    active.add(child)
                    stack.append([child, 0, None])
                else:
                    add(node, child)
            else:
                active.remove(node)
                stack.pop()

    for root, slot in enumerate(slots):
        if _unsigned(slot, 0x60c) != 0 or not special[root]:
            continue
        for child in children[root]:
            if special[child]:
                recursive(child)
            add(root, child)
    return tuple(bytes(slot) for slot in output)


def apply_owned_total_price(slots):
    """Original 0x6621f0 unsigned wrapping sum into first slot offset 0x1eb.

    The recovered double conversion/rounding/ftol sequence preserves these
    uint32 integer bits; it does not clamp prices or reset subsequent records.
    """
    slots = _validate(slots)
    if not slots:
        return ()
    total = sum(_unsigned(slot, 0x1eb) for slot in slots) & 0xffffffff
    first = bytearray(slots[0])
    struct.pack_into('<I', first, 0x1eb, total)
    return (bytes(first),) + slots[1:]
