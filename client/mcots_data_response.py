"""Recovered opaque post-login data records; field meanings remain unresolved."""
from dataclasses import dataclass, field
import struct
from client.mcots_framing import MCOTSFrame


_REPLIES = {0x144: (0x145, 0x239), 0x142: (0x143, 8),
            0x16b: (0x16c, 0x204), 0x185: (0x186, None)}


@dataclass(frozen=True)
class MCOTSDataReply:
    operation: int
    continuation_value: int | None
    records: tuple[bytes, ...] = field(repr=False)
    extension: bytes = field(repr=False)

    @property
    def more(self):
        return bool(self.continuation_value)

    @classmethod
    def from_frame(cls, frame, *, transaction_value, request_operation):
        """Decode a matching direct reply, retaining unknown fields and tails.

        List replies have uint16 count at +2, continuation byte +4 and fixed
        records at +5. The fixed 0x186 reply includes its opcode in 118 bytes.
        This does not aggregate pages or handle generic rejection replies.
        """
        if not isinstance(frame, MCOTSFrame):
            raise ValueError('expected MCOTS frame')
        frame.encode()
        if type(transaction_value) is not int or not 0 <= transaction_value <= 0xffffffff:
            raise ValueError('expected uint32 pending transaction')
        if type(request_operation) is not int or request_operation not in _REPLIES:
            raise ValueError('unsupported post-login request operation')
        if frame.transaction_value != transaction_value:
            raise ValueError('MCOTS data reply does not match pending transaction')
        opcode, stride = _REPLIES[request_operation]
        payload = frame.payload
        if len(payload) < 2 or struct.unpack_from('<H', payload)[0] != opcode:
            raise ValueError('MCOTS data reply conflicts with pending operation')
        if stride is None:
            if len(payload) < 118:
                raise ValueError('truncated fixed MCOTS data reply')
            return cls(opcode, None, (payload[:118],), payload[118:])
        if len(payload) < 5:
            raise ValueError('truncated MCOTS data list header')
        count = struct.unpack_from('<H', payload, 2)[0]
        end = 5+count*stride
        if end > len(payload):
            raise ValueError('truncated MCOTS data records')
        return cls(opcode, payload[4],
            tuple(payload[offset:offset+stride] for offset in range(5, end, stride)),
            payload[end:])
