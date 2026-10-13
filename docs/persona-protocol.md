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
