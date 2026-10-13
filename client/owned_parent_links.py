"""Original root selection (0x661a40) and parent/family pass (0x661ed0).

Inputs are owned slots and the already resolved 1596-byte type cache, including
its index-zero sentinel. This is an isolated pass, not a full assembly loader.
"""
import struct


def _integer(record, offset=0):
    return struct.unpack_from('<i', record, offset)[0]


def _validate(slots, templates):
    if not isinstance(slots, (tuple, list)) or not slots:
        raise ValueError('expected nonempty owned-part slots')
    if not isinstance(templates, (tuple, list)) or not templates:
        raise ValueError('expected resolved type cache with index-zero sentinel')
    if any(not isinstance(record, bytes) or len(record) != 1596
           for record in (*slots, *templates)):
        raise ValueError('expected 1596-byte slots and type-cache records')
    if _integer(templates[0]) != 0:
        raise ValueError('type-cache index zero must be the abstract-zero sentinel')
    if any(not 0 <= _integer(record, 0x600) < len(templates) for record in templates):
        raise ValueError('resolved type parent indexes must reference the cache')
    if any(not 0 <= _integer(record, 0x600) < len(slots) for record in slots):
        raise ValueError('owned parent indexes must reference existing slots')
    lookup = {}
    for record in templates[1:]:
        lookup.setdefault(_integer(record), record)
    # Original ancestor walks have no cycle limit. Reject cyclic input rather
    # than silently manufacturing a distance or hanging during root selection.
    for abstract in lookup:
        _distance(abstract, 0, templates, lookup)
    return tuple(slots), lookup


def _distance(abstract, target, templates, lookup):
    steps, seen = 0, set()
    while abstract != 0 and abstract != target:
        if abstract in seen:
            raise ValueError('cyclic abstract-part parent chain')
        seen.add(abstract)
        steps += 1
        template = lookup.get(abstract)
        if template is None:
            return steps
        abstract = _integer(templates[_integer(template, 0x600)])
    return steps


def _select(slots, templates, lookup):
    if len(slots) <= 1:
        return slots, 1
    for index, record in enumerate(slots):
        template = lookup.get(_integer(record))
        if template is None:
            return slots, 3
        if _integer(templates[_integer(template, 0x600)]) == 0:
            result = list(slots)
            result[0], result[index] = result[index], result[0]
            return tuple(result), 1
    best_index, minimum = 0, 255
    for index, record in enumerate(slots):
        abstract = _integer(record)
        if abstract == 1001:
            best_index = index
            break
        distance = _distance(abstract, 1001, templates, lookup)
        if distance < minimum:
            best_index, minimum = index, distance
    result = list(slots)
    result[0], result[best_index] = result[best_index], result[0]
    return tuple(result), 1


def select_owned_root(slots, templates):
    """Return (whole-record reordered slots, original status 1 or 3)."""
    slots, lookup = _validate(slots, templates)
    return _select(slots, templates, lookup)


def link_owned_parents(slots, templates):
    """Select root, link parents, and propagate EngineBlockFamilyID at 0x203.

    Root-selection status is intentionally ignored by the original caller.
    Missing type matches yield parent-template index zero. Existing owned
    parent indexes survive unless a matching parent overwrites them.
    The fallback uses the type cache's BlockFamilyCompatibility at 0x14.
    """
    slots, lookup = _validate(slots, templates)
    slots, _status = _select(slots, templates, lookup)
    result = [bytearray(record) for record in slots]
    for parent_index, parent in enumerate(result):
        parent_abstract, parent_attachment = _integer(parent), _integer(parent, 0x61c)
        for child in result:
            abstract = _integer(child)
            template = None if abstract == 0 else lookup.get(abstract)
            template_parent = 0 if template is None else _integer(template, 0x600)
            if (template_parent != 0 and
                    _integer(templates[template_parent]) == parent_abstract and
                    (parent_attachment == 0 or _integer(child, 0x61c) == parent_attachment)):
                struct.pack_into('<i', child, 0x600, parent_index)
    target = source = None
    for index, record in enumerate(result):
        if _integer(record) == 36001:
            target = index
        if _integer(record) == 160001 and struct.unpack_from('<I', record, 0x1e3)[0] != 0:
            source = index
    if target is not None:
        if source is not None:
            result[target][0x203:0x207] = result[source][0x203:0x207]
        else:
            struct.pack_into('<i', result[target], 0x203, 0)
            for record in result:
                template = lookup.get(_integer(record))
                if (_integer(record, 0x600) == target and _integer(record, 0x203) != 0 and
                        template is not None and _integer(template, 0x14) != 0):
                    result[target][0x203:0x207] = record[0x203:0x207]
    return tuple(bytes(record) for record in result)
