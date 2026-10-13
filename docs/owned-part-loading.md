# Original owned-part loading

The persona's 0xad response is a compact list of eight-byte pairs, not a list
of complete stock cars. Handler `0x655520` uses the first value as an owned
instance ID, updates the local cache for each pair, allocates zeroed 1596-byte
slots, stores instance IDs at +0x5f8 and invokes `0x66f7d0` to populate them.
This distinction matters for modifications, damage and ownership: two instances
can share a branded part while retaining different instance state.

`0x66f7d0` binds query `Part_SelectENew` by instance ID. The saved query in
the external `Online.mdb` establishes its selection order and predicate
`Part.PartID = partId`. The seven columns are:

| Column | Database field | Local slot offset |
| --- | --- | --- |
| 0 | PartID | +0x5f8, already seeded from the response |
| 1 | BrandedPartID | +0x1e3 |
| 2 | PercentDamage | +0x610 |
| 3 | ItemWear | +0x614 |
| 4 | ParentPartID | +0x60c |
| 5 | RepairCost | +0x62c |
| 6 | ScrapValue | +0x630 |

The field bindings are integer reads. After a successful row read, a -1
indicator for its part-ID column returns native status 0x14. A populated
row is followed by branded metadata and physics enrichment through `0x6690a0`,
which uses saved queries `BrandPart_SelectE` and `Physics_Select`. The later
pass performs additional condition and value calculations. The entire slot
is a local object, not a wire payload.

`client.owned_parts.OwnedPart` represents the seven confirmed instance fields.
`native_seed` produces the zeroed initial slot plus these fields, before
enrichment. `OwnedPartCache.seed_car_pairs` resolves the first word against
explicit instance rows; a zero ID remains an empty slot. The second word's
original cache-update behavior remains separate. Duplicate or absent instance
rows are rejected. No stock catalogue fallback can invent missing damage,
wear, parent or ownership state.

The supplied base `Data/DB/Online.mdb` has zero rows in `Part`, while its query
and schema are present. This was inspected read-only; no database was opened
through COM or changed. Thus the base catalogue can supply branded metadata,
but does not itself provide the live owned-instance cache. The cache-update
path and complete enrichment still need reconstruction.

`python -m tools.owned_part_seed_oracle /path/to/original/mcity.exe` executes
the six original stores at `0x66f8eb`–`0x66f912` with controlled query values.
Three cases match all 1596 output bytes, including signed edge values and
unaligned stores. Query execution, cache mutation, enrichment and subsequent
calculations do not execute in that bounded check. Tests also verify distinct
damage values for two instances of the same brand, response ordering, zero-ID
slots, and rejection of missing or duplicate instance data.

Evidence: `ev_91fedcba62903d34e42733c19159b0260c79635b48f80029b667b35b0ac69786`
(population), `ev_db8b2c092fdf32844cbff5ae788769d0e332775a4217233b166af6c353195d65`
(metadata enrichment), and `ev_1f726b43f538dfe05b86469b15a418d98e2938808021d0007bfbc72ae80d3146`
(saved-query preparation). Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
External database SHA-256:
`bdd86d8e781f127ac7dee5a5dab38945d0f9f03db354248e3cf50bbf9a13e021`.
The database and raw native evidence remain external to the published repository.
