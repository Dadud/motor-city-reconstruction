# Cylinder state and gas exchange

The dyno's inner calculation maintains cylinder state and evaluates valve flow
against intake and exhaust boundaries. Several stages are now reproduced exactly
for tested float32 outputs. The complete crank integration step is now recovered;
the standalone unboosted core driver now composes those stages. The functions live in [thermodynamics.py](../../client/thermodynamics.py).

## Initialization and piston geometry

At `0x479e4d–0x479f35`, the solver initializes temperature to 2000 and starts the
first RPM with pressure approximately 44.1. These are native numeric values;
their physical units are not fully established. Later cycles carry state, so
resetting every cycle to those numbers would change the calculation.

Cylinder volume follows slider-crank geometry. Let `r = stroke/2`, `L` be rod
length, `A` piston area, `Vc` clearance volume and `θ` crank angle:

```text
volume(θ) = A × r × [1 - cos θ
                    + (L/r) × (1 - sqrt(1 - ((r/L) × sin θ)²))] + Vc
```

The actual implementation stores some trigonometric and geometric terms as
float32 before reuse. The initialization derives mass-related values from this
volume, pressure and native constants. Those constants do not yet establish
physical mass units, so the fields remain `mass_term` and `reference_mass_term`.

## Intake boundary and charge temperature

The intake boundary combines total displacement, RPM, carburetor capacity and
mode. Its broad structure is:

```text
rate     = total_displacement × RPM
capacity = carb_capacity × coefficient_selected_by_carb_code
scale    = adjusted_capacity × 207360
flow     = (rate × 70 × 0.01) / scale
pressure = 14.7 - flow² × 7.916e-6
```

Carb codes 2 and 4 select coefficients approximately `3.810418e-5` and
`5.387931e-5`. Intake mode 4 quarters the capacity before scaling. A positive
boost contribution is added after storing the base pressure. Negative values
are not newly clamped by the reconstruction: preserving the original calculation
also requires understanding its later failure handling.

Charge temperature uses a raw mode word and RPM. In the stock core's mode 1,
below 5,500 RPM it follows approximately `610 - RPM × 0.01272`; at and above that
threshold it becomes 540. Other mode ranges select different branches. At
2,000 RPM the stored stock-mode value is `584.5599975585938`. This is a numeric
reference, not a verified temperature in degrees Fahrenheit or Kelvin.

The preparation also stores `24000/RPM` and a temperature polynomial. We name
that value `angle_step_factor`; its name does not establish the final integration
interval or how often the game calls the dyno.

## Exhaust boundary varies with crank angle

Seven exhaust modes select a baseline, amplitude, reference RPM and RPM exponent.
For example, mode 1 uses baseline 35, amplitude 0.3, reference RPM 4000 and an
exponent near 1.06. The baseline is divided by the supplied flow factor.

An angle-dependent phase drives a sine wave:

```text
phase_factor = 270 / (360 - start_angle)
phase        = (angle - start_angle) × reference_RPM / RPM × phase_factor
wave_scale   = RPM^exponent × 0.0013332
wave         = sin(phase × radians_per_degree) × wave_scale
```

The wave is multiplied by 2 below phase 180, by the mode's amplitude between
180 and 360, and by approximately 0.8 above 360, then added to the baseline.
At exactly 180 or 360 the native branch retains the preceding value. Positive
boost selects a separate RPM-only result. These details matter when reproducing
stateful behavior, even if they appear unusual in a general physics model.

The variable's role as an exhaust boundary follows its consumers. Describing it
as a measured real-world exhaust pressure waveform would exceed the evidence.

## Flow can reverse

At an open intake valve, the calculation compares intake boundary pressure with
cylinder pressure. It chooses the larger and smaller values and forms a ratio:

```text
q = f32(low_pressure / high_pressure)
flow_term = f32(5 × (q^1.4279999732971191 - q^1.7139999866485596))
```

Using the selected source temperature `Ts`, the intake branch stores:

```text
thermal_root = f32(sqrt(Ts × 2405.01806640625))
delta ≈ thermal_root × high_pressure × 0.0187441427 / Ts
        × sqrt(flow_term) × valve_area × 0.16666667 / RPM
```

The sign is positive into the cylinder and negative out through the intake.
The source temperature comes from the intake when intake pressure is higher;
otherwise it comes from the cylinder. Equal pressures make the flow term zero.

The exhaust branch uses the same basic pressure-ratio expression. Positive
exhaust delta leaves the cylinder. If the exhaust boundary pressure is higher,
flow reverses and its incoming temperature is the native fixed value 2000.
Unlike intake, exhaust retains an unrounded square-root intermediate during the
main multiplication. Rounding both branches identically would lose fidelity.

These deltas still await complete accumulation and unit interpretation. Do not
label them kilograms per second merely because the formula resembles gas flow.

## Feedback makes the intake stateful

Before calculating the current intake transfer, the original uses the preceding
exchange's stored flow, thermal-root and density fields with the current area:

