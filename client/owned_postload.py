"""Recovered owned loader tail at 0x66f2b0 with explicit research boundary.

The description pass remains unrecovered. Enriched processing requires the
caller to supply it explicitly; this is not a complete client or a mod API.
"""
import struct

from .owned_aggregates import (apply_owned_component_counts,
                               apply_owned_repair_scrap_aggregates,
                               apply_owned_total_price)
from .owned_dependencies import link_owned_dependencies
from .owned_induction import prune_owned_induction_placeholders
from .owned_insertion import insert_owned_placeholders
from .owned_ordering import reorder_owned_parts
from .owned_parent_links import _integer, _validate, link_owned_parents


def _dependency_ids(slots, templates):
    lookup = {}
    for template in templates[1:]:
        lookup.setdefault(_integer(template), template)
    dependencies = []
    for slot in slots:
        if _integer(slot) == 0:
            raise ValueError('abstract-zero dependency helper behavior is unrecovered')
        template = lookup.get(_integer(slot))
        if template is None:
            raise ValueError('owned dependency lookup requires a matching abstract type')
        index = _integer(template, 0x604)
        if not 0 <= index < len(templates):
            raise ValueError('owned dependency lookup requires a resolved cache index')
        dependencies.append(_integer(templates[index]))
    return tuple(dependencies)


def postprocess_owned_slots(slots, templates, *, finalize_enabled=True,
                            finalize_mode=0, display_mode=2, reorder=True,
                            enriched=True, description_pass=None):
    """Run the verified pass order with an explicit description substitute.

    Caller-supplied description output must preserve record count and return
    immutable slots. No identity callback is installed implicitly. Original
    assets, templates and caller records are never changed.
    """
    if any(type(flag) is not bool for flag in (finalize_enabled, reorder, enriched)):
        raise ValueError('post-load flags must be bool')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff
           for value in (finalize_mode, display_mode)):
        raise ValueError('post-load modes must fit uint32')
    if enriched and not callable(description_pass):
        raise ValueError('enriched post-load requires an explicit description pass')
    if not isinstance(slots, (tuple, list)) or not 1 <= len(slots) <= 10000:
        raise ValueError('expected 1..10000 owned-part slots')
    result, _lookup = _validate(slots, templates)
    if finalize_enabled and finalize_mode != 1:
        result = insert_owned_placeholders(result, templates, display_mode=display_mode)
        result = prune_owned_induction_placeholders(result)
    if not result:
        raise ValueError('post-load finalization removed the backing root slot')
    initialized = []
    for slot in result:
        output = bytearray(slot)
        struct.pack_into('<I', output, 0x634, 1)
        initialized.append(bytes(output))
    result = tuple(initialized)
    if reorder:
        result = reorder_owned_parts(result, templates)
    if enriched:
        result = link_owned_parents(result, templates)
        result = link_owned_dependencies(result, _dependency_ids(result, templates))
        described = description_pass(result)
        if (not isinstance(described, (tuple, list)) or len(described) != len(result) or
                any(not isinstance(slot, bytes) or len(slot) != 1596 for slot in described)):
            raise ValueError('description pass must preserve immutable slot count and size')
        result = apply_owned_component_counts(tuple(described))
        result = apply_owned_repair_scrap_aggregates(result)
    return apply_owned_total_price(result)
