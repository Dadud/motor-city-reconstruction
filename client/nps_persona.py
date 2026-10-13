"""Recovered persona-map messages and identity fields."""
import struct
from dataclasses import dataclass, field
from client.nps_framing import encode_message, MessageHeader
from client.nps_response import _Reader


@dataclass(frozen=True)
class PersonaMapEntry:
    value_1: int
    value_2: int
    value_3: int
    value_4: int
    name: bytes = field(repr=False)

    @property
    def account_user_id(self):
        """Customer ID in the native persona-info record (offset 0)."""
        return self.value_1

    @property
    def persona_id(self):
        """Persona ID used for lobby login (native record offset 0x38)."""
        return self.value_2

    @property
    def shard_id(self):
        """Shard ID in the native persona-info record (offset 0x50c)."""
        return self.value_3


@dataclass(frozen=True)
class PersonaMaps:
    entries: tuple[PersonaMapEntry, ...]
    trailing_value: int

    @classmethod
    def from_frame(cls, frame):
        """Header-enabled 0x607 response; native reader begins at wire +12."""
        if frame.message_id != 0x607:
            raise ValueError('expected persona-map success reply 0x607')
        MessageHeader.from_frame(frame)
        return cls.decode(frame.body[8:])

    def find(self, persona_id, shard_id):
        """Original local selection comparator 0x4ab740 checks both IDs."""
        for value in (persona_id, shard_id):
            if type(value) is not int or not 0 <= value <= 0xffffffff:
                raise ValueError('persona selection identities must be uint32')
        return next((entry for entry in self.entries
                     if entry.persona_id == persona_id and entry.shard_id == shard_id), None)

    @classmethod
    def decode(cls, payload):
        """0x607 payload: uint16 count, counted records, then one byte.

        The fourth entry value and final byte remain uninterpreted. Exact
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


def encode_persona_activation_request(account_user_id, persona_id, shard_id):
    """Prepare native 0x503 activation; no network or selection side effects.

    Field order follows task 5 at 0x4ab7a0 and serializer 0x7290d0.
    Native uint32 fields have no recovered nonzero validation here.
    """
    values = (account_user_id, persona_id, shard_id)
    if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in values):
        raise ValueError('persona activation identities must be uint32 values')
    return encode_message(0x503, struct.pack('>3I', *values), auxiliary=24)


def native_persona_activation_result(message_id):
    """Original 0x728d10 reply classification, independent of reply body.

    0x207 means success on this auth connection; lobby heartbeat handling
    belongs to a different protocol context. Unknown replies fail with -1.
    """
    if type(message_id) is not int or not 0 <= message_id <= 0xffff:
        raise ValueError('persona activation reply ID must be uint16')
    return {0x207: 0, 0x612: -11}.get(message_id, -1)
