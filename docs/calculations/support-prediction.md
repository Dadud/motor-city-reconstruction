# Complete support predictor consumer

`client.support_prediction.predict_support` reconstructs the complete owner
arithmetic and four ordered terrain projections in original `0x53d320`.
`mco::predict_support` in `native/src/support_prediction.cpp` now carries the
same bounded calculation in the native library. The native/Python comparison
checks all 722 support cases byte-for-byte for owner state and exactly for the
four ordered query contexts, transformed points, and previous world points.
The original comparison below separately checks the Python model against all
722 original calls with terrain projection supplied. A second original-binary
check runs the bounded terrain service through `0x53d320` and compares complete
owner memory across 722 synthetic four-wheel track cases.

Retained evidence:
`ev_f04dec3c392ad24344e59e34d5c69e17e64ee1532b5945b4ef2c74bb0683da4b`
(`0x53d320`) and
`ev_f4bc15ed3c6ec25b3a4b48e92ed376a9c4e2a29c406d633cf278f64cdf14f79b`
(`0x42e010`). Bounded execution uses verified `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Private original instruction inspection additionally establishes the scalar
matrix helper's precision switch and query-record position alias.

## Producer map

Each wheel record starts at owner `+0x5fc + slot * 0x10c`. Slots are the original
consecutive records, preserving the original rear-wheel ordering.

| Source/output | Owner or wheel field |
| --- | --- |
| Body position | owner `+8`, `+0xc`, `+0x10` |
| Body velocity | owner `+0x14`, `+0x18`, `+0x1c` |
| Prepared world transform | owner `+0xc10`, nine floats |
| Four local support points | wheel `+0x100`, `+0x104`, `+0x108` |
| Terrain context | owner `+0x370` |
| Fallback surface class | owner `+0x404` |
| Terrain projection record | wheel `+0x14`, eight words |
| Surface descriptor reference | wheel `+0x20`, projection-record word 3 |
| World support point / terrain-query alias | wheel `+0x34`, `+0x38`, `+0x3c` |
| Retained query coefficients | wheel `+0x40` through `+0x57`, 24 bytes |
| Contact reference | wheel `+0xb8` |
| Support difference | wheel `+0xe8` |
| Contact byte | wheel `+0xec` |
| Surface class | wheel `+0x58` |
| Total contacting records | owner `+0xc08` |

The predictor does not write normal load or suspension force. These support
outputs feed later consumers. A valid surface descriptor is independent of
the contact byte: contact is decided by the numeric comparison below.

## Lookahead and transform

First compute three stored float32 coordinates:

`lookahead = float32(position + velocity * float32(1 / 48))`.

Then transform each local point as a row vector with the supplied prepared
matrix, adding lookahead translation. The shipped scalar dispatcher
`0x6f1320` → `0x6f28f0` → `0x83a290` → `0x83a540` changes x87 precision to
24 significant bits and restores its previous control word afterward. Its
individual products and sums therefore round to float32 precision, unlike
other original helpers which retain wider products until a store:

`world[i] = float32(float32(float32(float32(x*m[i]) + float32(y*m[3+i]))`
`                         + float32(z*m[6+i])) + lookahead[i])`.

The Python implementation explicitly rounds those boundaries. The oracle
executes the actual original dispatch, including its temporary precision
change. Alternative CPU-specific vector dispatch implementations are not
verified by this corpus. The constant does not establish the scheduler rate.

## Projection and the aliased reference point

For each slot, original `0x53d320` passes its terrain record, the transformed
point and context to `0x42e010`. The query initializes the first eight record
words, obtains a terrain selection from `0x42e760`, and on success uses
`0x42dc50` and `0x4b71a0` to replace the input point's Y with road height.

An important alias is part of the contract: projection-record `+0x20` is the
same memory as wheel `+0x34`, the world-point triple. Normal hit and miss paths
in `0x42e760` write the incoming query point to this tail before optional
height projection. Consequently the subsequent subtraction usually means
road height minus incoming wheel height, rather than road height minus the
previous tick's road height. Reading retained pseudocode without following
the query's writes loses this distinction.

The typed boundary receives the slot, transformed point and context together
with the incoming wheel record, prior world point and retained 24-byte query
tail. It returns `SupportProjection(point, reference_position, record,
query_tail)`; the tail models writes through query-record `+0x2c..+0x43` that
alias wheel `+0x40..+0x57`. The predictor preserves the returned record,
reference point and aliased tail. The composition matches 722 complete original
`0x53d320` owner images when driven through the bounded triangle-mode terrain
query. The row-mode stack normal remains an explicit input because its producer
has not yet been recovered.

`SupportRecord` carries sector/group/status observations, a nullable stable
surface identity, four nullable vertex identities and the observed descriptor
byte. Public identities are not executable pointers. The original surface
service and private oracle marshal identities into their own native records.

## Contact and surface classification

After projection, for every record:

1. Store `difference = float32(projected_y - returned_reference_y)`.
2. Store the projected world-point triple.
3. Set contact when `difference >= -contact_reference`, including equality.
4. Count contacting records from zero for this call.
5. With a non-null surface descriptor, class is `descriptor_byte & 31`.
   Otherwise use the supplied owner fallback surface class.

For example, a reference Y of zero, projected Y of `-0.5` and contact reference
`0.5` produce contact. A slightly smaller projected height does not. A missing
descriptor does not automatically force contact false: if a supplied miss
leaves projected and reference Y equal, difference is zero and contact is true
for a nonnegative contact reference. This preserves the observed consumer,
rather than adding a terrain-found guard the original predictor does not have.

## Verification and remaining work

`tools.support_prediction_oracle` checks 722 complete original predictor calls.
The original transform dispatcher executes; the projection boundary supplies
authored observations. Comparisons check exact ordered points/context/record
targets, reference-position handoffs and the complete resulting owner image.
All sixteen surface-hit masks, five heights around contact thresholds, signed
velocity, identity/yaw/banked matrices, negative contexts, descriptor high bits,
large coordinates and changed reference-position writes are covered.
Maximum absolute error is zero.

Nine Python behavioral tests separately verify inclusive contact, the position
alias, missing-surface classification, descriptor masking, ordered lookahead,
repeated state, required boundaries and matrix precision. The matrix precision
regression returns Y `-0.07811832427978516`; postponing rounding until the final
store incorrectly gives `-0.07811833173036575` for the same inputs.

The original terrain selection/projection service is not recovered by these
722 tests. Existing `track_surface` and `contact` helpers are not silently
installed as the service: reference-height selection and edge tolerances there
include authored behavior and require independent original-asset comparison.
Special lookup/recovery branches, authentic context/local-point production,
CPU-specific transform equivalence and native port remain open. This module is
a verified integration dependency, not full terrain/collision equivalence.
