"""Owned-instance fields loaded by original Part_SelectENew, before enrichment."""
from dataclasses import dataclass
import struct


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
        return cls(*(row[key] for key in ('PartID','BrandedPartID','PercentDamage',
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
