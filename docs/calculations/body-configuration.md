# Catalogue body configuration

`client/body_configuration.py` reconstructs the numeric body initialization
section of `0x54a390`, called by body loader `0x54a2b0` in the `0x54e720`
assembly dispatcher. This gives the startup pipeline actual catalogue geometry
and body parameters rather than model-marker estimates.

The input is a body Physics row with exactly 39 values. The component record
stores mass at `+0x30` and Val1 through Val39 beginning at `+0x3c`. The recovered
owned-component query selects Physics ordinal 1. `stock_body_configuration`
joins StockAssembly → BrandedPart → PartType → Physics using that behavior;
the StockAssembly PhysicsDefault flag is not interpreted as an ordinal.

| Constructed value | Physics input | Configuration destination |
| --- | --- | --- |
| Body mass; initial assembly mass | Mass | `0x1c`, `0x20` |
| Wheelbase | Val2 | `0x2c` |
| Front / rear track | Val3 / Val4 | `0x30`, `0x34` |
| Body front weight fraction | Val34 | `0x40` |
| Front / rear wheel clearance reference | Val31 / Val32 | `0x11c`, `0x120` |
| Body class selector | Val33, truncate | `0x44` |
| Body shape selector | Val7, truncate | `0x48` |

Mass is in the same catalogue mass units used by later aggregation. Geometry
is in the same distance units as the recovered wheel setup (metres). The mass
at `0x20` is a starting accumulator; reporting it as the completed vehicle mass
would be incorrect. The body weight fraction also precedes component-weight
aggregation and does not determine the completed car's COM by itself.

Every other store is retained in the configuration image, including repeated
copies, byte-width flags, zero accumulators, and the two `9.0` constants. Fields
without established physical meanings remain identified by offset. The loader
leaves unrelated configuration bytes untouched. Three integer stores use x87
round-to-nearest-even; other integer and byte stores use the CRT `0x6995b4`
helper, which truncates into int64 and exposes its low 32 bits. These modes
differ for halves and out-of-int32 values; byte stores retain the low byte.

For the separately supplied vehicle 101 catalogue, the body is branded/type
20101, abstract type 20001, Physics ordinal 1. Constructed geometry is wheelbase
approximately 2.692 m, both tracks approximately 1.4224 m, front weight parameter
approximately 0.4305, and both clearance references approximately 0.28 m. Body
mass is 575; this is not the assembled mass. Outputs are float32, so printed
decimal values can differ slightly from these rounded descriptions.

## Verification and limits

`tools/body_configuration_oracle.py` executes original instructions from
`0x54a3c1` to `0x54a594`, including the actual CRT conversion helper, against
the SHA-verified executable. It compares all `0x820` configuration bytes against
the reconstruction using a nonzero initial image. The comparison passes 145
authored cases and the actual vehicle 101 body row: 146 cases with zero byte
mismatches. Fixtures distinguish integer rounding, byte wrapping, repeated
stores, signed zero, and untouched regions. Five unit tests cover the readable
API, stock join, shape validation, and preservation behavior.

The original semantic validator `0x542a00` and the body quality wrapper are
outside this bounded numeric comparison. API shape/finite checks are not a
replacement for original semantic validation. Other component loaders, final
assembled mass, COM/inertia initialization in `0x53a1f0`, and wheel initialization
in `0x53b8a0` still require their own recovered producers. Brake and tire force
parameters are not produced by this body section.

Private supporting evidence: assembly finalizer dossier 196
`ev_f20d56d975c43fb2f81535392e722376837ccf5bd4bb65eae81fd4724b981024`,
startup dossier 125
`ev_1a903ab2ddcafa04ae6b6038e5b45065d3ac5269d29810fffae5201146d951b8`,
the retained physics dispatcher, and conversion-helper dossier
`ev_79b8b4bc38a157029a6a61e89373f46bdd6268fedb51f78b850cfca097a1449a`.
No original code or database rows are distributed with the authored module.
