"""Original type/attachment traversal at 0x66f0d0 and caller count gate.

Ordering is driven by the resolved abstract-type cache, not owned parent links.
Matches are first records in the unchanged input; visits do not consume them.
"""
from .owned_parent_links import _integer, _validate


_ATTACHMENT_ORDER = (10, 1, 2, 5, 11, 3, 4, 6, 7, 8, 9, 0)
_MAX_TYPE_VISITS = 100000


def order_owned_candidates(slots, templates, max_parts=10000):
    """Return the original DFS candidate sequence, possibly omitting records.

    A repeated type visit can append the same first input match again. Invalid
    cache references, cyclic traversals, output limits and a fixed 100000 type
    visit limit are authored guards. The latter bounds duplicate-cache paths
    even when those paths produce no output records.
    """
    if type(max_parts) is not int or max_parts < 1:
        raise ValueError('expected positive ordering part limit')
    if not isinstance(slots, (tuple, list)):
        raise ValueError('expected an owned-part slot list or tuple')
    if not slots:
        _validate((bytes(1596),), templates)
        return ()
    slots, _lookup = _validate(slots, templates)
    if len(slots) > max_parts:
        raise ValueError('owned component count exceeds configured limit')
    indexes = {}
    children = [[] for _ in templates]
    for index, template in enumerate(templates[1:], 1):
        indexes.setdefault(_integer(template), index)
        children[_integer(template, 0x600)].append(_integer(template))
    matches = {}
    for slot in slots:
        matches.setdefault((_integer(slot), _integer(slot, 0x61c)), slot)
    output = []
    # Explicit enter/leave records preserve recursive DFS order without using
    # Python's recursion stack. Active types detect only traversed cycles.
    stack = [(_integer(slots[0]), False)]
    active = set()
    visits = 0
    while stack:
        abstract, leaving = stack.pop()
        if leaving:
            active.remove(abstract)
            continue
        visits += 1
        if visits > _MAX_TYPE_VISITS:
            raise ValueError('abstract-type ordering exceeds traversal limit')
        if abstract in active:
            raise ValueError('cyclic abstract-type ordering traversal')
        active.add(abstract)
        for attachment in _ATTACHMENT_ORDER:
            slot = matches.get((abstract, attachment))
            if slot is not None:
                if len(output) >= max_parts:
                    raise ValueError('ordered component count exceeds configured limit')
                output.append(slot)
        stack.append((abstract, True))
        index = None if abstract == 0 else indexes.get(abstract)
        if index is not None:
            for child_abstract in reversed(children[index]):
                stack.append((child_abstract, False))
    return tuple(output)


def reorder_owned_parts(slots, templates, max_parts=10000):
    """Original 0x66f2b0 acceptance gate: use candidates only if counts match.

    This gate is a count comparison, not a uniqueness or permutation check.
    """
    ordered = order_owned_candidates(slots, templates, max_parts=max_parts)
    return ordered if len(ordered) == len(slots) else tuple(slots)
