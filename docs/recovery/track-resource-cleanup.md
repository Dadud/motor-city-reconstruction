# Track resource cleanup path

`release_track_loader_globals` translates the observed cleanup order in native
`mcity.exe` function `0x4287a0`: clear global `0x0097c414`; release the
nonzero pointers in `0x0097c3fc` and `0x0097c410` independently, zeroing each
slot after release; then clear the current-base pointer in `0x0097c408`. The
intervening child `0x590b40` has an observed one-byte `RET` body.

`close_track_loader_globals` composes the wrapper observed in `0x42ce30`: clear
`0x00988e28`, run the `0x4287a0` sequence, and then run `0x42e3d0`, which
conditionally releases and clears `0x00988e98`.

The Python functions operate on a caller-supplied mapping keyed by observed
global addresses. Deallocation is an explicit callback because the native
allocator implementation and pointer ownership are not modeled here. The
addresses are intentionally left unnamed; the evidence establishes pointer
use and write order, not higher-level semantic types. This is static-analysis
translation only and has not been compared against original runtime calls.

Evidence, all on the same SHA-pinned `mcity.exe` analyzed with Ghidra 12.1.4
and profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`:

- `0x4287a0`: `ev_9503df83fe1bc312308478a2e459d30fa650e87289fcbaf65c7b14f337256f78`
- `0x42ce30`: `ev_5d5793ffd0b3e652f77e7a64134f2fd174caaf86911c572d3b2536e770fe0c48`
- `0x42e3d0`: `ev_685145d3daf3f87b594e683803f22cd32a0d48d933ce79d4284d20d18de28f88`
- `0x590b40`: `ev_16c8798794d11884dd1d26f5fcdd79d5bc6c5c5c2b8ac33666e2d349158e7571`
