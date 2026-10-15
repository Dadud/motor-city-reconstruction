# Startup load, balance and brake producers

`client/startup_balance.py` and `native/src/startup_balance.cpp` translate five
original functions used by the owner initializer. All addresses below refer to
main executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
These are recovered calculations, not replacement handling rules. Names describe
their role in startup; exact physical meanings and output units require further
caller/runtime recovery.

| Original entry | Authored interface | Inputs / output |
| --- | --- | --- |
| `0x54a0e0` | `startup_load_coefficient` | Finalized configuration; float32 coefficient at the initializer's store |
| `0x53acc0` | `startup_balance_coefficient` | Configuration including tire-response tables, original alternate-load flag; float32 result clamped to `[-10,10]` |
| `0x53b040` | `startup_brake_balance` | Configuration, brake selectors, tire dimensions and axle coefficients; float32 result clamped to `[float32(0.1),1]` |
| `0x538820` | `brake_diameter` | Original uint32 selector; stored float32 diameter |
| `0x5399d0` | `brake_capacity` | Diameter, material, construction, pressure and auxiliary flag; double-precision intermediate result |

The first coefficient uses mass difference `M = cfg[0x20] - cfg[0x28]`,
height parameter `H = cfg[0x38]`, and `S = cfg[0xfc] + cfg[0x104]`:

```
coefficient = H * float32(0.9090908765792847) * M * float32(9.81)
              / (S - H * float32(0.3181818127632141) * M
                       * float32(0.17121680080890656))
```

Do not rename either mass term or the denominator fields to a particular physical
component without establishing their producers. Zero denominators and nonfinite
observations are rejected by the authored bounded adapter.

The balance producer derives an angle from original `0x6f1430`:
`atan2(wheelbase,33) * 0.15915493667125702`, rounded to float32. It computes axle
loads using finalized front weight fraction and clamps tire-width/template-width
ratios to `[float32(0.9),1.5]`. It calls the recovered primary and secondary
26-knot wheel-response functions, including their actual alternate-load behavior,
then derives the final clamped coefficient. Original intermediate stores matter:
an intermediate transfer calculation remains in x87 registers before its square.
Rounding it early to float32 produces a measurable mismatch.

## Brakes

The diameter selector covers 21 nominal sizes from 8 to 18 inches in half-inch
steps. Unknown uint32 selectors use the original default size. The translation
preserves the actual stored float constants; recomputing sizes from a decimal inch
conversion changes several values by one float32 bit.

The capacity helper squares the half-diameter before multiplying by the remaining
coefficients, in this original order:

```
capacity = (diameter/2)^2 * pi_f32 * float32(16.31012725830078)
           * 2500 * material_factor * pressure
```

Material selectors `0,1,2` use float32 factors `0.85,0.9,0.95`; other selectors
use 1. Construction selector 1 then multiplies by float32 `0.98`, and additionally
by float32 `0.8` when the auxiliary flag equals one. Other construction selectors
do not apply either factor. For example, halving pressure halves the helper result.
It returns a double here because the original caller retains that precision until
a later store. Material multiplication must not be moved before the radius square.

The brake-balance producer uses both axle capacities and original tire radii,
clamps their normalized ratio to `[0.5,1]`, then incorporates mass distribution,
height, wheelbase and axle coefficients. It uses a stored float32 mass-force value
in one calculation while retaining its unrounded value in another. It also retains
one transfer denominator at higher precision. Both distinctions are preserved.

## Verification

`tools.startup_balance_oracle` executes all five complete original functions and
their real wheel-response/brake children in bounded CPU emulation. Its external
database option assembles the supported original stock corpus without publishing
configuration or table data:

```sh
python -m tools.startup_balance_oracle /path/to/mcity.exe --database /path/to/online.mdb
```

The checked corpus contains 54 authored configurations and all eight supported
stock configurations: 372 coefficient calls, 24 diameter calls and 144 capacity
calls. All float32 coefficient/diameter bytes and double capacity bytes match
exactly. Cases include both load modes, width clamps, zero secondary curves,
asymmetric distribution, material/construction defaults and auxiliary behavior.
This is not integrated handling or a complete original initialized vehicle.

The native/Python runner compares 108 configuration scenarios and 168 helper
cases, including double-precision output bits. MSVC and Zig/Clang comparisons pass; CI also
runs the runner on Windows/Linux. The main owner initializer still needs
projected area, shift-curve production and complete state publication.

Private REA dossiers:

- Load coefficient: `ev_c2e5e1bb3d39840217832c05e1914651d0be7284231f7da182f78463d0c29368`.
- Balance coefficient: `ev_7bf836c839bf30af9a8b72d9aaba6bb1606938930985af858fcc738139e5f068`.
- Brake balance: `ev_3ede33b8031391c4a3c7188337ce8111aa4e46460ec616a3044219fc591ed33b`.
- Diameter selector: `ev_414ae2754ef35ecdaca46fe7204dbe094eda3f59e6cd35c146e778cbbe0a469d`.
- Capacity: `ev_71e9d5de5fb4358adc431b1cac95e6f8f9abce28d4f29692e368d2af8dd0a7e2`.
