# Leaving a room before changing its settings

The original room-switch caller `0x4509c0` first calls room disconnect
`0x44d750` with waiting enabled. Disconnect resets two local containers through
`0x4485f0` (room `+0x2e0`) and `0x456930` (room `+0x1fc`), in that order.
Those container effects are separate from the settings image described here.

If the connected short at `+0xec` is zero, the function resets settings and
returns zero without queuing a disconnect. This branch does not wait for or
clear a nonzero pending flag at `+0x3a8`. If connected and pending, it instead
repeatedly calls `Sleep(0)` until pending clears, then reevaluates the connected
short. It may therefore enter the disconnected reset branch after that wait.

A stable connected room saves the old server selector at `+0x39c` and channel
at `+0xc0` into the first eight argument bytes of local room task 1. It resets
settings **before** queuing that task through worker receiver room `+12`.
With waiting disabled it requests an untracked operation and returns zero.
With waiting enabled it requests tracking, queries completion and pumps the
application until completion or an application abort. Completion returns the
worker's signed result; an abort returns `-51`. These waits are observed static
control flow and are not implemented by the stable preparation helper.

The stack-local task is not cleared in this producer. Its task kind and first
eight argument bytes are initialized, but the remaining payload bytes are not
given meaning by this path. The portable helper exposes only initialized data.
Any later owned queue materialization must document its authored padding rather
than claim parity for unspecified stack bytes.

## Settings reset

The routine clears the 32-byte name, 16-byte secondary string and 256-byte
opaque data region. Channel and neighboring uint32 fields at `+0xc0..+0xcb`,
`+0x1f4`, `+0xe8` and `+0xf0` become zero. It sets protocol `+0xcc` to `0x21`,
short `+0xe0` to 2, and byte `+0xe4` to 1. Shorts at `+0xe2`, `+0xec`, `+0x1f8`
and `+0xe6` become zero. Unwritten bytes retain their prior values, including
the server selector, pending flag, retained errors and padding bytes.

`client/room_disconnect.py` implements this selective reset and initialized task
preparation. It requires a stable connected image: a pending connected operation
raises `PendingRoomOperation` so a caller cannot silently bypass the original
wait. That exception is an authored boundary, not an original exception. The
helper does not reset containers, schedule tasks, pump events or contact a server.

Four focused tests cover disconnected/pending behavior, connected preparation,
preserved fields, extraction of the reset settings, waiting flags and invalid
images. `tools/room_disconnect_oracle.py` compares 32 original disconnected
returns and 64 connected preparations, across random complete images and both
waiting switches. It executes from entry through return or the enqueue boundary;
only container reset calls and enqueue are substituted. Logging is disabled.
Pending waits, completion pumping, container contents and live sockets are excluded.

```text
python -m tools.room_disconnect_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

## Downstream channel close

Room dispatcher `0x44e820` receives worker `this = room +12`. Task 1 forwards
the two initialized values to interface entry `+0x20` (full room interface field
`+0x3b4`). The singleton table maps that entry to `0x730f50`. With channel zero,
that interface performs no channel-removal call: the primary channel requires
server logoff. With a nonzero channel it calls registry helper `0x73ec30`, but
returns zero regardless of that helper's result. Thus a zero worker result alone
does not prove a server acknowledged removal.

The lower helper has a communication cleanup branch and constructs opcode
`0x105`. Its packet argument decoding, reference lifetime and actual delivery
still need recovery and verification. Room cleanup must not be substituted for
the distinct server-disconnect operation.

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra 12.1.4 evidence:

| Observation | Evidence |
| --- | --- |
| Switching caller | `ev_30a7fdbaae68a4c70f8ed085fcd42ee41c41b89e8de61b638ef153090d238e09` |
| Disconnect producer and settings reset | `ev_11eebe917bf56c1fcf4c590a33cde1e3fc0c1f280a7d104b7d81f880484d372f` |
| Room worker dispatch | `ev_909326c29111fb1725c9250b25bede9c8a4f9c5b5b8a0ed1cfbcb7120df3a135` |
| Channel-close interface | `ev_4337293aa59d20168cc79d7aded866525dad0c0005433ac5f231644afd78f842` |
| Lower registry helper | `ev_74e9a2d6c7c16ccdd8f34fbb27c4ff7ec179e8311ecfd4174ddec3fd14f90165` |

The lower helper's decompiler signature fails to recover its stack arguments;
assembly establishes the interface call and opcode observation. Its pseudocode
alone is not a verified source-level implementation.

## Native port

`native/include/mco/room_disconnect.hpp` implements equivalent stable-state
preparation, optional initialized arguments, tracking/return intents and the
pending-operation boundary. Its native unit test and 96 C++/Python whole-image
comparisons pass on Windows. The native CI matrix includes the differential
runner on Windows and Linux; actual Linux results remain subject to that run.

```text
python -m tools.native_room_disconnect_compare build/native-check/mco_room_disconnect_compare.exe
```
