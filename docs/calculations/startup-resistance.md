# Startup resistance table

`client/startup_resistance.py` and `native/src/startup_resistance.cpp` translate
the complete original `0x53e620` and `0x550ed0` functions in the finite supported
domain. Addresses refer to main executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

The owner initializer calls this producer alongside per-gear force tables and
subtracts its entries before finding shift thresholds. This is one startup table;
it does not establish the complete runtime road-load model. The finalized area
producer and the rest of shift selection remain unresolved.

## Inputs and equation

The table contains 135 entries, with integer index `v` from 0 through 134. The
caller supplies mass `M`, coefficient `C`, projected-area input `A`, and a uint32
surface selector `s`. The exact speed units and physical meaning of `C` still
need caller/runtime verification. Do not substitute a unit conversion.

Write `f(x)` for the original stored float32 constant or store. The helper is:

```
R(s,v) = 0                                     when v < 1
         v * f(0.000096) + f(0.012)             when s = 2
         v * f(0.000072) + f(0.013)             when s = 3 or 5
         v * f(0.000048) + f(0.010)             otherwise

mass_force = f(M * f(9.81))
table[v] = f(v*v*C*A*f(0.5905) + R(s,v)*f(1.1)*mass_force)
```

The original helper returns an x87 intermediate; narrowing it to float32 changes
later table values. The authored helper returns a double, and the table preserves
the mass-force store and final float32 stores. Multiplication and addition order
are preserved under the project's strict floating-point build flags.

For example, with selector 2 and index 10, the helper is approximately `0.01296`.
With mass 1000, coefficient 0.3 and area 2, its contribution is approximately
139.85 and the quadratic contribution is approximately 35.43, before final
rounding. These values illustrate the equation rather than defining new units.
Entry zero is zero. Halving mass halves only the mass-dependent contribution.

## Verification

```
python -m tools.startup_resistance_oracle /path/to/mcity.exe
python -m tools.native_startup_resistance_compare /path/to/mco_startup_resistance_compare
```

Bounded CPU emulation executes complete original functions and the real child
helper: 72 helper calls and 180 tables, covering 24,300 entries. Double helper
bits and float32 table bits match exactly. Sentinels before and after each table
verify its write extent. Cases cover the one-unit threshold, negative and signed
zero speeds, every selector branch and unknown selectors, zero contributions,
and varying mass/coefficient/area. No original bytes or table data are published.

The same corpus matches Python and native outputs exactly under MSVC and
Zig/Clang. CI runs native comparisons on Windows/Linux. Original integrated
vehicle startup and runtime driving are not verified by these comparisons.
Nonfinite inputs/outputs are outside this authored adapter's supported domain.

Private REA dossiers: surface helper
`ev_635538f47c7f729c047db14c444e5b6fac93ce8353d3f794659adca91f43ff13`;
table producer
`ev_0dac06f89e40e220d45f9b5012886e7afc8ef38c9bcb425ff5366aeaaeae9750`.
