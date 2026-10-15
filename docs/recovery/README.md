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
The [export checkpoint](export-checkpoint.md) records the completed static pass,
build verification and the remaining reconstruction work.

- `function-enumeration.json`: function addresses/names and REA enumeration identity.
- `functions.csv`: sortable per-function recovery worksheet.
- `functions.json`: worksheet with structured references and summary counts.
- `function-reviews.json`: explicitly reviewed completion claims and remaining work.
- [status.md](status.md): generated counts and reviewed translation totals.
- `binary-scope.json`: recursive executable-header scan and EXE/DLL extension candidates.
- `modules/`: per-binary function inventories, interfaces and direct-call edges.
- `dependencies.json`: imported-library names and installed filename candidates.
- `decompilation-failures.json`: remaining failed or timed-out exports.

No executable bytes, disassembly, pseudocode or account information are included.
Names and addresses identify functions in the exact recorded binary.

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
