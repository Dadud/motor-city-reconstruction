"""Connection success payload shared by native opcodes 0x120 and 0x308.

Original 0x7e64d0 reads format 'lpb': uint32, counted bytes up to 32,
then 64 fixed bytes. Preserve the counted bytes, including any NUL terminator.
"""
from dataclasses import dataclass, field
import struct

from client.nps_framing import Frame


_REJECTIONS = {0x21e: -0x22, 0x22a: -0x87, 0x20a: -3,
               0x20b: -4, 0x213: -0x17, 0x22b: -0x8c}


def native_connection_rejection(message_id):
    """Known server-reply return code from 0x73a720, or None.

    None does not imply success: it includes queue and unknown message IDs.
    Names for unconfirmed rejection meanings are deliberately not guessed.
    """
    if type(message_id) is not int or not 0 <= message_id <= 65535:
        raise ValueError('message ID must fit uint16')
    return _REJECTIONS.get(message_id)


@dataclass(frozen=True)
class LobbyLoginSuccess:
    user_id: int
    username: bytes = field(repr=False)
    caller_blob: bytes = field(repr=False)

    @property
    def native_username(self):
        """Original bounded C-string view; capacity 32 reserves a terminator.

        Keep the wire field separately so embedded NUL and truncation are
        visible to callers rather than silently changing the retained payload.
        """
        return self.username[:31].split(b'\0', 1)[0]

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
