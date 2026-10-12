"""Recovered NPS byte framing, without login payload or session interpretation.

Main binary SHA256 28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164.
Serializer 0x7e0800; receiver 0x72f600. All integer fields are big endian.
Four-byte frames are retained because the receiver permits them; their purpose
has not been established. Flags and auxiliary fields have no guessed meaning.
"""
from dataclasses import dataclass, field
import struct

MAX_FRAME_BYTES = 65535
_PREFIX = struct.Struct('>HH')
_HEADER = struct.Struct('>HHHHI')


@dataclass(frozen=True)
class Frame:
    message_id: int
    body: bytes = field(repr=False)

    def encode(self):
        if not isinstance(self.message_id, int) or not 0 <= self.message_id <= 65535:
            raise ValueError('message ID must fit uint16')
        if not isinstance(self.body, bytes):
            raise TypeError('frame body must be bytes')
        length = 4 + len(self.body)
        if length > MAX_FRAME_BYTES:
            raise ValueError('frame exceeds uint16 length')
        return _PREFIX.pack(self.message_id, length) + self.body


def native_flags(message_id):
    """Value written at header offset four by the recovered serializer."""
    return 0x101 if 0x501 <= message_id <= 0x51a or 0x521 <= message_id <= 0x526 else 0


def encode_message(message_id, payload=b'', *, auxiliary=0):
    """Serialize the observed 12-byte header; auxiliary is caller supplied.

    Native code can compute auxiliary through a virtual method. That method's
    semantics remain unresolved, so this helper does not create login messages.
    """
    if not isinstance(auxiliary, int) or not 0 <= auxiliary <= 0xffffffff:
        raise ValueError('auxiliary must fit uint32')
    if not isinstance(payload, bytes):
        raise TypeError('payload must be bytes')
    body = struct.pack('>HHI', native_flags(message_id), 0, auxiliary) + payload
    return Frame(message_id, body).encode()


@dataclass(frozen=True)
class MessageHeader:
    message_id: int
    length: int
    flags: int
    reserved: int
    auxiliary: int

    @classmethod
    def from_frame(cls, frame):
        """Explicit interpretation only: not every received frame has a header."""
        wire = frame.encode()
        if len(wire) < _HEADER.size:
            raise ValueError('frame too short for a message header')
        return cls(*_HEADER.unpack_from(wire))


class FrameDecoder:
    """Incremental TCP framing with at most one incomplete frame buffered.

    After malformed framing, discard the decoder and close the connection.
    Unknown message IDs and bodies are retained without interpretation.
    """
    def __init__(self):
        self._pending = bytearray()
        self._failed = False

    def feed(self, data):
        if self._failed:
            raise ValueError('decoder failed; create a new connection decoder')
        if not isinstance(data, bytes):
            raise TypeError('received data must be bytes')
        frames = []
        cursor = 0
        while cursor < len(data):
            target = 4
            if len(self._pending) >= 4:
                _, target = _PREFIX.unpack_from(self._pending)
            count = min(target - len(self._pending), len(data) - cursor)
            self._pending.extend(data[cursor:cursor + count])
            cursor += count
            if len(self._pending) < 4:
                continue
            message_id, length = _PREFIX.unpack_from(self._pending)
            if length < 4:
                self._pending.clear()
                self._failed = True
                raise ValueError('frame length is smaller than its prefix')
            if len(self._pending) == length:
                frames.append(Frame(message_id, bytes(self._pending[4:])))
                self._pending.clear()
        return frames

    def finish(self):
        """Check EOF; a partial prefix or body is a truncated connection."""
        if self._failed or self._pending:
            raise ValueError('connection ended with invalid or incomplete framing')
