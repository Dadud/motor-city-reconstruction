# How Motor City Online's calculations worked

These writeups explain the original calculations recovered so far, alongside
their portable implementations. Start with the engine overview, then follow
the cylinder state and vehicle geometry articles.

| Article | What it explains |
| --- | --- |
| [Engine assembly and dyno](engine-dyno.md) | How component data becomes geometry, valve movement, airflow and sampled engine outputs |
| [Cylinder state and gas exchange](cylinder-cycle.md) | Intake/exhaust boundaries, directional mass transfer, feedback and energy terms |
| [Vehicle motion and road contact](vehicle-motion.md) | Tire dimensions, spring parameters, wheel velocity, body motion and road height |

Each article distinguishes recovered arithmetic from inferred physical meaning
and reconstruction choices. An equation can be established even when the name
or unit of a native field is still unknown. The addresses refer to the analyzed
x86 executable with SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`;
they are virtual instruction addresses, not file offsets or universal addresses
for every game version.

The original executable contains considerably more engine computation than a
single horsepower lookup. That does not establish that its driving loop runs
the entire dyno calculation every frame. The recovered dyno creates sampled
engine outputs; its exact invocation schedule and complete connection to driving
remain to be recovered.

## Reading the equations

`f32(x)` means round and store a value as an IEEE-754 32-bit float. Equations
show the structure of the calculation; the linked Python functions preserve
the more detailed operation order and store boundaries. Decimal constants in
the prose are abbreviated where stated. Replacing an expression with an
algebraically equivalent one can change the result after rounding.

Evidence comes from static reverse engineering and bounded execution of original
instruction ranges in a CPU emulator. Exact comparison means identical stored
float32 results for the tested inputs. It does not establish correctness for
every input, original hardware equivalence, or a complete working physics model.
See [research and verification](../research.md) for coverage and reproduction.

The temporary driving and racing modules are authored development systems.
Their acceleration, grip, 120 Hz stepping and checkpoint rules are not evidence
of the original game's behavior. These articles identify that boundary wherever
it affects the explanation.
