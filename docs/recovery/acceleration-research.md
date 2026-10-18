# Recovery acceleration research

Research date: 2026-10-17. Verified baseline: `6a236aa`. The unfinished key-down, translation, and queue-resize changes are excluded from accepted results.

## Finding

The largest opportunity is to recover connected behavior in batches, with shared types and fixtures, rather than repeatedly establish context for isolated routines. Bulk decompilation already exists for 25,434 functions. Faster decompilation alone will not resolve the remaining interface, state, platform, and integration work.

The full-game acceptance scope in `plan.md` remains unchanged. The baseline has 67 comparison cells, 17,589 original/native cases, and 28 connected traces. These are valuable checks, but neither cell counts nor raw decompiler exports measure whole-game completion. There is no defensible completion date or project-wide speed multiplier yet.

## Local measurements

Measurements used the existing 67-cell corpus and verified key-query comparison executable, without accepting the unfinished queue work. Timings are local samples with warm caches, not portable benchmarks. Raw results are retained locally in `build/recovery/acceleration-measurements.json`.

| Operation | Result | Implication |
| --- | ---: | --- |
| Read full JSON corpus | 174,500,431 bytes; 0.0794 s | Disk reading is a small part of this sample. |
| Decode full corpus | 2.1511 s | Every single-cell driver currently pays for unrelated cells. |
| Decode compact key-query-only shard | 6,769,470 bytes; median 0.0875 s over three runs | About 24.6 times faster decoding for this selected cell only. |
| Replay and compare key query | 1,472 cases; 0.6007 s | Unrelated JSON decoding costs more than the selected native replay. |
| Gzip full corpus | 5,886,382 bytes; compression 0.0597 s, decompression 0.0775 s | About 29.6 times smaller storage; exact byte round trip verified. JSON decoding still remains. |

A historical Zig build log indicates approximately 35.6 seconds with 53 compilation tasks and 293 executable links. This is an estimate from the final Ninja completion-time segment, cross-checked against the saved build log, not a fresh build benchmark. The monolithic `mco_core` archive and widely included layout header explain substantial rebuild fan-out. The unfinished queue fixtures prevent treating a fresh full build of the current draft as baseline validation.

Direct-call graph inspection also shows why batch size must follow behavior rather than an arbitrary function count:

| Entry point | Reachable entries including root and imports | External entries |
| --- | ---: | ---: |
| Key down `0x584450` | 6 | 2 |
| Free camera `0x433820` | 15 | 0 |
| Camera frame `0x434f90` | 105 | 2 |
| Vehicle update `0x53c140` | 508 | 50 |

These are static direct-call reachability counts, not complete dependencies: indirect calls, shared state, and runtime callbacks still require review.

## Recommended order

