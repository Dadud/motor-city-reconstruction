# Input queue consumption recovery

The raw-scan translator `0x6f05b0` is implemented as `input_scan_translate`. Queue pop `0x5830c0` and peek `0x583160` are also implemented; connected producer/consumer comparison is verified below.

The translator always requests device state kind 6 before processing the scan. Caps-lock scan `0x3a` toggles the separate caps flag and returns zero without dereferencing the returned state. Otherwise modifier priority is alt, control, shift, caps, then normal. Shift plus caps selects the shift plane rather than inventing caps inversion. The second value passed by queue callers is unused by this original body.

Five table starts lie 91 bytes apart in one mapped lookup window. The native contract supplies a 620-byte window so byte-sized queue scans can reach the same overlapping addresses; it does not pretend each plane is an independent 256-byte array. Tables are caller supplied. No original embedded table bytes are published. Device-state byte offsets and table starts are registered in `layouts.json`.

Mapped values below 128 are returned directly. Values 128 through 143 are shifted left eight; values 144 through 255 first lose their high bit, then shift left eight. Control plus scan 1 requests exit code zero when enabled, unless the higher-priority alt branch was selected. The original exit helper leads to ExitProcess(0); the native exit bridge must not return. A returning bridge is rejected instead of continuing through an impossible normal return.

Verification: 3,152 complete original translator cases match MSVC and Zig exactly, including eight observed exit requests. Original translation code runs unchanged against synthetic table/device inputs. Device acquisition is a declared bridge; exit observations stop at the selected exit request rather than executing process cleanup. Cases cover every byte scan, left/right modifier combinations and precedence, caps values, output encoding boundaries, unused extra arguments, provider mutations, caps handling with an unused null state, and exit suppression/selection. All cases compare results, flags and bridge observations; selected boundary/mutation cases additionally compare complete device/table images. Compact fixture configurations avoid repeating large synthetic read-only inputs in every golden case.

Native tests independently check plane priority, encoding, caps/provider ordering, null-state caps handling, and the control-Escape request. The retained corpus now contains 86 cells and 44,143 routine cases; the prior 44 connected traces are unchanged. The complete checkpoint is verified below.

The device acquisition implementation, process cleanup and live keyboard platform behavior remain unfinished. Supported scans are the byte-sized values supplied by queue records; invalid original dereferences and arbitrary out-of-domain scans are not emulated.

## Queue consumers

Pop and peek match 137 and 138 original cases respectively under MSVC and Zig. Both use the actual recovered scan translator. Cases compare complete queue/key/remap images, lock observations, translation state and provider observations, including changes made by lock and device-state callbacks. Synthetic alias indices exercise mapped 32-bit event-address arithmetic.

Peek discards records whose translation returns zero, retaining the first usable record. Pop consumes that record. Both preserve the last scan prefix when all translations return zero, sign-extend stored 16-bit characters, and reload the head after translation. A selected terminal exit does not advance the head or execute the leave callback. Independent native tests cover these behaviors, repeated peeking, and empty queues with zero capacity.

The retained corpus now contains 88 cells and 44,418 routine cases. The corpus retains 44 connected traces, with the four queue traces extended as described below.

The four queue lifecycle traces now extend the original producer/query/release/resize sequences with 13 operations each: resize, raw key production including caps, a high-bit character message, repeated peek/pop, and empty reads. Every step compares complete queue/key/remap/latch images, accumulated synchronization observations, caps/exit state, accumulated provider observations and device/table images. The actual recovered consumers and translator execute together; device acquisition and lock imports remain explicit bridges. MSVC and Zig match all four original traces.

## Verified checkpoint

All 88 implemented cells (44,418 routine cases) and 44 connected traces pass the aggregate comparison: fresh hash-checked original execution under MSVC, retained original observations under Zig. Native CTest passes 169 MSVC tests and 171 Zig tests. Python unittest discovery passes 989 tests with seven skips; the 15 targeted corpus/layout checks pass again after metadata refresh. Inventories now record 152 explicitly reviewed main-executable entries. These counts do not establish whole-game completion.

The later acquisition batch now connects the actual state accessor and poll/read wrappers to these queue traces; see `device-acquisition-progress.md`. Device-information enumeration and platform interfaces, process cleanup and live keyboard behavior remain unfinished.

The mapped lookup-window tail overlaps callback identity `0x8c8924` at offset `0x1dc`. Runtime setter/translation comparisons and a shared callback-word binding are documented in `device-session-progress.md`.
