"""Bounded byte operations for the client's shared string-buffer records."""


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
