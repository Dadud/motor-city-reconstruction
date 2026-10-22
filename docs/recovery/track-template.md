# Track loader template copy

Native `mcity.exe` function `0x427d80` copies exactly 62 dwords (248 bytes)
from image address `0x0083b830` to global destination `0x0097c238`. The Python
translation preserves the bytes literally in `client/track_template.py` and
copies them into a writable destination view. The content is intentionally
unnamed: current evidence establishes the byte image and copy operation, not
the table's semantic role.

`tools/track_template_oracle.py` checks the embedded bytes against the pinned
executable's loaded image and runs the original function through the bounded
Unicorn oracle. The source image and all 248 destination bytes matched. This
verifies only the copy operation under emulation; it does not establish its
consumer, Windows runtime behavior, or full track-loader equivalence.

Evidence:

- Function `0x427d80`: `ev_d0d13035ac8f2df45dbbf79c68ee6e8f7b7a0cefa9aa0a53306ab7bd3eee1974`
- Source bytes at `0x0083b830`: `ev_05e8bf8832128df93db1571e641d79ea25f2ab730d1eb3e5066469cf0971776f`

The target is `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`; the
static analysis used Ghidra 12.1.4 and profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`.
