# Room worker dispatch boundary

The original room worker `0x44e820` is a separate local dispatcher from the game
network worker `0x454d50`. Their task numbers must not be mixed. This observation
narrows the research path for asynchronous room joining; neither catalogue
establishes a runtime sequence or supplies authenticated arguments.

The room worker reads a task kind at offset zero and passes arguments beginning
at byte 12. Its task zero calls `0x44eba0` with that argument region. The latter
invokes the lobby interface's channel-add entry at vtable offset 8 with the
argument pointer and two values stored on the room object at `0x3ac`/`0x3b0`.
It does not supply the game worker's task-seven constants at this call site.

A nonnegative channel-add result is stored as the room's communication ID at
`0xc0`; the room short at `0xec` becomes one, the field at `0x3a8` becomes zero,
and helper `0x456ae0` receives the room object's field `0x39c` and communication
ID. A negative result is stored at `0x3a4`, the field `0x3a8` is cleared, and the
error is returned. Debug text suggests asynchronous room connection, but the
caller, scheduling order and complete meaning of these fields remain unverified.

Several other worker cases use a virtual object loaded from `0x3a8`, whereas
the join helper uses the interface at `0x3b4` and clears `0x3a8`. The apparent
reuse of `0x3a8` requires object-lifetime and construction tracing before assigning
a portable type. No field is treated as a socket or callback solely from this
observation. Password/name/capacity diagnostic references are also insufficient
to populate a complete authenticated room argument.

Next recovery work is to trace the room object's constructor, task scheduling
and producer of the argument region and `0x3ac`/`0x3b0`, then compare actual
original-client sessions. The worker's reported caller list is empty; virtual
registration and queue ownership still need explicit investigation.

Static Ghidra 12.1.4 evidence: join caller
`ev_44022a6f12e8ca5829b63bda50f1ab8cf7a18858ac1191c119506cb059f76dae`;
worker `ev_6db0f83495745c5ce4f0a890522b4c1a1406153602b1be9cbc72c71c1049ccd8`.
Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
These are static findings, not native worker comparisons or live joins.
