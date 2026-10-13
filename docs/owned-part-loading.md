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
explicit instance rows; a zero ID remains an empty slot. The second word supplies
the branded ID during the cache update described below. Duplicate or absent instance
rows are rejected. No stock catalogue fallback can invent missing damage,
wear, parent or ownership state.

The supplied base `Data/DB/Online.mdb` has zero rows in `Part`, while its query
and schema are present. This was inspected read-only; no database was opened
through COM or changed. Thus the base catalogue can supply branded metadata,
but does not itself provide the live owned-instance cache. The cache-update
path is now reconstructed in memory; complete enrichment remains unfinished.

`Catalogue.owned_part_metadata` now reproduces the `BrandPart_SelectE` join
from the instance's actual `BrandedPartID` through `PartType` and `Model`.
It does not replace an owned instance with a `StockAssembly` vehicle. The
saved selection order identifies part type, part-type text, brand, model,
abstract type, extra information, filename, retail price, maximum wear,
manufacturing date, short model, grade, engine family and a final literal zero.
Nullable integer results follow the native zero conversion.

`OwnedPartMetadata.apply_numeric_fields` applies the first confirmed numeric
stores while preserving the instance seed:

| Field | Slot offset |
| --- | --- |
| AbstractPartTypeID | +0 |
| PartTypeID | +0x1e7 |
| RetailPrice | +0x1eb |
| MaxItemWear | +0x1ef |
| Manufacturing year | +0x1fb |
| PartGradeID | +0x1ff |
| EngineBlockFamilyID | +0x203 |

Metadata text is returned separately without guessing its original narrow-byte
encoding. These stores precede other metadata helpers, text copying,
`Physics_Select`, cache-backed enrichment and subsequent price adjustments.
They are an intermediate object stage, not the final playable car record.

`python -m tools.owned_metadata_oracle /path/to/original/mcity.exe` executes
the original numeric stores at `0x669346`–`0x669374` with controlled query
values. Three engine-family cases match all 1596 bytes, including preserving
owned-instance damage and wear. No metadata query, text helper, physics or
later value computation executes. A separate read-only check joined all 212
stock-body catalogue rows in the installed database and formed their numeric
metadata slots. That validates real table references, not live garage state.

`OwnedInstanceCache.apply_persona_car_pairs` reproduces the car-list update:
each nonzero first word selects `PartID`, the second supplies `BrandedPartID`,
and the selected persona supplies `OwnerID`. Parent is SQL NULL; attachment,
damage, wear, repair cost and scrap value are explicitly zero. Existing fields
outside those assignments, such as `PartName`, are retained. Repeated instance
IDs update in order, so the final pair wins. Zero IDs are ignored by the native
update routine and its caller continues.

Saved query `Part_UpdatePartNew` updates by `PartID`. If its execution fails
or affects zero rows, original `0x6725d0` falls back to `Part_InsertNew` with
the same data and a different parameter order. `0x680190` binds NULL for a
zero parent. Integer reader `0x67f080` writes zero for a present NULL/empty
variant; accordingly, `OwnedPart.from_row` converts present null values to
zero when forming a native slot. Missing columns remain errors. This does
not imply that every instance's real damage is zero: it reproduces this
specific initial car-list cache update before later population.

`fetch_persona_startup` now applies the list to an authored cache and returns
the corresponding initial part slots alongside the merged profile. Callers
can provide an existing `instance_cache`; cache changes occur immediately
after the car-list reply and remain if a later profile step fails, as in the
original sequence. Brand/physics enrichment is still required before these
slots can represent complete playable cars. All changes are in memory.

`python -m tools.owned_part_update_oracle /path/to/original/mcity.exe` executes
the original binding and fallback logic with query boundaries substituted.
Four cases confirm existing-row update, zero-row insert fallback, failed-query
insert fallback, and rejection of a zero ID. It verifies the exact parameter
maps and NULL parent binding; it does not execute SQL or modify a database.

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

Additional evidence: `ev_fdfb5c0da53c5d462fe14bbc44d485c8973d188a5c23a3b39081d3c3a43cc967`
(query names), `ev_7f0f24842329efb01a59e535640ba6389a8e2ea116a82f04988d36315beebef0`
(update/insert bindings), `ev_6e74cd2ef153184a2d25f6d152664e19241c451d2d55082cf10d3aac1aaaf72b`
(NULL binding), and `ev_cb3e03b3169f51828fea7566b7df1b3056b1f5c85b9ed541284dcf9a887628ac`
(integer NULL reading).
