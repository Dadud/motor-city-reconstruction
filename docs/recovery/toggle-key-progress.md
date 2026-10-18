# Startup toggle-key recovery

Follow-up: [connected startup verification](startup-toggle-progress.md) now replaces
the mocked Num Lock entry in a separate startup probe. It establishes the bounded
scan-byte/temporary-word transfer; the original isolated checkpoint below remains
historical.

The startup wrapper `0x6bfc80` calls the complete toggle setter `0x6bfc90` with selector one and desired state zero: it requests Num Lock off. This corrects the previous description of that startup boundary as an unidentified helper. It does not establish the incoming ECX value required by the later device-initialization fixture; that synthetic register setup remains explicit and is not replaced by a guessed Windows register effect.

## Static observations

REA 6.7.0 / Ghidra 12.1.4 Evidence `ev_a70577ea306a84a7816cca212dc0ecd56e0be483e85c2443045a769cb9c28f40` identifies the complete inclusive wrapper body `0x6bfc80..0x6bfc8c` (13 bytes). Evidence `ev_2a83c75f72b24ced24f1b8fc67f065efe2f4669b6424b09a0a7551d6267efdf3` identifies the setter `0x6bfc90..0x6bfd10` (129 bytes). Both have one contiguous observed body range. Target SHA-256 is `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`; profile digest is `3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`. Complete records are retained privately in `evidence/rea-toggle-key-6.7.bundle.json` and its matching snapshot.

Selectors zero, one and two choose virtual keys `0x14`, `0x90`, `0x91` and scan bytes `0x3a`, `0x45`, `0x46`. Other selector words return without a platform call. The GetKeyState import at `0x83b3e4` is queried once. Its low bit is compared with the full desired-state word; desired values greater than one are not normalized to Boolean. On mismatch, the keybd_event import at `0x83b3e8` is loaded after that query and cached across two events. Num Lock uses flags one then three; the other selectors use zero then two. Extra information is zero. The original initializes only the low bytes of two stack argument slots; Windows BYTE key/scan observations exclude their unspecified upper bits.

## Bounded verification and remaining work

984 original-instruction cases match MSVC and Zig. They cover valid/invalid selectors, ordinary and non-Boolean desired words, query-state high bits, startup wrapper execution, query-time event-target changes and event-time target changes. The native implementation has explicit returning query/event bridges. Independent native checks enforce the key/scan/flags, invalid-selector no-call behavior, high-bit masking, full-width desired comparison and cached event identity.

These checks execute hash-verified original x86 instructions in Unicorn with declared synthetic Windows import bridges. They do not send host key events or observe live Windows state. The original void routines' incidental register results are not an authored return contract. Whole startup traces still substitute this helper's register behavior; connecting actual Windows input, mouse initialization, remaining runtime helpers and full client startup remain unresolved. Previous startup and connected-trace counts are historical checkpoints, not new verification claims.

The retained corpus now has 99 implemented cells and 60,976 routine cases; all 88 previously retained connected traces remain present. Complete MSVC and Zig replays passed this checkpoint, including all 88 retained connected traces. The new independent self-test passes on MSVC and Zig; 26 targeted inventory, triage, corpus and layout tests pass. Full prior checkpoint test counts are not relabeled as reruns.
