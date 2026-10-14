# Room settings selection before joining

`client/room_selection.py` implements the selection performed by original
`0x450830`. This connects settings lookup/defaults to the recovered argument
producer. It does not fabricate a room-list reply or schedule a join.

Target is the installed `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra static evidence for selection:
`ev_7e2b9ff7c22bf4085d19eb75989bbae9b04588c0e2039102fae1bbb6bbe433cd`.

## Selection order and sources

The receiver is a game-network owner. Its room subobject starts at `+0xa0`.
The portable research interface accepts that room image separately.

| State | Observed result |
| --- | --- |
| Connected short at room `+0xec` or pending DWORD at `+0x3a8` is nonzero, exact current name matches | Return 1, preserve entire room, do not query cache |
| Connected or pending, different name | Return 0, preserve entire room, do not query cache |
| Disconnected and idle, successful settings cache lookup | Clear connected short at settings `+0x4c`, transfer settings, return 1 |
| Disconnected and idle, cache miss | Initialize settings, copy requested name, force `+0x4c` to zero, transfer settings, return 1 |

The cache lookup receiver is **network owner `+0x458`**, not the room receiver.
Wrapper `0x44be10` calls generic lookup `0x45f040` with an explicit comparator
object at its receiver `+0x44`. The generic collection walks existing nodes and
accepts the first comparator result equal to **1**. On a requested output, it
uses collection virtual size/copy methods. Actual cache insertion, room-list
decoding, comparator implementation and copy ownership remain separate work.
The reconstruction therefore accepts a supplied successful cached settings
image, rather than inventing those operations.

Current-name equality (`0x44dba0`) is byte-exact and case-sensitive; a null native
input returns false. The authored selection interface requires a byte string
of at most 31 bytes without NUL and a bounded current-name terminator. Null
selection/unsafe overflow are outside the interface.

Settings initialization (`0x44a460`) writes protocol `0x21`, short `+0x40 = 2`,
byte `+0x44 = 1`, zero strings/scalars/opaque data. It preserves unspecified
padding, including `+0x45` and `+0x4e..0x4f`, and bytes after `+0x159`. The
initializer function accepts a preexisting image so those untouched bytes can
be compared. The cache-miss selection uses zero backing bytes only as an
authored storage choice; untouched padding is not copied into the room by
the [settings transfer](room-settings-transfer.md).

After either new selection, [field transfer](room-settings-transfer.md)
preserves the local server selector at room `+0x39c`. The next
[argument producer](room-request-production.md) reads the selected room name,
protocol, requested channel, opaque bytes and maxReady from the room.
The forced zero at settings `+0x4c` becomes room `+0xec`, the connected short;
**maxReady is settings `+0x46`, room `+0xe6`, and is preserved on cache hits**.

## Original comparisons

```powershell
python -m tools.room_selection_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_room_selection
```

The bounded oracle executes complete `0x450830` entry through return in 144
cases. It executes original name equality, settings initialization and settings
assignment. It checks the entire resulting room, return value, lookup receiver
and call count, unchanged network prefix, and restoration of an emulator-owned
empty exception chain. Only cache lookup `0x44be10` is substituted with an
explicit hit/miss and image. Another 24 randomized initializers match without
substituted calls. Execution is bounded; startup and host imports do not run.

Evidence: name equality
`ev_2683929f0c5c1c31d15140ffe8760bb6152a743df90ab8adfa987a35db5999e9`;
cache wrapper
`ev_bb5bd1b1fc9e7aabb181315db00cfc351577476e058b60204cba30df3573d1ae`;
generic lookup
`ev_a036b2b95b86d8ab11ccc0b323e9e54e0d6417440f22a98d4f271aa0f64381b3`;
initializer
`ev_18ae39c595a52405841e8439bba7e17c089742b9c045360b3cdcde77fa4463b4`.

No live room is discovered or joined. Existing authenticated connection binding,
actual settings cache contents and asynchronous task execution remain required.

The C++20 port additionally matches 24 initializers and 72 Python selections,
including complete images and result/source values. Its native unit test
passes locally on Windows. The Windows/Linux CI matrix includes the comparison;
this local check does not establish a Linux runtime result.
