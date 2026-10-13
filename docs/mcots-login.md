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

Evidence:

- Task construction: `ev_98e890e64e73c615ef54da5b8da851d17b657aae5399cf65f32c7f9e932cbc3e`.
- Task pump: `ev_6fab521cecde27ecd584769d507599c2e08311d002e1b0669de5eca97418d96e`.
- Worker: `ev_8e3ec4a8df1632d62a6835e8befec82fa0c7530d1e61d0034631b1157a45179a`.
- Record construction: `ev_adb87dffe0ecd759d11af38c37ee17895a0908bbce7620b35c741b9f33a36a5f`.

The source executable SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
