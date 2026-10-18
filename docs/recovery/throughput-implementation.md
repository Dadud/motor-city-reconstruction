# Throughput implementation — 2026-10-18

## Implemented and verified

- The authoritative corpus is now `corpora/wave0/index.json` plus 123 compressed
  content-addressed records (103 cells and 20 probe collections). Total storage
  is **7,388,416 bytes**, replacing the 545,948,830-byte LFS JSON. Old history is
  preserved; a local legacy copy remains in ignored `build/recovery/wave0-legacy.json`.
- The exporter writes deterministic gzip records and atomically publishes the
  manifest last. Unchanged records are reused. Readers check SHA-256, record
  identity and target identity. Full-suite and individual lifecycle readers
  support shards; old JSON/gzip and schema-1 cell shards remain readable.
- Current CI uses ordinary Git checkout instead of downloading the old LFS
  object. Cell manifests and review records point to the new corpus directory.
- Logical parity verified every metadata field and every cell/probe hash against
  the old JSON. MSVC and Zig each pass **103 cells, 67,800 routine cases and 96
  connected traces**. Python discovery passes **997 tests with seven skips**.

See [corpus operations](corpora/README.md). The upload speedup remains a payload
projection until measured on a real publication; this change does not accelerate
the original-instruction emulator or complete additional game behavior.

## Library and similarity tools

`tools/similarity_pilot.py` uses a retained export project with `-process`,
`-readOnly`, and `-noanalysis`. It validates the program target identity, records
script and bundled FID database hashes, queries Function ID without renaming
functions, and seeds a private local H2 BSim database. It refuses to overwrite
old output and requires a successful report even when Ghidra exits zero.

The executed pilot used Ghidra 12.1.4 and the retained main-executable project:
**77 functions have unreviewed Function ID candidates** at the default 14.6
threshold. A selection prioritizing those candidates produced **200 actual BSim
signature records**, plus 118 related callee descriptions, for one executable.
The iterator reports 25,435 internal functions; the inventory's 25,773 base count
also includes 338 external entries. No inventory entries were reclassified.

Raw candidate names, reports, database and provenance remain private under
`evidence/throughput-fid-bsim-2026-10-18`. This is supplemental Ghidra analysis,
not primary REA Evidence. Matching libraries or other builds must be added and
candidate ambiguity reviewed before claiming semantic equivalence or recovered
game functionality. BSim seeding alone is not a reviewed cross-binary match.

```powershell
python -m tools.similarity_pilot --export evidence/recovery-export/TARGET_SHA256 --ghidra C:/path/to/ghidra --java-home C:/path/to/jdk --output evidence/new-similarity-pilot
```

## Frida availability and repeatable runtime check

The installed REA 6.7.0 dependency `frida@17.23.2` lacked its native binding.
Running `npm rebuild frida --foreground-scripts` in the existing REA package
installed that binding without upgrading REA or editing Codex configuration.
Fresh `rea list-frida-devices --json` now succeeds. The current MCP process still
retains the initial import failure and needs reconnection; the matching CLI works.

`tools/frida_canary.py` builds an owned Windows x86 executable with the existing
Zig compiler, attaches through REA, and verifies four native entry/return pairs
with 32-bit pointers before detaching and cleaning up its child. The observed
outputs equal their inputs plus seven. Evidence from the first controlled x86
hook check is retained privately in `build/recovery/frida-x86-hook-canary.json`.
The final helper run produced Evidence
`ev_f9e314af30a28bbbf5b35bbabacdaa88ac69fe3e11dc7675c096ca1f9422e8ea`.
The reproducible helper retains full Evidence and source/script/executable hashes
under its caller-selected ignored output directory.

```powershell
python -m tools.frida_canary --zig .venv/Lib/site-packages/ziglang/zig.exe --output evidence/new-frida-canary
```

This proves local Windows x86 instrumentation on an owned canary, **not MCO
startup, hook-address validity, COM behavior or a real game lifecycle**. MCO
capture still needs a bounded scenario, verified target/module-relative
addresses and pointer/state normalization before it can become a regression
fixture. No original game process was launched for these checks.

## Remaining experiments

Review Function ID candidates, add compatible reference binaries to BSim, and
capture one real MCO input lifecycle. Reuse the existing SCC/dependency backlog
and retained REA evidence for connected packages. PyGhidra type overlays, Qiling,
angr, x32dbg and TTD remain optional experiments; they were not installed or
represented as completed integrations by this change.
