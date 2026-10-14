# Room arguments through channel serialization

`tools/room_channel_pipeline_oracle.py` compares the recovered room argument
builder with the next original data stages: channel constructor `0x743d50`,
record-copy range `0x7398a7..0x739a0e` and payload serializer `0x7e4c30`.
This checks that the authored modules agree when composed, rather than only
matching independent artificial records.

The room builder's output is supplied to the original constructor. Its producer
has a [separate original comparison](room-request-production.md), and does not
execute again in this pipeline oracle. Each case supplies an explicitly zeroed
channel allocation and synthetic caller/connection fields. The constructor's
vtable identity is excluded from the portable comparison; only the Windows
critical-section initializer is substituted with an inert return. Original
string-copy and payload-packing code execute.

```powershell
python -m tools.room_channel_pipeline_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows result: 30 complete pipelines match constructor data, complete
serializer records and payload bytes. Cases combine name lengths 0, 1, 29, 30
and 31; empty, one-byte and 16-byte passwords; and both observed flag branches.
The explicit allocation keeps constructor-untouched name-tail bytes zero. This
does not prove that the original allocator clears them, or make every arbitrary
allocation/string combination safe to serialize.

No record is sent. Connection-derived user/socket fields, allocation producers,
authenticated room-state population, listener concurrency and live server
acceptance remain separate required work. The payload is only the recovered
channel-add body; transport headers and encryption remain outside this check.

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Individual source evidence and original-call exclusions are recorded in
[channel construction](lobby-channel-record.md),
[channel serialization](lobby-channel-codec.md) and the room producer writeup.
