# Channel-add wire payload recovery

The original `0x738f00` channel-add routine builds a native record, serializes it
with opcode `0x106`, sends it through the existing server TCP connection, and
waits for a reply. It accepts `0x214` and `0x215` at this boundary. This extends
the earlier [channel validation findings](lobby-channels.md); it does not yet
establish a complete authenticated room join.

## Serializer layout

`0x7e5e60` routes `0x106`, `0x112`, and `0x113` to `0x7e4c30`, with a
`0x170`-byte output capacity. `client/lobby_channel_codec.py` implements that
payload from an explicitly supplied `0x1a4`-byte native record. Native fields
with unresolved origins retain their offsets rather than invented meanings.

| Native offset | Serialized representation |
| --- | --- |
| `0x00` | Big-endian uint32 |
| `0x04` | Big-endian uint32 byte count, then C-string bytes including NUL |
| `0x24`, `0x28`, `0x50`, `0x54`, `0x58` | Five big-endian uint32 fields |
| `0x5c`, `0x5e`, `0x60`, `0x62`, `0x64`, `0x66` | Six big-endian uint16 bit patterns |
| `0x74` | Big-endian uint32 byte count, then C-string bytes including NUL |
| `0x86` | Big-endian uint16 bit pattern |
| `0x88` | One byte |
| `0x8a`, `0x8c` | Two big-endian uint16 bit patterns |
| `0x90`, `0x94` | Two big-endian uint32 fields |
| `0xa0` | Exactly 256 unchanged bytes |
| `0x1a0` | Big-endian uint32 |

The original writer sign-extends some short/byte arguments when calling its
variadic packer, which ultimately writes only their low 16/8 bits. Negative
native bit patterns therefore retain their bytes without a guessed signed
public interpretation.

The portable boundary requires each string to terminate before the next mapped
field: `0x24` for the first, `0x86` for the second. These are safe record
boundaries, not claims about every original upstream string producer.

For string lengths excluding their NULs, the payload length is
`321 + first_length + second_length`. The strings can individually fit the
record but exceed the packer's combined capacity: lengths 31 and 17 produce
369 bytes, so the original packer returns -1 against its 368-byte capacity.
The portable codec rejects that case before producing a frame.

`ChannelJoinRecord.frame()` creates the plain `Frame(0x106, payload)` for the
existing lobby envelope layer. It does not choose or advance a cipher.

## Reply fields and channel state

The decoder at `0x7e64d0` reads two uint32 fields for `0x214`/`0x215`. The
consumer in `0x738f00` assigns the first to the channel ID. The second is used
on the UDP path; its complete semantics remain unresolved. The codec retains
both fields and the opcode, and refuses truncated or trailing payload bytes.

The native consumer records whether the opcode was `0x214` in a channel short
field. This does not justify discarding `0x215` as a failed response.

The same routine's registry check rejects an existing **requested nonzero**
channel ID. The earlier portable check accidentally allowed equality and
rejected an unrelated existing ID instead. `ChannelAddRequest.validate()` now
matches the keyed collision rule; requested zero remains permitted.

## Evidence and verification

Target: supplied `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4; static observations:

- Channel consumer `0x738f00`: `ev_3e3ea38f01df2e4f9827438f500cb911b3e218d2d2a1db4376e910dd0d57da94`.
- Serializer dispatch `0x7e5e60`: `ev_cc0facadba7490ea32646abee151818c396ddaaf44fc1b818eb9980da37dabe3`.
- Payload serializer `0x7e4c30`: `ev_2f4ac0163aeceb83cf319f7ad0e90b0289dca8db6875c3bb1b79bb63db01ac05`.
- Format bytes `0x8e06b0`: `ev_3fb5d287f0140dfd6b53dc567bd12a8255ed7671ee94fb9cdf573d4dff92c6f7`.
- Generic packer `0x7e4140`: `ev_0d2b2ddfa965f2ae67729e2d4005e1d05586002fadd7fd7770fa6535cc5abce2`.
- Reply decoder `0x7e64d0`: `ev_180e13b28205bb1864c008e4b4d49a1a23980843f3df277f3638a0c180cac594`.
- Reply format `0x8e0674`: `ev_76a1cde335e218bd78dd99cb0758e306d9835e4a99f704a00c29a4dcc8d806b5`.

Bounded local execution on Windows:

```powershell
python -m tools.lobby_channel_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Result: 27 payload cases match byte-for-byte, nine combined-capacity rejections
match the original -1 return, and six reply field-reader cases match both
decoded uint32 values and consumed length. Synthetic inputs cover zeros, all-one
bits, deterministic random records, empty strings and string boundaries. The
reply oracle executes the native field reader; opcode routing and channel
assignments are corroborated statically. It does not execute the whole consumer.

No host game startup, sockets or Windows imports run in this oracle. Original
bytes and pseudocode remain external and are not distributed.

## C++20 port

`native/include/mco/lobby_channel_codec.hpp` exposes the same bounded payload
encoder and two-field success decoder. The C++ codec belongs to `mco_core`; it
does not open a socket or select room arguments. Its unit test covers NUL bounds,
capacity, opaque bytes and reply validation. The native comparison tool accepts
one binary record on stdin and writes only the encoded payload on stdout.

```powershell
python -m tools.native_lobby_channel_compare build/native-check/mco_lobby_channel_compare.exe
```

Local Windows result: 136 payloads match the original-verified Python codec,
11 string/capacity rejections agree, and three malformed input lengths are
rejected. All 17 native CTest checks pass. CI includes this comparison on Windows
and Linux; these local results do not establish a Linux or live server run.

The [argument constructor and record-copy follow-up](lobby-channel-record.md)
now recovers the preceding bounded data writes. Authenticated room producers,
allocation initialization and lifecycle remain unresolved.

Remaining work: construct records from authenticated room state, recover request
ordering and upstream opaque fields, integrate cancellation/timeouts with the
listener, verify UDP fallback and patched TCP preferences, and compare live
original/reconstructed joins. Static dispatcher task kinds alone do not prove
the race-entry sequence or fan-server acceptance.

## Rejection and pending reply slot

`ChannelJoinRejection` decodes opcode `0x213` as one big-endian uint32.
The original decoder's format at `0x8e0668` is `l`; format-byte evidence is
`ev_4b96b3648cbaa007229a29c628879813b217f444e2c6700b2ce56ada07c3ccbc`.
The consumer preserves the raw status, returns its signed 32-bit interpretation,
and converts `0xffffffff` to `-23`. Other error meanings remain opaque.

`ChannelReplyMailbox` models a single pending slot. The original listener routes
`0x213`, `0x214` and `0x215` to `0x74632d`; it accepts a reply only when the
server object's waiting field (`0x194`) is nonzero and completed field (`0x190`)
is zero, then stores the reply at `0x18c` and sets completed to one. The routing
table evidence is `ev_844ba77da77f1074aa16e5f3f7d0b12538745b017ab641c32c4010c2cfc102b0`;
branch evidence is `ev_ff2223ceaf87460d728cb9d1eb234786aff6a33424f4d775f29189420d31c87d`.
These branches were inspected as original x86 instructions because Ghidra did
not recover the enclosing handler as a function.

The portable model rejects overlapping begins and malformed exact-size payloads
as defensive boundaries. Those checks are authored safeguards, not recovered
original error returns. Its input is an already extracted opcode payload, not an
encrypted or header-bearing network packet. It has no sockets, timeout scheduler,
cancellation or reconnect handling and is not yet connected to live room entry.
Five focused tests cover status boundaries, unsolicited/duplicate replies,
malformed replies and reuse of the pending slot. Live acceptance remains pending.
