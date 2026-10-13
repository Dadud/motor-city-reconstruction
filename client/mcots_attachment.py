"""Native 40-byte MCOTS service attachment payload, operation 0x1b6."""
from dataclasses import dataclass, field
import struct


@dataclass(frozen=True)
class MCOTSAttachment:
    account_user_id: int
    persona_id: int
    persona_name: bytes = field(repr=False)

    def encode(self):
        for value in (self.account_user_id, self.persona_id):
            if type(value) is not int or not 0 <= value <= 0xffffffff:
                raise ValueError('MCOTS attachment identities must fit uint32')
        if (not isinstance(self.persona_name, bytes) or len(self.persona_name) > 32 or
                b'\0' in self.persona_name):
            raise ValueError('expected bounded unterminated persona name bytes')
        return (struct.pack('<HII', 0x1b6, self.account_user_id, self.persona_id)+
                bytes(13)+self.persona_name[:12].ljust(12, b'\0')+b'\0'+
                struct.pack('<I', 0x1b5a))
