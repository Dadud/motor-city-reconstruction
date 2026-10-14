"""Original 0x6628d0 template/assembly descriptions and leaf dispatch.

Attachment labels and the still-unrecovered branded leaf renderer are explicit
inputs. This is a research interface, not a complete description implementation.
"""
from collections.abc import Mapping
import struct
from .part_type_templates import _SPECIAL_TYPES


def _integer(slot, offset=0):
    return struct.unpack_from('<i', slot, offset)[0]


def _text(slot, offset, capacity):
    data = slot[offset:offset + capacity]
    if b'\0' not in data:
        raise ValueError('description text lacks a bounded terminator')
    return data.split(b'\0', 1)[0]


def apply_owned_descriptions(slots, templates, *, attachment_labels, leaf_description=None):
    """Populate description at 0x20, preserving bytes beyond its terminator.

    Assembly output retains complete lines only, stopping before the first line
    that would exceed 351 bytes. Missing templates preserve prior descriptions.
    """
    if (not isinstance(slots, (tuple, list)) or len(slots) > 10000 or
            not isinstance(templates, (tuple, list)) or not templates or
            any(not isinstance(slot, bytes) or len(slot) != 1596 for slot in (*slots, *templates))):
        raise ValueError('expected bounded immutable slots and type cache')
    if _integer(templates[0]) != 0:
        raise ValueError('expected abstract-zero cache sentinel')
    if not isinstance(attachment_labels, Mapping):
        raise ValueError('expected explicit attachment labels')
    labels = {}
    for key, label in attachment_labels.items():
        if type(key) is not int or not 1 <= key <= 11 or not isinstance(label, bytes) or b'\0' in label or len(label) > 128:
            raise ValueError('invalid bounded attachment label')
        labels[key] = label
    lookup = {}
    for template in templates[1:]:
        lookup.setdefault(_integer(template), template)
    result = list(slots)
    for index, slot in enumerate(result):
        abstract, branded = _integer(slot), _integer(slot, 0x1e3) != 0
        if not branded:
            template = lookup.get(abstract)
            if template is None:
                continue
            description = _text(template, 0x20, 352) or b' '
        elif abstract not in _SPECIAL_TYPES:
            if not callable(leaf_description):
                raise ValueError('branded leaf descriptions require an explicit renderer')
            updated = leaf_description(slot)
            if not isinstance(updated, bytes) or len(updated) != 1596:
                raise ValueError('leaf description must return an immutable 1596-byte slot')
            result[index] = updated
            continue
        else:
            description = b''
            for child_index, child in enumerate(result):
                if child_index == index or _integer(child, 0x1e3) == 0 or _integer(child, 0x600) != index:
                    continue
                attachment = _integer(child, 0x61c)
                if 1 <= attachment <= 11 and attachment not in labels:
                    raise ValueError('missing original/localized attachment label')
                line = (_text(child, 0x287, 64) + b' ' + labels.get(attachment, b'') +
                        (b' ' if attachment != 0 else b'') + _text(child, 0x180, 64))
                candidate = description + (b'\n' if description else b'') + line
                if len(candidate) > 351:
                    break
                description = candidate
        updated = bytearray(slot)
        updated[0x20:0x20 + len(description) + 1] = description + b'\0'
        result[index] = bytes(updated)
    return tuple(result)
