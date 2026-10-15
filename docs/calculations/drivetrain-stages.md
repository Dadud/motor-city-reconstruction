# Driving clutch, coupling and wheel torque

The Python research runtime now executes all eight children of the original
engine driving dispatcher together with recovered loads, environment, brakes and
tire forces. This closes the five previously supplied numeric drivetrain bodies;
it does not close the stock-car initialization, terrain, collision or playable
driving gates. The five bodies now also have a C++20 port in
`native/src/drivetrain_stages.cpp`.

Authored implementation: `client/drivetrain_stages.py`. Shared-state adapter:
`client/driving_drivetrain.py`. Defaults in the research records are synthetic
observations, never verified stock-car initialization.

## What each calculation does

The dispatcher calls these bodies in their original order, around its separately
recovered torque, condition and thermal children:

| Routine | Inputs and resulting behavior |
| --- | --- |
| `0x545ec0` clutch | Moves engagement toward release or engagement, then shapes its gain; respects the catalogue mode, override byte, damage and previous coupling resistance |
| `0x546130` preparation | Reads previous rotation, averages rear radii for acceleration, finds maximum contacting driven-wheel rotation and derives engine coupling resistance |
| `0x546ad0` request | Accumulates a bounded component-condition request from movement and catalogue modifiers; this is separate from clutch engagement |
| `0x547c60` distribution | Applies coupling gain, gearbox drag, ratio/loss, damage, final drive and per-wheel distribution; emits required damage/component calls |
| `0x548050` application | Converts wheel torque into longitudinal force and spin adjustment, with per-wheel service gates, reverse and speed/RPM limits |

### Clutch

The nominal engagement step is `1 / clutch_steps`. In the non-assisted branch,
coupling resistance above 200 reduces the step by 0.3 when damage is below 0.5 or
the bypass is active. Damage at least 0.5 instead multiplies the nominal step by
1.8. Engagement is clamped to `[0,1]`.

Between the endpoints, the shaped gain is `1 - (1 - engagement)^4`. For example,
engagement 0.5 gives gain 0.9375 before the assisted-mode modifier. Assisted mode
can multiply the gain by a clamped factor between 1 and 2.5 using the ratio of
reference rotation to engine angular speed. The release conditions also differ
between assisted and non-assisted configurations; they are retained separately.

### Coupling and wheel acceleration

Wheel acceleration is the observed local acceleration divided by the mean rear
wheel radius, clamped to `[-100,100]`. The original then derives rotation using
the active gear and final-drive ratio. With no contacting driven wheel it
**preserves the previous driven-speed field**, rather than resetting it to zero.
Neutral gear has a distinct reference-rotation update.

Coupling resistance is stored as:

`(engine_angular_speed - reference_rotation) * (gear_inertia + inertia_sum)
 * engagement * engagement * 32`

The original retains the unrounded inertia sum for this product. A memory store
visible in the assembly does not always consume the continuing x87 value.
The factors of 32 describe recovered arithmetic, not an independent measurement
of scheduler frequency. Physical units of several component fields still need
confirmation; the API preserves their observed values.

### Distribution and force

Positive effective torque, or fully engaged coupling, produces transmitted
torque equal to gain times effective torque. Otherwise a low-driven-speed branch
supplies 10 below 25 and zero at or above 25. Neutral produces zero output; a
nonzero signed hold counter also produces zero and decrements the counter.

For the normal active-gear branch:

`output = (transmitted - abs(drag_speed) * gear_inertia) * gear_loss * gear_ratio`

Over-capacity output delivers damage operation 13, followed by component
operation 25. Those calls are explicit consumers and may change damage before
the subsequent damage multipliers read it. Each damage field at least 0.25
multiplies output by `1 - (damage - 0.25)^2`.

Each wheel receives:

`torque = (output - abs(final_drive_acceleration) * inertia_sum)
 * distribution * final_drive * efficiency`

For an enabled driven wheel, force is
`(torque - abs(wheel_acceleration) * wheel_inertia) / radius`, with a sign change
for reverse gear. Contact, normal load and RPM/speed gates control accumulation
into longitudinal force. Non-driven wheels have a separate acceleration/inertia
subtraction. The per-wheel service gate is queried separately, not cached once.

