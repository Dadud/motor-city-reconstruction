# Startup record constructor (owner binding 0x53a1f0)

## Scope

The owner-binding initializer `0x53a1f0` builds the 0x4a8-byte startup record
at stack `EBP-0x4d8` and copies it to `owner+0x17ec`. The translation covers
the whole call: gear tables from the recovered gear binding
(`client/gear_binding.py`), inertia scales from the body-shape table, wheel
radii from the tire fields, the turn scalars through `0x6f1430` (atan2 scaled
to turns) and `0x536d80` (degrees-to-samples clamp), resistance from the
recovered startup resistance producer, crossing-derived shift thresholds, and
both 112-sample acceleration tables from the recovered producer
(`client/acceleration_table.py`).

The constructor now accepts either the original scene-area result or decoded
scene nodes. `raster_nodes_from_render_list` adapts the reconstructed render
records' model index, surface index and mesh-type fields into the scene nodes.
With `scene_nodes=...`, the constructor invokes
`scene_area_measure.scene_area_from_nodes` and feeds the measured result into
the same startup-resistance and shift-threshold calculations. This removes the
manual area scalar when callers already have a recovered node/FCE list. It does
not acquire the native linked scene registry or reproduce its resource lifetime;
callers must still supply correct node order, surface IDs and mesh types.

## Evidence

- DynoOracle emulation of the original `mcity.exe` (SHA-256 `28c0cdde...`),
  driven by `tools/startup_record_oracle.py`: seven cases across 4/8/6/5-gear
  configurations, marker-present, marker-missing and NULL-model inputs, and
  supplied `FUN_00483450` scene-area returns (0.0, 1.25, 2.05 and 3.5).
- Complete cases compare the 0x4a8-byte record, permitting the documented
  one-binary32-ULP difference at angular field `0x10c`, and confirm the owner
  bytes are untouched outside the documented copy; the
  missing-marker case returns 0 with an unmutated owner and the NULL-model
  case exercises the authored half-wheelbase default axles.
- Per-gear prefix fields (thresholds 0xa4+gear*4, rps 0x24+gear*4, factors
  0x64, inertias 0x84, turns 0x108-0x118, radii 0x100/0x104, denominators
  0xe0-0xfc) are additionally compared mid-call before the acceleration
  tables run.
- `tools/native_startup_record_compare.py` compares `native/src/startup_record.cpp`
  against the translation over the same seven cases with zero bit differences.
- `tests/test_startup_record.py` verifies decoded scene nodes produce the same
  complete startup record as supplying their measured area result directly.
- `tests/test_raster_scene.py` verifies a stable-sorted render list feeds the
  projected-area path with the original selected surfaces and mirror types.
- Portable arithmetic checkpoint: 128 additional positive tire configurations
  perturb binary32 tire fields near ordinary rim/width/aspect boundaries.
  MSVC and Zig/Clang both match all 135 Python cases bit-exactly. The original
  oracle accepts all 135 with one early marker failure and 17 cases using the
  existing one-ULP angular allowance. Tire-radius fields remain bit-exact.
  The oracle now reports tolerance usage explicitly and compares the aligned
  angular word rather than four-byte slices starting at each differing byte.

## Method notes

- The `FUN_00483450` scene-area query is an owner-method dependent on real
  game state and stays out of scope: its binary32 return is an explicit
  translation input, supplied through memory. The original compares the
  return against 0.0 and replaces a zero result with the geometric fallback
  `(2*cc)*(2*d0)*0.8f` computed at `0x53a7df..0x53a7f7`.
- Wheel radii (record 0x100/0x104) chain their products and sum through the
  x87 result register at 64-bit mantissa precision before the single binary32
  store. binary64 intermediates double-round differently on boundary inputs
  (case 3's rear tire), so `client/startup_record.py` reproduces the 64-bit
  intermediate exactly with exact rational arithmetic.
- Turn scalar 0x10c passes through the unrounded 80-bit difference of two
  atan2 results; the binary64 reference may legitimately differ by one
  binary32 ULP and the oracle documents that single tolerance.
- Shift thresholds subtract the recovered resistance from the recovered gear
  force, scan for the sign crossing, and interpolate the crossing fraction;
  the fraction times the per-gear rpm scale must reach 3650 rpm before the
  threshold is accepted.
- The native port mirrors the translation's arithmetic width: every helper
  (`f32`, `own`, `number`) returns the binary32 value widened to binary64, so
  no operation mixes binary32 operands and the product chains round once
  exactly as the original does. The wheel-radius sum is carried as an exact
  integer rational in portable four-word two's-complement arithmetic (products aligned downward with a sticky
  bit, since a left-aligned 144-bit sum does not fit) and rounded through the
  64-bit and 53-bit mantissas before the binary32 store.

## Repeat the portable arithmetic checkpoint

Build with `python build.py --test` using the installed toolchain's CMake.
Then, for an MSVC build in `build/recovered`:

```powershell
python -m tools.native_wide_int_compare build/recovered/Release/mco_wide_int_compare.exe
python -m tools.native_startup_record_compare build/recovered/Release/mco_startup_record_compare.exe --radius-cases 128
.venv/Scripts/python.exe -m tools.startup_record_oracle 'C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe' --radius-cases 128
```

The arithmetic driver checks 5,464 cases against Python's arbitrary-precision
integers and binary64 conversion: carries, borrows, products, masks, signed
shifts across all word boundaries, and ties-to-even conversion. No original
bytes are used in that arithmetic check. The last command requires the original
binary and Unicorn, retaining the supplied scene-area return described above.
Use executables directly under `build/native-zig` for that configured build.

## Limitations

- `FUN_00483450` has a bounded geometry translation and 19 original comparisons;
  real registry/allocator integration and installed-asset validation remain
  open. The startup-record comparison supplies its return as an explicit input.
- The native radius path assumes positive tire fields; a negative or
  exponent-spread extreme is truncated at the 127-bit budget rather than
  rejected, and no corpus case reaches it.
