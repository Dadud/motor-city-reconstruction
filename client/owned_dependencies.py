"""Isolated original owned-component dependency pass at 0x662060.

The caller supplies abstract dependency IDs already resolved by the original
type-template lookup (0x64c720). This pass does not guess or load templates,
choose a root, establish parents, or complete an owned vehicle assembly.
"""
import struct


def link_owned_dependencies(slots, resolved_dependency_ids):
    """Return new 1596-byte slots with original dependency/flag writes.

    Parent indexes must already be valid. Rejecting malformed indexes before
    processing is an authored safeguard against the original unchecked read.
    A missing matching dependency preserves the previous dependency index.
    """
    if not isinstance(slots, (tuple, list)) or not slots:
        raise ValueError('expected a nonempty owned-part slot list or tuple')
    if not isinstance(resolved_dependency_ids, (tuple, list)):
        raise ValueError('expected explicit resolved abstract dependency IDs')
    if len(resolved_dependency_ids) != len(slots):
        raise ValueError('dependency ID count must match owned-part count')
    if any(not isinstance(slot, bytes) or len(slot) != 1596 for slot in slots):
        raise ValueError('expected 1596-byte owned-part slots')
    if any(type(value) is not int or not -0x80000000 <= value <= 0x7fffffff
           for value in resolved_dependency_ids):
        raise ValueError('resolved dependency IDs must fit int32')
    parents = tuple(struct.unpack_from('<i', slot, 0x600)[0] for slot in slots)
    if any(not 0 <= index < len(slots) for index in parents):
        raise ValueError('owned-part parent indexes must reference an existing slot')

    abstract_ids = tuple(struct.unpack_from('<i', slot, 0)[0] for slot in slots)
    attachments = tuple(struct.unpack_from('<i', slot, 0x61c)[0] for slot in slots)
    root_absent = struct.unpack_from('<I', slots[0], 0x5f8)[0] == 0
    result = []
    for index, (slot, dependency_id) in enumerate(zip(slots, resolved_dependency_ids)):
        updated = bytearray(slot)
        if dependency_id == 0:
            struct.pack_into('<i', updated, 0x604, 0)
        else:
            for candidate, abstract_id in enumerate(abstract_ids):
                if abstract_id == dependency_id and (
                        attachments[candidate] == 0 or
                        attachments[candidate] == attachments[index]):
                    # No early exit: the original retains the last match.
                    struct.pack_into('<i', updated, 0x604, candidate)
        if (root_absent or abstract_ids[index] in (2001, 20001, 6001) or
                abstract_ids[parents[index]] == 6001):
            struct.pack_into('<i', updated, 0x634, 0)
        result.append(bytes(updated))
    return tuple(result)
