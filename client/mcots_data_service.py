"""Serial post-login requests over an accepted primary MCOTS session."""
from collections import deque
from dataclasses import dataclass, field
import struct
import time
from client.mcots_data_assembly import MCOTSDataAssembler
from client.mcots_framing import MCOTSFrame
from client.mcots_response import decode_completion
from client.nps_transport import _timeout
from client.owned_parts import OwnedInstanceCache


def encode_data_request(operation, *, argument=0):
    """Ten-byte native payload, using the normal pool's zero initialization."""
    if type(operation) is not int or operation not in (0x144,0x142,0x16b,0x185,0xac,0x6c,0x108):
        raise ValueError('unsupported post-login request operation')
    if type(argument) is not int or not 0 <= argument <= 0xffffffff:
        raise ValueError('expected uint32 request argument')
    if operation not in (0x142,0xac,0x6c,0x108) and argument:
        raise ValueError('request has no recovered argument field')
    return struct.pack('<HI',operation,argument)+bytes(4)


@dataclass(frozen=True)
class MCOTSPersonaStartup:
    persona_id: int
    car_pairs: tuple[bytes, ...] = field(repr=False)
    profile: bytes = field(repr=False)
    extensions: tuple[tuple[bytes, ...], ...] = field(repr=False)
    part_seeds: tuple[bytes, ...] = field(default=(),repr=False)


def fetch_persona_startup(client, persona_id, *, timeout=120, instance_cache=None):
    """Fetch the car list and original profile-plus-supplement sequence.

    Preserve the eight-byte car pairs; resolving complete car objects from
    the original cache/database is separate. Use one caller-defined deadline.
    """
    if type(persona_id) is not int or not 1 <= persona_id <= 0xffffffff:
        raise ValueError('expected nonzero selected persona ID')
    if instance_cache is None:
        instance_cache = OwnedInstanceCache()
    if not isinstance(instance_cache,OwnedInstanceCache):
        raise ValueError('expected owned-instance cache')
    deadline = time.monotonic()+_timeout(timeout)
    replies = []
    for operation in (0xac,0x6c,0x108):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            client.session.close()
            raise TimeoutError('MCOTS persona startup timed out')
        replies.append(client.fetch(operation,argument=persona_id,timeout=remaining))
        if operation == 0xac:
            instance_cache.apply_persona_car_pairs(persona_id,replies[-1].records)
            seeds = instance_cache.part_cache().seed_car_pairs(replies[-1].records)
    cars, profile, supplement = replies
    merged = profile.records[0][:0x1ab]+supplement.records[0]
    return MCOTSPersonaStartup(persona_id,cars.records,merged,
                              tuple(reply.extensions for reply in replies),seeds)


class MCOTSDataRejected(ValueError):
    def __init__(self, operation, result_code):
        self.operation, self.result_code = operation, result_code
        super().__init__('MCOTS data request was rejected')


class MCOTSDataClient:
    """Use serially; retain unrelated application frames for their consumers.

    The caller supplies the next unused transaction ID and owns the session.
    Resource and transport failures close it. A correlated server rejection
    leaves the connection usable, as in the original data completion handlers.
    """
    def __init__(self, session, *, first_transaction, max_pending_bytes=1024*1024):
        if type(first_transaction) is not int or not 0 <= first_transaction <= 0xffffffff:
            raise ValueError('expected uint32 next transaction')
        if type(max_pending_bytes) is not int or max_pending_bytes < 1:
            raise ValueError('expected positive pending-frame capacity')
        self.session, self._next = session, first_transaction
        self._pending, self._pending_bytes = deque(), 0
        self.max_pending_bytes = max_pending_bytes

    def pop_pending(self):
        """Return an unrelated decoded frame, or None if none is retained."""
        if not self._pending:
            return None
        frame = self._pending.popleft()
        self._pending_bytes -= len(frame.payload)+11
        return frame

    def fetch(self, operation, *, argument=0, timeout=120,
              max_bytes=16*1024*1024, max_pages=1024):
        payload = encode_data_request(operation, argument=argument)
        timeout = _timeout(timeout)
        transaction = self._next
        assembly = MCOTSDataAssembler(operation,transaction,max_bytes=max_bytes,max_pages=max_pages)
        self._next = (transaction+1)&0xffffffff
        deadline = time.monotonic()+timeout
        try:
            self.session.send(MCOTSFrame(transaction,0,payload),timeout=timeout)
            while True:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('MCOTS data request timed out')
                frame = self.session.receive(timeout=remaining)
                opcode = struct.unpack_from('<H',frame.payload)[0] if len(frame.payload)>=2 else None
                # Operation 0x198 updates a cache independently of transaction
                # correlation in the original completion handler.
                if frame.transaction_value != transaction or opcode == 0x198:
                    size = len(frame.payload)+11
                    if self._pending_bytes+size > self.max_pending_bytes:
                        raise ValueError('MCOTS pending frames exceed configured capacity')
                    self._pending.append(frame)
                    self._pending_bytes += size
                    continue
                if opcode in (0x65,0x66,0x67,0x107):
                    completion = decode_completion(frame,transaction_value=transaction,operation=operation)
                    if not completion.successful:
                        raise MCOTSDataRejected(operation,completion.result_code)
                    raise ValueError('MCOTS data acknowledgement lacks its direct data record')
                result = assembly.feed(frame)
                if result is not None:
                    return result
        except MCOTSDataRejected:
            raise
        except Exception:
            self.session.close()
            raise
