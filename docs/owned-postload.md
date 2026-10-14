# Original owned-car postload sequence

`client.owned_postload` and `mco::postprocess_owned_slots` connect recovered
passes in the original loader's order. They accept already discovered/enriched
1596-byte records and a resolved type cache. They are research interfaces, not
a complete car loader or the public mod API.

## Sequence and entry flags

The tail of `0x66f2b0` performs these operations:

1. Call finalizer `0x66ea20`. Its sixth argument must be nonzero and its fifth
   argument must differ from 1 for insertion **and** induction pruning to run.
2. Set field `0x634` to 1 in every remaining record.
3. If requested, run type/attachment ordering and adopt its candidate only on
   count equality.
4. If metadata enrichment was requested, run root/parent/family linking,
   dependencies, descriptions, component counts, and repair/scrap aggregation,
   in that order.
5. Sum total price into the first record regardless of enrichment.

`finalize_mode` corresponds to the finalizer's fifth argument. `display_mode`
corresponds to separate global state at `0xb18014`; it affects inserted display
names and must not be confused with the finalizer skip flag.

For example, disabling finalization retains induction placeholders that would
otherwise be pruned. Disabling enrichment skips linking, descriptions, counts
and repair/scrap aggregation, but still initializes `0x634`, optionally orders
the records and computes total price. Enabling enrichment can clear `0x634`
again through the dependency pass before descriptions observe the records.

## Explicit incomplete stage

The [outer description routine](calculations/owned-component-descriptions.md)
now has recovered template copying and assembly lists. Complete description
routine `0x6628d0` remains partial because it delegates branded
nonassembly parts to `0x668710`, including a table of part-specific callbacks and
wear-limit behavior; assembly descriptions also depend on attachment text and
localized resources. The new orchestration does not silently substitute an
identity function. Enriched processing requires an explicit description callback
and rejects missing callbacks or output with a different record count.

This boundary permits controlled comparisons of the surrounding sequence. It
does not establish original descriptions, native garage loading, mechanical
simulation inputs, live transactions, or a working owned modified car. The
callback remains internal research infrastructure; mods will use typed public
interfaces rather than these records or offsets.

Input records remain immutable. The interface requires 1..10,000 records and
rejects finalization that removes all records because it has no backing root
for the subsequent loader operations. Cache/index/cycle validation and rejection
of unsupported dependency lookups are authored safeguards. An enriched abstract-zero
record is explicitly unsupported pending recovery of its dependency lookup.

## Verification

```text
python -m tools.owned_postload_oracle /path/to/original/mcity.exe
python -m tools.native_owned_postload_compare /path/to/mco_owned_postload_compare
```

The 96-case corpus matches original instructions `0x66f586` through `0x66f699`,
including the real finalizer, induction pruning, ordering, linking, count,
repair/scrap and price helpers. It varies finalization flags/modes, display mode,
ordering and enrichment and compares every output record byte and count.
Allocation/free, two bounded `sprintf` formats, and the **entire description
routine** are substituted; the latter writes an explicitly authored fixture.
The exception chain is isolated inside the emulator. Preallocated capacity
excludes growth and allocation failure. Earlier database discovery/enrichment
and subsequent buffer-manager handoff are not executed.

The same 96 fixtures match Python/C++ byte-for-byte. Local Windows validation
passes 414 Python tests and twelve native suites; CI runs asset-free comparisons
on Windows/Linux. These results prove the stated sequence with the supplied
boundary, not complete original-client behavior.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Local REA evidence for the loader:
`ev_07c134590f4352ac597bcadd8a4f36aa12dd194b450c4aa3ba9f518f3a283a41`.
Description research:
`ev_7cf1013c317d06cf8417983d5c00118e459ca555866d3269580d5eb81c03115d`
and `ev_93e758d7494ef08c8d2b10484d2739f96da64cff55cb7db9fa6e125a3e470488`.
