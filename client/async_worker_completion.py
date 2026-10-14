"""Recovered worker completion selection/removal, with owned portable records.

Original queues use 0x80c-byte images and operation IDs at offset 4. This model
does not allocate native nodes, expose pointers, schedule workers or lock threads.
"""
from dataclasses import dataclass
import struct

WORKER_RECORD_SIZE = 0x80c


def _record(value):
    if not isinstance(value, bytes) or len(value) != WORKER_RECORD_SIZE:
        raise ValueError('completion requires an exact 0x80c-byte worker record')
    return value


@dataclass(frozen=True)
class CompletionQuery:
    found: bool
    record: bytes | None


class WorkerCompletionQueue:
    """Single-owner completion queue; preserve order and remove first match.

    Queue node allocation/free and original optional critical sections remain
    outside this owned-record boundary. Owners must serialize access themselves.
    """
    def __init__(self, records=()):
        self._records = [_record(record) for record in records]

    @property
    def records(self):
        return tuple(self._records)

    def append(self, record):
        self._records.append(_record(record))

    def query(self, operation_id, *, copy_output=True):
        if type(operation_id) is not int or not 1 <= operation_id <= 0xffffffff:
            raise ValueError('completion query requires a nonzero uint32 operation ID')
        if type(copy_output) is not bool:
            raise TypeError('copy_output must be boolean')
        for index, record in enumerate(self._records):
            if struct.unpack_from('<I', record, 4)[0] == operation_id:
                removed = self._records.pop(index)
                return CompletionQuery(True, removed if copy_output else None)
        return CompletionQuery(False, None)


@dataclass(frozen=True)
class CompletedOperation:
    kind: int
    operation_id: int
    result: int
    argument: bytes

    @classmethod
    def from_record(cls, record):
        """Interpret a retrieved record; result is the signed worker return.

        This does not classify a task kind or presume that a positive result
        means success. Only the operation's recovered consumer can decide that.
        """
        _record(record)
        kind, operation_id, bits = struct.unpack_from('<III', record)
        result = bits if bits < 0x80000000 else bits - 0x100000000
        return cls(kind, operation_id, result, record[12:])
