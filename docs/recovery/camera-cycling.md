# Camera preset and subject cycling

Original `0x436520` (`record_selection_cycle`) and its actual child `0x436fa0`
(`record_mode_apply`) now have native implementations. The cycle controller
has 3,192 complete-function comparison cases; the explicit mode child has
1,155. Both retain the supplied handler substitutions from the earlier
[camera selection recovery](camera-selection.md). Normalization, context tests,
handler classification, pair scans and transition children execute their
original instructions in the oracle; those children are not stubbed.

## Viewport subjects and early returns

The cycle controller takes one cdecl viewport index. It reads the current
record identifier first and returns immediately for identifier ten, without
reading the subject tables. Otherwise it compares pointer identities at
`0x98c370 + viewport*4` and `0x98c3ac + viewport*4`. The native interface receives
one caller-owned byte span containing both tables at their observed `0x3c`
spacing. It checks the requested entries before reading them. The corpus uses
a 120-byte window and viewports zero through fourteen; this window is an
observation domain, not a recovered array count or class size. Pointer
identities are compared, never cast or dereferenced on the host. The blocked
ten path also covers viewport `0xffffffff` without a subject read.

Different subjects return immediately for current identifiers 27 and 11.
Otherwise they increment the mode index with 32-bit wrapping and signed
remainder modulo nine, skipping table values equal to four. The original
stores the new index only after finding a usable entry. Tests cover wrapping
from eight, starting at minus one, starting at INT_MAX minus one, and tables
with eight skipped entries. A negative resulting table access is outside the
supported domain and is rejected. A table containing only fours would loop
forever in the original; the host rejects it after a full cycle without
storing an index. These rejections are bounds behavior, not original fault or
nontermination emulation.

A selected value 23 writes both external counters to ten. With a zero mode
byte it selects identifier eight and request flag two. With a nonzero mode
byte it uses the real context predicate, selects identifier twelve, and sets
the flag to one or four. Other values clear the flag. The actual handler
selector and `record_transition` then replace the current record. Callback
writes to the request flag survive this path.

## Preset cycling and explicit application

Equal subjects cycle presets only for the handler group `0x42f8f0`.
Identifier ten still returns through the earlier guard. Other handler groups
leave the state untouched. The accepted path first normalizes all six selection
words, advances the selected slot modulo four, and skips zero presets.
**Negative nonzero presets stop the scan but cause no transition.** This is
signed original behavior; skipping all nonpositive values would be incorrect.
A positive preset selects preset minus one. Zero mode composes the direct
selection controller, including its second normalization and its final request
flag clear. Nonzero mode calls the newly recovered explicit mode child using
the current mode-table index.

The explicit child takes one signed index argument and does not store it into
the global index. Indexes at least nine return before reading current. It
rejects negative table accesses in the host. It selects the same nine-word
mode table and handles special value 23 differently from the earlier general
application controller: zero mode selects eight/flag two; nonzero mode selects
twelve/flag one or four. It uses the general transition's inherited-word order,
which is distinct from the direct selection path. Snapshot-alias callback
redirections exercise both orders. Supplied images/tables and the external
counters must have the distinct storage relationships of the original globals.

The shared host normalization helper only packs and unpacks the canonical
four-preset/index/slot state around the previously recovered normalizer. It is
not counted as another original function.

## Verification

The aggregate now contains 64 implemented cells and 13,033 complete-function
cases. The coarse region accounting is W0 63/658 plus one W6 context dependency.
All earlier 62 cell observations and fourteen lifecycle traces are unchanged.

Eight new connected traces execute six complete calls each: initialization,
selection, equal-subject preset cycling, explicit special mode application,
and two different-subject mode cycles. The caller changes subject identity and
mode byte between calls, as recorded in the probe. Each trace retains eleven
callback-entry images. Two image seeds, match/miss tables, and callbacks that
mutate the preset/counter globals are covered. These are separate integration
probes, not additional function coverage or cell cases.

MSVC and Zig/Clang match every complete-function observation and all 22
connected lifecycle traces exactly. Native tests pass 144/144 and 146/146
respectively. The Python suite runs 985 tests successfully with seven skips.
The layout audit retains 98 distinct registered offsets, now across 37
consumers, with no shared unregistered offsets and a current generated header.

The eight actual record handlers are still RET plus controlled observation/
mutation hooks. Recovering those handlers, their collision/input/math
children, authentic UI producers and integrated camera rendering remains
required. Original invalid reads and nonterminating inputs remain outside the
bounded host contracts. This batch does not establish live camera behavior.

Run `python -m tools.run_cell_comparisons BUILD_DIR` for every cell and all
three connected lifecycle groups. Add `--original MCITY_EXE` to recreate the
hash-checked original observations before comparison.
