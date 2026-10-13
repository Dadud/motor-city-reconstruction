"""Bounded operation 0xd5 fields read by the native MCOTS login handler.

Unresolved service bytes and field meanings remain explicit. Parsing does not
connect services or claim that the subsequent native login work succeeded.
"""
from dataclasses import dataclass, field
import struct
from client.mcots_framing import MCOTSFrame


@dataclass(frozen=True)
class MCOTSServiceRecord:
    service_id: int
    opaque: bytes = field(repr=False)

    @property
    def unused(self):
        return self.service_id == 0xff


@dataclass(frozen=True)
class MCOTSLoginSuccess:
    session_value: int
    capability_flags: int
    opaque_07: bytes = field(repr=False)
    values_09: tuple[int, ...]
    services: tuple[MCOTSServiceRecord, ...]
    values_89: tuple[int, ...]
    extension: bytes = field(repr=False)

    @property
    def native_feature_bits(self):
        return tuple(bool(self.capability_flags & (1 << bit)) for bit in range(3))

    @classmethod
    def decode(cls, payload):
        if not isinstance(payload, bytes) or not 173 <= len(payload) <= 65526:
            raise ValueError('MCOTS login success requires at least 173 bounded bytes')
        if struct.unpack_from('<H', payload)[0] != 0xd5:
            raise ValueError('expected MCOTS login success operation 0xd5')
        services = tuple(MCOTSServiceRecord(struct.unpack_from('<I', payload, offset)[0],
                                          payload[offset+4:offset+26])
                         for offset in range(0x21, 0x89, 26))
        return cls(struct.unpack_from('<I', payload, 2)[0], payload[6], payload[7:9],
                   struct.unpack_from('<6I', payload, 9), services,
                   struct.unpack_from('<9I', payload, 0x89), payload[173:])

    @classmethod
    def from_frame(cls, frame, *, transaction_value):
        """Require the envelope to match the pending login before parsing."""
        if not isinstance(frame, MCOTSFrame):
            raise ValueError('expected MCOTS frame')
        frame.encode()
        if type(transaction_value) is not int or not 0 <= transaction_value <= 0xffffffff:
            raise ValueError('expected uint32 pending transaction')
        if frame.transaction_value != transaction_value:
            raise ValueError('MCOTS login reply does not match pending transaction')
        return cls.decode(frame.payload)
