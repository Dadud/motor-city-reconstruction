"""Recovered encrypted lobby wrapper ID 0x1101 (native receiver 0x7414b0).

Outer framing has a four-byte prefix, with ciphertext immediately following.
The decrypted message retains its own prefix. The native sender rounds up its
scratch-buffer input without clearing the tail; padding is therefore explicit.
These helpers open no socket.
"""
from dataclasses import dataclass, field
import struct

from client.nps_framing import Frame


@dataclass(frozen=True)
class DecodedEnvelope:
    inner: Frame
    padding: bytes = field(repr=False)


def native_encrypts_message(message_id):
    """Recovered selector 0x7381f0, after connection encryption is enabled."""
    if not isinstance(message_id, int) or not 0 <= message_id <= 65535:
        raise ValueError('message ID must fit uint16')
    return message_id not in (0x207, 0x217)


def encrypt_envelope(inner, cipher, *, padding):
    """Build the TCP wrapper with caller-supplied opaque scratch-buffer tail.

    Callers must separately apply the connection encryption flag and heartbeat
    selector. Validation completes before advancing the connection's CBC state.
    """
    if not isinstance(inner, Frame):
        raise ValueError('expected an inner Frame')
    wire = inner.encode()
    if not isinstance(padding, bytes) or len(padding) != (-len(wire)) % 8:
        raise ValueError('padding must exactly complete the final eight-byte block')
    if len(wire) + len(padding) + 4 > 60000:
        raise ValueError('wrapper exceeds original lobby receive limit')
    return Frame(0x1101, cipher.update(wire + padding))


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
