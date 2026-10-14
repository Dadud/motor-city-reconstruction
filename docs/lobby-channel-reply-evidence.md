# Channel rejection and pending-reply mailbox evidence

`tools/lobby_channel_reply_oracle.py` executes bounded original instructions
against synthetic images and compares them with `ChannelJoinRejection` and
`ChannelReplyMailbox`. It uses the exact original executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
No original instruction bytes or decompiler output are distributed here.

## Rejection status

The format at `0x8e0668` is `l`: one big-endian uint32. REA byte evidence is
`ev_90f219113b94d18602754a1c14c7f402dcd28b7bf56fdaf1915e3148ca5bb27c`.
The existing receive format dispatcher associates it with opcode `0x213`.
The oracle checks the exact format bytes and executes the original generic
field reader `0x7e42e0` with that format on eight synthetic statuses.

After decoding a non-success channel-add reply, the original consumer loads
the status into `EDI`. Its instruction range `0x739bb8..0x739bc2` maps raw
`0xffffffff` to `0xffffffe9`, or signed -23, and leaves every other bit pattern
unchanged. The portable `native_result` reports the resulting signed int32.
This establishes that one sentinel conversion only; it does not assign names
or meanings to other status values.

The compared statuses are zero, 1, 23, the signed-positive boundary, the
signed-negative boundary, -23, -2, and -1 as uint32 bit patterns. All eight
reader results and all eight consumer conversions match.

## Single pending-reply slot

The adjacent dispatch-table entries at `0x747d40 + 6*4` route opcodes
`0x213`, `0x214`, and `0x215` to `0x74632d`. The oracle checks all three raw
destinations. The branch reads these server-object fields:

| Offset | Observed role in this branch |
| --- | --- |
| `0x194` | Nonzero permits a pending reply to be accepted |
| `0x190` | Nonzero rejects another reply as already completed |
| `0x18c` | Receives the serializer-returned reply pointer |

Acceptance requires `0x194 != 0 && 0x190 == 0`. The accepted branch passes
the opcode and supplied decoded-field pointer to serializer `0x7e5e60`, stores
its returned pointer at `0x18c`, and writes 1 to `0x190`. It leaves `0x194`
unchanged. The rejected branch leaves all three fields unchanged and does not
invoke the serializer. This is a single-slot acceptance rule; these observations
do not establish wire transaction correlation or a full connection lifecycle.

The portable mailbox retains a typed decoded reply instead of an original
allocation pointer. Its `receive` acceptance and flag behavior are compared to
this original branch. Portable `begin`/`take` convenience methods, pointer
ownership and cleanup are outside this oracle's coverage.

## Controlled substitution and coverage

For the mailbox range, the sole substituted callable boundary is serializer
`0x7e5e60`. A Unicorn instruction hook captures the two original arguments,
returns an explicitly supplied synthetic pointer, and reproduces the callee's
two-argument stack cleanup. It does not serialize bytes or allocate memory.
Original data constructors/destructors `0x7e4120` and `0x7e4130` execute.
Diagnostic logging is disabled by setting the original logging-enable global
`0xb38014` to zero. No import, logger, socket, account operation or game startup
is invoked.

The oracle enters `0x74632d` with supplied registers, stack arguments, object
fields and decoded-field bytes. It stops at the accepted continuation
`0x7472e7` or rejected continuation `0x7472e0`, before unrelated outer cleanup.
Each invocation has instruction-count and elapsed-time limits. The mailbox
corpus combines three opcodes with waiting/completed values 0, 1, 2 and
`0xffffffff`, producing 48 cases. It checks serializer arguments, pointer
storage and both flags, including ignored duplicates and inactive waits.

```powershell
python -m tools.lobby_channel_reply_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows bounded execution matched 8 rejection reads, 8 result conversions,
48 mailbox cases and 3 dispatch destinations. These results verify the isolated
original branch under the supplied serializer boundary. They do not establish
actual serializer output, allocation failures, listener/queue transport,
thread synchronization, timeouts, cancellation, connection ownership, or a
successful live room join. Those remain separate recovery and acceptance work.
