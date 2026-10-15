# Private static recovery exports

The [approved plan](plan.md) is the current work order. The exporter reads the
installed binaries, checks their recorded SHA-256 values, and imports exact
private copies into persistent Ghidra projects. It never launches the game or
changes installed files. It needs Python 3.11+, Ghidra and a compatible JDK;
these are research tools, not game build dependencies.

```sh
python -m tools.recovery_export "/path/to/Motor City Online" --ghidra "/path/to/ghidra" --java-home "/path/to/jdk" --max-functions 0
```

This recursively inventoried binary set includes nested setup, database and NPS
support files. Files with identical hashes share one project. Use repeated
`--binary relative/path.dll` arguments to select a subset. Projects and raw exports
must remain under ignored `evidence/`; tracked or public output locations are
rejected. Exact private import copies avoid a Ghidra Windows launcher bug with
parentheses in installed folder paths.

After inventory/analysis, export a bounded batch with the same command and
`--max-functions 200`, or all remaining analyzed functions with
`--max-functions -1`. Each function has a default 30-second timeout. Completed
outputs are skipped on resume. Failed/time-out attempts are retained and skipped
until `--retry-failed` is explicitly selected. Use `--retry-timeouts --timeout 120`
to increase the time budget without repeating non-timeout failures. Missing successful outputs are
re-exported. An invalid journal stops the run for inspection rather than silently
discarding records. Do not run two exports against the same binary/project at once.

Each hash directory contains the persistent project, analysis metadata, the
complete analyzed function list and direct callees, imported/exported symbols,
data-type identities, per-function pseudocode, a flushed attempt journal, and a
headless log. A per-run completion token detects script errors even when Ghidra
returns process status zero. The initial inventory-only pass saves the analyzed
project before long decompilation batches.

Use `--failure-listings` to preserve private instruction listings for remaining
failed functions without retrying decompilation. These support manual boundary
and type investigation; they do not count as successful pseudocode exports.

Publish only metadata with:

```sh
python -m tools.recovery_catalogue
```

The catalogue validates function counts and artifact identity, checks successful
output files, and publishes module-specific functions and interfaces plus
[export status](export-status.md). Addresses are scoped to binary hashes. Existing
REA records and reviewed translation claims remain in their separate worksheet.
Custom exports are labeled local Ghidra observations, not fabricated REA Evidence IDs.
The same command generates a private `evidence/recovery-export/README.md` browser
with per-binary links to pseudocode and failed-function instruction listings.

Decompilation success means the tool produced text. It does not establish correct
types, function boundaries, indirect-call resolution, original behavior, or
compilable source. In particular, stack helpers and address-taken callbacks can
confuse default analysis; these require manual boundary and calling-convention
review. Exported types are observed database identities, not final source headers.
Keep such uncertainties visible during translation and comparison.
