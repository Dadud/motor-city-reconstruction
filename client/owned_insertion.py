"""Original missing-part insertion prefix of finalization 0x66ea20.

Uses resolved original type templates, not stock components. Induction pruning
and later parent/dependency linking are separate passes. Caller skip flags are
outside this isolated implementation.
"""
import struct

from .owned_parent_links import _integer, _validate
from .part_type_templates import _SPECIAL_TYPES


_PAIRED_ATTACHMENT_TYPES = frozenset((100001, 110001, 10001, 12001, 11001, 13001, 14001))
_SUPPRESSED_WITH_TYPE_2001 = frozenset((23001, 34001, 35001))


def _text(record, offset, capacity):
    region = record[offset:offset + capacity]
    if b'\0' not in region:
        raise ValueError('placeholder text lacks a bounded terminator')
    return region.split(b'\0', 1)[0]


def _copy_text(output, offset, text, capacity):
    if len(text) >= capacity:
        raise ValueError('placeholder text exceeds output region')
    output[offset:offset + len(text) + 1] = text + b'\0'


def _clone(first_template, child_template, attachment, display_mode):
    output = bytearray(first_template)
    _copy_text(output, 0x347, _text(child_template, 0x347, 64), 64)
    struct.pack_into('<i', output, 0x61c, attachment)
    # 0x6623a0 is not the owned-part year/display formatter. Mode 2 always
    # emits brand + space + model, including vehicle abstract type 101.
    model = _text(output, 0x307, 64)
    if display_mode != 2:
        _copy_text(output, 0x287, model, 64)
        if _integer(output) != 0 and _integer(output) in _SPECIAL_TYPES:
            _copy_text(output, 0x207, model, 128)
        else:
            brand = _text(output, 0x2c7, 64)
            _copy_text(output, 0x207, brand + b' ' + model, 128)
    else:
        brand = _text(output, 0x2c7, 64)
        _copy_text(output, 0x207, brand + b' ' + model, 128)
    _copy_text(output, 0x180, _text(first_template, 0x180, 64), 64)
    return bytes(output)


def insert_owned_placeholders(slots, templates, *, display_mode=2, max_parts=10000):
    """Append missing type/attachment placeholders while walking growing slots.

    Cache order and first matching type lookup are preserved. Size limits and
    bounded text checks are authored safeguards, not recovered game rules.
    """
    if type(display_mode) is not int or not 0 <= display_mode <= 0xffffffff:
        raise ValueError('placeholder display mode must fit uint32')
    if type(max_parts) is not int or max_parts < 1:
        raise ValueError('expected positive placeholder part limit')
    if not isinstance(slots, (tuple, list)):
        raise ValueError('expected an owned-part slot list or tuple')
    if not slots:
        # The original zero-count path inserts nothing. Reuse cache validation
        # with an inert record; no owned parent fields are read by this check.
        _validate((bytes(1596),), templates)
        return ()
    slots, lookup = _validate(slots, templates)
    if len(slots) > max_parts:
        raise ValueError('owned component count exceeds configured limit')
    indexes = {}
    for index, template in enumerate(templates[1:], 1):
        indexes.setdefault(_integer(template), index)
    result = list(slots)
    cursor = 0
    while cursor < len(result):
        parent = result[cursor]
        abstract = _integer(parent)
        owned = struct.unpack_from('<I', parent, 0x5f8)[0] != 0
        parent_template_index = indexes.get(abstract)
        if abstract != 0 and (owned or abstract in _SPECIAL_TYPES) and parent_template_index is not None:
            for child_template in templates[1:]:
                if _integer(child_template, 0x600) != parent_template_index:
                    continue
                child_abstract = _integer(child_template)
                attachments = (10, 11) if child_abstract in _PAIRED_ATTACHMENT_TYPES else (0,)
                for attachment in attachments:
                    if any(_integer(slot) == child_abstract and _integer(slot, 0x61c) == attachment
                           for slot in result):
                        continue
                    if (child_abstract in _SUPPRESSED_WITH_TYPE_2001 and
                            any(_integer(slot, 0x1e7) == 2001 for slot in result)):
                        continue
                    if len(result) >= max_parts:
                        raise ValueError('owned component count exceeds configured limit')
                    result.append(_clone(lookup[child_abstract], child_template,
                                         attachment, display_mode))
        cursor += 1
    return tuple(result)
