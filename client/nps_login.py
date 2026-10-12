"""Recovered 0x501 payload layout, without authentication/session generation.

Serializer 0x72c120 and string writer 0x7e0c90 in the original main binary.
Field origins: ticket from AuthLogin; authorization mode is 0 for HTTPS and 1
for the alternate NPS AAI branch; opaque string from 0x72c3f0; service ID from
NPSUserLogin's caller; final uint32 from that caller's fourth argument.
The opaque string and final uint32 semantics are not yet established.
"""
from dataclasses import dataclass, field
import struct


def _string(value, limit):
    if not isinstance(value, bytes):
        raise TypeError('native narrow strings must be bytes')
    if b'\0' in value or len(value) > limit:
        raise ValueError('string contains NUL or exceeds original field capacity')
    return struct.pack('>H', len(value)) + value


@dataclass(frozen=True)
class LoginPayload:
    ticket: bytes = field(repr=False)
    authorization_mode: int
    opaque_string: bytes = field(repr=False)
    service_id: bytes
    caller_value: int

    def encode(self):
        if not isinstance(self.authorization_mode, int) or not 0 <= self.authorization_mode <= 65535:
            raise ValueError('authorization mode must fit uint16')
        if not isinstance(self.caller_value, int) or not 0 <= self.caller_value <= 0xffffffff:
            raise ValueError('caller value must fit uint32')
        return (_string(self.ticket, 128) + struct.pack('>H', self.authorization_mode)
                + _string(self.opaque_string, 512) + _string(self.service_id, 64)
                + struct.pack('>I', self.caller_value))

    @classmethod
    def decode(cls, payload):
        if not isinstance(payload, bytes):
            raise TypeError('payload must be bytes')
        cursor = 0

        def take(size):
            nonlocal cursor
            if cursor + size > len(payload):
                raise ValueError('truncated login payload')
            result = payload[cursor:cursor + size]
            cursor += size
            return result

        def string(limit):
            size = struct.unpack('>H', take(2))[0]
            if size > limit:
                raise ValueError('string exceeds original field capacity')
            value = take(size)
            _string(value, limit)
            return value

        ticket = string(128)
        mode = struct.unpack('>H', take(2))[0]
        opaque = string(512)
        service = string(64)
        caller = struct.unpack('>I', take(4))[0]
        if cursor != len(payload):
            raise ValueError('unexpected trailing login payload data')
        return cls(ticket, mode, opaque, service, caller)
