# What currently prevents original driving startup

The stock inspector now reads vehicle 101, the Ford 32 V-8 Coupe, together with
the installed Drag track. It loads all four tire, spring and shock assemblies,
engine-block dimensions, decoded wheel markers and terrain under each wheel.
Run it from the source repository:

```powershell
.venv/Scripts/python.exe -m tools.inspect_stock_driving "C:/Program Files (x86)/EA Games/Motor City Online" --output build/stock-driving-inputs.json
```

The report remains outside the original installation. It distinguishes recovered
component facts from measured model geometry and the current authored placement.
The latter raises the car until every tire clears terrain; it does not reproduce
original spawn, suspension compression or the original wheel-support flags.

Original initialization is a larger dependency chain. The recorded `0x43a990`
path calls component assembly `0x54e720`, model/geometry setup, owner binding
`0x53a1f0` and final setup `0x53b8a0`. Component assembly also computes aggregate
values before building the engine curve. Binding engine-block mass as total car
mass, or applying marker spacing as an already verified configuration dimension,
would bypass this chain. Those substitutions are deliberately rejected.

The [body numeric initializer](body-configuration.md) now supplies actual
vehicle 101 catalogue configuration: body-base mass 575, wheelbase approximately
2.692, front/rear track approximately 1.4224, front weight fraction approximately
0.4305 and front/rear clearance references approximately 0.28. These appear in
`recovered_body_configuration`, separately from model-marker measurements.
They are original initializer outputs, not completed owner binding or final
assembled mass/inertia. Original semantic validation and body quality remain
outside the bounded comparison.

| Input area | Available now | Still required before faithful startup |
|---|---|---|
| Wheels and suspension | Stock tire dimensions/radius, springs, shocks; decoded marker spacing | Verified owner/configuration dimensions, initial compression, support flags/scales and surface lookup |
| Body and forces | Recovered force consumers and body catalogue initializer | Final whole-car mass, centre of mass, inertia, area/height and initialized transforms |
| Engine and transmission | Engine-block geometry, core dyno reconstruction, recovered consumers | Complete assembled torque table, RPM limits, inertia, gearing/clutch/differential initialization |
| Tires and brakes | Recovered update calculations | Assembled axle curves and coefficients; brake material, capacity, cooling, distribution and initialized state |
| Session and controller | Recovered scheduler/controller order and selected connected stages | Real service/input observations and remaining child implementations on shared state |

`client.stock_driving_state` exposes these facts and a machine-readable missing
input report. `construct_observed_state` requires **every** field of a selected
recovered record, including fields with research defaults. Nested wheel, engine
and brake records must be typed explicitly. Supplying a complete observation
record does not establish its provenance; numeric validation remains in the
recovered calculation. `require_recovered_driving` currently fails with the
remaining startup requirements, so this inspection cannot accidentally launch
the prototype handling as recovered driving.

Evidence: original initialization
`ev_1a903ab2ddcafa04ae6b6038e5b45065d3ac5269d29810fffae5201146d951b8`,
assembly/finalization
`ev_f20d56d975c43fb2f81535392e722376837ccf5bd4bb65eae81fd4724b981024`.
The external asset read verifies data availability and placement queries. It
does not demonstrate an original-equivalent initialized car or a driven race.
