"""Original post-load repair/scrap arithmetic, with explicit server factors."""
from dataclasses import dataclass
import math
import struct


_PERCENT = struct.unpack('<f',struct.pack('<f',0.01))[0]


@dataclass(frozen=True)
class PartValuationRates:
    repair: float
    scrap: float

    def __post_init__(self):
        for name in ('repair','scrap'):
            value = getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,(int,float)):
                raise ValueError('valuation factors must be finite numeric data')
            try:
                value = float(value)
            except OverflowError as error:
                raise ValueError('valuation factors must fit float64') from error
            if not math.isfinite(value):
                raise ValueError('valuation factors must be finite numeric data')
            object.__setattr__(self,name,value)

    @classmethod
    def from_reply(cls,record):
        from .mcots_data_records import MCOTSFixed186Record
        if record is None:
            return cls(0.1,0.75)
        if not isinstance(record,MCOTSFixed186Record):
            raise ValueError('expected decoded server data reply 0x186')
        return cls(record.double_1e,record.double_26)


@dataclass(frozen=True)
class OwnedPartValuation:
    repair_cost: int
    scrap_value: int
    wear_condition: float


def _f32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]


def _ftol_low32(value):
    # Native __ftol truncates into int64, then these callers use signed EAX.
    if not math.isfinite(value) or value < -0x8000000000000000 or value >= 0x8000000000000000:
        return 0  # x87 indefinite int64 is 0x8000000000000000.
    return ((math.trunc(value)+0x80000000)&0xffffffff)-0x80000000


def calculate_owned_valuation(slot,rates):
    """Recovered x87 flow with 53-bit arithmetic and float32 local stores."""
    if not isinstance(slot,bytes) or len(slot) != 1596 or not isinstance(rates,PartValuationRates):
        raise ValueError('expected owned-part slot and explicit valuation rates')
    if not struct.unpack_from('<I',slot,0x5f8)[0] or not struct.unpack_from('<I',slot,0x1e3)[0]:
        return None
    price = struct.unpack_from('<i',slot,0x1eb)[0]
    maximum = struct.unpack_from('<i',slot,0x1ef)[0]
    damage,wear = struct.unpack_from('<ii',slot,0x610)
    condition = 1.0 if maximum == 0 else _f32(1.0-wear/maximum)
    repair = 0 if damage == 0 else max(1,_ftol_low32(rates.repair*price*(damage*_PERCENT)+0.5))
    base = _ftol_low32(rates.scrap*price*condition+0.5)
    remainder = base-_f32(repair)
    scrap = _ftol_low32(remainder) if remainder >= 0 else 0
    identifier = struct.unpack_from('<I',slot)[0]
    if 20001 <= identifier <= 20999:
        value_11 = struct.unpack_from('<f',slot,0x454)[0]
        if not math.isfinite(value_11):
            raise ValueError('body physics Val11 must be finite')
        scrap = _ftol_low32(rates.scrap*value_11+scrap)
    return OwnedPartValuation(repair,scrap,condition)


def apply_owned_valuation(slot,rates):
    valuation = calculate_owned_valuation(slot,rates)
    if valuation is None:
        return slot
    output = bytearray(slot)
    struct.pack_into('<ii',output,0x62c,valuation.repair_cost,valuation.scrap_value)
    return bytes(output)
