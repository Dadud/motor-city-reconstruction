# Record stack and ordered copies

Ten W0 routines are translated and compared against the exact original
`mcity.exe` identified by SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Decompiler drafts were checked against original instructions before translation;
the shared original-execution oracle supplies expected outputs from synthetic
memory and arguments. MSVC and Zig/Clang agree with all 771 new cases.

| Original | Cell | Observed operation | Cases |
| --- | --- | --- | ---: |
| `0x435f80` | `record_cursor_pop` | Subtract a record stride and clamp with an unsigned comparison | 64 |
| `0x435fb0` | `record_stack_contains` | Search identifiers through the current record, always checking the base | 200 |
| `0x436270` | `record_identifier` | Read the current record's identifier | 16 |
| `0x436280` | `record_related_value` | Read a second opaque current-record value | 16 |
| `0x436c40` | `record_state_copy48` | Copy twelve state words with the original staging and MOVSD order | 39 |
| `0x437ac0` | `record_signed_negate` | Negate one record word with 32-bit wrap | 16 |
| `0x437ae0` | `record_flag_toggle` | Toggle flag `0x100`, preserving other bits | 16 |
| `0x43f960` | `copy_words24` | Copy six words with the final pair staged before stores | 39 |
| `0x43ad80` | `copy_prefix2` | Stage byte one, copy two bytes, append zero | 27 |
| `0x433e70` | `copy_line_segment` | Copy through an inclusive limit or newline, then skip a source byte | 338 |

This brings the [aggregate comparison corpus](cell-comparisons.md) to 3,855
cases across 52 implemented cells. Expected observations for the earlier
42 cells are unchanged.

## Address and layout boundaries

The current-record global is `0x98c0f8`; the base-record global is `0x98badc`.
The host receives byte spans and explicit 32-bit address identities. It never
dereferences an original process address. The registry's `state_record` describes
the observed `0x100` stride and the identifier, exported-state start, flags,
related value and negated word. Ownership and class/lifetime contracts remain
unknown. `detail/byte_words.hpp` reads and writes little-endian words without
host alignment assumptions or pointer casts.

The pop helper uses `JAE`, so its comparison is unsigned. For example, cursor
`1` with base `0` becomes `0xffffff01`; it does not clamp to zero. The scalar
corpus includes both sign-bit boundaries and underflow. The scan helper always
reads the base identifier before considering its cursor, even for a null cursor.
Cases cover absent targets, a unique target in the final active record,
duplicates, and nonaligned cursor positions. Scans crossing 32-bit address wrap
or unreadable supplied bytes are rejected; original fault behavior is not claimed.

## Overlap is part of these copy contracts

The 24-byte helper is thiscall with `ret 4` and leaves the destination address
in EAX. The host returns the destination span, whose identity is compared as
well as memory. It copies four words sequentially,
then loads the last two words before storing either. The 48-byte helper is
cdecl; its first argument is unused and its second is the destination. It stores
the first word, stages the next pair, then executes nine forward `MOVSD` copies.
The original's caller must have the direction flag clear. The native port
preserves these sequences instead of substituting `memcpy` or `memmove`.

The two-byte helper stages source byte one before writing destination byte zero.
The corpus uses self-copy, unaligned overlap in both directions, aligned overlap,
and disjoint spans, comparing the entire backing image each time. The comparison
transport checks span offsets before constructing views, so malformed corpus
input cannot create an out-of-bounds C++ span.

## Text helper limits

The limit is inclusive: limit zero still copies one byte unless the source
already points to newline. Embedded NUL bytes are copied; carriage return is
ordinary data. Negative limits write only a destination terminator. The original
returns one byte beyond the source position it reached, including a limit stop
or a negative limit; the host returns that numeric offset instead of constructing
an out-of-range pointer. For source `AB` and limit zero, the output is `A\0`
and the next-source offset is `2`.
The original loop increments a 32-bit counter and uses signed `JLE`; with
`INT_MAX` as the limit, counter wrap cannot terminate it. The host retains that
open-ended limit and requires a newline before exhausting the supplied spans.
The extreme-limit corpus cases use early newlines; multi-gigabyte traversal is
not established by those cases.
The retained `line_counter_wrap` probe separately enters just the original loop
with its counter preloaded at `INT_MAX`: it copies `AB` across the signed wrap
and stops at newline. This is explicit subregion evidence, excluded from the
3,855 complete-function case count, and regenerates with the same oracle command.

The corpus covers immediate and later newlines, embedded NUL/CR, no newline,
negative and extreme signed limits, and overlapping spans. Invalid original
pointers, faults and aliased original globals remain outside scope. Bounded
helper equivalence does not establish an integrated record owner or game flow.
