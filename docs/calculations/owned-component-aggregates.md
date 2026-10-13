# Original owned-component aggregates

The original owned assembly pipeline performs separate count, repair/scrap and
total-price passes. These operate on 1596-byte slots; they do not load a complete
vehicle, calculate its forces, or submit an economy transaction.

## Component counts

Procedure `0x661370` starts with one for the current slot only when BrandedPartID
at `0x1e3` is nonzero and the signed field at `0x0c` equals zero. The type-template
encoder supplies a special-type indicator at `0x0c`; this algorithm still tests the
stored value directly rather than recomputing type membership. It recursively includes eligible branded children
whose parent index at `0x600` points to the current slot. The original caller stores
the returned count at `0x638` for each slot. A slot is excluded from its own child
scan even when its parent field equals its own index. Preserve the selection rule
rather than equating this value with the number of all discovered records.

## Repair and scrap aggregation

Outer pass `0x661d60` processes slots whose ParentPartID at `0x60c` is zero and whose
abstract type belongs to the original twelve-type list: 101, 1001, 2001, 3001,
36001, 210001, 37001, 4001, 38001, 15001, 5001 and 6001.

Helper `0x661cd0` finds children by owned parent index `0x600`. Special-type
children are recursively aggregated before their repair field `0x62c` and scrap
field `0x630` are added to the parent's **existing** values. Other children also
contribute their values. Addition wraps modulo 2^32; it is not saturation.

This pass mutates totals in traversal order. It does not first clear assembly totals,
and it is not an idempotent reduction: repeated visits can add already accumulated
values again. Replacing it with a fresh sum of leaf values would change original
behavior. Caller preparation and slot order therefore remain part of the contract.

For example, take ordered slots vehicle 101 → chassis 1001 → ordinary part 55,
with initial repair values 10, 20 and 30, and all ParentPartID values zero.
Processing the vehicle first updates the chassis to 50 and the vehicle to 60.
The later outer chassis visit adds the part's 30 again, leaving final values
60, 80 and 30. If the chassis ParentPartID is nonzero, its outer visit is skipped
and the final values are 60, 50 and 30. Scrap follows the same rule independently.
At each addition, `new_value = (existing_value + child_value) mod 2^32`.

## Total price

Procedure `0x6621f0` adds every slot's unsigned price field at `0x1eb`, wrapping
modulo 2^32. It converts the unsigned sum to double, passes it through the original
rounding helper, and stores the low 32 bits of the original floating-to-integer
conversion into slot zero's `0x1eb`.

A second invocation includes slot zero's previously stored total in the new sum.
Do not treat the first record as excluded or automatically clear it. With zero
count the original writes zero when given a valid backing buffer; the authored
empty-tuple interface returns an empty tuple because it has no destination record.

Prices 10, 20 and 30 produce 60 in slot zero, preserving 20 and 30 in the other
slots. Repeating the pass produces 110. Prices with bit patterns `0xffffffff`
and `0x00000002` produce `0x00000001` after wrapping. These are integer price
fields; the recovered pass introduces no additional currency-unit conversion.

## Verification boundary

```text
python -m tools.owned_aggregates_oracle /path/to/original/mcity.exe
```

The oracle passed 97 deterministic cases for each of the count, repair/scrap and
price passes, using the complete original functions and real helpers without hooks.
It compares every byte of the 1596-byte output records and exercises unsigned wrap,
existing totals and arbitrary unmatched parent values. The empty count case skips
`0x661370`, as its caller does; empty repair/scrap and price cases execute with a
valid dummy buffer. Database loading, full assembly orchestration and live
transactions are outside that scope.

The authored implementation limits input to 10,000 records and rejects recursive
cycles that would prevent termination. These are portable safeguards. Out-of-range
owned parent values remain harmless unmatched comparisons in these passes.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Local REA evidence:

- Count: `ev_ab2789c600f94a53b746c84fd0702f2d01616e5a959d6c223a6923d096f24e2c`.
- Outer repair/scrap: `ev_b82befc13ecd9e2e261ea6c0689fc478f39c52818a8956bfb7ba2126aca3e3eb`.
- Recursive repair/scrap: `ev_8420f80ce37bad2f5c40dea080acd0ccee033c169401feafc5b0b261e57d9dd0`.
- Total price: `ev_9ea43a5f62b24fe3e436e30759781fc2959f27054a30b542be143d52edbfbdf8`.
