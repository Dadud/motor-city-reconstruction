# Raw key queries, press latches and key releases

Three complete original routines are recovered without input-body substitutions:

| Entry | Native routine | Complete cases |
| --- | --- | ---: |
| `0x460670` | `input_key_raw` | 2,396 |
| `0x4acdc0` | `input_key_query` | 1,472 |
| `0x584610` | `input_key_release` | 688 |

The free-camera handler at `0x433820` calls the latched query for its controls.
Its complete update body remains unrecovered. These routines establish actual
input dependencies and one release-message producer, not hardware polling or
an integrated camera update.

## Raw bytes and latched queries

The raw table begins at `0x8c8648` and has 128 observed query bytes. A **signed**
code at least 256 returns zero. Every other 32-bit value, including negative
signed values, reads byte `code & 127`. Thus codes 1 and 129 share a raw byte,
while `0x80000000` reads byte zero. The instructions zero-extend the byte into
EAX; the result is not normalized to a boolean. Cases include every byte value,
all codes zero through 511, signed extrema, aliases and deterministic random
32-bit codes.

The query calls the actual raw helper, reads its own latch byte at
`0x9e1be8 + code`, ANDs that byte with the raw result, and always stores the
masked latch. A zero press-only argument returns whether the raw byte is
nonzero. A nonzero argument returns true only when the raw byte is nonzero
and the masked latch is zero, storing `0xff` in that case. The entire argument
is tested: 256 is nonzero, unlike a low-byte-only mode check.

A level query does not consume a first press when the latch is still zero.
Repeated press-only queries reduce the consumed `0xff` to the raw mask; a
release clears it. If a nonzero raw mask changes from 128 to 1 after a held
query, their disjoint bits can produce a new press. Replacing raw bytes with
booleans would change this behavior. Codes sharing raw state retain independent
latch bytes. A nonnegative code above 255 still clears a supplied mapped latch
because the raw helper returns zero. The corpus provides a 512-byte latch
observation window; this is not a recovered original array-size claim.

The host raw query accepts every code. The latched host query requires a
nonnegative code inside the supplied latch span, disjoint from the raw image.
Negative original latch accesses and pointer faults are outside that contract.

## Actual release producer and calling convention

The release handler first checks a nonzero enabled argument and equality between
the message window identity and the configured identity at `0xacadb0`. It
extracts `(message_bits >> 16) & 127` and optionally maps that byte through the
128-byte table addressed by `0xacae18`. A mapped code of 42 or 54 clears both
Shift bytes, 54 then 42. Other codes clear only the selected byte. Every path
returns zero. The native interface makes the global window identity and optional
mapping explicit; original arguments three, four and six are unused.

The decompiler displayed five parameters, but the original exits at `0x584655`
and `0x584667` use **RET 0x18**. This is a six-argument callee-cleanup callback.
The initial five-argument cdecl oracle adapter failed with an unmapped return
fetch. The corrected adapter plants six arguments and omits caller cleanup;
all complete-body captures then finish. No reference outputs were changed to
fit the native implementation. The calling-convention registry records this
correction for future window-dispatch recovery.

Cases cover all 128 scan indexes, absent/reverse/high-byte/Shift remaps,
disabled messages and matching/foreign windows. Remapping can select a byte up
to 255, so the release corpus observes a 256-byte window at the raw table base.
Its first 128 bytes overlap the query image. The extra observed bytes are not
claimed as part of the original raw-key array. The host checks the selected
mapped byte and both Shift stores against the supplied span. Disabled or
foreign-window messages perform no key-image access.

## Connected verification and remaining work

Six connected traces contain 21, 21 or 42 query steps for each of two initial
image seeds. Nonzero byte setups are supplied by the caller. Zero-byte steps
call the actual six-argument release handler before querying, rather than
planting zero directly. The traces exercise raw-mask changes, level and
press-only queries, shared raw aliases, independent latches, mapped high-code
latches, Shift pairing and repeated sequences. Every query result and full
raw/latch images are retained. No input callback, child body or Windows API is
substituted in these calls. The release handler's EAX is checked separately in
its 688 complete-function cases.

The aggregate now covers 67 functions and 17,589 complete-function cases.
All previous 64 cell observations and 22 camera lifecycle traces are unchanged.
Six input traces bring the separate lifecycle total to 28. The coarse region
map assigns W0 63/658, W5 1/6,635 and W6 3/1,763. These are function coverage
counts, not whole-game completion percentages.

MSVC and Zig/Clang match every case and connected trace exactly. Native suites
pass 148/148 and 150/150 respectively. The Python suite runs 985 tests
successfully with seven skips. Its target/routine rejection test now copies
only the real cell it reads, avoiding repeated copies of unrelated large
images; the separate all-cell corpus/runner checks remain intact. Layout audit
reports 98 distinct offsets across 40 consumers, no shared unregistered offsets,
and a current generated header.

Key-down producer `0x584450` is recovered over its caller-owned queue and
key-state images, with original-comparison coverage. Focus-loss handler
`0x584070` is now reconstructed with explicit bridges for
`DefWindowProcA`, `UnhookWindowsHookEx`, `GetModuleHandleA` and
`SetWindowsHookExA`. It matches 18 hash-checked original executions covering
activation, deactivation/minimization, hook setup/teardown and rejected calls;
the separate activation flag and 128-byte raw-key table are modeled directly.
Live Win32 delivery and global hook behavior remain unverified. Window
dispatch, authentic message/input producers, actual camera handler math and
collision calls, and live keyboard/camera acceptance remain required. No real
window was driven and no PE entry point was started.

Replay all cells and four lifecycle groups with
`python -m tools.run_cell_comparisons BUILD_DIR`; add `--original MCITY_EXE`
for fresh hash-checked original-code capture.
