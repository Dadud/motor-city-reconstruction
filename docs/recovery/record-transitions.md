# Record initialization and callback transitions

Seven more original entrypoints now have bounded native implementations, plus
two connected lifecycle traces. The target remains `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
All controller and selector bodies execute in the original-code oracle. Actual
handler implementations are **not recovered by this batch**: callback calls use
the explicit substitutions described below.

| Entry | Cell | Compared cases |
| --- | --- | ---: |
| `0x434e40` | `record_machine_initialize` | 30 |
| `0x434ef0` | `record_machine_reset` | 30 |
| `0x432620` | `record_transition` | 96 |
| `0x436230` | `record_activate` | 24 |
| `0x435270` | `record_handler` | 38 |
| `0x433dd0` | `record_pair_match` | 216 |
| `0x435840` | `record_should_retain` | 2,040 |

The aggregate now covers 59 cells and 6,329 cases. The two lifecycle traces are
separate integration checks, not additional recovered entries or cell cases.
MSVC and Zig/Clang match the original observations, including every recorded
callback-entry image and final machine state.

## Original order and memory contracts

The six `0x100` record slots begin at `0x98baf8`. Initialization clears all six,
sets the base and current pointers, installs identifier 24 and handler identity
`0x432180`, and sets the first record's `0xc8` sentinel to `0xffffffff`.
It calls handler event zero **before** clearing the rollover/post-stack globals.
The external first camera preset is read after the callback; only a signed-positive
preset updates the selected index to preset minus one. A callback's current-record
redirection is preserved. The reset entry has the same observed body and reuses
the authored initializer in C++.

`0x435270` returns original 32-bit handler identities. They are opaque keys for
the native callback bridge, never addresses cast to host function pointers.
The pair matcher accepts either orientation and stops at a first-word
`0xffffffff` sentinel before reading its second word.

The predicate's meaning comes from its caller at `0x434f90`: true means retain
the current record. An override requests identifier-only matching. Otherwise,
selected handler groups additionally compare parameters; identifiers 14 and 22
have explicit same-identifier exceptions. Different identifiers use the signed
retention gate and handler classification. The corpus tests the identifier
groups, override values, parameter differences and signed deadline boundaries.

The transition controller then preserves this order:

1. Read the entry current-record identifier and scan the pair table.
2. For a matching pair, copy 256 bytes to the snapshot at `0x98b9a0`; otherwise
   set rollover and clear its three auxiliary words.
3. A replacement calls the old handler with event 3, then reloads current from
   the global. A nonzero push flag advances the captured entry cursor by `0x100`.
4. Write the new identifier, handler and parameter, then call event 0.
5. Reload current again. For a matched pair, set its `0x20` flag and copy the
   three inherited words from their current global values in instruction order.

Those three globals alias words inside the snapshot. They can also be changed
by callbacks, so neither the old record span nor cached pre-callback values can
replace the original reloads. The original controller reads current+4 before
its later null branch; a null entry current is not admitted as a valid push
input merely because decompiled pseudocode shows that branch.

Activation supports a null current pointer. Otherwise it sets `0x10` before
calling a nonnull optional handler with event zero. A null handler still allows
the flag write; a missing native implementation for a real handler raises an
explicit error instead of silently becoming a no-op.

## Authored view and substitution boundary

`mco::RecordMachine` is an authored view over caller-owned bytes starting at the
original virtual identity `0x98b9a0`, with three separate scalar globals. It is
not a recovered class definition. Named offsets come from `layouts.json`.
The backing span stays fixed during a call; callbacks may mutate its bytes and
the scalar globals. Address mappings are checked and cannot extend into the
separate selection globals. The pair table represents the separate original
`0x88acdc` image and must have storage disjoint from the machine arena.
Callback ownership, real handler logic, faults,
stack overflow and live owner integration remain unresolved.

`tools/record_machine_cases.py` temporarily replaces the first instruction of
eight handler entrypoints with RET and attaches a controlled observation/mutation
hook; it restores their original bytes afterward. These are `0x42f630`,
`0x42f8f0`, `0x431ba0`, `0x432180`, `0x432730`, `0x432bc0`, `0x433200` and
`0x433820`. The controller bodies and dispatch jump tables are unchanged.
The native fixture implements the same declared callback scripts.

Each callback records its identity, raw event word, all three external scalars
and the complete machine image before mutation. Scripts exercise current-pointer
redirection, record parameter/flag changes, snapshot-word alias changes,
selection-count changes and rollover changes. Final images are compared too.
This establishes controller behavior under those substitutions, not correctness
of the original handler bodies or their wider side effects. The original word
copies assume the caller's direction flag is clear.

## Connected trace and commands

The lifecycle trace initializes, sets an expired retention gate, verifies that
the current record need not be retained, selects a handler, checks a pair,
pushes, activates, pops and searches. It runs nine complete original calls and
compares all callback-entry images and final state with the native sequence.
Two initial byte patterns are retained. The CTest integration gate additionally
checks that transition and activation flags compose and that popped child
identifiers are excluded from the active stack search.

```powershell
python -m tools.run_cell_comparisons build/recovered
.venv/Scripts/python.exe -m tools.run_cell_comparisons build/recovered --original 'C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe'
python -m tools.native_record_lifecycle_compare build/recovered/Release/mco_record_lifecycle_compare.exe
```

The aggregate runner automatically includes the lifecycle comparison, on one
consistent corpus snapshot. Individual drivers remain available. A fresh oracle
export recreates the callback substitutions and connected traces; raw original
instructions and game assets are not stored in the corpus.

The subsequent [camera selection recovery](camera-selection.md) establishes all
four preset words and corrects the old count/pending interpretations.
