# Original owned-component root and parent links

`client.owned_parent_links` reconstructs original root selection `0x661a40`
and parent/family pass `0x661ed0`. These are isolated passes over complete
1596-byte slots and an already resolved type cache, not a complete vehicle loader.
The cache must include its abstract-zero sentinel at index zero. Type-cache parent
indexes and owned-slot parent indexes share offset `0x600` but reference different
arrays; callers must not confuse them.

## Root selection

`select_owned_root(slots, templates)` returns reordered whole records and original
status 1 or 3. Zero/invalid inputs are rejected by authored validation. A single
valid slot returns status 1 unchanged, even when its abstract type is absent from
the cache.

For multiple slots, the original examines each slot in order. A missing template
returns status 3 without swapping records. The first type whose resolved parent
has abstract ID zero is swapped with slot zero. The swap moves every byte of both
1596-byte records, including existing indexes; it does not repair those indexes.

If no such top-level type is found, the fallback selects the first chassis type
1001. Otherwise it selects the first candidate with the smallest ancestor-walk
distance toward abstract 1001. The initial minimum is 255 and comparison is strict
less-than: equal distances retain the first candidate, and distances of 255 or
greater do not replace the initial slot-zero choice. The helper counts steps until
1001, zero, or a missing ancestor lookup; reaching zero does not prove that the
candidate descends from chassis 1001. Duplicate cache types use the first match.

## Parent linking

`link_owned_parents(slots, templates)` invokes root selection first. Like the native
caller, it ignores that selection's status and continues linking.

Each candidate parent is compared with every child. The child's resolved type-cache
parent must be nonzero and have the candidate parent's abstract type. A candidate
parent attachment at `0x61c` of zero is a wildcard; otherwise it must equal the
child's attachment. Each match writes the candidate's owned-slot index at the
child's `0x600`. Traversal continues after a match, so the **last matching parent
wins**. A child with no match retains its existing parent index. An abstract-zero
child or missing type lookup uses parent-template index zero and does not match.

## Engine block family propagation

The pass remembers the last slot of abstract type 36001 and the last slot of type
160001 with nonzero BrandedPartID at `0x1e3`. If both exist, it copies the latter's
EngineBlockFamilyID at `0x203` into the selected 36001 slot.

Without a branded 160001 source, it clears the selected target's family, then scans
all slots. A slot supplies its family only when its owned parent index points to
that target, its family is nonzero, and its type-cache BlockFamilyCompatibility at
`0x14` is nonzero. Again the last eligible child wins. No 36001 target means no
family changes. These field names come from catalogue metadata, not guessed
physical interpretations of the abstract IDs.

## Validation and verification

Both APIs return immutable records without modifying their inputs. They require
1596-byte records, valid parent indexes and the index-zero sentinel. Type-parent
cycles are rejected. These checks are authored safeguards: the original ancestor
walk has no cycle limit, and malformed cache/index behavior is not reproduced.

Run the portable cases with:

```text
python -m unittest tests.test_owned_parent_links
```

Run the optional original-instruction comparison with an external executable:

```text
python -m tools.owned_parent_links_oracle /path/to/original/mcity.exe
```

The oracle compares 96 root-selection cases and 96 parent/family cases, including
every output byte and returned status. It executes the full original functions,
initializer `0x661180` and lookup/walk helpers `0x64c830`, `0x64c8a0`, `0x64c7b0`
and `0x64c1d0`, with deterministic synthetic acyclic caches. It does not initialize
the cache from the database, run preceding component finalization/reordering, or
verify downstream aggregation and dependency assignment. Unit cases additionally
cover the strict 255 distance cutoff, first/last match rules and malformed input.

This work is not yet integrated into owned startup as a complete car. Original
component finalization, other reorder passes, dependencies, aggregation and online
refresh still require integration and acceptance evidence. The isolated dependency
pass is already recovered; see [dependency linking](owned-component-dependencies.md).

The C++ port matches the Python outputs for the same 96 root and 96 parent/family
cases, including every record byte and root return status. These asset-free checks
also run in native Windows/Linux CI:

```text
python -m tools.native_owned_parent_links_compare build/native/mco_owned_parent_links_compare
```

The preceding type-cache resolver is documented in [type cache](part-type-cache.md).

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Local REA evidence IDs:

- Root: `ev_87d3ea1c6bdb73e1eb85b82b8d7ddd24959b2cc865fe1f66ccb286c3e436f3b1`.
- Parent/family: `ev_001a7185566f881b9fc6413d6483aa68e702e3e140a9000b098dbe497fe5a33c`.
- Root helper: `ev_6587e4afc1c40973f153c55d8bb2a573eb52951d73f9fb5fc3d228f8763b3e00`.
- Distance helper: `ev_027f5e0c2b8dd90acf3b442b69bbb55a079d4265272f64974fb0c1adbb1352b4`.
