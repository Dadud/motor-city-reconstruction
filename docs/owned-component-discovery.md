# Original owned-component discovery

Original `0x66f2b0` builds provisional owned-part slots starting from a supplied
root instance ID. This differs from StockAssembly: it queries actual Part rows
whose ParentPartID matches the current instance. `client.owned_tree` recovers
this discovery stage without replacing modified parts with stock defaults.

Saved query `Part_SelectAllChildren` inner-joins Part to BrandedPart and PartType.
Its predicate is `PART.ParentPartID=[curPart]`. Selected columns are PartID,
AbstractPartTypeID, PartFilename, AttachmentPointID, BrandedPartID and PartTypeID.
The native discovery routine binds only the first four; complete branded and
instance enrichment occurs afterward.

The initial slot is zeroed except for root PartID at `0x5f8`. Each accepted
child adds another zeroed 1596-byte slot, with these fields:

| Offset | Child query value |
| --- | --- |
| `0` | AbstractPartTypeID |
| `0x387` | PartFilename including terminator |
| `0x5f8` | PartID |
| `0x61c` | AttachmentPointID |

Discovery walks the growing slot list in breadth-first order. The root is
always queried. A later slot is expanded only if its abstract type is in the
original `0x64c260` membership list: 101, 1001, 2001, 3001, 36001, 210001,
37001, 4001, 38001, 15001, 5001 or 6001. It is incorrect to recursively query
every component type. The list also serves other native consumers; no broader
semantic classification is assumed here.

`discover_owned_tree(root_id, instance_cache, catalogue, text_encoding=...)`
returns provisional slots and the exact queried-parent sequence. Cache rows
preserve the supplied order; the SQL has no ORDER BY, so this does not claim
identical Jet row ordering for every database. Missing branded/type references
are excluded by the recovered inner-join semantics. NULL parents do not match
nonzero parent IDs. No original database is changed.

The native routine starts with capacity 100 and grows its allocation. The
authored routine instead uses dynamic storage with a caller-set maximum
(default 10,000), detects repeated IDs/cycles, validates int32 query values,
and requires a terminator within the original nine-byte filename buffer.
These are authored safeguards, not native limits or native malformed-data rules.

`python -m tools.owned_tree_seed_oracle /path/to/original/mcity.exe` compares
two discovered-child slots against the original stores/copy instructions at
`0x66f4d1`–`0x66f530`, including a NULL filename and attachment. Every byte of
the 1596-byte slot matches. Query values are supplied; SQL, traversal,
allocation and finalization are excluded from that bounded CPU check. Tests
separately cover breadth-first expansion, the assembly gate, missing references,
NULL parents, cycles and configured size limits.

The original continues through instance/physics loading, `0x66ea20` component
finalization, optional reorder, aggregation, link/index assignment and other
passes. Those stages are not represented by this discovery API. In particular,
these slots are not complete rendered cars, and the component rows still need
their original online refresh path. Live authenticated gameplay remains unverified.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence: `ev_885eac3305bd8573866d4d513bd2a017c8bd322d8db51b661aec84c7a0ec1390`
(discovery routine) and `ev_daaafcf0c4ca3d7f9f5d3bac76548075761b45359f43fedfad1b450ffff48ce4`
(query references). The saved-query selection/predicate was read directly from
the external database with `tools.query_fields`.
