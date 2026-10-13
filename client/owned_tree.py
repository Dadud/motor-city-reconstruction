"""Recovered child discovery before original component-tree finalization."""
from dataclasses import dataclass, field
import codecs
import struct
from .owned_parts import OwnedInstanceCache
from .part_type_templates import _SPECIAL_TYPES


@dataclass(frozen=True)
class OwnedTreeDiscovery:
    slots: tuple[bytes, ...] = field(repr=False)
    queried_parent_ids: tuple[int, ...]


def discover_owned_tree(root_id,cache,catalogue, *, text_encoding,max_parts=10000):
    """Breadth-first Part_SelectAllChildren, with the original expansion gate.

    No stock parts are substituted. Cycles and size limits are authored
    safeguards. The returned provisional slots exclude later finalization.
    """
    if type(root_id) is not int or not 1 <= root_id <= 0xffffffff:
        raise ValueError('expected nonzero owned root ID')
    if not isinstance(cache,OwnedInstanceCache) or type(max_parts) is not int or max_parts < 1:
        raise ValueError('expected instance cache and positive part limit')
    if not isinstance(text_encoding,str):
        raise ValueError('expected explicit child text encoding')
    codecs.lookup(text_encoding)
    root = bytearray(1596)
    struct.pack_into('<I',root,0x5f8,root_id)
    slots, seen, queried = [bytes(root)],{root_id},[]
    cursor = 0
    while cursor < len(slots):
        slot = slots[cursor]
        identifier = struct.unpack_from('<I',slot,0x5f8)[0]
        abstract = struct.unpack_from('<i',slot)[0]
        if cursor == 0 or abstract in _SPECIAL_TYPES:
            queried.append(identifier)
            for row in cache.child_rows(identifier):
                # Reproduce the saved query's inner joins. A missing reference
                # excludes that row rather than inventing stock metadata.
                branded = catalogue.branded.get(row['BrandedPartID'])
                kind = None if branded is None else catalogue.types.get(branded['PartTypeID'])
                if kind is None:
                    continue
                child_id = row['PartID']
                if child_id in seen:
                    raise ValueError('owned component cycle or repeated instance')
                if len(slots) >= max_parts:
                    raise ValueError('owned component count exceeds configured limit')
                filename = '' if kind['PartFilename'] is None else kind['PartFilename']
                if not isinstance(filename,str) or '\0' in filename:
                    raise ValueError('invalid owned child filename')
                encoded = filename.encode(text_encoding)
                if len(encoded) >= 9:
                    raise ValueError('owned child filename lacks bounded terminator')
                child = bytearray(1596)
                abstract_id = 0 if kind['AbstractPartTypeID'] is None else kind['AbstractPartTypeID']
                attachment = 0 if row['AttachmentPointID'] is None else row['AttachmentPointID']
                if any(type(value) is not int or not -0x80000000 <= value <= 0x7fffffff
                       for value in (abstract_id,attachment)):
                    raise ValueError('owned child query integers must fit int32')
                struct.pack_into('<I',child,0x5f8,child_id)
                struct.pack_into('<i',child,0,abstract_id)
                struct.pack_into('<i',child,0x61c,attachment)
                child[0x387:0x387+len(encoded)+1] = encoded+b'\0'
                slots.append(bytes(child))
                seen.add(child_id)
        cursor += 1
    return OwnedTreeDiscovery(tuple(slots),tuple(queried))
