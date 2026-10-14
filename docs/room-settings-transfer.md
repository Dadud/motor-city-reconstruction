# Assigning settings before a room request

Original wrapper `0x44db80` assigns a separate settings record into the room
at room offset `0xa0`, through `0x44a9d0`. Assembly shows both functions return
their destination receiver in EAX, even though the decompiler declares them
void. This is a selective field copy, not a replacement of the room object.

The original first copies the name through its terminating NUL, then all 256
opaque bytes at settings `+0x54`, then the secondary string at `+0x30` through
its NUL. Each string's remaining destination tail is preserved. In particular,
assigning a shorter name does not clear the previous longer name's suffix.
Consumers must respect the terminator rather than serialize the entire old tail
as a new string.

The subsequent scalar copies, in observed order, are:

| Settings offset | Width in bytes | Destination |
| --- | --- | --- |
| `0x24` | 4 | Room `+0xc4` |
| `0x2c` | 4 | Room `+0xcc`: requested protocol |
| `0x20` | 4 | Room `+0xc0`: requested channel |
| `0x40` | 2 | Room `+0xe0` |
| `0x154` | 4 | Room `+0x1f4` |
| `0x42` | 2 | Room `+0xe2` |
| `0x4c` | 2 | Room `+0xec` |
| `0x158` | 2 | Room `+0x1f8` |
| `0x46` | 2 | Room `+0xe6`: readiness input |
| `0x48` | 4 | Room `+0xe8` |
| `0x44` | 1 | Room `+0xe4` |
| `0x28` | 4 | Room `+0xc8` |
| `0x50` | 4 | Room `+0xf0` |

Other meanings remain private/unknown. These copies do not assign the room's
server selector at `+0x39c`; its [connection-result source](room-server-binding.md)
is recovered separately. The connected short at `+0xec` is copied from the
supplied settings; this function does not independently validate it.

`client/room_settings.py` implements the selective copy and preserves the entire
remaining room image. Its authored safety boundary requires independent immutable
images, a NUL within the name's 32-byte and secondary string's 16-byte fields,
and sufficient source/destination sizes. Original unbounded string-copy overflow
and overlapping source/destination semantics are excluded.

Three focused tests check full-image preservation, maximum strings, rejection
boundaries and extraction into the existing room-request input reader. The
bounded oracle executes both original functions through their returns without
substituted callable boundaries or imports. Eighty cases vary both string lengths
and random preexisting bytes, comparing the complete destination, unchanged source
and return receiver. It does not launch a client or contact a server.

```text
python -m tools.room_settings_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra 12.1.4 wrapper evidence:
`ev_97fcba5c2b678c79ae65f05b4f0afb8f7e0c611bce3af05fbb76b9eb803e4c0a`;
assignment evidence:
`ev_7917edcd0050a8d8a9510f5803bdecff729f0b8eedbb4ac18233d35f2de0c43b`.
Authenticated settings selection, source construction in each caller, worker
scheduling and live room acceptance remain required before racing.

## Native port

The C++20 port in `native/include/mco/room_settings.hpp` reproduces the same
ordered assignment and image/string boundaries. A native unit test covers
preserved bytes, maximum strings and invalid inputs. Eighty native/Python cases
compare complete images including trailing bytes; they match locally on Windows.
The CI matrix includes the differential runner on Windows and Linux, with Linux
results subject to the actual CI run.

```text
python -m tools.native_room_settings_compare build/native-check/mco_room_settings_compare.exe
```
