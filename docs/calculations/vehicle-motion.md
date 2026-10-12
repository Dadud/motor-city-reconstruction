# Vehicle motion, dimensions and road contact

The recovered vehicle work includes dimensions, component parameters, wheel-point
velocity and motion increments. Complete tire forces, suspension response and
collision response are still missing. This article deliberately separates those
recovered calculations from the temporary driving model.

## Tire size changes physical radius

The tire record stores width in millimetres, aspect percentage and rim diameter
in inches. Recovered consumers at `0x53a1f0` and `0x5a39d0` lead to:

```text
sidewall_metres = width_mm × 0.001 × aspect_percent × 0.01
radius_metres   = rim_inches × 0.0254 / 2 + sidewall_metres
```

A synthetic 225/60 R15 tire therefore has a 0.135 m sidewall and a 0.3255 m
radius. These are physical dimensions, rather than dimensions guessed from the
rendered mesh. The original placement calculation at `0x53bf20` includes an
extra allowance `max(radius - 0.37, 0)` for larger tires. The
[portable tire interpretation](../../client/tires.py) preserves that value.

This does not recover grip. Width, compound, slip, load sensitivity and force
response require their own evidence before handling can be claimed equivalent.

## Springs contribute an axle roll parameter

The component interpretation has recovered spring rate/style/mass and shock
coefficient/length/mass, with native validation ranges. At `0x54a840`, a spring
adds an axle contribution with this structure:

```text
arm = track_width × (0.76 for front, 0.68 for rear)
roll_contribution = arm × spring_rate × arm × 0.0087265
```

The loader accumulates it on the left-front or left-rear attachment, once per
axle. Summing the same contribution for both wheels would double it. Since the
arm is squared, changing track width affects this parameter quadratically.

It is a response parameter, not the complete force at a compressed wheel.
The code does not establish that an ordinary `force = spring_rate × compression`
formula reproduces the game's vertical response. The shock coefficient's
conversion into damping remains unresolved. See
[suspension.py](../../client/suspension.py).

## Wheels have different velocities during rotation

The vehicle model provides wheel attachment centers. For a wheel's world lever
arm `r` relative to the center of mass, rigid-body motion gives:

```text
wheel_velocity = body_linear_velocity + angular_velocity × r
```

The recovered contact calculation uses this cross product and converts native
angular storage from turns per second to radians per second. The portable
[wheel helper](../../client/contact.py) accepts radians per second directly.

For a synthetic lever arm `(1, 0, 2)`, world angular velocity `(0, 1, 0)` and
body velocity `(0, 0, 10)`, the rotational part is `(2, 0, -1)` and the wheel
velocity is `(2, 0, 9)`. A wheel can therefore experience lateral motion even
when the center of mass has none. This calculation is a foundation for wheel
slip; the game's final slip-to-force law has not yet been reconstructed.

## Velocity and pose use distinct increments

Recovered active branches update linear velocity at `0x540c30` and angular
velocity at `0x53c140` using a factor of `1/32`:

```text
velocity_next = velocity + acceleration / 32
```

The pose update at `0x520450` uses `1/64` for position and angular increments.
A terrain support predictor at `0x53d320` uses `velocity/48` for its look-ahead
position. Those constants do not prove a single 32 Hz or 64 Hz game loop.
Actual call scheduling, gating and substep ordering still need recovery.

The body rotates around its center of mass. In the portable column-vector
convention the incremental rotation is composed as:

```text
R_next = Rz × Ry × Rx × R
world_COM_next = world_COM + velocity / 64
body_origin_next = world_COM_next - R_next × local_COM
```

Updating the body origin as if it were the center of mass would be wrong for
an offset center of mass. The native row-vector layout requires the corresponding
convention conversion. [motion.py](../../client/motion.py) implements the
recovered active arithmetic; inactive-motion gates, collision response, periodic
matrix repair and x87 extended-precision equivalence are outside that helper.

## Finding road height under a wheel

The decoded FRD track contains spatial references to surface quads. Native
surface lookup and sampling at `0x42e760`/`0x42eed0` and
`0x42dc50`/`0x4b71a0` establish the core selection and plane calculation.
The reconstruction traverses spatial candidates, tests projected containment,
then chooses the applicable triangle of a quad.

Given a point `b` on the triangle and its normal `n`, height at horizontal
position `(x, z)` comes from the plane equation:

```text
y = b.y - ((x - b.x) × n.x + (z - b.z) × n.z) / n.y
```

The normal is normalized for callers. Degenerate and effectively vertical planes
cannot supply a usable road height. This establishes geometry beneath a wheel;
it does not establish collision impulses or suspension force.

Two optional behaviors in [track_surface.py](../../client/track_surface.py)
are authored additions: choosing the surface nearest a supplied reference height
and allowing edge tolerance. The default retains native candidate order and
exact containment. The additions help the current prototype distinguish road
levels and tolerate tiny edge discrepancies; they must not be attributed to
the original lookup.

## What the current driving prototype adds

The temporary `driving.py` uses a bicycle steering model, authored acceleration,
drag and lateral limits, 120 Hz fixed steps, and terrain-following placement.
It stops when wheel support is absent. `racing.py` constructs checkpoints from
road slices and supplies authored timing rules. The conservative spawn helper
raises the car to clear all four supports; it does not simulate settling springs.

Those systems make input, rendering and race development possible while native
forces are recovered. Their behavior is not the specification for the original
game. Matching Motor City Online requires replacing their force and rule choices
with verified original behavior and testing the resulting connected simulation.
