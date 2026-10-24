# Shared string-buffer recovery

`0x415410` assigns bytes into the string object held in `ECX`. The observed
object fields are a data pointer at `+4`, byte length at `+8`, and inline
capacity at `+0xc`; the byte immediately before the data pointer distinguishes
the unique-buffer path from shared ownership.

`client.string_buffer.assign_inline_buffer` and its C++ counterpart implement
the bounded in-place branch: the buffer is uniquely owned, capacity is below
32, and a nonzero requested length fits. They reproduce the original forward
four-byte copies, trailing byte copies, stored length and NUL terminator.
512 original x86 executions match every destination byte and the length field;
512 native/Python cases match byte-for-byte. Both unique sentinels observed by
the original (`0` and `0xff`) are covered.

The shared-buffer detach, empty assignment, heap allocation, exception and
cleanup branches remain untranslated. In particular, the bounded adapter does
not claim to model the allocator at `0x415b60` or the release path at
`0x4150b0`. The adjacent `0x4154c0` length-and-terminator primitive is already
implemented natively and is composed by the C++ inline assignment.
