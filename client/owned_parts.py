"""Owned-instance fields loaded by original Part_SelectENew, before enrichment."""
from dataclasses import dataclass
import struct


def apply_owned_vehicle_price(slot,query_price=0):
    """Final enrichment override for abstract type 101 (query column 13)."""
    if not isinstance(slot,bytes) or len(slot) != 1596:
        raise ValueError('expected owned-part intermediate slot')
    if type(query_price) is not int or not -0x80000000 <= query_price <= 0x7fffffff:
        raise ValueError('vehicle query price must fit int32')
    if struct.unpack_from('<i',slot)[0] != 101:
        return slot
    output = bytearray(slot)
    struct.pack_into('<i',output,0x1eb,query_price)
    return bytes(output)


def apply_owned_model_brand(slot,row, *, text_encoding):
    """Copy cached model-brand name/picture after family labels.

    None is a failed lookup, which preserves the existing family label.
    A present NULL field becomes an empty cached string.
    """
    if not isinstance(slot,bytes) or len(slot) != 1596:
        raise ValueError('expected owned-part intermediate slot')
    if row is None:
        return slot
    fields = []
    for offset,count,key in ((0x399,8,'PicName'),(0x2c7,63,'Brand')):
        value = '' if row[key] is None else row[key]
        if not isinstance(value,str) or '\0' in value:
            raise ValueError('expected unterminated model-brand text')
        # Original brand-cache initialization copies bounded prefixes into a
        # cleared record; enrichment then copies through the resulting NUL.
        fields.append((offset,value.encode(text_encoding)[:count]+b'\0'))
    output = bytearray(slot)
    for offset,value in fields:
        output[offset:offset+len(value)] = value
    return bytes(output)


@dataclass(frozen=True)
class OwnedEngineFamily:
    family_id: int
    brand_id: int
    brand_name: str | None
    name: str | None
    short_name: str | None

    def apply(self,slot, *, text_encoding, brand_cache_name):
        """Original family overrides; None means brand-cache lookup failed."""
        if not isinstance(slot,bytes) or len(slot) != 1596:
            raise ValueError('expected owned-part intermediate slot')
        if self.family_id == -1 or struct.unpack_from('<i',slot,0x203)[0] != self.family_id:
            raise ValueError('engine family does not match owned-part metadata')
        def encode(value):
            value = '' if value is None else value
            if not isinstance(value,str) or '\0' in value:
                raise ValueError('expected unterminated engine-family text')
            return value.encode(text_encoding)
        fields = []
        for offset,capacity,value in ((0x3a2,64,self.brand_name),
                (0x3e2,26,self.name),(0x3fc,8,self.short_name)):
            text = encode(value)
            if len(text) >= capacity:
                raise ValueError('engine-family query text lacks a bounded terminator')
            fields.append((offset,text.ljust(capacity-1,b'\0')))
        brand = None if brand_cache_name is None else encode(brand_cache_name)[:63].ljust(63,b'\0')
        output = bytearray(slot)
        if brand is None:
            output[0x2c7] = 0
        else:
            output[0x2c7:0x306] = brand
        for offset,text in fields:
            output[offset:offset+len(text)] = text
        return bytes(output)


@dataclass(frozen=True)
class OwnedPartMetadata:
    abstract_type_id: int
    part_type_id: int
    retail_price: int
    max_item_wear: int
    manufacture_year: int
    part_grade_id: int
    engine_block_family_id: int
    brand_id: int
    part_type_name: str | None
    model_name: str | None
    short_model_name: str | None
    extra_info: str | None
    part_filename: str | None

    def apply_numeric_fields(self,part):
        """Add confirmed integer metadata; text and physics remain separate."""
        slot = bytearray(part.native_seed())
        for offset,value in ((0,self.abstract_type_id),(0x1e7,self.part_type_id),
                (0x1eb,self.retail_price),(0x1ef,self.max_item_wear),
                (0x1fb,self.manufacture_year),(0x1ff,self.part_grade_id),
                (0x203,self.engine_block_family_id)):
            if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
                raise ValueError('owned-part metadata must fit int32')
            struct.pack_into('<i',slot,offset,value)
        return bytes(slot)

    def apply_text_fields(self,slot, *, text_encoding):
        """Copy recovered query text, before family/type-specific overrides.

        Model, short model, extra info and filename require a terminator in
        the original query buffer. Reject overlong input rather than recreate
        the native unbounded read beyond that buffer.
        """
        if not isinstance(slot,bytes) or len(slot) != 1596:
            raise ValueError('expected owned-part intermediate slot')
        def encoded(value):
            if value is None:
                value = ''
            if not isinstance(value,str) or '\0' in value:
                raise ValueError('expected unterminated owned-part text')
            return value.encode(text_encoding)
        fields = []
        for offset,capacity,value in ((0x307,64,self.model_name),
                (0x20,352,self.extra_info),(0x387,9,self.part_filename),
                (0x287,64,self.short_model_name)):
            text = encoded(value)
            if len(text) >= capacity:
                raise ValueError('owned-part text lacks a bounded native terminator')
            fields.append((offset,text+b'\0'))
        name = encoded(self.part_type_name)[:63]
        output = bytearray(slot)
        output[0x347:0x387] = name.ljust(64,b'\0')
        for offset,text in fields:
            output[offset:offset+len(text)] = text
        output[0x390] = 0  # Original explicitly cleared local text buffer.
        return bytes(output)


