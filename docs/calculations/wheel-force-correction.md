# Wheel force and spin correction

The complete original routine at `0x53e130` operates on four consecutive wheel
records. It reconciles observed spin with projected wheel motion, limits that
correction using existing tire forces, and applies directional clamps. It does
not create the brake force, integrate wheel spin over time, or determine its
coefficients. Those producers remain separate recovery work.

## Observed state

Each record starts at owner `+0x5fc + slot*0x10c`. Relevant fields are projected
speed `+0x10`, spin `+0x7c`, spin adjustment `+0x88`, positive spin scale `+0xbc`,
lateral force `+0xd0`, normal load `+0xd4`, longitudinal force `+0xd8`, contact
byte `+0xec`, and directional-correction byte `+0xc5`. Coefficients at `+0x5c`
and `+0x60` multiply normal load to form two force capacities. Their catalogue
mapping and physical units are unresolved. These offsets describe research
evidence; the public API uses typed observations rather than offsets.

Control observations come from owner `+0xa90`, `+0xa94`, `+0xa6b`, `+0xa69` and
`+0xa88`. The service and parking descriptions reflect observed branch behavior;
they do not establish a recovered mapping from keyboard/controller input.

## Calculation

Write `F(x)` for an original float32 store. For a contacting wheel with nonzero
normal load, projected speed `v`, spin `s`, scale `r`, old adjustment `a`, lateral
force `y` and longitudinal force `x`, compute:

```
m = F(-((s - v/r)*32 + a))
z = F(-(s*32 + a))
q = F(sqrt(y*y + x*x))
c = F(primary_coefficient * normal_load)
d = F(secondary_coefficient * normal_load)
t = max(F(d*F(0.15)), min(c, F(c-abs(x))))
```

If `q > c`, the new adjustment is
`F(a + max(0, F(d-abs(x)))*m/q)`. Otherwise, negative longitudinal force with
positive service control, negative longitudinal force on either rear slot with
parking control, or positive longitudinal force with positive other control
uses `F(a+t*m/c)`. All remaining contacting cases use `F(a+m)`.

When the wheel correction byte is set, direction mode at least two and a clear
override byte imposes a lower bound `z`. Mode zero imposes an upper bound `z`.
Mode one leaves the calculated adjustment untouched. The mode producer is still
external to this routine.

For noncontacting or zero-load wheels, the adjustment remains unchanged. Spin
decays by `F(s*F(0.999375))` only when longitudinal force is exactly zero. A
nonzero force preserves spin even without contact. This decay is per invocation;
no timestep or rate is inferred from the constant.

For example, a contacting wheel with `v=10`, `s=20`, `r=0.5`, `a=3` and zero
tire forces has no spin mismatch. Its new adjustment becomes zero while spin
remains 20. The routine changes the adjustment, not spin, on this contact path.

## Verification and limits

The bounded CPU oracle executes the complete original routine with no helper
substitutions and verifies every other owner byte stays unchanged. A synthetic
matrix of 2,880 cases covers service/other control signs, parking, direction
modes 0/1/2/255, override, contact masks, correction flags, zero load, and positive,
negative, zero and capacity-exceeding longitudinal forces. All compared float32
outputs matched exactly. This is instruction-level evidence on supplied state,
not an integrated driving or original-runtime test.

The authored API rejects nonfinite values, nonpositive spin scale, negative
loads/coefficients and a zero-capacity correction division. Original malformed
or unsupported state behavior is not adopted as a public API contract.

Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Private executable bytes and disassembly are not distributed.
