# Model preparation dependencies

This package translates original local-space part half-extents (`0x4c4050`),
three-stream part scaling (`0x4c42d0`), and secondary-model alignment after
selection of its reference node (`0x52bc60`). Addresses apply only to main
executable SHA256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

The implementation uses complete FCE byte images. The existing decoded model
does not preserve dummy positions and every stream mutated by the original.
The image is caller-owned; these functions allocate no original objects, acquire
no model ownership, and infer no reference counting or destruction policy.
Finite vectors, bounded tables, terminated names and valid selected parts define
the supported input domain. Malformed images raise errors rather than emulate
the original out-of-bounds memory behavior.

## Observed shared layouts

| Object | Offset | Meaning used by this call chain |
|---|---|---|
| Assembly owner | `0x19c` | Head of component/model linked list |
| Assembly owner | `0x214` | Secondary model pointer |
| Assembly owner | `0x21c` | Head of selected render-part linked list |
| Assembly owner | `0x22c` | Flags; bit `0x40` suppresses later type16/17/18 lift |
| List node | `0x00` / `0x04` | Next node / model pointer |
| List node | `0x0c` | Signed 16-bit part index |
| List node | `0x10` | Flags; bit `0x40` selects mirrored bounds |
| List node | `0x14` / `0x18` | Type selector / wheel-position selector |
| Component node | `0x3c` / `0x40` / `0x44` | Three float size fields used by tire preparation |
| Component node | `0x338` | Class selector |
| FCE image | `0x58` / `0x5c` | Dummy count / contiguous xyz dummy origins |
| FCE image | `0x11c` / `0x120` | Part count / contiguous xyz part origins |
| FCE image | `0x420` / `0x520` | Per-part first-vertex index / vertex count |
| FCE image | `0xe28` | Part names; 64-byte entries |
| FCE image | `0x14`, `0x34`, `0x2c` | Offsets of the three scaled vector streams, relative to `0x2038` |

The list nodes and FCE images remain separate objects. Multiple nodes can refer
to one image; future assembly adapters must preserve this aliasing rather than
copy each node's model. The containing owner does not establish ownership or
lifetimes through these functions alone.

## Complete translated primitives

`model_part_half_extents` / Python `part_half_extents` scans the selected part's
first vector stream without adding the part origin. Each result is
`float32(abs(maximum - minimum) * 0.5)`. Invalid indices and zero-vertex parts
produce no result. Other parts and all model bytes remain unchanged.

`model_scale_part_streams` / Python `scale_part_streams` multiplies selected
xyz values by the supplied axis scales in stream order `0x14`, `0x34`, `0x2c`.
Each multiplication stores float32. It does not normalize vectors, change part
origins, or update dummies. Aliased streams are visited repeatedly; three
identical stream offsets apply the scale three times. The stream semantics
beyond these observed memory operations are not assumed by this API.

`model_align_secondary` / Python `align_secondary_model` accepts the secondary
image and an already-selected reference image/part. The original wrapper first
checks owner `0x214`, then takes the first type `0x11` node in the `0x21c` list.
It requires that selected node's model pointer and signed part index be valid.
The translation receives that selection explicitly and checks its bounds.

The first secondary part whose NUL-terminated name contains case-sensitive
substring `_W` supplies the source origin. Let `R` be the reference origin and
`S` that source origin:

```
D.x = float32(R.x - S.x)
D.y = float32(R.y - S.y)
D.z = float32(R.z - S.z)
D.y = float32(D.y + 0.05000000074505806)
```

The stored vector is then added to every secondary part origin and dummy origin,
with float32 stores. Geometry streams and all other bytes remain unchanged.
The delta stores are visible in instructions `0x52bd5b..0x52bd84`; simplifying
the pseudocode into one unrounded expression would change behavior. Original
`0x52bc60` returns void; the authored adapter returns whether alignment occurred.

## Connected startup contract and remaining gates

Observed `0x52be40` order:

1. Save the selected-part list head from owner `0x21c`.
2. Run tire preparation `0x52b950` for selectors **1, 2, 4, 3**, then suspension
   preparation `0x52b7c0`.
3. Union valid nonempty selected-part bounds through real `0x4c3e50`, honoring
   each node's mirror flag.
4. Calculate negative center and half-extents, then translate every part and
   dummy origin in each model reached through owner `0x19c`.
5. Run secondary alignment `0x52bc60`.
6. Unless owner flag `0x40` is set, lift y of selected part origins with node
   types `0x10`, `0x11`, `0x12` by stored `0.05f`.
7. Publish the union half-extents.

The apparent head search in the export starts at index0 and immediately exits
after a failed check; it does not justify searching other owner head slots.

`0x52b950` chooses the first class `0x1adb1` component for its selector, derives
requested size and two correction helpers (`0x53bf20`, `0x53bf10`), finds a named
part and its half-extents, then scales all matching component models of classes
`0x1adb1`, `0x186a1`, `0x1d4c1`. The part-name substring at `0x895c98` is `:PH`.
Existing tire-size code already identifies `0x53bf20` as extra placement
allowance. Saved exports show `0x53bf10(width)` subtracts stored float
`0.23000000417232513` and returns retained precision; `0x53bf20(radius)` returns
stored float `max(float32(radius - 0.3700000047683716), 0)`. These children,
their original float-store behavior and the complete linked-list producer must
still be connected and compared before claiming this producer translated.

`0x52b7c0` selects a class `0x1adb1` wheel at position3, falling back to4, and a
class `0x3e9` component. It searches `_PHrearsusp` and `_PHtire`, uses the tire
part's absolute x origin and suspension x half-extent to scale suspension x,
then copies tire y/z origin and stores suspension x=0. Its complete producer
and part-name lookup remain integration work.

No full `0x52be40` execution, model loader, graph lifetime, attachment producer,
assembled vehicle, driving dimensions, or rendered startup is certified by
these three dependency translations.

## Reproduction

```
python -m unittest tests.test_model_preparation
python -m tools.model_preparation_oracle "<original>/mcity.exe"
python -m tools.native_model_preparation_compare "<build>/mco_model_preparation_compare.exe"
```

The original oracle executes **106 calls**: 40 half-extents, 40 scale operations,
26 secondary alignments. It checks status/output for half-extents and the entire
image, including untouched sentinels, for mutations. Inputs include empty and
invalid part indices, separate and aliased streams, case-sensitive/name-substring
selection, multiple matching parts, nonzero dummy origins, and missing-secondary
or missing-selected-node exits. The original CRT substring helper executes;
there are no replaced child functions. CPU-only bounded execution is not an
original-client runtime trace. Native comparisons use the same authored corpus
and require exact output bytes.

Retained REA dossiers: `0x4c4050`
`ev_d7d24f4e6b390a76ff3f4edfa09189c93f9309ecf9f9d0e5f743f6a368ccaf91`,
`0x4c42d0`
`ev_5e50dc0766a99b7f87c8ce67f37388aae53a3113f010bc36b5e30fc1a4bbc5aa`,
and `0x52bc60`
`ev_dbb8bb8c451d3072a60915d8a99e2c36ad0b8c8f37bea7ede24bd1adcef9157f`.
