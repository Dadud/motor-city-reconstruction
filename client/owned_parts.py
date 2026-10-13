"""Owned-instance fields loaded by original Part_SelectENew, before enrichment."""
from dataclasses import dataclass
import struct


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
