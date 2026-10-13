"""Confirmed record fields, without guessed game-specific business meanings."""
from dataclasses import dataclass, field
import struct


def _record(raw, size):
    if not isinstance(raw,bytes) or len(raw) != size:
        raise ValueError('expected exact recovered MCOTS record size')
    return raw


@dataclass(frozen=True)
class MCOTSList145Record:
    raw: bytes = field(repr=False)

    def __post_init__(self):
        _record(self.raw,569)

    @property
    def identifier(self):
        return struct.unpack_from('<I',self.raw)[0]

    @property
    def value_04(self):
        return struct.unpack_from('<I',self.raw,4)[0]

    @property
    def text_window_0c(self):
        # Consumers compare a C string here. Its full declared capacity is
        # unresolved; expose only the bounded window before the +0x2c flag.
        return self.raw[12:44].split(b'\0',1)[0]

    @property
    def flag_2c(self):
        return self.raw[44]

    @property
    def reference_137(self):
        return struct.unpack_from('<I',self.raw,0x137)[0]

    def eligible(self, reference_known):
        """Recovered common selection predicate, with external lookup result."""
        if type(reference_known) is not bool:
            raise ValueError('expected a resolved reference membership boolean')
        return bool(self.identifier and self.value_04 and self.reference_137 and
                    reference_known and self.flag_2c and
                    (self.raw[12] or self.value_04 == 14))


@dataclass(frozen=True)
class MCOTSList143Record:
    raw: bytes = field(repr=False)

    def __post_init__(self):
        _record(self.raw,8)

    @property
    def value_00(self):
        return struct.unpack_from('<I',self.raw)[0]

    @property
    def value_04(self):
        return struct.unpack_from('<I',self.raw,4)[0]


@dataclass(frozen=True)
class MCOTSList16CRecord:
    raw: bytes = field(repr=False)

    def __post_init__(self):
        _record(self.raw,516)

    @property
    def identifier(self):
        return struct.unpack_from('<I',self.raw)[0]

    @property
    def body(self):
        return self.raw[4:]


@dataclass(frozen=True)
class MCOTSFixed186Record:
    raw: bytes = field(repr=False)

    def __post_init__(self):
        _record(self.raw,118)
        if struct.unpack_from('<H',self.raw)[0] != 0x186:
            raise ValueError('expected fixed MCOTS reply 0x186')

    @property
    def values_02(self):
        return struct.unpack_from('<3I',self.raw,2)

    @property
    def double_1e(self):
        return struct.unpack_from('<d',self.raw,0x1e)[0]

    @property
    def double_26(self):
        return struct.unpack_from('<d',self.raw,0x26)[0]


def first_145_identifier_for_value(records, value):
    """Original 0x5e89a0: first +4 match, without the eligibility predicate."""
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('expected uint32 lookup value')
    for record in records:
        if not isinstance(record,MCOTSList145Record):
            raise ValueError('expected decoded 0x145 records')
        if record.value_04 == value:
            return record.identifier
    return 0
