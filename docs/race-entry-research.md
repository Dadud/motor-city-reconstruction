# Race entry research boundary

`client/game_network.py` represents the local structure read by dispatcher
`0x454d50`: task kind at offset 0, eight unresolved header bytes at offsets
4–11, and operation arguments starting at offset 12. Decoding and re-encoding
preserve the unresolved header. These structures are **not network packets**.

The dispatcher has ten independent cases. Their existence does not establish
an execution order. Earlier Python code generated tasks `(0, 5, 7, 8)` with
empty arguments and called their round trip a successful race-entry probe.
That construction was unsupported and has been removed. The research builder
now requires explicit caller-supplied tasks and protocol; accepting them means
only that their local envelopes and selected channel fields are admissible.
It does not validate operation-specific arguments or execute a join.

Task 7 invokes channel-add with its argument and opaque values `-1` and `1`.
`RoomCallerValues` models these as 32-bit data, without invoking them or
asserting function-pointer semantics. Other call sites must be investigated
independently before assigning types to these channel fields.

The installed `FastJoin` flag is retained as a configuration observation.
Neither `True`, `False`, nor a missing value selects `0x21` or `0x42` in this
code. Static dispatcher diagnostics about UDP preference do not prove the
patched client's effective transport or eventual negotiated protocol.

`probe_race_entry_path` and `probe_room_channel_path` report missing recovery
work. Their legacy `*_probe_passed` fields are false. They construct no tasks,
send no packets, and provide no race compatibility claim. The dispatch-case
catalogue is separate from the empty recovered race-entry sequence.

To implement actual entry, trace the upstream task scheduling and populated
arguments in equivalent original-client sessions, recover server/session IDs
and request correlation, establish patch transport selection, then compare
authenticated room negotiation and game-start exchanges with Revival. See
[static dispatcher evidence](lobby-channels.md) and the
[original channel wire codec comparisons](lobby-channel-codec.md).

The [room worker follow-up](room-worker-dispatch.md) identifies a separate local
dispatcher: its task zero invokes channel-add with room-object caller values.
Those values must be traced independently from game-worker task seven's -1/1
constants. The new branch map narrows recovery work without establishing a
complete entry sequence.
