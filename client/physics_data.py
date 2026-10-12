"""Portable Physics table records; generic values retain database order.

Native 0x67d900/0x67d5b0 stop numeric values at the first NULL column.
Semantic interpretation belongs to recovered component-specific loaders.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PhysicsRecord:
    part_type_id: int
    ordinal: int
    mass: float | None
    values: tuple


def decode_physics_table(columns):
    required=('PartTypeID','Ordinal','Mass',*(f'Val{i}' for i in range(1,51)))
    if any(name not in columns for name in required):
        raise ValueError('missing Physics table column')
    count=len(columns['PartTypeID'])
    if count>100000 or any(len(columns[name])!=count for name in required):
        raise ValueError('invalid Physics table column lengths')
    records={}
    for row in range(count):
        key=(columns['PartTypeID'][row],columns['Ordinal'][row])
        if any(type(v) is not int or v<0 for v in key) or key in records:
            raise ValueError('invalid or duplicate Physics identity')
        mass=columns['Mass'][row]
        if mass is not None and (not isinstance(mass,(int,float)) or not math.isfinite(mass) or mass<0):
            raise ValueError('invalid Physics mass')
        values=[]
        for i in range(1,51):
            value=columns[f'Val{i}'][row]
            if value is None:
                break
            if not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('non-finite or non-numeric Physics value')
            values.append(float(value))
        records[key]=PhysicsRecord(*key,float(mass) if mass is not None else None,tuple(values))
    return records