```text
velocity_term = sqrt(previous_flow_term) × previous_thermal_root × area
                / (valve_scale² × 0.7853982)
boundary'     = (boundary × 144 - velocity_term² × previous_density × 0.5)
                × 0.0069444445 + wave_term
```

This ordering is recovered at `0x47ab69–0x47abe4`. Feeding the new transfer into
its own boundary calculation would change the dependency. A closed valve sets
its delta to zero but retains feedback fields, so zero flow does not mean that
all state should be cleared. A native scratch slot also changes role between
stages; composing individually verified functions still requires correct state
ordering.

## Energy depends on temperature

The next recovered range, `0x47ae8f–0x47af0b`, computes two polynomial terms.
With `T` the stored temperature, the formulas below abbreviate native constants:

```text
capacity_term = 1.17048e-8 T² + 1.0396e-5 T + 0.16528
                - 3.74528e-12 T³ + 3.1578e-16 T⁴
energy_term   = 5.1979e-6 T² + 0.16528 T + 3.9016e-9 T³
                - 9.3632e-13 T⁴ + 6.3156e-17 T⁵
```

Their algebra is consistent with a temperature-dependent capacity term and
its integrated energy term. The physical interpretation is an inference;
units remain unverified. The native coefficients and operation order, rather
than an analytically simplified replacement, are implemented.

| Native temperature input | Stored capacity term | Stored energy term |
| --- | --- | --- |
| 540 | 0.1737440675497055 | 91.30455017089844 |
| 2000 | 0.2079814374446869 | 369.6042785644531 |
| 4000 | 0.2352825552225113 | 818.962646484375 |

These are synthetic reference inputs, not a measured operating-temperature
range. A 10,000-input sweep matched 20,000 float32 fields against bounded
execution of the original instructions.

## Coupled crank integration

[The integrator](../../client/cylinder_integration.py) recovers the complete
`0x47ae8f–0x47b285` stage: geometry, pressure, temperature, mass, exchanged
energy, wall energy and work. It consumes current valve transfers and already
accumulated intake mass. Labels describe observed algebra; SI units remain
unverified.

The angle interval is `f32(RPM × f32(0.0003))`. Each evolving state uses:

```text
next_value = f32(value + step × (1.5 × current_rate - 0.5 × previous_rate))
```

This has the mathematical form of a two-step Adams–Bashforth method. The native
initialization clears derivative histories at each RPM knot. Clearing them at
every angle would change the calculation.

Outgoing intake flow selects cylinder energy plus `T × 0.06857`; incoming intake
flow selects charge energy. Reverse exhaust flow selects the fixed native energy
`506.7442626953125`. Signed transfer accumulates before state evolves.
Wall exchange combines current volume, bore, prepared wall area and RPM with
`800 - cylinder_temperature`. Combustion is a sine pulse strictly between angles
710 and 770; exact endpoints contribute zero. Prepared fuel ratio and fuel energy
remain explicit inputs rather than invented fuel properties.

Pressure evolution balances fuel, wall and transferred energy, pressure-volume
work, and a mass-dependent energy term. Temperature evolution then uses this
pressure derivative, current mass and net mass exchange. Accumulated work uses
the volume difference and the mean of old and new pressures.

Advancing angle retains an unrounded intermediate for the radians store. The
next rod projection multiplies its unrounded value by its stored float32 copy.
Rounding either expression uniformly caused observable work differences.

## Carryover and verification

`0x479e2a–0x479e4d` selects pressure: knot zero starts near 44.1, knot one retains
live pressure, and later knots copy the stored end-pressure field. The
`carry_cycle_pressure` API retains these distinct choices. Each new knot resets
temperature to 2000, initializes mass from selected pressure and geometry, and
clears work, energy totals and derivative histories. Intake flow feedback lives
outside these resets and must persist when the full driver is assembled.

`tools.verify_cylinder_integration` observes the full bounded original solver
with real power and boost helpers. The stock-derived Ford record and four
explicit variations (compression 6 and 18; cam advance minus and plus 10) each
complete all nineteen RPM knots and 8,927 steps. Ten persistent state fields and
seven result fields match exactly: 151,759 float32 fields per run, or 758,795
fields across 44,635 steps.

A second run substitutes only the portable integration stage and feeds its
outputs into subsequent original valve and cycle stages. Each of the five final
1004-byte solver records remains byte-identical. This verifies a full feedback
trajectory, including end-pressure carryover, rather than independently reset
formula samples. These are CPU emulation results, not hardware observations or
proof over every engine. Neither the game's entry point nor Windows imports run.

With a locally retained JSON record containing `input_hex`, reproduce using:

```text
python -m tools.verify_cylinder_integration path/to/mcity.exe path/to/private-record.json
```

The verified source SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Static sources are REA 221 assembly and refreshed dossier
`ev_87ab2b6c22a4418bdcf1a2a832cb6bce2d9467d2cea8fe8f9233bbdaaff87265`.
The dossier reports full body `0x478ec0–0x47b467`; its high-pcode value-flow is
truncated, so no completeness claim relies on that facet.

