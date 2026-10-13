"""Recovered persona-map request; response and activation remain separate."""
import struct
from dataclasses import dataclass, field
from client.nps_framing import encode_message
from client.nps_response import _Reader


@dataclass(frozen=True)
class PersonaMapEntry:
    value_1: int
    value_2: int
    value_3: int
    value_4: int
    name: bytes = field(repr=False)


@dataclass(frozen=True)
class PersonaMaps:
    entries: tuple[PersonaMapEntry, ...]
    trailing_value: int

    @classmethod
    def decode(cls, payload):
        """0x607 payload: uint16 count, counted records, then one byte.

        Entry meanings and final byte meaning remain uninterpreted. Exact
        record lengths are checked beyond the original reader's copy behavior.
        """
        reader = _Reader(payload)
        count = struct.unpack('>H', reader.take(2))[0]
        # Each entry needs a two-byte outer count plus 18 minimum record bytes.
        if count > max(0, (len(payload)-3)//20):
            raise ValueError('persona-map count exceeds available payload')
        entries = []
        for _ in range(count):
            record = reader.nested()
            entries.append(PersonaMapEntry(record.u32(), record.u32(),
                record.u32(), record.u32(), record.counted(32)))
            record.finish()
        trailing = reader.take(1)[0]
        reader.finish()
        return cls(tuple(entries), trailing)


def encode_persona_maps_request(account_user_id):
    """Native 0x71dab0 request 0x532, serializer 0x71e340.

    Uses the account ID from authenticated login success, not a persona ID.
    This only prepares bytes and never sends an account request.
    """
    if type(account_user_id) is not int or not 1 <= account_user_id <= 0xffffffff:
        raise ValueError('persona-map account ID must be a nonzero uint32')
    return encode_message(0x532, struct.pack('>I', account_user_id), auxiliary=16)
