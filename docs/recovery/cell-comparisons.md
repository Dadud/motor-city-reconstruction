# Recovery cell comparisons

The 67 implemented cells have generated C++ comparison runners and a shared
corpus transport. The current corpus has 17,589 cases, captured from the
hash-checked original `mcity.exe` using Unicorn x86 emulation and matched
bit-exact by native runners on Windows with Zig/Clang. This verifies bounded
inputs, not whole-game integration or live services.

After wiring the first 28 cells, six more routines were recovered through the
same pipeline: `0x429440` and `0x429460` (null-guarded pointer-clear siblings),
`0x410c10` and `0x42cad0` (global assignments), `0x4154c0` (buffer length and
terminator), and `0x424cc0` (nullable table target clear). Original instruction
bytes establish cdecl versus thiscall/`ret 4` conventions; 82 additional
original/native cases cover these bodies. Invalid host lengths and table entries
are rejected explicitly; original fault behavior is outside the supported domain.
The subsequent [entity and mask batch](entity-table.md) adds eight routines and
2,452 cases, including packed fields, signed wrapping and byte selectors.
The [record-stack batch](record-stack.md) adds ten routines and 771 cases,
including instruction-ordered overlapping copies and inclusive text limits.
The [record controller batch](record-transitions.md) adds seven routines and
2,474 cases plus two connected lifecycle traces. Its callback bodies are
explicitly substituted; those handlers remain unrecovered.
The [selection-state helper](selection-state.md) adds one complete register-input
routine and 536 cases with no substituted dependencies. The subsequent
[camera application controller](camera-selection.md) adds two routines, 1,821
cases and twelve separate connected traces. It composes the real context
predicate and normalization; actual callback bodies remain substituted.
The [camera cycling batch](camera-cycling.md) adds two controllers and 4,347
cases, plus eight six-call lifecycle traces. The [input state batch](input-key-state.md)
adds raw-key and latch queries plus the actual release producer: 4,556 cases
and six connected query/release traces without input substitutions.

## Repeat the comparison

After building, replay committed observations without original assets or
Unicorn (the native CI workflow runs this command with its own build directory):

```sh
python -m tools.run_cell_comparisons build/native-zig
```

Runners may live directly in the build directory or its `Release` child.
The aggregate also runs all four groups of connected lifecycle comparisons, separately
from cell coverage. It loads one corpus snapshot and calls the common comparator
directly, avoiding a new Python process and full corpus parse per cell.
With the original game and optional Unicorn dependency available, capture
fresh observations and compare native outputs in one invocation:

```powershell
.venv/Scripts/python.exe -m tools.run_cell_comparisons build/native-zig --original 'C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe'
```

To retain fresh observations for inspection or regression updates:

```powershell
.venv/Scripts/python.exe -m tools.w0_cell_corpus 'C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe' --output build/recovery/wave0-fresh.json
python -m tools.run_cell_comparisons build/native-zig --corpus build/recovery/wave0-fresh.json
```

`corpora/wave0.json` contains synthetic inputs and observed outputs, with the
executable SHA-256 and original function addresses. Outputs come from original
registers and memory, never from translated implementations. Original table
addresses are seeded with synthetic bytes before execution. No executable bytes
or original assets are exported; the entry point and host services are not run.

## Transport and gates

Each manifest's `comparison.body` adapts its host signature to decimal uint32
words. Byte images travel as individual byte-valued words, signed inputs as
two's-complement bits, and each case has a leading zero marker. The shared
`native/tests/cell_io.hpp` rejects empty, incomplete and trailing input. Each
runner prints one row per case. Python rejects missing/extra rows, differing
widths or words, empty corpora, and mismatched target hashes or addresses.
The aggregate runner also refuses drivers reporting zero verified cases.

`tools/function_cell.py` renders runners from manifests and records provenance
hashes. Python tests require every implemented cell to have nonempty original
observations and runners matching its manifest. New cells still require an
authored oracle adapter and comparison body; scaffolding is not verification.

Memory cases compare full supplied images, including preserved fields and
trailing guards. Buffer copies adapt the original object's `+8` destination
field to the host's twelve-byte span. Registry registration compares the node
and counter; the oracle also checks its head-global update, which remains caller
responsibility in the host interface. Pointer-clear and fallback-clear helpers
now accept empty spans for null pointers, with both branches compared.

Overlap is verified for the copy and text helpers described in the record-stack
batch. Aliasing in other interfaces, invalid original pointers, division faults
and inputs outside corpus domains remain unverified. Self-tests remain
separate from corpus comparisons.

## Compiler verification

Windows MSVC and Zig/Clang now build successfully and both replay all 17,589 cell
cases exactly. The startup record's `__int128` has been replaced by portable
four-word integer arithmetic. Its 5,464 Python integer/conversion comparisons
pass on both compilers. See [startup record](../calculations/startup-record.md)
for the expanded 135-case constructor comparison and remaining angular
tolerance. Missing `<stdexcept>` includes in the entity-clear source and both
buffer-copy self-tests have been fixed. Linux execution remains unverified
locally; the native CI workflow runs the portable arithmetic comparison on both
Windows and Linux.