## Standalone unboosted core driver

[solve_core_record](../../client/cylinder_solver.py) now composes the recovered
stages without reading or executing the original. It accepts an assembled
1004-byte record and returns the same record with seven nineteen-knot result
series populated. It preserves input fields outside those output series.

The integration is connected in the observed order:

| Original range | Composed role |
| --- | --- |
| `0x478f44–0x47901d` | Cylinder geometry and displacement |
| `0x479062–0x4790eb`, `0x479af2–0x479b29` | Fuel energy and train-dependent fuel ratio |
| `0x4793e6–0x479af2` | Valve events, flow tables and cam profiles |
| `0x479b93–0x479df6` | RPM step, charge temperature and intake correction |
| `0x479e2a–0x479f35` | Pressure carryover, mass initialization and history resets |
| `0x479f42–0x47a145` | Exhaust and intake boundary preparation |
| `0x47a145–0x47aa3d` | Intake/exhaust lift, effective areas and pressure correction |
| `0x47aa3d–0x47ab69` | Exhaust wave and retained piecewise intake wave |
| `0x47ab69–0x47ae8f` | Prior-flow intake feedback, current transfer and accumulation |
| `0x47ae8f–0x47b285` | Coupled cylinder integration and work |
| `0x47b285–0x47b446` | Cycle termination, fill metric and seven output series |

One additional carryover is essential: the intake boundary starts with a fill
input of 70, but `0x47b2b1` replaces it with the preceding knot's accumulated
intake mass divided by reference mass, multiplied by 100. The next knot reuses
that value. Calling the earlier isolated boundary API with its fixed 70 at every
knot produced incorrect later output, despite matching the first knot.

The intake wave rises linearly strictly above angle 510 through 540, then uses a
sine branch strictly above 540 and below 650. Outside those updates it retains
its preceding value until the next RPM reset. Consumed intake mass also persists
when the intake valve is closed; the running intake accumulator resets at each
knot. Intake flow/thermal/density feedback and the exhaust wave persist across
knots. These behaviors follow the original stores rather than a physical model's
preferred reset policy.

The boost helper `0x586730` performs no boost-state updates when raw boost mode
at record `+0x3c4` is zero. For modes 1–3, `client/engine_boost.py` now models its
per-RPM scratch updates. The first three modes (0–2) compare byte-for-byte with
the original on one synthetic state, but a nine-case RPM sweep found one-ULP
differences in mode 1 charge at 2000 RPM and mode 2 work at 10000 RPM. Mode 3
differs in one or more boost/work fields at all three sampled RPMs. These
results are consistent with x87 intermediate precision and power rounding, but
the exact mismatch cause has not been isolated. Static inspection shows the
power path at `0x69ba30` executes `FYL2X` and calls `0x6a5120`, whose body uses
`FRNDINT`, `F2XM1`, and `FSCALE`; `0x6a5209` handles exceptional results. This
confirms the target's x87 power sequence, but does not by itself explain every
different stored byte. The repeatable bounded sweep is
`tools/verify_engine_boost.py`. REA helper evidence is
`ev_5e018651d07e8334f54a4f391646402acb352dcebaa66b8caf02fb467e547c14`;
the x87 helper inspection is retained in the ignored
`evidence/engine-x87-power-ghidra.snapshot.json`.
The helper has not yet been composed into the cylinder driver: boost-dependent
intake timing/pressure, charge initialization, work output and multi-knot state
carryover still need integration and complete-record comparisons. Time-based
native abort behavior and final curve corrections also remain unimplemented.
Invalid positive-gas-domain inputs raise an error rather than imitating the
native zero-first-output abort. The driver is a recovered numerical core, not
verified vehicle-driving forces.

The initial comparisons cover fifteen distinct stock-derived records and the
five integration records above. Every complete 1004-byte result matches bounded
original execution exactly, including all 133 result floats per record. An
authored synthetic record also matches; regression tests retain its first three
power and boundary-pressure outputs to catch the prior-fill carryover behavior.

Reproduce a complete core comparison with a locally retained input record:

```text
python -m tools.verify_cylinder_solver path/to/mcity.exe path/to/private-record.json
```

Twenty-five additional authored variations all match complete original records:
intake modes 1–6; exhaust modes 1–7; fuel modes 9, 10, 18, 19, 20, 21 and 22;
valve trains 2 and 3; both two-valve multipliers; and adjusted cam timing.
Those tests use carb capacity 2400 to stay within the positive boundary domain.
Across the fifteen stock, five integration, one base synthetic and twenty-five
branch comparisons, 46 complete records and 6,118 result floats match exactly.
This is bounded coverage rather than proof over every assembled record.

The driver rejects non-finite or excessive valve angles, limits each knot to
2,000 integration steps and requires angle progress after every step. Malformed
float32 angles cannot stall the loop indefinitely.

No original instructions, stock records, raw pseudocode or private captures are
required by the portable driver or redistributed with these authored files.
Prototype driving remains independent of this core until its remaining force,
boost and finalization dependencies are recovered and validated.
