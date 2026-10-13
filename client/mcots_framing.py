"""MCOTS TCP envelope recovered from native sender 0x6f7f20.

Payload must already have undergone any connection-specific transformations.
This module neither compresses nor encrypts it, and does not connect a socket.
"""
from dataclasses import dataclass, field
import struct

MARKER = 0x434d4f54
HEADER = struct.Struct('<HIIB')


@dataclass(frozen=True)
class MCOTSFrame:
    transaction_value: int
    flags: int
    payload: bytes = field(repr=False)

    def encode(self):
        if type(self.transaction_value) is not int or not 0 <= self.transaction_value <= 0xffffffff:
            raise ValueError('MCOTS transaction value must fit uint32')
        if type(self.flags) is not int or not 0 <= self.flags <= 255:
            raise ValueError('MCOTS flags must fit uint8')
        if not isinstance(self.payload, bytes) or not 1 <= len(self.payload) <= 65526:
            raise ValueError('MCOTS payload must contain 1..65526 bytes')
        return HEADER.pack(len(self.payload)+9, MARKER, self.transaction_value, self.flags)+self.payload

    @classmethod
    def decode(cls, wire):
        """Decode one complete frame; reject truncation or additional frames."""
        if not isinstance(wire, bytes) or len(wire) < HEADER.size+1:
            raise ValueError('truncated MCOTS frame')
        length, marker, transaction, flags = HEADER.unpack_from(wire)
        if length+2 != len(wire) or marker != MARKER:
            raise ValueError('invalid MCOTS frame length or marker')
        return cls(transaction, flags, wire[HEADER.size:])
