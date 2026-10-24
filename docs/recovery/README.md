# Function recovery inventory

This inventory tracks the installed `mcity.exe` by SHA-256, not filenames alone.
It enumerates every function identified by the stated Ghidra analysis profile.
That includes library/runtime code and thunks; it is not a claim that analysis
found every possible code entry. Supporting DLLs, launcher executables, ASI plugins
and historical executable cache files have separate hash-scoped inventories.
The [approved implementation plan](plan.md) and [private export workflow](exporting.md)
now drive that work; [installation export status](export-status.md) covers all binaries.
[Established shared layouts](shared-layouts.md) document current byte contracts,
pointer boundaries and unresolved startup dependencies.
The [cell comparison checkpoint](cell-comparisons.md) documents the shared
native/original corpus workflow and its bounded coverage.
The [INI-style configuration loader recovery](ini-config-loader.md) records the
byte parser and lookup model plus the remaining Win32/global-table boundaries.
The [configuration-name comparison](config-name-compare.md) documents the
directly compared default-mode primitive used by that lookup.
The [export checkpoint](export-checkpoint.md) records the completed static pass,
build verification and the remaining reconstruction work.

- `function-enumeration.json`: function addresses/names and REA enumeration identity.
- `functions.csv`: sortable per-function recovery worksheet.
- `functions.json`: worksheet with structured references and summary counts.
- `function-reviews.json`: explicitly reviewed completion claims and remaining work.
- `triage.json` / [triage.md](triage.md): rule-based classification of every exported
  function with the rule that fired, code-shape clustering and the resulting required set.
- `dispositions.json`: published scope decisions. Region dispositions for the game client
  cite the original's own string vocabulary; module dispositions are role assignments and
  are marked behavior-review-pending where internals are unreviewed.
- [status.md](status.md): generated counts and reviewed translation totals.
- `binary-scope.json`: recursive executable-header scan and EXE/DLL extension candidates.
- `modules/`: per-binary function inventories, interfaces and direct-call edges.
- `dependencies.json`: imported-library names and installed filename candidates.
- `decompilation-failures.json`: remaining failed or timed-out exports.

No executable bytes, disassembly, pseudocode or account information are included.
Names and addresses identify functions in the exact recorded binary.

See the [REA workflow audit and operating contract](rea-workflow.md) for current tool alignment, Evidence rules and limitations.
The [startup toggle-key recovery](toggle-key-progress.md) records the recovered Num Lock boundary and its platform limitations.
The [connected startup toggle batch](startup-toggle-progress.md) now executes that
body together with device initialization, layout, input and cleanup, including its
defined original x86 temporary-word transfer.
The [startup/mouse batch](startup-mouse-progress.md) separately connects actual
startup, Num Lock and mouse runtime bodies through shared dimensions, diagnostics,
window state and cleanup, while retaining the keyboard initialization boundary.
The [mouse lifetime recovery](mouse-lifetime-progress.md) records initialization, cleanup, bounds forwarding and unresolved platform calls.
The [connected mouse batch](mouse-batch-progress.md) adds state setting, geometry, callbacks and persistent runtime comparisons.

## Read the labels

`decompilation=retained` means a saved matching-target REA function/pseudocode
record was found locally. `not-indexed` means no such record was indexed; it does
not prove that nobody has decompiled the function. Raw records remain private.
`bulk_decompilation` records the separate full Ghidra export result for each
function. It is merged only when the binary hash and complete entry sets agree.

`translation=unreviewed` means published completion has not been established by
this inventory. It is deliberately different from `missing`: source may exist.
The Python, native, verification and documentation reference columns contain
exact address mentions in tracked files, with line numbers. They are navigation
and review candidates; callers, oracles and comments can mention a function
without implementing it. Instruction addresses are included only when they also
match enumerated function entries. Historical documentation does not automatically
establish completion either.

`native-bounded` identifies C++-only recovery cells whose stated domains have
original-execution comparisons; it does not claim a Python implementation.

Explicit reviews distinguish bounded implementations, partial work, unpublished
drafts and missing translations. Original-comparison labels apply only to each
row's described domain. Verification status is reviewed metadata, not a claim
that the comparison ran during inventory generation. The build script verifies
compilable authored code, not overall binary recovery.

## Refresh

From a public checkout, regenerate tracked-file links and preserve published
evidence IDs with:

```sh
python -m tools.function_inventory
```

Researchers with private saved REA evidence can rebuild its metadata index:

```sh
python -m tools.function_inventory --evidence evidence
```

Refresh the installation's binary identities separately with
`python -m tools.binary_inventory "/path/to/Motor City Online"`. This reads files
without loading or executing them. The [export catalogue](export-status.md) records
completed and pending DLL/function inventories.

The generator rejects a mismatched executable digest, duplicate addresses,
enumeration-count mismatches and reviews for absent functions. Track this
directory and the generator before regenerating so published files participate
in `git ls-files`.

To replace the base enumeration, open the exact executable in REA/Ghidra and
request `search_procedures` with regex `.*`; retain the complete result privately.
Store its address/name pairs, digest, evidence ID, analysis profile and full count
in `function-enumeration.json`. Never use truncated previews as the inventory.
Ghidra enumeration is static analysis, not runtime verification or recovered source.

Next: review linked candidates, identify subsystem boundaries and external
interfaces, then translate unresolved functions in dependency order. Counts here
measure records and reviewed scope; no completion percentage is inferred from
address mentions or decompiler coverage.

## Supplemental callable boundaries

`function-supplements.json` records independently evidenced, hash-scoped callable entries absent from the retained enumerations. It does not edit the original REA enumeration or module exports. Each entry declares a contiguous boundary, name, direct callees, evidence and existing source paths. The loader rejects duplicate/conflicting entries, overlapping supplemental ranges, unsafe/missing sources, malformed addresses and incomplete base inventories. Unknown call targets are never promoted automatically.

Inventory, module triage and dependency backlog all apply the same supplement loader. Outputs distinguish the base count and supplement count/digest, retain per-entry boundary provenance, and mark new decompilation as `not-exported-supplement`. Supplements establish entry identity only: a separate explicit review is still required to claim translation or verification. The first entry is the registered shutdown callback `0x6f0350`, proven by its registration, instruction boundary and complete original-execution comparisons.
