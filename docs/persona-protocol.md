# Persona-map retrieval

After account login the game requests its persona list before selecting a
persona and establishing the lobby connection. The reconstructed request
encoder is `client/nps_persona.py`; no request is sent by that module.

Request routine `0x71dab0` constructs opcode `0x532`. Its payload serializer
`0x71e340` writes the account user ID as a big-endian uint32. The size helper
`0x71e330` returns four payload bytes plus the standard 12-byte header when
enabled. The default auxiliary calculation therefore writes total length 16.
This opcode is outside the native nonzero-flags ranges, so flags are zero.

| Offset | Bytes | Field |
| --- | --- | --- |
| 0 | 2 | Opcode 0x532 |
| 2 | 2 | Total length 16 |
| 4 | 2 | Flags 0 |
| 6 | 2 | Reserved 0 |
| 8 | 4 | Default auxiliary 16 |
| 12 | 4 | Authenticated account user ID |

The native request checks for a zero account ID and fails before sending.
The authored encoder additionally validates the uint32 type and range.
Four synthetic account IDs matched the original payload writer under bounded
Unicorn emulation, including its output cursor advance. Run
`python -m tools.nps_persona_oracle` with the verified executable path.
The whole request function and complete framed request have not been replayed.

The game wrapper at `0x4aa010` queues local task kind 2 with the account ID and
game-name string. That local task structure is distinct from this wire request.
The response records, persona activation request, and network lifecycle remain
under investigation. Neither successful parsing nor fan-server acceptance is
claimed by the payload check.

Evidence comes from executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra does not identify the request entry as an analyzed function, so its
instructions were inspected directly with Capstone and source-bound REA bytes.
The payload serializer has Ghidra evidence
`ev_f9cc0f6046dab21db04fb9bb4ed5fe099595976c27416f4f1e652917e1928cea`.
Game wrapper evidence:
`ev_acfdd6163e0796226d54663ee4d941bf56a468205f9ba920caa4a68fbd960614`.
Raw source instructions remain local and excluded from publication.

## Persona-map success payload

The request's reply switch accepts opcode `0x607` (comparison at `0x71dd94`).
Its derived response table `0x84af2c` selects reader `0x71e940`, which reads a
big-endian uint16 entry count, then nested records through `0x7e0e30`, then a
single final byte. Each nested record has a uint16 byte length. Entry factory
`0x71e6d0` selects table `0x84af58` with reader `0x71e820`.

Each entry contains four big-endian uint32 values followed by a uint16 byte
count and at most 32 name bytes. The reader appends a local NUL terminator;
the wire count does not include that appended byte. Field meanings and the
final byte's meaning are not yet assigned by the reconstructed parser.

`PersonaMaps.decode` bounds counts against available bytes and requires exact
nested and outer lengths. It rejects names over 32 bytes rather than reproducing
the native reader's truncation. Three entry cases matched original instructions
under emulation, including empty and maximum names, integer values, and cursor
advance. The enclosing list reader was inspected statically, not replayed.

Entry reader evidence:
`ev_8d66d19d22cabf07777a549c5f773d40233c168d6169a7ad9147245e8f8edb6b`.
Nested record helper:
`ev_fb720fb3faac0c2b1fd4b99e9d0fa0de85dc6d45f0783def9f8c23dff619ceeb`.
This parser does not activate a persona or establish a server session.
