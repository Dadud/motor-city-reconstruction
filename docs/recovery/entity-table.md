# Entity fields and clamped mask helpers

This W0 batch translates eight complete original bodies on bounded host inputs.
All addresses refer to `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Private exported pseudocode supplied the drafts; disassembly of the exact image
established cdecl stack arguments, signed division, byte versus dword reads,
and the x87 instructions in the word setter. Expected corpus outputs come from
executing those bodies with synthetic state, not from the translations.

| Original | Native cell | Observed operation | Cases |
| --- | --- | --- | ---: |
| `0x4030e0` | `entity_side_flag` | Select bit `0x10`/`0x20`; null table returns zero | 100 |
| `0x403120` | `entity_word_assign` | Set the selected float word at a signed wrapped index | 244 |
| `0x403160` | `entity_byte_assign` | Set the selected byte at a signed wrapped index | 244 |
| `0x4031a0` | `entity_side_flag_assign` | Set/clear one selected bit, preserving the rest of the flag word | 244 |
| `0x403220` | `cyclic_index_difference` | Wrapped subtraction and optional single half-ring adjustment | 1,344 |
| `0x403320` | `indexed_masked_bit` | Read a record mask and apply the clamped reversed bit | 165 |
| `0x403370` | `clamped_bit_mask` | Increment, clamp to 0..15, select bit 15..0 | 11 |
| `0x403470` | `entity_mode_flag` | Select bit 2/4 using a byte argument; null table returns zero | 100 |

These add 2,452 comparisons to the previous 632. The aggregate corpus now has
3,084 cases across 42 implemented cells. Run the commands in
[cell comparisons](cell-comparisons.md) to replay the observations or capture
fresh ones from the original.

## Shared memory contracts

The entity pointer global is `0x8e3ab8`; the wrapped writers use the signed count
at `0x988e38`. The host takes an explicit span and count instead of dereferencing
process addresses. `layouts.json` names the 28-byte record's two float words,
two byte fields and 16-bit flags, and the separate 84-byte mask record's word.
Names describe accesses; ownership, lifetimes and units remain unresolved.

Packed fields now declare their actual width in the registry. An omitted width
still means four bytes, preserving older entries. The renderer and validator
accept the final two-byte flag field without allowing a four-byte field to
overrun the same record. The common `detail/entity_table.hpp` computes checked
offsets; the earlier `entity_flag` and `entity_flag3` readers now use it too.
At this batch's checkpoint, the registry reported 83 offsets, 19 audited consumers and
zero shared unregistered offsets in that scope.

## Behavioral boundaries

- The null guard runs before division and before float validation. A null table
  returns without mutation even with zero count, negative index or a NaN value.
  Nonnull wrapped writes require a positive count fitting the supplied span
  and a nonnegative signed remainder. Negative indices divisible by the count
  are included; negative remainders would access before the span and are rejected.
- The side selector uses a complete dword. The mode selector and the flag
  enable argument read only a byte: `0x100` is false for those byte tests.
  The corpus includes these distinctions and both null branches.
- The word setter executes `FLD`/`FSTP` in the original. Zero, signed zero,
  finite normal/subnormal values and infinities match in memory. NaN payload
  transformations and floating-point exception state are not established by
  Unicorn, so nonnull host NaN writes are rejected rather than claimed exact.
- Index subtraction and bit-index increment wrap at 32 bits before signed
  comparisons. `INT_MAX+1` therefore takes the negative clamp branch. The cyclic
  helper adjusts by one count only; it does not normalize arbitrary differences
  repeatedly. Its scalar corpus also exercises negative and zero count bit
  patterns without inferring that game callers normally supply them.
- Every memory case compares the supplied image, including adjacent fields and
  trailing bytes. Invalid original pointers, fault equivalence, aliased globals,
  live game integration and hardware floating-point status remain outside scope.
