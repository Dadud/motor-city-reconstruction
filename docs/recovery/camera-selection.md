# Camera preset application

Two additional original entrypoints are recovered: `0x436c90`
(`record_selection_apply`, 1,583 cases) and `0x489cb0`
(`camera_context_special`, 238 cases). Their complete bodies execute in the
hash-checked original `mcity.exe` oracle. The controller's callback handlers
remain explicit substitutions; the context predicate executes its actual body.

## Preset state and producers

The six words at `0x9aba98` are four camera preset values, a selected camera
index, and a selected preset slot. The first word is **not a count**, and the
last word is **not pending state**. The original reset paths at `0x531360` and
`0x617ef0` write presets `1,2,3,4`, selected index `1`, and slot `0`.
The latter also references the original reset-cameras message. Initial setup
at `0x48b670` writes the middle three presets. These producer conclusions are
static instruction/pseudocode evidence, not claims that their full UI and
notification paths have been implemented.

The cycling controller at `0x436520` indexes the first four words by the slot,
skips zero presets, and uses a positive preset minus one as the selected index.
The subsequent [camera cycling recovery](camera-cycling.md) implements that
controller and its explicit mode child; the UI producers remain unrecovered.
The native
`RecordMachine` now stores all four presets in one array, the selected index,
and the slot. Existing three-word comparison transports retain their original
ordering so earlier observations remain unchanged.

## Complete application behavior

The low byte of original global `0xaa459c` chooses the application path.
Zero normalizes all six words using the recovered signed rules, then chooses
identifier `selected_index + 4` and handler identity `0x42f8f0`. The returned
quotient from normalization is ignored here. Nonzero reads a signed table
index from `0x98c100`. Indexes at least nine return before reading the current
record. Negative indexes address storage before the original mode table and
are outside this bounded host contract; the host rejects them.

Indexes zero through eight select one of nine supplied words corresponding to
`0x88ac50`. A selected identifier 23 sets both external counters at `0x88ac30`
and `0x88ac34` to ten. The actual context predicate reads `0x9aa9b0`: a first
word of 18, or a third word of 23 or 24, produces true. The request flag becomes
one for true and four for false, and the resulting identifier becomes 12.
Other selections clear the request flag. The counters' wider roles remain
unresolved. Handler classification matches the original jump-table groups.

Both paths scan the supplied symmetric pair table, copy the entire current
record to the snapshot on a match, or set rollover and clear its three auxiliary
words on a miss. They call the old handler with event three, reload the global
current record, install the selected identifier/handler and zero parameter,
then call the new handler with event zero. A match reloads current again and
inherits three snapshot words. Direct selection clears the request flag after
callbacks; the table path preserves callback writes to it.

The inline transition's instruction order differs from `record_transition`:
it reads inherited word one before setting flags, reads word zero after that
write, stores word zero, then reads word two and stores the last two words.
The implementation preserves this order independently. Cases redirect current
to overlapping snapshot views at offsets zero, four, eight and twelve, so an
apparently equivalent reordered copy would fail. Ordinary callbacks can also
redirect into other slots and modify flags, parameters, all six selection
words, counters, and rollover state. Every callback-entry image and final
image is compared, including the supplied mode/context/pair tables.

## Connected verification and limits

Twelve separate traces compose four complete calls: initialization, direct
selection, special-mode selection, and disabled-mode selection. They retain
five callback observations each, vary match/miss paths, initial image seeds,
and callback mutations. The aggregate runner checks them automatically in
addition to the two earlier record lifecycle traces. These are integration
probes, not additional recovered functions or cell cases.

The aggregate has 62 implemented cells and 8,686 complete-function cases.
The coarse region map assigns 61 to W0 and this context predicate to W6; its
recovery is a dependency of the W0 controller. The corpus retains its historical
`wave0.json` filename.
All prior 60 cell observations and two prior lifecycle observations are
unchanged. MSVC and Zig/Clang compare every case exactly, including the twelve
new connected traces. Native suites pass 141/141 and 143/143 tests respectively;
the Python suite runs 985 tests successfully with seven skips. Layout audit
reports 98 distinct registered offsets across 34 consumers, zero shared
unregistered offsets, and a current generated header.

Callback substitution is deliberate: the eight handler entries are replaced
by RET and controlled observation/mutation hooks. Controller instructions,
selection normalization instructions, predicate instructions and jump tables
execute unchanged in the original oracle. This is not a recovered camera
update, collision system, input implementation or live-game acceptance claim.
Original pointer faults, unsupported memory windows, and negative table indexes
remain outside the host interface. Authentic UI/input producers, actual handlers, and wider owner integration
remain required; cycling is covered by the subsequent batch.

Replay with `python -m tools.run_cell_comparisons BUILD_DIR`. Add
`--original MCITY_EXE` to capture fresh hash-checked original observations.
