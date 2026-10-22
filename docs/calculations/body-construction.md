# Base body construction and startup geometry

Authored implementations: `client/body_constructor.py`, `client/body_geometry.py`,
`client/body_startup.py`, `native/src/body_constructor.cpp` and their public headers.
Addresses refer exclusively to main executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

## Original contracts

| Entry | Recovered behavior | Verification domain |
| --- | --- | --- |
| `0x51ed40` | Build 22 body sampling positions | All five internal shapes; asymmetric, negative and signed-zero extents |
| `0x51f440` | Clear and construct the base owner, mass, volume, inertia, response coefficients, matrices and two sampling arrays | All five shapes, nine material values, zero/nonzero mass and 27 dimension sets, including zero/negative extents |
| `0x43a240` | Catalogue-body adjustment of selected sampling coordinates | All eight catalogue selectors and ten distinct arrays |
| `0x53a150` | Three body inertia multipliers | Known and unknown selectors, including nonidentity prior values |
| `0x43ab88..0x43acb1` | Connected body phase of the larger startup function `0x43a990` | 320 authored owner/configuration/model states; all observation bytes compared |

The internal primitive selector `0..4` and catalogue selector `0..7` are different
contracts. Vehicle startup constructs primitive zero and subsequently customizes
it with the catalogue selector. Treating the catalogue value as a primitive would
change the shape, inertia and sampling arrangement.

The direct Python comparison now also covers zero and negative dimensions, including zero-volume and infinite inverse-inertia writes. These edge cases match all original observation bytes; the native implementation comparison remains limited to the prior nondegenerate extent corpus.

The original clears exactly `0x418` bytes. The authored observation image holds
`0x2000` bytes so comparisons can also detect unintended writes in derived state;
this is not a recovered original allocation size. Construction preserves prior
high-offset model pointers, wheel markers, axle observations and configuration
references. Host APIs receive objects separately and never dereference emulated
32-bit addresses.

## Geometry and calculations

Half extents `(x,y,z)` generate eight corners, six face positions and eight edge
positions, in original order. Pyramid-like and wedge-like primitives collapse
upper corner coordinates. Rounded shapes multiply corner coordinates by the
original float32 constant approximately `0.707`. Face and edge samples are created
before that modification. The sphere additionally adjusts edge sample heights.
No vertical-edge midpoint samples are appended by this helper.

Construction stores the model-vector magnitude and original gravity-like y value,
then mass and inverse mass. A supplied zero mass follows the original fallback
of 1000. It must not be used to conceal an unrecovered assembly producer.
Primitive zero uses:

```
volume = (2*z) * (2*y) * (2*x)
Ix = (float32(4*z*z) + float32(4*y*y)) * mass * float32(1/12)
Iy = (float32(4*z*z) + float32(4*x*x)) * mass * float32(1/12)
Iz = (float32(4*y*y) + float32(4*x*x)) * mass * float32(1/12)
```

For `(1,0.5,2)` and zero supplied mass, the stored mass is 1000 and volume is 8.
Inverses use stored float32 inertias. Separate shape branches preserve their
observed formulas rather than replacing them with textbook formulas. For example,
the sphere branch uses maximum half extent for all axes and an inertia expression
linear in that extent. Its volume rounds `x*x` before multiplying by `x` and the
original float32 sphere constant. Omitting that intermediate store changes volume
and density in the comparison corpus.

The first `0x108`-byte sampling array begins at owner `0xe0`; an initial copy
begins at `0x1e8`. Catalogue customization and stance subsequently change the first
array only. Rebuilding the second array after those adjustments would violate the
original sequence.

## Connected startup phase

`prepare_startup_body` requires finalized mechanical configuration, model half
extents and existing high-offset geometry. It executes:

1. Primitive-zero base construction with default material.
2. Original owner flag and coefficient stores.
3. Catalogue sampling customization (`0x43a240`).
4. Existing recovered stance adjustment (`0x53b3c0`).
5. Catalogue response stores and configuration coefficient copy.
6. Vertical and longitudinal COM stores using the existing front marker/lever.

The phase stops immediately before `0x53a1f0`. It does not substitute the later
computed axle lever into the earlier COM calculation. Model assembly, the main
owner initializer, projected-area calculation, shift thresholds and complete
startup failure handling remain required. This phase alone is not a driving car.

## Evidence and repeatable checks

Private REA dossiers:

- Primitive samples: `ev_89d8d160ac871298ee33787bdc125c8f793aaa218f35a0a0cb2bceca8a3b6be8`.
- Base construction: `ev_72f133d03c8ace40e1c44f7594a89daac4f9709f6111637dc4eba91cfe1894b7`.
- Catalogue customization: `ev_e7d371c291013ac52fe4428f40b8337c6dbd80f6fd8b103e4e3fe1f91644b7ad`.
- Inertia multipliers: `ev_83ae2c5f8f30453495eb6fd89760b560c3d5790f9c5d1ef17732bd78fe8a7acf`.

`tools.body_constructor_oracle` executes 1,080 complete constructors and 30 complete
geometry calls. `tools.body_startup_oracle` executes 80 catalogue adjustments,
26 inertia-scale calls and 320 connected startup-body scenarios. The existing
`tools.owner_binding_oracle` also passes 120 mass/inertia, 18 lever and 16 COM
comparisons. All compared output bytes match exactly. The source executable is
an external input; no original bytes are published or PE entry point executed.

Native/Python runners compare the same 1,110 construction/geometry cases, 320
startup cases and 180 owner-binding cases, including signed output bits. They pass
with MSVC and Zig/Clang on Windows. CI runs the comparisons on Windows and Linux;
Linux results for this change must be observed before claiming cross-platform
acceptance. None of these checks substitutes for original whole-game traces.
