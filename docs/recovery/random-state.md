# Shared random state

The game uses `0x6f0fa0` to advance six global 32-bit words at
`0x8c89d0..0x8c89e4`. `RandomState` makes that state explicit and advances it
with the same add-with-carry recurrence. It returns the updated first word.
This is a reusable primitive for callers such as the procedural sky-material
builder; it does not imply that a caller's complete random behavior has been
reconstructed.

`tools/random_state_oracle.py` compares one transition across 1,024 supplied
states against the installed original using bounded Unicorn x86 execution. The
cases include one observed native initial state plus deterministic random
states. The local tests also cover input validation and the rare counter-wrap
carry path. This is synthetic-state emulation, not a live game runtime test.

Evidence: REA pseudocode and body for `0x6f0fa0`,
`ev_1a069217dbc28f2f1f5ade3b367ef667595ba5f70dd491c621a1b5ea1326a625`,
Ghidra 12.1.4 on `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
