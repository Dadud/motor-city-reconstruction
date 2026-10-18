# Input queue recovery checkpoint

2026-10-17. Extends baseline `6a236aa` with original key-down (`0x584450`), key translation (`0x583a90`), and queue resizing (`0x584ca0`).

The queue implementation preserves repeat clamping, raw key updates, optional remapping, translated character handling, cursor wrap and overwrite-oldest behavior, and observable ordering around synchronization calls. Caller-owned byte images and an explicit synchronization callback describe the supported domain; they do not claim recovered C++ class layouts or a working Windows critical section.

Verification completed:

- Three standalone behavior tests pass under MSVC and Zig.
- All 2,382 added routine observations match exactly under both compilers: translation 1,548, resize 18, and key down 816.
- Four connected traces execute down, query, release, and resize against shared queue/key/latch state. Both compilers match original observations after every call. Only critical-section imports use declared observation substitutions.
- Full native suites pass: MSVC 151 tests; Zig 153 tests.
- Python discovery passes 986 tests with seven skips.
- MSVC and Zig aggregate comparisons pass all 70 implemented cells and 32 connected lifecycle traces. The corpus contains 19,971 cell cases; lifecycle traces are counted separately.

Per-cell snapshots are available through `python -m tools.cell_corpus --shard-to DIRECTORY`. They retain source and shard digests and avoid loading unrelated observations during individual comparisons. Re-export snapshots after corpus changes. Full-suite and lifecycle comparisons still consume the complete corpus.

Remaining work includes live window dispatch, actual synchronization integration, input-to-camera handling, and broader whole-game recovery. These bounded comparisons do not establish full client equivalence. Inventory counts remain review bookkeeping, not a project completion percentage.
