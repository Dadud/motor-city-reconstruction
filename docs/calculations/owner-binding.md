# Owner mass, inertia, axle levers and startup COM

`client/owner_binding.py` reconstructs numeric producers used by startup, rather
than assigning force-consumer defaults. The complete `0x53a1f0` initializer is
larger: it also constructs gearing arrays, wheel radius and clearance angles,
spring-related values, projected area and shift thresholds. Those remaining
producers are not silently supplied by this module.

## Inputs and destinations

| Input | Original producer | Bound output |
| --- | --- | --- |
| Finalized mass, cfg `0x20` | All component loaders and assembly aggregation | owner `0x50` mass, `0x54` inverse mass via `0x51f440` |
| Model half extents | Model geometry fields `0x4c`, `0x50`, `0x54`, passed to `0x51f440` | owner `0xcc`, `0xd0`, `0xd4` |
| Body shape, cfg `0x48` | Body initializer from Physics Val7 | Three inertia scales via `0x53a150` |
| Wheelbase, cfg `0x2c` | Body initializer from Physics Val2 | Axle levers |
| Finalized front weight fraction, cfg `0x3c` | Assembly `0x53b590` | owner `0x18b8` front lever and `0x18bc` rear lever |
| Height parameter, cfg `0x38` | Body initializer from Physics Val5 | Vertical COM coordinate, together with model half height |

`bind_finalized_owner` requires an explicit assembly-completion assertion and
the model half extents. It reads the original offsets from the supplied final
configuration. A body-only loader image is rejected when assembly is incomplete.
The assertion records caller responsibility; it cannot verify arbitrary caller
claims. The module does not manufacture final mass or dimensions.

The actual vehicle 101 body supplies wheelbase approximately 2.692, shape 2,
and height parameter approximately 0.5334. Shape 2 produces float32 inertia
scales approximately `(0.88, 0.94, 0.83)`. These inputs are constructible now.
Body mass 575 and body fraction at cfg `0x40` cannot substitute for finalized
cfg `0x20` and cfg `0x3c`. Authentic model half extents must come from verified
model geometry setup; marker spacing does not establish them.

## Calculations

For half extents `(a,b,c)`, mass `m`, and body scales `(sx,sy,sz)`, the initializer
calculates:

```
Ix = (4*c*c + 4*b*b) * sx * m * float32(1/12)
Iy = (4*c*c + 4*a*a) * sy * m * float32(1/12)
Iz = (4*b*b + 4*a*a) * sz * m * float32(1/12)
```

Products use the original default x87 53-bit precision until the float32 stores.
The stored inertias feed reciprocal calculations. They are copied into owner
`0x18d4`, `0x18d8`, `0x18dc`; inverses go into `0x18e0`, `0x18e4`, `0x18e8`.
The mass-binding section uses the original mass-zero fallback of 1000 and then
stores the reciprocal. This observed fallback does not authorize using missing
mass as zero during reconstruction.

For wheelbase `L` and finalized front fraction `f`, front lever is `(1-f)*L`
and rear lever is `L*f`, each rounded when stored. For example, the authored
comparison case `L=4`, `f=0.25` yields front lever 3 and rear lever 1. These are
COM-to-axle distances, not the raw model wheel-marker coordinates.

Startup `0x43ac8e` separately writes longitudinal COM as existing owner `0x18c4`
minus existing owner `0x18b8`. It writes vertical COM as cfg `0x38` times the
float32 constant approximately `0.9090909`, minus owner half height `0xd0`.
**These stores occur before the call to `0x53a1f0`.** `bind_startup_com` therefore
requires the existing marker/lever observations explicitly; it does not reorder
the operation by substituting the newly computed lever. The prior producer of
those existing values must still be established. This range does not write
lateral COM.

## Verification and remaining work

The bounded executable oracle passes 120 mass/inertia cases, 18 axle-lever
cases and 16 startup COM cases with zero byte differences. It executes the
original shape helper, not a replacement. Cases cover every known shape and
unknown-selector identity behavior, multiple masses/extents, zero-mass fallback,
and asymmetric distribution. Seven unit tests verify the public producer API
and the refusal to bind an incomplete assembly. No original stock initialized
owner or complete assembled vehicle has yet been claimed by these comparisons.

Private retained evidence: wheel/owner dossier 026 (also retained as 087),
startup dossier 125, body assembly dossier 196, and verified original numeric
ranges `0x51f4dd..0x51f518`, `0x53a3f5..0x53a4be`,
`0x53a7b6..0x53a7df`, `0x43ac8e..0x43acb1`.
The source executable remains external and unchanged. No new REA lifecycle
session was necessary for this recovery.
