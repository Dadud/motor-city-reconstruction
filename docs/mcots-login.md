# MCOTS attachment and login record

MCOTS is a separate stage after lobby connection. Game caller `0x5ef240`
invokes `0x683100` with the selected persona's account ID, persona ID and name,
the retained client session bytes and their length, three additional values,
and a status pointer. It waits while status is 2; successful status is 1.
The selected record's account field was previously overwritten with the
authenticated account ID by the persona-list worker.

`0x683100` allocates and clears a 300-byte local task record. It stores account
ID at +4, persona ID at +8, name at +0xc, key length at +0x1c and key bytes at
+0x20, plus the additional values at +0x120, +0x124 and +0x128. It queues local
task kind 700. This task number is not a wire opcode.

The task pump `0x65ded0` scans a table of 12-byte dispatch records until its
0x89 sentinel. Entry `0x8bf148` maps task 700 to handler `0x6830c0`, which calls
`0x682df0`. That function initializes communication, attaches to service ID
0xfe through `0x682090`, waits for attachment status, then constructs a
39-byte login record and passes it to transaction queue routine `0x6831f0`.
Attachment has an explicit wait loop with a roughly 20-second bound.

## Record layout

The record builder clears 39 bytes at `0x683028`, writes integers directly
in little-endian native memory and calls the original `strncpy` for the name.

| Record offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 2 | Login operation 0x69 |
| 2 | 4 | Account user ID |
| 6 | 4 | Persona ID |
| 10 | 4 | Task value at +0x128, unresolved |
| 14 | 4 | Task value at +0x120, unresolved |
| 18 | 4 | Task value at +0x124, unresolved |
| 22 | 13 | Persona name, truncated or NUL padded |
| 35 | 4 | Literal 0x1b5a, meaning unresolved |

An exactly 13-byte name has no NUL in that field. Longer names are truncated.
The portable `MCOTSLoginRecord.encode_native_record` preserves this behavior
and leaves the additional values explicit. Its output is the recovered memory
record, not an NPS frame or a complete MCOTS wire packet. The attachment
handshake, transaction header, wire transformations, response matching and
login-success payload remain under investigation. No MCOTS request is sent by
the record module or oracle.

`python -m tools.mcots_login_oracle /path/to/original/mcity.exe` executes only
the bounded original record construction, including its real `strncpy`, and
stops before transaction queueing. Four cases matched all 39 bytes, starting
with nonzero destination memory: empty, ordinary, exactly 13-byte and 32-byte
names. This proves those record bytes, not successful MCOTS authentication.

## Transaction ownership and outgoing queue

The next stage is an asynchronous outgoing queue, rather than a direct socket
write. Routine `0x6831f0` finds service 0xfe in the service table and copies its
connection handle into offset 0 of the message allocation. It copies the
global value at `0x8c13b4` into allocation offset +0xb. Before handing the
allocation off, it saves the operation at +0x14 and the four-byte value at +0xf
for the transaction tracking record. The meaning of that four-byte value and
the default header value still require further tracing.

Communication constructor `0x6f7710` selects vtable `0x84a220`; its send slot
at +0xc resolves to `0x6f8270`. That method immediately takes ownership of the
message: it reads the pointer through its first argument and clears the
caller's pointer. It rejects a zero payload length at allocation +9 and a zero
connection handle. For an ordinary positive connection handle it resolves a
connection record through `0x6f73a0`, checks that record's +8 field, then puts
the allocation onto the outgoing queue through `0x64dfd0` when the second
argument is zero. It updates queue counters and signals the worker event.
Consequently a successful return from this method proves queue acceptance;
it does not prove a socket write or server acceptance.

The allocation uses a 20-byte local prefix: connection handle at +0, another
four-byte field at +4, allocation class at +8, payload length at +9, the field
at +0xb, the field at +0xf, and a byte at +0x13. Payload begins at +0x14.
Allocator `0x6f8e10` selects class 1, 2 or 4 according to pool-size thresholds.
These class and ownership fields belong to local memory management. No wire
header should be inferred by copying this prefix wholesale. The outgoing
worker and its encoding remain the next boundary to recover.

Additional static evidence:

- Transaction queue: `ev_0278b349e65a18dd873bd7ed20107e49079727fb970c76de6a05866a7bca753c`.
- Communication constructor: `ev_b78bea98aa1ea714bcb9c4682c3d2fe9ac098b3b3d64464cb59c52927e7a7533`.
- Allocation: `ev_c9ed7afdcc898ed4e69ce04b4cf5ece65540fe3ef5f812fae6fbc1c52681e94a`.
- Outgoing queue method: `ev_4e6470594521129189c6097579c2c7bc8865e5bf9ef82d0183b4516ec1c280c6`.

## Login construction evidence

- Task construction: `ev_98e890e64e73c615ef54da5b8da851d17b657aae5399cf65f32c7f9e932cbc3e`.
- Task pump: `ev_6fab521cecde27ecd584769d507599c2e08311d002e1b0669de5eca97418d96e`.
- Worker: `ev_8e3ec4a8df1632d62a6835e8befec82fa0c7530d1e61d0034631b1157a45179a`.
- Record construction: `ev_adb87dffe0ecd759d11af38c37ee17895a0908bbce7620b35c741b9f33a36a5f`.

The source executable SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
