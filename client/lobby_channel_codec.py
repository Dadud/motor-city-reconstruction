"""Recovered channel-add payload serializer and success reply fields.

0x7e4c30 serializes native record offsets using 0x7e4140; 0x738f00 sends
opcode 0x106 and consumes 0x214/0x215. Unnamed native fields remain opaque.
This codec does not construct a complete room argument or open a live channel.
"""
from dataclasses import dataclass, field
import struct

from client.nps_framing import Frame

NATIVE_RECORD_SIZE = 0x1a4


@dataclass(frozen=True)
class ChannelJoinRecord:
    native: bytes = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.native, bytes) or len(self.native) != NATIVE_RECORD_SIZE:
            raise ValueError('channel serializer requires a 0x1a4-byte native record')

    def payload(self):
        raw = self.native
        def integer(offset, width):
            return raw[offset:offset + width][::-1]
        def counted_string(start, end):
            data = raw[start:end]
            terminator = data.find(bytes([0]))
            if terminator < 0:
                raise ValueError('native channel string requires a bounded NUL terminator')
            data = data[:terminator + 1]
            return struct.pack('>I', len(data)) + data
        payload = (integer(0, 4) + counted_string(4, 0x24)
                + b''.join(integer(offset, 4) for offset in (0x24, 0x28, 0x50, 0x54, 0x58))
                + b''.join(integer(offset, 2) for offset in (0x5c, 0x5e, 0x60, 0x62, 0x64, 0x66))
                + counted_string(0x74, 0x86) + integer(0x86, 2) + raw[0x88:0x89]
                + integer(0x8a, 2) + integer(0x8c, 2)
                + integer(0x90, 4) + integer(0x94, 4)
                + raw[0xa0:0x1a0] + integer(0x1a0, 4))
        if len(payload) > 0x170:
            raise ValueError('channel payload exceeds original 0x170-byte serializer capacity')
        return payload

    def frame(self):
        return Frame(0x106, self.payload())


@dataclass(frozen=True)
class ChannelJoinSuccess:
    message_id: int
    channel_id: int
    value_2: int

    @classmethod
    def from_frame(cls, frame):
        if not isinstance(frame, Frame) or frame.message_id not in (0x214, 0x215):
            raise ValueError('expected channel success 0x214 or 0x215')
        if not isinstance(frame.body, bytes) or len(frame.body) != 8:
            raise ValueError('channel success requires two uint32 fields')
        return cls(frame.message_id, *struct.unpack('>II', frame.body))
