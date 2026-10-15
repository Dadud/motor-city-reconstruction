# Assembled weight distribution and numeric postload

The original recomputes weight distribution after component loading. Body-only
catalogue weight distribution is an input to that calculation, not its result.
The recovered Python and C++ implementations reproduce the numeric postload
tail before final engine-curve generation. Complete stock-car startup remains
incomplete: component loaders, preceding quality updates, total mass accumulation,
and engine curves must still supply their actual outputs.

## Evidence and execution coverage

Source: separately supplied `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

REA/Ghidra evidence:

- Assembly routine `0x54e720`,
  `ev_f20d56d975c43fb2f81535392e722376837ccf5bd4bb65eae81fd4724b981024`.
- Weight-distribution helper `0x53b590`,
  `ev_c2da69a8643cc7944997b381ebfe5d580588150c21d0b342b0d892d290f52bbb`.

The helper runs to its real return with no substituted calls. Its 728 authored
cases cover body fractions including zero/one, three wheelbases, isolated masses
in every component slot, and reproducible mixed component masses. Both the double
return and caller's float32 store match exactly. The postload corpus compares all
2,080 configuration bytes across another 728 executions of `0x54e8ea..0x54ea89`,
including the actual weight helper. All ten coefficient indices and four
clearance-copy combinations are exercised. These are bounded CPU comparisons,
not observed original-client driving sessions.

## Weight calculation

Let `B` be body mass, `f` the body's weight fraction, `L` wheelbase, and `S`
the shared component mass. The original starts with two group accumulators:

```
H = float32(B * 0.5)
F = S * 0.25 + H + ordered front component contributions
R = S * 0.75 + H + ordered rear component contributions
front_moment = F * (f * L)
rear_moment  = ((1 - f) * L) * R
assembled_fraction = front_moment / (rear_moment + front_moment)
```

Five slots in each group contribute twice their stored mass. Their mapping and
addition order are explicit in `client/assembly_weight.py`. Full semantic names
for all slots remain under recovery; executable offsets are internal research
identifiers and are not mod API IDs. Masses use the mechanical configuration's
common mass unit; this helper itself performs no unit conversion. Wheelbase
uses the original configuration length unit. The output is dimensionless.

For a body mass of 1,000, fraction 0.5, wheelbase 2.5, and no components, the
fraction remains 0.5. Add 250 in one doubled front slot: the group masses become
1,000 and 500, giving a fraction of 2/3 before float32 storage. Add the same mass
in a doubled rear slot and the result returns to 0.5. With no such parts but a
shared mass of 1,000, the asymmetric 25/75 split instead gives 0.375.

The owner-binding producer consumes the assembled fraction, stored at configuration
`+0x3c`, to calculate axle levers. It must not use the original body fraction at
`+0x40`. Whole-car mass at `+0x20` remains a separate component-loader output.

## Other numeric postload operations

The recovered tail:

1. Supplies the original selector-dependent fallback at `+0x5b0` when `+0x5a0`
   is nonpositive: 0.025 for selector zero, 0.03 for one, zero otherwise.
2. Copies the two clearance overrides only when both source values are nonzero.
3. Adds `whole_car_mass * float32(0.02)` to the existing `+0x28` accumulator.
4. Computes the original reciprocal weighted sum at `+0x448` using the ten-entry
   coefficient table and its observed component slots.
5. Stores the recalculated assembled fraction.

The physical interpretation of the two accumulators is not established here.
The expression printed by the decompiler rearranges additions; the ports follow
instruction order. The helper stores only half-body mass as float32 internally;
the other intermediates retain the original 53-bit x87 precision. Cancelling
wheelbase or rounding each component addition would change that behavior.

Public boundaries require finite physical mass inputs, a positive wheelbase,
valid table indices, and nonzero divisors. These checks are authored protections;
the original numeric routines do not validate every such condition. A caller's
`components_loaded=True` assertion is a provenance requirement, not independent
proof that all required parts were loaded. Neither API invents missing masses.

## Repeatable checks

With original assets supplied separately:

```powershell
python -m tools.assembly_weight_oracle '<game>/mcity.exe'
python -m tools.assembly_finalization_oracle '<game>/mcity.exe'
```

After building native targets:

```powershell
python -m tools.native_assembly_weight_compare build/native-check/mco_assembly_weight_compare.exe
python -m tools.native_assembly_finalization_compare build/native-check/mco_assembly_finalization_compare.exe
python -m unittest tests.test_assembly_finalization tests.test_owner_binding
```

Both native differential runners use authored fixtures and need no original
binary. They are included in Windows/Linux CI. Original function comparisons
remain local and never distribute executable bytes or decompiler output.
