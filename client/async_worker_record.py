"""Recovered local worker header writes, not network packet fields.

The generic worker queue uses task kind, operation ID and worker result at
offsets 0, 4 and 8. Argument bytes begin at 12. Queue storage/threading remain
separate; these helpers preserve every byte outside the observed writes.
"""
from dataclasses import dataclass
import struct


def _uint32(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('worker value requires uint32 bits')
    return value


def _record(value):
    if not isinstance(value, bytes) or len(value) < 12:
        raise ValueError('worker record requires a complete 12-byte header')
    return value


@dataclass(frozen=True)
class StampedOperation:
    record: bytes | None
    counter: int
    operation_id: int


def stamp_operation(record, *, counter, tracked, manager_present=True):
    """The bounded pre-enqueue writes of 0x4a5390.

    Null data or a missing manager returns zero without changing a record or
    counter. Tracked IDs increment with uint32 wrap, skipping zero. Actual queue
    insertion and wakeup are excluded. Size/type checks are authored boundaries.
    """
    _uint32(counter)
    if record is None or not manager_present:
        return StampedOperation(record, counter, 0)
    _record(record)
    if tracked:
        counter = (counter + 1) & 0xffffffff
        if counter == 0:
            counter = 1
        operation_id = counter
    else:
        operation_id = 0
    output = bytearray(record)
    struct.pack_into('<I', output, 4, operation_id)
    return StampedOperation(bytes(output), counter, operation_id)


def store_worker_result(record, result_bits):
    """0x4a55b0 result write; return whether a completion record is queued.

    No operation ID means no completion queue insertion, even though the worker
    writes its result. The returned boolean is not a success classification.
    """
    _record(record)
    _uint32(result_bits)
    output = bytearray(record)
    struct.pack_into('<I', output, 8, result_bits)
    return bytes(output), struct.unpack_from('<I', record, 4)[0] != 0
