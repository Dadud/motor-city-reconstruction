"""Portable representation of the sorting/linking subpass in 0x52dd70.

The original owner-level routine also locates the body node, invokes the body
and component collectors, allocates the resulting record array, and only then
copies, stable-sorts, and links the records. This module represents that final
subpass; it does not model those producer or allocation steps. A portable
caller cannot depend on host pointers, so it retains records and represents
the linked chain as record indices.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderRecord:
    words: tuple[int, ...]

    def __post_init__(self):
        if len(self.words) != 9:
            raise ValueError('render records contain exactly nine 32-bit words')
        if any(type(word) is not int or not 0 <= word <= 0xffffffff
               for word in self.words):
            raise ValueError('render record words must be unsigned 32-bit integers')

    @property
    def sort_key(self):
        return self.words[5]


@dataclass(frozen=True)
class RenderList:
    records: tuple[RenderRecord, ...]
    next_indices: tuple[int | None, ...]

    def __post_init__(self):
        if len(self.records) != len(self.next_indices):
            raise ValueError('record and link counts must agree')
        for index, next_index in enumerate(self.next_indices):
            expected = index + 1 if index + 1 < len(self.records) else None
            if next_index != expected:
                raise ValueError('render links must form one ordered null-terminated chain')


def build_render_list(records):
    """Reproduce the stable ordering and linked traversal subpass of 0x52dd70."""
    ordered = list(records)
    if any(not isinstance(record, RenderRecord) for record in ordered):
        raise TypeError('records must be RenderRecord instances')
    # Native swaps only when left key < right key, producing descending order;
    # equal keys therefore preserve collector insertion order.
    for end in range(len(ordered) - 1, 0, -1):
        changed = False
        for index in range(end):
            if ordered[index].sort_key < ordered[index + 1].sort_key:
                ordered[index], ordered[index + 1] = ordered[index + 1], ordered[index]
                changed = True
        if not changed:
            break
    return RenderList(tuple(ordered),
                      tuple(range(1, len(ordered))) + ((None,) if ordered else ()))
