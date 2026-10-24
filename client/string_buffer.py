"""Bounded ports for the client's shared string-buffer records."""

from dataclasses import dataclass


def assign_inline_buffer(destination, source, length, capacity):
    """Port the in-place branch of 0x415410 for a unique inline buffer.

    The original takes the shared string object in ECX, a source byte pointer,
    and a byte count. This branch applies when the source and destination are
    mapped, the destination is uniquely owned, its capacity is below 32, and
    the nonzero requested length fits. Shared-buffer release and allocation
    remain caller boundaries.
    """
    if (not isinstance(destination, (bytearray, memoryview)) or
            (isinstance(destination, memoryview) and destination.readonly) or
            not isinstance(source, (bytes, bytearray, memoryview))):
        raise TypeError('mutable destination and byte source required')
    if type(length) is not int or type(capacity) is not int:
        raise ValueError('integer byte length and capacity required')
    if not 0 < length <= capacity < 0x20:
        raise ValueError('in-place path requires 0 < length <= capacity < 32')
    if len(destination) < capacity + 1 or len(source) < length:
        raise ValueError('mapped source and destination ranges required')

    source = memoryview(source)
    offset = 0
    word_count = length >> 2
    for _ in range(word_count):
        chunk = bytes(source[offset:offset + 4])
        destination[offset:offset + 4] = chunk
        offset += 4
    for _ in range(length & 3):
        destination[offset] = source[offset]
        offset += 1
    destination[length] = 0
    return length


@dataclass
class BufferRecord:
    """One 0x415410 object; storage[0] is the byte before its data pointer."""

    storage: bytearray | None
    length: int
    capacity: int


def assign_buffer(record, source, length, allocate, release):
    """Model the mapped-buffer paths of original 0x415410.

    ``allocate(size)`` returns writable storage including the one-byte header;
    ``release(storage)`` observes a uniquely-owned old allocation. Shared
    allocations are detached by decrementing their header. Allocator failure,
    exception unwinding, and source pointers into storage freed by ``release``
    are deliberately outside this adapter's contract.
    """
    if not isinstance(record, BufferRecord):
        raise TypeError('BufferRecord required')
    if not callable(allocate) or not callable(release):
        raise TypeError('allocator and release callbacks required')
    if type(length) is not int or not 0 <= length <= 0xfffffffd:
        raise ValueError('length must be an unsigned byte count accepted by 0x415410')
    if not isinstance(source, (bytes, bytearray, memoryview)) or len(source) < length:
        raise ValueError('mapped source range required')

    old = record.storage
    if old is not None and (not isinstance(old, (bytearray, memoryview)) or
                            (isinstance(old, memoryview) and old.readonly) or
                            len(old) < record.capacity + 2):
        raise ValueError('buffer storage must include a header and capacity plus terminator')
    old_length, old_capacity = record.length, record.capacity
    header = old[0] if old is not None else 0
    unique = old is None or header in (0, 0xff)

    if unique:
        if length == 0:
            if old is not None:
                release(old)
            record.storage = None
            record.length = record.capacity = 0
            return 0
        if old is not None and old_capacity < 0x20 and length <= old_capacity:
            assign_inline_buffer(memoryview(old)[1:], source, length, old_capacity)
            record.length = length
            return length
        if old is not None:
            release(old)
            record.storage = None
            record.length = record.capacity = 0
        old_length = 0
    elif length == 0:
        old[0] = (header - 1) & 0xff
        record.storage = None
        record.length = record.capacity = 0
        return 0

    rounded = length | 0x1f
    if rounded > 0xfffffffd:
        rounded = length
    allocation_size = (rounded + 2) & 0xffffffff
    if allocation_size & 0x80000000:
        allocation_size = 0
    if allocation_size < length + 2:
        raise ValueError('allocator size is outside the bounded mapped domain')
    new = allocate(allocation_size)
    if not isinstance(new, bytearray) or len(new) < allocation_size:
        raise ValueError('allocator returned an undersized mutable allocation')
    new[0] = 0

    # 0x415bda preserves the prefix before 0x415410 overwrites it. This matters
    # for a source that aliases the old shared buffer, so snapshot source before
    # changing either ownership header.
    source_copy = bytes(memoryview(source)[:length])
    copied = min(old_length, length) if old is not None else 0
    if copied:
        new[1:1 + copied] = old[1:1 + copied]
    if old is not None and not unique:
        old[0] = (header - 1) & 0xff
    new[1:1 + length] = source_copy
    new[length + 1] = 0
    record.storage = new
    record.length = length
    record.capacity = length
    return length
