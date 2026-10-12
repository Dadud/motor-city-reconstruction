"""Recovered encrypted lobby wrapper ID 0x1101 (native receiver 0x7414b0).

Outer framing has a four-byte prefix, with ciphertext immediately following.
The decrypted message retains its own prefix. Padding bytes remain opaque until
native filter end/reset behavior has been verified; this helper opens no socket.
"""
from dataclasses import dataclass, field
import struct

from client.nps_framing import Frame


@dataclass(frozen=True)
class DecodedEnvelope:
    inner: Frame
    padding: bytes = field(repr=False)


def decrypt_envelope(outer, cipher):
    if not isinstance(outer, Frame) or outer.message_id != 0x1101:
        raise ValueError('expected encrypted lobby wrapper 0x1101')
    if not isinstance(outer.body, bytes) or not outer.body or len(outer.body) % 8:
        raise ValueError('wrapper must contain complete ciphertext blocks')
    if len(outer.body)+4 > 60000:
        raise ValueError('wrapper exceeds original lobby receive limit')
    decoded = cipher.update(outer.body)
    if len(decoded) < 4:
        raise ValueError('decrypted message has no complete prefix')
    message_id, length = struct.unpack_from('>HH', decoded)
    if length < 4 or length > len(decoded) or len(decoded)-length >= 8:
        raise ValueError('decrypted inner message has inconsistent length')
    return DecodedEnvelope(Frame(message_id, decoded[4:length]), decoded[length:])
