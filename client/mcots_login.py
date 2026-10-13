"""Recovered MCOTS login record in native memory, not transport framing.

Worker 0x682df0 builds this 39-byte record before handing it to 0x6831f0.
Wire transformations, attachment handshake and login replies remain separate.
"""
from dataclasses import dataclass, field
import struct


@dataclass(frozen=True)
class MCOTSLoginRecord:
    account_user_id: int
    persona_id: int
    persona_name: bytes = field(repr=False)
    value_120: int
    value_124: int
    value_128: int

    def encode_native_record(self):
        """Exact little-endian memory record; do not send this as an NPS frame.

        The original zeroes the record and strncpy-copies 13 name bytes.
        Longer names are truncated; an exactly 13-byte name has no terminator.
        Names retain the original narrow bytes; no text encoding is guessed.
        """
        values = (self.account_user_id, self.persona_id,
                  self.value_128, self.value_120, self.value_124)
        if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in values):
            raise ValueError('MCOTS login values must fit uint32')
        if (not isinstance(self.persona_name, bytes) or len(self.persona_name) > 32 or
                b'\0' in self.persona_name):
            raise ValueError('expected bounded unterminated persona name bytes')
        return (struct.pack('<H5I', 0x69, *values)+
                self.persona_name[:13].ljust(13, b'\0')+struct.pack('<I', 0x1b5a))