@dataclass(frozen=True)
class OwnedPart:
    part_id: int
    branded_part_id: int
    percent_damage: int
    item_wear: int
    parent_part_id: int
    repair_cost: int
    scrap_value: int

    @classmethod
    def from_row(cls,row):
        # Native 0x67f080 writes zero for a present SQL NULL integer column.
        return cls(*(0 if row[key] is None else row[key] for key in ('PartID','BrandedPartID','PercentDamage',
            'ItemWear','ParentPartID','RepairCost','ScrapValue')))

    def native_seed(self):
        """Zeroed 1596-byte slot plus confirmed query fields; incomplete object.

        BrandPart_SelectE, Physics_Select and later computations still have
        to enrich this seed. The resulting bytes are not a network packet.
        """
        identifiers = (self.part_id,self.branded_part_id,self.parent_part_id)
        values = (self.percent_damage,self.item_wear,self.repair_cost,self.scrap_value)
        if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in identifiers):
            raise ValueError('owned-part identifiers must fit uint32')
        if any(type(value) is not int or not -0x80000000 <= value <= 0x7fffffff for value in values):
            raise ValueError('owned-part instance fields must fit int32')
        if not self.part_id:
            raise ValueError('owned part requires a nonzero instance ID')
        slot = bytearray(0x63c)
        for offset,value in ((0x5f8,self.part_id),(0x1e3,self.branded_part_id),
                             (0x60c,self.parent_part_id)):
            struct.pack_into('<I',slot,offset,value)
        for offset,value in ((0x610,self.percent_damage),(0x614,self.item_wear),
                             (0x62c,self.repair_cost),(0x630,self.scrap_value)):
            struct.pack_into('<i',slot,offset,value)
        return bytes(slot)


class OwnedPartCache:
    """Explicit instance rows; never substitute a stock catalogue row."""
    def __init__(self,rows):
        self._parts = {}
        for row in rows:
            part = OwnedPart.from_row(row)
            part.native_seed()
            if part.part_id in self._parts:
                raise ValueError('duplicate owned-part instance ID')
            self._parts[part.part_id] = part

    def get(self,part_id):
        try:
            return self._parts[part_id]
        except KeyError as error:
            raise ValueError('owned-part instance is missing from cache') from error

    def seed_car_pairs(self,pairs):
        """First pair word selects an instance; retain zero IDs as empty slots.

        The second word participates in the original cache update before this
        query. Cache mutation and complete object population are separate work.
        """
        result = []
        for pair in pairs:
            if not isinstance(pair,bytes) or len(pair) != 8:
                raise ValueError('expected eight-byte persona car pair')
            identifier = struct.unpack_from('<I',pair)[0]
            result.append(self.get(identifier).native_seed() if identifier else bytes(0x63c))
        return tuple(result)


class OwnedInstanceCache:
    """Authored in-memory equivalent of the recovered car-list SQL updates.

    Keep SQL NULL parent values distinct from integer zero in cache rows.
    Conversion to native integer slots follows the original NULL read rule.
    No installation database is changed.
    """
    def __init__(self,rows=()):
        self._rows = {}
        for source in rows:
            row = dict(source)
            part = OwnedPart.from_row(row)
            part.native_seed()
            if part.part_id in self._rows:
                raise ValueError('duplicate owned-part instance ID')
            self._rows[part.part_id] = row

    def apply_persona_car_pairs(self,persona_id,pairs):
        if type(persona_id) is not int or not 1 <= persona_id <= 0xffffffff:
            raise ValueError('expected nonzero selected persona ID')
        validated = []
        for pair in pairs:
            if not isinstance(pair,bytes) or len(pair) != 8:
                raise ValueError('expected eight-byte persona car pair')
            validated.append(struct.unpack('<II',pair))
        for identifier,brand in validated:
            if not identifier:
                continue  # Original 0x6725d0 rejects zero; its caller continues.
            row = dict(self._rows.get(identifier,{}))
            row.update(PartID=identifier,OwnerID=persona_id,BrandedPartID=brand,
                ParentPartID=None,AttachmentPointID=0,PercentDamage=0,ItemWear=0,
                RepairCost=0,ScrapValue=0)
            self._rows[identifier] = row

    def row(self,identifier):
        try:
            return dict(self._rows[identifier])
        except KeyError as error:
            raise ValueError('owned-part instance is missing from cache') from error

    def part_cache(self):
        return OwnedPartCache(self._rows.values())

    def child_rows(self,parent_id):
        """Snapshot rows matching the original ParentPartID equality predicate."""
        if type(parent_id) is not int or not 1 <= parent_id <= 0xffffffff:
            raise ValueError('expected nonzero owned parent ID')
        return tuple(dict(row) for row in self._rows.values() if row.get('ParentPartID') == parent_id)
