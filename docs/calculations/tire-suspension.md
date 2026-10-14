# Tire and suspension parameters

The recovered tire and suspension work supplies physical dimensions, native
validation ranges and axle roll parameters. It does not yet recover slip curves,
vertical spring forces, shock damping laws or stance placement beyond the tire
radius allowance documented in [vehicle motion](vehicle-motion.md).

## Tire dimensions from catalogue physics

Tire records store width in millimetres, aspect percentage and rim diameter in
inches. Consumers at `0x53a1f0` and `0x5a39d0` compute:

```text
sidewall_metres = width_mm × 0.001 × aspect_percent × 0.01
radius_metres   = rim_inches × 0.0254 / 2 + sidewall_metres
```

The portable [tire interpretation](../../client/tires.py) preserves those
constants and exposes `stance_adjustment = max(radius - 0.37, 0)` from the
placement path at `0x53bf20`. That adjustment shifts rendered stance for
larger rolling radius; it is not a grip or load term.

Grip, compound, pressure, temperature and longitudinal/lateral force laws remain
**unknown** until separate evidence is recovered. Comparison harnesses should
pass recovered radii into wheel contact queries rather than inferring radius from
mesh bounds.

## Spring and shock records

Springs and shocks load from component physics with native validation ranges
enforced in [suspension.py](../../client/suspension.py):

| Part | Mass (kg) | Value 1 | Value 2 | Notes |
| --- | --- | --- | --- | --- |
| Spring | 2–30 | rate 10 000–120 000 | style 0–3 | style is rounded to integer |
| Shock | 2–10 | coefficient 0.2–0.4 | length 0.1016–0.4064 m | length is finite travel metadata |

The shock coefficient's conversion into damping force is **partial**. The code
stores the coefficient and length but does not claim a `F = c × velocity` law
matches the executable.

## Axle roll contribution (not ride height)

At `0x54a840`, each spring adds one axle roll parameter:

```text
arm = track_width × (0.76 front, 0.68 rear)
roll_contribution = arm × spring_rate × arm × 0.0087265
```

The loader accumulates this on the left-front or left-rear attachment only,
once per axle. Doubling by summing both wheels on an axle would inflate the
parameter. Track width enters quadratically through `arm²`.

This term is a **response parameter** used during component aggregation, not the
instantaneous vertical force at a compressed wheel. Full suspension integration
requires recovered compression, droop, anti-roll coupling and per-frame force
application evidence that is not yet wired into the driving loop.

## Stock vehicle simulation inputs

[simulation_inputs.py](../../client/simulation_inputs.py) collects per-wheel tire
radius, spring rate, shock coefficient and shock length for catalogue stock
cars, together with engine mass/bore and the recovered motion step constants
(`1/32` simulation, `1/64` pose, `1/48` support look-ahead). This bundle
feeds comparison harnesses and future native integration; it does **not** replace
the prototype [driving model](../../client/driving.py).

## Worked example (225/60 R15, front spring)

```text
width_mm = 225, aspect = 60, rim = 15
sidewall = 225 × 0.001 × 60 × 0.01 = 0.135 m
radius   = 15 × 0.0254 / 2 + 0.135 = 0.3255 m
stance_adjustment = max(0.3255 - 0.37, 0) = 0

spring_rate = 45000, track_width = 1.5 m (front)
arm = 1.5 × 0.76 = 1.14 m
roll_contribution = 1.14 × 45000 × 1.14 × 0.0087265 ≈ 510.3 (native f32 path)
```

Verify the roll term with unit tests on `Spring.roll_contribution`; verify
radius with catalogue tire fixtures. Do not treat the roll number as Newtons
without further evidence.

## Open questions

- Shock coefficient to damping force mapping and any speed-dependent scaling.
- Whether style selects discrete spring curves or rendering-only variants.
- Per-wheel ride height, camber/toe from customization and nested components.
- Connection from roll parameters to the active force integrator during driving.

Until those are recovered, fan-server garage loading and component valuation can
use tire/suspension metadata; online race handling must not be claimed equivalent
to the original client.
