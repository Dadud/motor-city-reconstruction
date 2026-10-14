# Asynchronous room worker result handling

Original function `0x44eba0` calls channel-add and applies its return value to
the asynchronous room worker. This is a separate layer from lobby dispatcher
task 7: the result handling here retains a nonnegative channel value and returns
zero, rather than only translating returned value 1.

All offsets below are relative to the function's `ECX` base. The worker interface
used by another dispatch layer is at base + 12; these offsets must not be
applied relative to that interface pointer.

| Original field | Observed use |
| --- | --- |
| `+0x3b4` | Interface token whose virtual entry `+8` receives channel-add |
| `+0x3ac`, `+0x3b0` | Two opaque 32-bit values forwarded after the room argument |
| `+0xc0` | Retained nonnegative channel-add return |
| `+0xec` | Two-byte field set to 1 on nonnegative return |
| `+0x3a4` | Retained negative channel-add return |
| `+0x3a8` | Four-byte field cleared on either result branch |
| `+0x39c` | Value forwarded to completion helper; no wire transaction semantics asserted |

The virtual call receives the original room argument unchanged. For a result
greater than or equal to zero, the function writes `+0xec`, `+0xc0` and
`+0x3a8`, then invokes helper `0x456ae0` with `ECX = base + 0x1fc` and two
stack arguments: the value at `+0x39c` and the newly retained value at `+0xc0`.
It returns zero. The previous error field at `+0x3a4` is untouched.

For a negative result, it writes that signed value at `+0x3a4`, clears
`+0x3a8`, and returns the negative value unchanged. It does not invoke the
completion helper or reset the previous channel/ready fields. Preserving these
untouched bytes matters when comparing failed requests with the original.

`client/room_join_result.py` exposes pure call extraction and result-image
transformation. Its notification record describes the helper boundary; it does
not execute the helper. Images include caller-supplied prior state and preserve
all unrelated bytes. Interface and caller values remain opaque integers.

Evidence: executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`,
REA function evidence
`ev_2d59c497f973b38df2333e2d6d77873c1b72a5cf4c63cf8820a84ceaefd20745`.
The authored model uses assembly-observed offsets and writes; decompiler output
and original executable bytes are not included in the repository.

Run the bounded original comparison with your separately supplied executable:

```text
python -m tools.room_join_result_oracle /path/to/mcity.exe
```

On the inspected executable this matches **72 cases**: 35 nonnegative and 37
negative results, including signed boundaries, zero, one, common channel errors,
random prior images, random forwarded values and four correlation-field
boundaries. It compares the entire supplied `0x3c0`-byte worker image, return
value, virtual-call arguments, helper owner, helper arguments and call order.

Execution starts at the original function entry and returns through its original
epilogue. Logging is disabled by zeroing global `0xb36a9c`; virtual channel-add
and helper `0x456ae0` are captured substitutions with explicit return behavior.
The comparison establishes this result transition, **not** those substituted
functions' implementation, actual worker threads, server negotiation, queue
ordering or a live race join. No sockets or credentials are used. The bounded
[room argument producer](room-request-production.md) is now recovered separately;
authenticated room-state population and runtime verification remain required.

The C++20 port in `native/include/mco/room_join_result.hpp` belongs to `mco_core`.
Native unit checks cover signed result boundaries, full image preservation,
forwarded arguments, notification fields and rejected sizes. The token fields
are never invoked as original host pointers. These checks supplement the Python/
original comparison; they do not prove an authenticated native room join.
