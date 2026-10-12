# Engine assembly and the dyno

The recovered engine path builds a numerical description of an assembled engine,
then evaluates it at RPM samples. Block dimensions, head and valve properties,
cam timing, intake/exhaust configuration and flow templates feed this description.
It is more detailed than assigning every engine a fixed horsepower number.

This article describes recovered stages, not a completed replacement solver.
Source addresses and coverage are tied to the build identified in the
[writeup index](README.md).

## From components to solver inputs

The core builder at `0x46d1d0` uses a 1,004-byte record. The portable
[builder](../../client/dyno.py) writes dimensions, timing, lifts, mode codes and
flow series into their recovered locations. It starts with a zeroed record.

Some important transformations are:

| Input | Recovered transformation |
| --- | --- |
| Block bore and stroke in metres | Convert to the solver's inch-based convention |
| Head valve dimensions in millimetres | Convert through metres to inches |
| Cam lift | Convert millimetres to inches and multiply by the assembled valve-train factor |
| Head compression ratio | Clamp to 6–18 |
| Carburetor capacity | Enforce a minimum of 300 |
| Intake flow factor | Clamp to approximately 0.9–1.1 |
| Exhaust flow factor | Clamp to approximately 0.95–1.08 |

Mode codes are transformed builder inputs, not interchangeable with raw database
values. Compatibility checks and fuel/boost assembly are not fully recovered.
The current stock comparison covers 199 supported assemblies; 13 remain rejected.
Matching builder output given assembled inputs does not prove that the entire
original component-loading path has been reproduced.

The template loader at `0x46dc20` supplies 16 flow templates. Each has an
identifier, four scalar fields and four eight-element series. The solver works
with ten-slot tables; the core builder leaves unused slots zero. A recovered
modifier scales two series while preserving the others. The templates stay in
the user's executable and are not redistributed with this repository.

## Cylinder geometry

For bore `b`, stroke `s`, compression ratio `c` and cylinder count `n`, the
geometry preparation at `0x478f44–0x47901d` has the familiar structure:

```text
swept volume per cylinder = s × b² × π/4
clearance volume          = swept volume / (c - 1)
total displacement        = n × s × b² × π/4
assumed rod length        = s × 1.62
```

These volumes follow the native inch-based convention. The rod length is a
solver assumption, rather than a separately measured rod for each engine. An
additional stored term uses `b² × 1.57`; its exact physical role remains unnamed.
The code uses stored float32 constants and rounds intermediate values at specific
points, so the equations above are explanatory rather than a bit-exact recipe.

For a synthetic 4-inch bore, 3.5-inch stroke, eight-cylinder engine with 9:1
compression, the geometric displacement is about 351.86 cubic inches. Increasing
compression reduces clearance volume without changing swept displacement.
This example describes geometry only; it predicts no finished horsepower result.

## Cam timing and valve movement

The preparation transforms four timing inputs into solver angle boundaries,
applies cam advance, and optionally applies a timing adjustment selected by
valve-train code. Some branches double effective valve size. The individual
timing fields retain offset-based names because conventional opening/closing
labels have not all been proven.

`cam_profiles` builds two piecewise profiles using circles, cosine, square root
and arctangent. `valve_lift` evaluates those profiles for the current angle:

1. Outside the active interval, lift is zero.
2. Inside it, one of three cosine-based branches supplies a radius.
3. Lift is `(radius - 0.55032) × 1.5`.
4. A negative result becomes a small positive value, approximately `1e-6`.

At two exact internal phase boundaries, the native branch leaves lift zero.
The reconstruction preserves those boundaries rather than smoothing the curve.
Changing them could alter downstream flow even if a plotted cam profile looks
almost identical.

## Turning lift into effective airflow area

The solver first normalizes template flow values, then interpolates a coefficient
at the current lift. Below the first table point it interpolates from an implicit
zero-lift coefficient of 1:

```text
C(lift) = 1 + (C₀ - 1) × lift / lift₀
```

Other segments use linear interpolation. A zero marker later in the table can
select extrapolation from a preceding pair; it is not simply a request to return
zero. Preserve the table-selection logic in
[interpolate_flow](../../client/dyno_solver.py) when changing this stage.

One branch clamps the coefficient to `[0, 1]`. Another applies a piecewise
pressure correction, using a threshold near `1.8929` and a minimum near `0.43`.
At the exact threshold the recovered branch returns the minimum. The final
effective area is:

```text
area = f32(coefficient × lift × effective valve size × π)
```

The product resembles a valve's curtain area modified by a flow coefficient.
That is a physical interpretation of the algebra; the complete unit chain has
not yet been established. It should not be silently replaced by SI area values.

## RPM samples, losses and outputs

The recovered core solver evaluates 19 RPM knots: 2,000 through 11,000 in steps
of 500. Those are solver samples, not proof that every engine can be driven to
11,000 RPM or that the final displayed curve uses only those points.

The recovered mechanical-loss term has this structure, with abbreviated constants:

```text
speed = RPM × stroke_inches × 0.16666667
loss  = (speed × 6.5476e-7 + 0.0030476) × speed + 12.964
```

It grows approximately quadratically with the speed term. Its native units remain
unverified. Once integrated cylinder work is available, the output stage combines
work divided by cylinder volume, mechanical loss, boost loss, a displacement/RPM
rate, an RPM-dependent factor and an additional contribution:

```text
power-like output = ((work / volume - loss) - boost_loss)
                    × displacement_rate × 1.2453719e-6 × RPM_factor
                    + additional_contribution
torque-like output = max(power-like output, 0) × 5250 / RPM
```

The factor is approximately 1.18 at 2,000 RPM, 1.12 at 2,500, 1.095 at 3,000,
1.07 at 3,500 and 1.06 thereafter. The native constant is 5250; substituting a
more familiar horsepower/torque conversion constant would change the game.
Intermediate work/loss outputs are computed before the power clamp. Their exact
stores are retained in `work_outputs`.

Final stock-curve conversion, penalties, low-RPM behavior and remaining boost/fuel
branches are incomplete. These outputs should therefore be described as native
solver fields, not a finished engine's verified wheel horsepower.

## What this tells us about tuning

The recovered data path gives bore, stroke, compression, valve size, timing, lift
and airflow a route into cylinder work. That supports reconstructing component
tuning through the original model. It does not yet justify claims such as a
particular cam adding a particular amount of power: the full cycle and finalizer
must first be reproduced.

Continue with [cylinder state and gas exchange](cylinder-cycle.md).
