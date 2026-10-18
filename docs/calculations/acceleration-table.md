# Original startup force and acceleration tables

`startup_force` translates the complete bounded helper at `0x538660` and
`acceleration_table` the complete 112-sample producer at `0x5384f0` from
executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
The helper calls the recovered torque interpolation at `0x548f00`; it does not
substitute a constant torque or the prototype driving model. The producer
rewrites only the two stored output ranges of the caller's startup record and
preserves every other byte.

REA evidence: helper
`ev_b69818b038c26ba632d54a4e83f9376006f68ad1c81c7be87d9da1f7e3ff08e3`; producer
`ev_57d0da54c52a8b9ee7c6491373e39b2c225b025ff1a196372cfbc18a2cc6a238`.
The complete retained dossiers and binary instruction bytes remain private.

## Helper fields and calculation

The configuration supplies signed idle and maximum RPM at `0x6c` and `0x70`,
26 torque knots beginning at `0x80`, mass at `0x20`, per-selector gear ratios
at `0x334`, the final-drive factor at `0x374`, correction magnitudes at `0x4d8`
and `0x4f4`, an easing gate at `0x68c`, secondary-force gates at `0x3e0` and
`0x3e4`, and a drive factor at `0x6e8`. The startup record supplies
per-selector factors at `0x64`, RPM increments at `0x2c`, shift thresholds at
`0xac`, and a positive denominator at `0x104`.

Let `S(x)` mean a binary32 store. Each decimal constant below represents its
stored binary32 value, promoted to binary64 for arithmetic; the original
startup x87 control word selects 53-bit precision.

```
fraction = S(rpm / maximum)
angular = S(rpm * 6.2831854820251465)          # stored binary32 two pi
size = field_4d8 + 1                           # nonnegative correction range
deduction = S(size * 4 * fraction * 60000 / angular)
loss = clamp(deduction, 0, S(size * 10))
effective = max(0, S((torque(rpm) - loss)
                     - (field_4f4 + 1) * fraction * 2 * 60000 / angular))
if gate_68c != 0 and 0 <= sample <= 10:
    t = sample * 0.1
    effective = effective * ((1 - t) * t * t * t * 1.5 + 1)
ratio = gear_ratio[selector] * final_drive
result = (record_factor[selector] * drive_factor * effective)
         / (ratio * ratio * 0.0015 + 1) / denominator   # binary64, not stored
```

The sixth ABI argument is passed by the original callers but unused inside the
helper; the translation keeps it as an observation parameter only. At
`sample == 10` the stored binary32 `0.1` leaves `t` slightly above one, so the
easing factor is slightly below one instead of exactly one — retained, not
corrected.

## Producer

`acceleration_table` walks samples 0–111. It advances the increment/threshold
index (starting selector two) whenever `threshold[index] < sample` and rejects
schedules that would exceed eight selectors. Each sample clamps
`rpm = round(min(12000, max(idle, sample * increment[index])))` with the
original's half-to-even rounding, runs the helper, and stores `S(force / mass)`
— zero when the force is nonpositive — for the primary range at `0x128` and,
when both secondary gates are positive, an eased secondary result at `0x2e8`.
Every byte outside `0x128..0x4a7` is preserved bit-exactly.

## Producer caller and record provenance

Ghidra xrefs give the producer exactly one caller: the owner-binding
initializer `0x53a1f0`, at call site `0x53ab60`; the helper `0x538660` is
called only inside the producer itself. REA evidence: producer xrefs
`ev_16cd64b02b271421cb1bd42d03aab93f971d71c2606418531422bcf913e5e87d`; helper
xrefs `ev_8d17dc67b018da4e2aefe26037d12753d178d1e6998cff4de057fa9831a3d238`;
caller pseudocode
`ev_5c9591f8b4668bcf8eeaf5c7c056cdf0b399b3df8d5b0825b55f34da1efc325c`.

The observed record production, per gear: run the recovered gear-force table
`0x53b260` for the gear and its successor, run the recovered startup-resistance
producer `0x550ed0`, subtract resistance from both gear tables clamping
nonnegative, and locate the crossing sample between the adjusted curves by
linear interpolation over the RPM increments (scaled by 0.98 below the top
gears). A crossing is rejected unless its RPM reaches `(idle+max)/2`; without
a crossing, gear two falls back to 7/10 and the others to 3/4 of an owner
maximum-RPM field, divided by the gear's RPM increment. After the gear loop
the code calls `FUN_005384f0` with the configuration pointer at owner `+0x1c94`
and the stack record, then copies the whole 0x4a8-byte record into the owner at
`+0x17ec`.

Instruction-level review of the caller listing pins the record layout. The
record base is `EBP-0x4d8` at the call site (Ghidra's `local_4dc` name is four
bytes off). Each array holds all eight gears while the producer consumes gears
two through seven, so producer index `i` reads caller slot `i+2`: speed-per-RPM
increments from the recovered gear-table producer `FUN_00539fe0` at `0x24`,
gear factors `factor_354*final_drive*ratio` at `0x64`, and shift thresholds at
`0xa4` (`-10000` for gears zero/one, crossing sample counts otherwise, `12000`
for the top gear). Record `0x104` is the rear tire radius, the same
`width*0.01*aspect*0.001` rim formula as the gear-force radius, and serves as
the startup-force denominator; `0x100` holds the front radius. Remaining
prefix scalars at `0xc4..0x124` come from the recovered suspension producers
`0x54a0e0`, `0x53acc0` and `0x53b040` plus rolling-resistance arithmetic.
Translation and whole-call comparison of this record-production section is the
next startup increment; its four callees are all already recovered.

## Exactness and verification

The assembly matters here: the helper's final division is not rounded to
binary32 before the caller's store, the loss upper bound is a separate store,
and the producer's rounding happens after clamping. The supported authored
interface requires complete records, positive bounded maximum RPM, denominator,
mass and idle, selector 0–7, and an ascending threshold schedule within eight
selectors; it rejects unsupported values rather than emulating original
malformed-input behavior.

The original-executable oracle runs the complete producer and the real original
helper with its real torque-lookup child. It launches no PE entry point and
implements no Windows imports. Its corpus covers three masses, three correction
regimes, both easing gates and secondary gates — 36 producer calls and 8,064
stored samples — plus 720 helper calls across RPM bounds, selectors, sample
edges (including 0, 10 and 10.001) and the unused sixth argument. It checks
every output bit, surrounding sentinels and unchanged input records.

Verification commands:

```
python -m tools.acceleration_table_oracle "<original-install>/mcity.exe"
python -m unittest tests.test_acceleration_table
python -m tools.native_acceleration_table_compare "<build>/mco_acceleration_table_compare.exe"
```

This demonstrates the complete bounded producer and helper, not integrated
vehicle startup: the authentic caller that owns the record, the upstream field
producers and the connected driving tick remain under recovery.
