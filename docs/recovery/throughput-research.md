# MCO recovery throughput research — 2026-10-18

Implementation follow-up: [completed changes and validation](throughput-implementation.md).
The measurements and availability observations below describe the initial research phase.

The best immediate improvement is reducing evidence transfer and repeated analysis setup. Additional analysis tools can help identify libraries, propagate reviewed types, and capture real runtime behavior; none establishes whole-game completion automatically.

## Measured bottleneck: corpus publication

At checkpoint `8ebbbab135c8a2f0fe0a2cf3ca89d0d4e784fc16`, the corpus is 545,948,830 bytes. The latest upload ran at approximately 888 KB/s and took about ten minutes. Local Python gzip benchmarks measured:

| Representation | Bytes | Local compression time |
| --- | ---: | ---: |
| Current JSON | 545,948,830 | — |
| gzip level 1 | 25,081,170 | 0.407 s |
| gzip level 6 | 7,606,107 | 1.088 s |
| All individually compressed cell/probe records | 7,356,849 | Not separately timed |
| Changed compressed records since `99632ab` | 346,575 | Not separately timed |

The level-6 artifact decompresses to the exact original SHA-256 `f0b3617a82c2d70d5eafb7d8b7a7e06c22b80c184857aa7cfc72242be3b0ce02`; decompression plus hashing took 0.471 seconds. These are local measurements, not network benchmarks. Compression alone reduces payload by 98.6%; it does not accelerate instruction execution or prove faster overall recovery.

The last batch changed three cell records and one lifecycle probe; all other compared records retained their canonical content hashes. Content-addressed compressed shards could therefore avoid uploading unchanged records. The 346,575-byte figure excludes manifests and transport overhead.

`tools/cell_corpus.py` already supports routine-cell sharding. Extend it to compressed cell **and probe** records, deterministic gzip timestamps, versioned manifests, checksum validation, and all suite/CI readers before migrating the authoritative corpus. Acceptance: identical 103 implemented cells, 67,800 routine cases, and 96 connected traces against both MSVC and Zig. Keep backward compatibility during migration.

Private reproducible benchmark artifacts: `build/recovery/throughput_research.py` and `build/recovery/throughput-research.json`. No corpus migration was performed by this research.

## Ranked tool shortlist

1. **Ghidra Function ID and BSim — first analysis pilot.** Ghidra is already installed. Identify known runtime/library functions and similar code across the 29 exported binaries, then review their dispositions instead of repeatedly recovering library internals. BSim supports a local H2 database. Its similarity scores are candidates, not equivalence proofs; compiler/library reference coverage and false positives require review. Pilot 100–200 candidates and measure accepted dispositions per hour. [Function ID](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Features/FunctionID/src/main/help/help/topics/FunctionID/FunctionIDPlugin.html), [BSim tutorial](https://ghidra.re/ghidra_docs/GhidraClass/BSim/BSimTutorial_Intro.html).

2. **Persistent Ghidra analysis and PyGhidra — amortize setup and type work.** Recent cold autoanalysis took roughly 143–151 seconds. Batch related questions and reuse compatible retained evidence. Ghidra supports processing existing projects and skipping analysis; these generic options are not automatically supported by REA's Windows P0 provider. A separate private working project could apply reviewed structure/vtable/prototype overlays through PyGhidra, with versioned exports and provenance. Do not silently mutate the primary evidence database or bypass provider boundaries. [Headless options](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md), [PyGhidra](https://github.com/NationalSecurityAgency/ghidra/blob/master/GhidraDocs/GettingStarted.md).

3. **Frida through REA — targeted runtime fixture capture.** Hook a small set of initialization/input/callback functions, collecting arguments and bounded before/after state to inform connected fixtures. This could reduce manual COM bridge and state-layout inference. REA already exposes the integration, but a read-only device-enumeration check currently fails because `frida_binding.node` is missing. Repair and verify the matching native binding before attempting MCO instrumentation. Windows x86 target compatibility remains untested; pointer normalization, OS behavior, and nondeterministic state still need explicit treatment. [Frida platform overview](https://frida.re/docs/home/), [instrumentation API](https://frida.re/docs/javascript-api/).

4. **x32dbg and WinDbg Time Travel Debugging — difficult runtime questions.** Use x32dbg for selected instruction/register/memory traces. Its ordinary Run operation does not record a trace. Use TTD for a short reproduction when identifying an earlier memory write or object lifetime is the blocker. Microsoft documents typical 10–20× recording overhead and potentially large traces, so blanket recording is a poor first throughput step. Neither tool was found on PATH; installation elsewhere was not exhaustively checked. [x64dbg trace documentation](https://help.x64dbg.com/en/latest/gui/views/Trace.html), [Microsoft TTD](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/time-travel-debugging-overview).

5. **Qiling and angr — bounded experiments.** Qiling adds OS/API emulation around Unicorn and supports Windows PE/x86; pilot one input chain to determine whether it removes more custom loader/import code than it adds. It does not supply MCO's complete graphics/input environment. angr is a candidate for generating inputs to a specific rare branch, not solving the whole client. Existing Unicorn and Capstone are already available; Qiling and angr are absent from the project environment, and Python 3.14 compatibility has not been verified. [Qiling](https://github.com/qilingframework/qiling), [angr](https://github.com/angr/angr).

6. **BinDiff/BinExport — version comparison when matching versions exist.** Useful for transferring function identities and reviewed knowledge between related builds. Ghidra integration is documented as Tier 4/manual and not well integrated, so start with built-in BSim before adding this maintenance burden. [Supported disassemblers](https://github.com/google/bindiff/blob/main/docs/disassemblers.md).

## Work organization and exclusions

Use the existing SCC/dependency analysis in `tools/recovery_backlog.py` to select connected packages. Reuse generic fixtures and reviewed ABI/type schemas across each package. Measure completed connected behavior and integration progress, not just function counts. The current checkpoint still lacks a fully linked playable original client; renderer, audio, platform/input, networking, and complete game-flow integration remain material work.

Kuna is not an accelerator for this target: the inspected REA provider supports ELF/thin Mach-O architectures and rejects PE. REA's `observe_native_calls` and `observe_native_ui` use a Mach-O/LLDB route and are likewise unsuitable for Windows MCO. Another wholesale decompilation pass is low priority because about 75,697 pseudocode exports already exist. No relevant additional plugin surfaced in the plugin directory search.

Recommended sequence: (1) compressed corpus migration with parity checks; (2) a measured Function ID/BSim triage pilot; (3) repair Frida availability and capture one bounded real input lifecycle. Record elapsed analysis, fixture construction, validation, and publication time separately before claiming an overall speedup. No new tools were installed and no game process was launched during this research.
