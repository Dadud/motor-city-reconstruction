# Shared string-buffer recovery

`0x415410` assigns bytes into the string object held in `ECX`. The object
fields are a data pointer at `+4`, byte length at `+8`, and capacity at `+0xc`;
the byte immediately before the data pointer describes ownership.

`assign_inline_buffer` implements the in-place branch for a uniquely owned
buffer with capacity below 32 when a nonzero requested length fits. It
reproduces the original forward four-byte copies, trailing byte copies, stored
length and NUL terminator. 512 original x86 executions match every
destination byte and the length field; 512 native/Python cases match
byte-for-byte. Both unique sentinels observed by the original (`0` and
`0xff`) are covered.

`assign_buffer` now models the other normal mapped paths: empty assignment
releases unique storage or decrements shared ownership, shared nonempty values
detach, and unique values that outgrow inline capacity release then allocate.
The allocator and release are explicit callbacks. Native and Python versions
match byte-for-byte across 512 deterministic cases, including object fields,
headers, allocation sizes and payloads. This cross-implementation comparison
does not itself prove these new paths against original execution.

The observed allocation helper at `0x415b60` rounds the requested allocation
to a 32-byte boundary plus its ownership header and terminator. Its continuation
at `0x415bda` copies the old prefix, drops the old reference and installs
capacity equal to the requested length. The wrapper at `0x4150b0` clears the
object and releases a unique old allocation. These observations come from
Ghidra evidence `ev_a6e5dc60668639e530995a403d003cf7de410212c8c421f58fcac2bbb990a8ad`,
`ev_ba723a1cfd85349eef7d64ce5c05e7498ccc1d5cff85b495b3d90ce4380d231b`, and
`ev_e25217d6bd48def98845f4d79144d504deaf77b55600b4857658dad36d55f0c0`.
The assignment function itself was re-inspected as
`ev_59be61c4dd9eaa8561597bcfa990fda5da366583031564b048f1928b635ed826`.

Allocator failure, exception unwinding and source pointers into storage freed
during unique growth remain outside the model. The adjacent `0x4154c0`
length-and-terminator primitive is implemented natively and is composed by the
C++ inline assignment.
