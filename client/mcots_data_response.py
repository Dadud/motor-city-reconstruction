"""Recovered opaque post-login data records; field meanings remain unresolved."""
from dataclasses import dataclass, field
import struct
from client.mcots_framing import MCOTSFrame


_REPLIES = {0x144: (0x145, 0x239), 0x142: (0x143, 8),
            0x16b: (0x16c, 0x204), 0x185: (0x186, None),
            0xac: (0xad,8), 0x6c: (0x7a,None), 0x108: (0x109,None)}
_FIXED_SIZES = {0x185:118, 0x6c:453, 0x108:26}


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

        Shared list replies have uint16 count at +2, continuation byte +4 and
        records at +5. Persona car lists use a byte count +2 and records +3.
        Fixed replies include their opcode in the recovered record size.
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
            size = _FIXED_SIZES[request_operation]
            if len(payload) < size:
                raise ValueError('truncated fixed MCOTS data reply')
            return cls(opcode, None, (payload[:size],), payload[size:])
        if request_operation == 0xac:
            if len(payload) < 3:
                raise ValueError('truncated MCOTS persona car-list header')
            count, start, continuation = payload[2], 3, None
        else:
            if len(payload) < 5:
                raise ValueError('truncated MCOTS data list header')
            count, start, continuation = struct.unpack_from('<H',payload,2)[0], 5, payload[4]
        end = start+count*stride
        if end > len(payload):
            raise ValueError('truncated MCOTS data records')
        return cls(opcode, continuation,
            tuple(payload[offset:offset+stride] for offset in range(start, end, stride)),
            payload[end:])
