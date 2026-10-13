"""Connection success payload shared by native opcodes 0x120 and 0x308.

Original 0x7e64d0 reads format 'lpb': uint32, counted bytes up to 32,
then 64 fixed bytes. Preserve the counted bytes, including any NUL terminator.
"""
from dataclasses import dataclass, field
import struct

from client.nps_framing import Frame


@dataclass(frozen=True)
class LobbyLoginSuccess:
    user_id: int
    username: bytes = field(repr=False)
    caller_blob: bytes = field(repr=False)

    @classmethod
    def from_frame(cls, frame):
        if not isinstance(frame, Frame) or frame.message_id not in (0x120, 0x308):
            raise ValueError('expected lobby connection success 0x120 or 0x308')
        body = frame.body
        if not isinstance(body, bytes) or len(body) < 8:
            raise ValueError('truncated lobby connection success')
        user_id, count = struct.unpack_from('>II', body)
        if count > 32 or len(body) != 8+count+64:
            raise ValueError('invalid lobby success field lengths')
        return cls(user_id, body[8:8+count], body[8+count:])