1. **Shard the golden corpus and support selected comparisons.** Keep a small index containing binary hash, schema, cell identity, and shard digest. Load only selected cells during edits. Use shared-source and dependency metadata to include affected consumers; use the full suite when the impact is uncertain. Preserve full original observations and exact comparisons. Compression is useful for storage, but selection removes the measured decoding overhead.
2. **Work on connected subsystem batches.** Finish the key-down-to-queue path, then a complete input-to-camera scenario. Establish shared state, calling conventions, and callback contracts once per batch. Retain per-function provenance while making end-to-end behavior the acceptance milestone. Avoid spending batches on unrelated leaf functions merely to increase counts.
3. **Automate ABI and fixture preflight.** Extract return stack adjustment, argument accesses, register inputs, call-site cleanup, and floating-point returns into an evidence report. Flag ambiguous conventions rather than guessing. Recent input handlers exposed hidden arguments and cleanup details; catching these before implementation avoids repeated oracle repairs. Feed verified types back into the private analysis database and refresh affected functions only.
4. **Reduce build fan-out.** Split core code into subsystem libraries and layout declarations into appropriate headers. Build affected test and comparison targets during edits. CMake already supports selected targets and parallel builds; use that before undertaking a larger build-system rewrite. Keep full MSVC, Zig, Python, and original/native checks at stable batch checkpoints. [CMake build documentation](https://cmake.org/cmake/help/latest/manual/cmake.1.html#build-a-project).
5. **Consolidate comparison transport and runners.** After selection works, pilot packed binary records and one persistent runner per subsystem. Current decimal representations of byte images and many small executable targets add serialization, parsing, and linking work. Preserve exact failing-word diagnostics and full observations; a checksum alone should not replace the evidence.
6. **Parallelize independent subsystems only after shared contracts are stable.** A small number of workers plus an integration owner could improve throughput. Shared globals and ABI discoveries make uncontrolled function-level parallelism expensive. No linear speedup is assumed, and this research did not launch parallel agents.

## External tooling and reuse

**Library identification:** Ghidra Function ID can identify suitable statically linked library implementations, including supported Visual Studio libraries. Matches depend on compiled form, so compiler differences can defeat matching. Use it to prioritize known-library equivalents and clone review, with evidence for each disposition; do not treat similar skeletons as equivalent behavior. [Official Function ID help](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Features/FunctionID/src/main/help/help/topics/FunctionID/FunctionID.html).

**Coverage-guided input generation:** AFL++ Unicorn mode can exercise original binary snippets through a Unicorn harness. Our existing oracle provides a useful starting point. It still needs valid memory maps, starting state, seeds, and imported-call models. Pilot it on the queue or camera harness to find missing branches and counterexamples, then retain minimized cases in the regression corpus. It does not recover semantics automatically. [Official Unicorn-mode documentation](https://github.com/AFLplusplus/AFLplusplus/blob/stable/unicorn_mode/README.md).

**Binary lifting:** Remill lifts instruction semantics to LLVM bitcode; this is a different deliverable from readable, organized recovered source. McSema advertises PE and x86 support but its repository was archived in August 2022. A small math-helper pilot could test value, including floating-point behavior, platform compatibility, and cleanup time. An all-project migration is not justified by the present evidence. Neither tool was installed or validated against this game during this research. [Remill](https://github.com/lifting-bits/remill), [McSema](https://github.com/lifting-bits/mcsema).

**Existing game research:** Inspect the Rusty Motors server for protocol and server-side reference work, and the prior Motor City Online RE repository for reusable format research before rebuilding that knowledge. Their documentation is not proof of compatibility with this client or completion of this reconstruction. Check licenses and interfaces before incorporating code. [Rusty Motors server](https://github.com/rustymotors/server), [prior Motor City Online RE](https://github.com/Dadud/Motor-City-Online-RE).

## First pilot and success criteria

The first optimization is now available for individual generated drivers:

```powershell
.venv/Scripts/python.exe -m tools.cell_corpus --shard-to build/recovery/corpus-shards
.venv/Scripts/python.exe -m tools.native_input_key_query_compare build/recovered/Release/mco_input_key_query_compare.exe --corpus build/recovery/corpus-shards
```

Snapshots record the source digest and validate each selected shard's digest, target, address, and observation words. Re-export explicitly after source corpus changes. They are intended for development comparisons; full-suite and lifecycle checks continue using the complete authoritative corpus. Snapshot loading does not automatically claim freshness against a subsequently edited source.

Implement selected/sharded corpus loading first, then finish the existing key-down batch using shared fixtures and an integrated queue scenario. Record elapsed implementation, oracle preparation, debugging, build, and verification time separately. Compare the next connected batch with that baseline using accepted integrated behavior per hour, not just recovered functions.

The pilot succeeds if selected runs avoid loading unrelated corpus data, all baseline observations and connected traces remain exact, the new queue path passes original/native comparisons, and stable-batch checks pass on both native compilers and Python. This yields a measured basis for revising the schedule. The local decoding improvement must not be presented as a 24.6-fold improvement in overall project completion speed.