## Shared aliases and control mode

Wheel distribution also supplies the brake coupling-inertia multiplier. Gear
tables must be shared with load, brake and wheel-spin consumers. The RPM gear
index and selected control byte are distinct observations. Engine effective
torque and catalogue curve torque are also distinct.

Original mode predicate `0x43b570` returns one for vehicle flags `0x200`, `2` or
`0x10`; otherwise it returns the policy setting only for the current local
vehicle. `client/driving_mode.py` preserves that rule. The controls bridge now
requires an explicit predicate callback because vehicle identity cannot be
inferred from its separate control-rate `local_player` field.

Connecting these stages exposed two earlier rounding errors. Rolling resistance
stores the combined axle/coefficient product rather than rounding each input.
Wheel projection retains the yaw conversion until it stores the half-yaw and
lever products. Python and C++ now preserve those stores. Their original-function
corpora each compare exactly: 1,344 resistance cases and 1,296 projection cases.

## Verification and limits

The native port matches every state field and ordered call on 3,377 Python
cases with zero error: the original-function corpus plus sixteen damage-mutation
and mode-policy scenarios and one signed hold-counter wrap boundary. It is built
into `mco_core`; Windows/Linux CI includes its comparison runner. This local run
was Windows. A complete native shared-owner driving adapter remains required.

The [recovered gear-table producer](gear-binding.md) now supplies the speed and
inertia arrays in an additional integrated corpus. This exposed two more
intermediate-store errors in force application and yaw accumulation, now fixed
in Python and C++. Earlier measurements below describe the initial supplied-table
corpus; the gear-binding writeup records current producer-bound results.

Source: original `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence, in the table order above:

- `ev_ac8a7b22e43876209038de981a29d7dc8fba43b47bd46bac1134b0b84cd5d9bc`
- `ev_b459353a5e84ff7e5e7e7b0acf73a00899868bf2b449d3f19f477460d4db7872`
- `ev_c135a11a58910830fc0b7b137c6429bf9a37a469e265740cb0ca38812fb434d2`
- `ev_11a8a469614f1244295833a569cefb43c1c6630ec019813c5551fc57c74cef92`
- `ev_93403e5c05356ca6743da9ed2ef94512b7911e8bdde41375004c6462165f2dd8`

Control-mode evidence:
`ev_c822bda9f9fcc1ad462223a8a073dcd8420431b09bbd01bbd405c22c497f9298`.

```powershell
python -m unittest tests.test_drivetrain_stages tests.test_driving_controls
python -m tools.drivetrain_stages_oracle '<original-install>/mcity.exe'
python -m tools.driving_drivetrain_oracle '<original-install>/mcity.exe'
python -m tools.driving_drivetrain_oracle '<original-install>/mcity.exe' --actual-support
```

On Windows, the five-body whole-owner/configuration comparison passes 3,360
cases: 1,920 clutch, 144 preparation, 288 request, 864 distribution and 144 force
application. After the denominator-store correction, maximum absolute error is
`0.00000095367431640625`, with the unchanged
comparison tolerance `max(0.0001, abs(original) * 4e-7)`.

The integrated supplied-contact run passes 144 scenarios / 288 repeated ticks,
including 1,296 recovered force calls, 288 engine/brake ticks, 17 component
mutation ticks and 576 drivetrain service/effect observations. Maximum owner
error is `0.000244140625`; maximum ordinary effect argument error is
`2.9802322387695312e-8`.

The integrated actual-support run passes another 144 scenarios / 288 ticks:
192 supported and 96 low-support, 1,152 terrain-query handoffs, 864 recovered
force calls, 192 engine/brake ticks and 384 drivetrain observations. Maximum
owner error is `0.00030517578125`, with zero effect argument error. Neither run
needs the existing conditioned radius or secondary-component exceptions.

These are bounded executions of original code with synthetic inputs. Terrain
projection, remaining preparation, gear services, service queries and component
implementations remain supplied. Mutation delivery within arbitrary wheel loops
is not established. No original-client driving capture, complete stock startup,
collision race, Linux gameplay or live fan-server race is claimed by these tests.
