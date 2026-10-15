# Installation export checkpoint — 2026-10-15

The first full static export pass is complete for the supplied installation.
All internal functions identified by the recorded Ghidra profiles have an export
attempt. This establishes research coverage, not complete source reconstruction.

- 30 discovered paths, 29 unique hashes: 28 PE binaries and one non-executable
  filename candidate. Identical `dx8z.dll` and `dx8zDB.dll` share one inventory.
- 75,697 successful private pseudocode exports, including bundled libraries,
  launcher code, plugins and two historical cached binaries.
- Active `mcity.exe`: 25,435 internal entries; 25,434 exports and one failure.
  Its 338 external imports are inventoried separately.
- Three residual entries: one main-client failure, one launcher failure and one
  launcher timeout. Private instruction listings preserve an alternative research
  path. See the [failure list](decompilation-failures.json).
- Original files remained external, read-only inputs. Raw output, projects,
  import copies and logs remain under ignored `evidence/recovery-export/`.

The [per-module report](export-status.md) records exact counts and locations.
Historical cache entries have independent hashes and addresses. Imports in
[dependencies.json](dependencies.json) are static symbol-library observations;
filename matches are candidates, not proof of runtime resolution. Dynamic loading,
unidentified code boundaries and original runtime traces remain separate work.

## Build verification

The published authored C++ sources build through `python build.py --test`.
Microsoft MSVC 19.51 with Ninja/Release passes all 67 native checks locally.
All 37 native/Python comparison commands from the native CI workflow also pass
against that MSVC build, including byte-exact wheel initialization and part bounds.
These comparisons verify supported bounded contracts, not a full driving client.
The local Python suite ran 913 tests successfully with seven optional tests skipped.

Ubuntu CI for source checkpoint `dd80971` passed the native build, CTest,
native/Python comparisons, and generated-asset SDL/OpenGL garage/platform smoke
checks. Windows compilation exposed a missing `<array>` include in a test;
`c001bb3` fixes it and the complete local MSVC build verifies the correction.
Original-asset Linux gameplay and complete online sessions remain unverified.

## Next recovery work

Review shared types and function dispositions, then connect translated systems in
the [approved dependency order](plan.md). The main worksheet currently has 31
explicitly reviewed entries; decompilation success does not promote any of the
remaining entries to implemented. Existing address-linked source is a review aid.
Complete startup, rendering/audio, interconnected simulation and services still
require translation and integration before a rebuilt original game can ship.
