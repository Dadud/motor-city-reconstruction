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

The constructor `0x44cce0` installs the room-worker vtable `0x83bc94` at object
offset 12. Table entry `+4` points to `0x44e820`. The worker's task-zero branch
explicitly subtracts 12 from its `this` pointer before calling `0x44eba0`.
Other worker cases use their subobject-relative field `0x3a8`, which is the full
room object's lobby-interface field `0x3b4`. It is therefore a different field
from full-object `0x3a8`, cleared by the join helper. An earlier interpretation
that these offsets described one reused field omitted the `this` adjustment;
the original instructions resolve that ambiguity. Password/name/capacity
diagnostic references remain insufficient to populate a complete authenticated
room argument.

Next recovery work is to trace the room object's constructor, task scheduling
and producer of the argument region and `0x3ac`/`0x3b0`, then compare actual
original-client sessions. The worker's reported caller list is empty; virtual
registration and queue ownership still need explicit investigation.

Static Ghidra 12.1.4 evidence: join caller
`ev_44022a6f12e8ca5829b63bda50f1ab8cf7a18858ac1191c119506cb059f76dae`;
worker `ev_6db0f83495745c5ce4f0a890522b4c1a1406153602b1be9cbc72c71c1049ccd8`.
Constructor `ev_78bcc28c73bf0682446833d51b09ca9ac7d9cd2300a4de0acdf5712abac226c7`;
vtable bytes `ev_dd2d1546834c1a7bcc757e008a83d4f8b5bf9c9cd9395bc1dff9e8020d0c90dc`.
Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
These are static findings, not native worker comparisons or live joins.
