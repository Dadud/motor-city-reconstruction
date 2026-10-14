# Channel-close opcode and local routing

`client/lobby_channel_close.py` provides the initialized local argument pair
and recovered plain opcode `0x105` serialization. It performs no local cleanup,
socket operation, logoff or server-acknowledgement processing.

Target original executable:
`C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
The authored description and codecs below contain no proprietary instruction
bytes or decompiler output.

## Local pair and wire field

Room task 1 supplies two uint32 values: server connection selector and channel
ID. `native_close_arguments` returns this initialized eight-byte pair in the
original little-endian layout. Both values are used for local registry lookup.
The selector is not serialized in the channel-close packet.

The lower helper `0x73ec30` calls serializer `0x7e5e60` with opcode `0x105`
and a pointer to the **second** original stack argument, the channel ID. The
opcode dispatch reaches `0x7e612e`, using format `l` at `0x8e0668`: one
big-endian uint32. The original prefix writer emits a big-endian uint16 opcode
and uint16 total length.

| Wire offset | Width | Value |
| --- | --- | --- |
| 0 | 2 | `0x0105` |
| 2 | 2 | 8, including the four-byte prefix |
| 4 | 4 | Channel ID, big endian |

For channel `0x87654321`, the complete plain frame is
`01 05 00 08 87 65 43 21`. No inferred acknowledgement, additional header,
transaction ID or server selector is appended. Existing connection transport
may transform this frame; this codec does not implement that transport.

The generic serializer accepts every uint32 field, including zero. The raw
codec preserves that behavior. This does not mean a zero-channel close packet
should be sent: the public interface `0x730f50` performs no channel-removal call
for channel zero. Separately, a direct call to lower helper `0x73ec30` with
channel zero takes its server-logoff branch. Those control-flow policies are
distinct from raw field encoding.

## Observed lower-helper ordering

When registry lookup fails, the lower helper neither cleans up a channel nor
constructs a packet. With a retained connection and nonzero channel, it calls
`0x743890` on the connection's local communication registry (`+0x180`) with
the channel ID. It then constructs `0x105`, invokes `0x736d90` using the
connection's TCP socket (`+0x16c`) and protocol value `0x21`, and releases its
retained connection reference. The send call also receives the retained holder
reference, zero as an opaque value and 1 as another opaque value. Their full
transport meanings are outside this codec.

There is no conditional branch on the local cleanup result before construction
or sending. The helper also has no acknowledgement wait in this path. The
public wrapper returns zero after calling the lower helper regardless of that
helper's outcome, as documented in [room-disconnect.md](room-disconnect.md).
Thus the room-worker's zero result does not establish that the server processed
the close. Real reference destruction, local cleanup contents and transport
error handling remain separate recovery work.

## Evidence and verification

Lower helper REA evidence:
`ev_74e9a2d6c7c16ccdd8f34fbb27c4ff7ec179e8311ecfd4174ddec3fd14f90165`.
Public wrapper evidence:
`ev_4337293aa59d20168cc79d7aded866525dad0c0005433ac5f231644afd78f842`.
Generic builder evidence:
`ev_eee230575b54d5dc1533f9be2eae357f55d6658186de3a5bd1aac9be14ac34ac`.
Format-byte evidence:
`ev_90f219113b94d18602754a1c14c7f402dcd28b7bf56fdaf1915e3148ca5bb27c`.
The lower helper's decompiler signature does not recover its stack arguments
correctly. Assembly stack tracking and bounded execution establish the channel
pointer above; decompiler parameter names are not treated as source evidence.

```powershell
python -m tools.lobby_channel_close_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows bounded execution matched 32 complete close frames and 5 direct
raw-serializer cases, including zero. It additionally verified 8 lower-helper
zero-channel/logoff paths and 40 missing-registry paths. Three focused Python
tests pass. Inputs vary local selectors, channel extremes, lookup outcomes,
cleanup returns and supplied transport returns.

The native C++ codec matches 81 Python local-argument, payload and plain-frame
encodings, and rejects four inputs wider than uint32 before narrowing. Two
integration tests connect disconnect arguments to the close codec and existing
CBC envelope, including consecutive frames on one cipher chain. No socket is
opened by these tests. Both codecs are isolated; they are not yet wired into
live room lifecycle orchestration.

```powershell
python -m tools.native_lobby_channel_close_compare build/native-check/mco_lobby_channel_close_compare.exe
```

The oracle executes original `0x73ec30` entry through return, including its SEH
setup against an emulator-owned empty chain, original serializer `0x7e5e60`,
field writer and prefix writer. Substituted capture boundaries are registry
lookup, local communication cleanup, allocation, transport send, server logoff
and reference decrement. The allocator supplies a bounded eight-byte buffer;
the reference decrement returns 1 so holder destruction is excluded. Logging
is disabled. It checks argument pairs, cleanup/send arguments, complete wire
bytes, boundary order and restoration of the SEH chain. Each run has execution
limits. The five direct serializer cases use only the allocation boundary.

No packet is sent to a live service. These comparisons establish plain-byte
construction and isolated ordering under supplied boundaries, not actual
cleanup behavior, TCP delivery, authenticated room switching, acknowledgement
or fan-server compatibility.
