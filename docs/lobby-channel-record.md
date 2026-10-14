# Channel argument initialization and serializer-record construction

The room argument is not already a wire payload. `0x743d50` initializes a
channel object from that argument, the channel-add path fills connection/caller
values, and `0x7398a7..0x739a0e` copies selected fields into the serializer record.
`client/lobby_channel_record.py` reproduces the bounded data initialization and
record-copy steps. Connection lookup, socket setup and live room choice remain
outside this interface.

The research functions require an explicit allocation image. The original
constructor allocates `0x3bc` bytes but does not initialize every byte. Silently
zeroing those bytes would hide a real recovery question. Vtable installation and
host critical-section initialization are excluded from the portable data model;
they are not gameplay or wire values.

## Argument fields

The supported argument image is `0x15c` bytes. The constructor reads through
`0x151`; the wait path separately reads an optional cancellation function/value
pair at `0x154` and `0x158`. Those native addresses are not invoked by this model.

| Argument offset | Observed channel initialization |
| --- | --- |
| `0x00` | Server selector retained at object `0x04` |
| `0x04` | Requested protocol retained at `0x5c` |
| `0x08` | Requested channel ID retained at `0x08` |
| `0x0c` | Complete flags retained at `0x190`; also supplies masked shorts |
| `0x10` | Name: `strncpy` of 30 bytes into object `0x0c` |
| `0x30` | Requested port read by the channel-add path, not the constructor |
| `0x34` | Exactly 17 password bytes copied into object `0x70` |
| `0x48`, `0x4c` | Opaque uint32 values retained at `0x88`, `0x8c` |
| `0x50` | Exactly 256 opaque bytes copied into object `0x90` |
| `0x150` | Short retained at `0x86`; room diagnostic labels it `maxReady` |

Flags initialize object `0x6e` with precedence: bit 0 gives 1; otherwise bit 2
gives 4; otherwise value 2. Object `0x6a` receives `flags & 0x20`, and object
`0x82` receives `flags & 0x4000`. These are retained bit patterns, not normalized
booleans. Their complete gameplay meanings remain unresolved.

Defaults include shorts 0 at `0x64`/`0x66`, short 1 at `0x68`, byte 1 at `0x84`,
and zero contact/address fields. The complete original argument flags survive
at the serializer record's `0x1a0` field.

## Connection values and untouched bytes

Channel-add writes its two opaque caller values to object `0x2c` and `0x30`.
Task 7 supplies -1 and 1. Their presence does not establish callable callback
types. The user ID comes from server connection `0x108` into object `0x60`.
The TCP path uses the existing connection socket and TCP port; a conflicting
requested port is replaced with that existing port. Requested `0x42` is still
present in the initial wire record; normalization to `0x21` occurs after sending.

The materialization function expects these overrides already supplied in its
image. It neither invents their values nor selects a transport from `FastJoin`.

Examples of bytes that survive from the allocation image:

| Location | Why it remains unresolved |
| --- | --- |
| Object `0x2a..0x2b` -> record `0x22..0x23` | 30-byte name copy leaves the last two bytes of the 32-byte region untouched |
| Record `0x85` | Password copy writes 17 bytes through `0x84`; the following byte is not copied |
| Record `0x8a..0x8b` | Materializer writes the next short at `0x8c`; this serialized short remains untouched |

The bounded codec still requires NUL-terminated strings. A 30-byte nonterminated
name and nonzero allocation tail fails that safety boundary. Whether upstream
producers or the allocator reliably clear these locations needs runtime evidence.
Neither successful synthetic comparisons nor a chosen zero image proves that.

## Evidence and verification

Target: original `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4.

- Constructor `0x743d50`: `ev_14df97a517e0986b98f1ce863f52406f38e8f32be825efe40491c66ad8cf330b`.
- Data defaults `0x7440c0`: `ev_e6aa9342bf7da0d33a8bca8bc680777d1e65b545c9d79c6d6466b86e2612d571`.
- Channel-add/materialization `0x738f00`: `ev_6d16bea2989f4c63bd2dabf36117c35301a413fa438ec019bd5bc5c4a31ee39b`.
- Room operation `0x44eba0`: `ev_2d59c497f973b38df2333e2d6d77873c1b72a5cf4c63cf8820a84ceaefd20745`.
- Room dispatcher `0x44e820`: `ev_909326c29111fb1725c9250b25bede9c8a4f9c5b5b8a0ed1cfbcb7120df3a135`.

```powershell
python -m tools.lobby_channel_record_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Windows bounded execution: 36 constructor cases and 36 serialized-record copy
cases match. Inputs vary flags, name lengths, allocation contents and synthetic
caller/connection fields. Original `strncpy` executes; only
`InitializeCriticalSection` is replaced with an inert `RET 4`. Vtable identity
is excluded from constructor equality. The record comparison covers the
`0x1a4`-byte serializer input, not the extra metadata short written after it.

The TCP listener's non-heartbeat path (`0x7413e0`) decodes messages, enqueues a
local record and signals an event. It does not directly complete channel-add.
Evidence: `ev_3e22e4e6d07690865815feeb4cdeb0d21e90d924353786892e097d15e790560d`.
Queue consumption and reply correlation with the waiting server object remain
unrecovered. No room request or account login runs in this oracle.

Next recovery: trace authenticated room argument producers, establish untouched
byte initialization, recover queue dispatch/error replies and finish the channel
join lifecycle. Full race entry also requires original task ordering and live
server scenarios.
