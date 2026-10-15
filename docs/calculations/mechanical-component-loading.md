# Mechanical component loading

The reconstructed startup now has seven complete component loaders in Python and
C++: engine block, transmission, rear end, wheel rims, springs, shocks and brakes.
They retain original validation, rounding, mass accumulation, configuration writes
and component quality. They do not complete vehicle assembly or start the driving
model. Tire templates, remaining engine/auxiliary/cosmetic components, grouping
quality updates, geometry/display preparation and full assembly orchestration
remain required.

## Source and scope

Separately supplied `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

| Behavior | Original function | REA/Ghidra evidence |
|---|---|---|
| Mechanical field copy | `0x52c2e0` | `ev_d47ee6ad69579878858281d8dcbeb1f3fb4eac79e110519c100c1bd4e37eff09` |
| Selection and pairing | `0x52c550` | `ev_95a70e36c1f8ee50b80aa6439f354bb9fe05fce107a3e13b8d634ac17fe33670` |
| Engine block | `0x54a5a0` | `ev_5961bea9d90c4ae9de2560d398f9fce08d3440b25248d750edde2dedbc3116d5` |
| Transmission | `0x54d080` | `ev_93dbce9097f5df211e3a23efb5bb67664850b11c62a7eb033d23733fb1f59d57` |
| Rear end | `0x54d2f0` | `ev_69a1352a82d84e9222283060d0d795a6e871e8aa15c887dcaed58886c04eb4b6` |
| Wheel rim | `0x54d420` | `ev_cd2faec80f4fafb9508b6815d51b4186614678850768585363a25307de2ca1b4` |
| Spring | `0x54a840` | `ev_5619b92e176cb3295c7b474fd8e47f0ba251c555318071f8774b01d0712e7c35` |
| Shock | `0x54a9a0` | `ev_8c1155d96a8dfed3f7fc1dc411516a170bad0c51925aef917f767deec035330f` |
| Brake | `0x54ab30` | `ev_9f44843fa16f915df930af065abc955bfeff43f8f905bb770a0ee24ae99e588c` |

These are authored reconstructions from shipped instructions, not recovered
original source. Original bytes, decompiler output and private captures are not
distributed. The raw intermediate/configuration adapters are internal research
interfaces, not mod interfaces or network packets.

## From catalogue or owned inventory to individual components

The physics copy moves a 1,596-byte inventory intermediate into a 2,436-byte
mechanical record. It copies the mass, all fifty stored numeric values, header
counts, and a bounded prefix of up to eight text slots. The values are copied
even when their header count is zero; the consuming loader decides whether the
count is acceptable. Text count selects a prefix, not a compact list of nonempty
strings.

Damage and wear conversion uses unsigned 32-bit observations. The original scales
damage by the float32 constant 0.01 and wear by 1,000. It also scales the signed
maximum-wear metadata by 1,000. Preserving that distinction matters for malformed
or boundary records; the conversion does not clamp a negative signed bit pattern
to zero.

The source's paired flag controls expansion, independently of its abstract type:

| Source attachment | Paired output attachments |
|---|---|
| Front (10) | 1, 2 |
| Rear (11) | 3, 4 |
| Zero | 5, 6 |
| Other | Original attachment unchanged |

Unpaired records retain their original attachment. Entries without a branded
part are skipped. Thus the Ford 32 V-8 Coupe's 45 stock entries become 57
mechanical records. The portable result retains source indices instead of native
linked-list pointers. Geometry filenames, pictures and display formatting in the
middle of `0x52c2e0` are explicitly excluded from the physics-copy implementation.

## Original mass and response rules

All seven loaders preserve float32 mass accumulator stores. Their component mass
uses the original mechanical mass unit, documented as kg by the catalogue
component interpretation. Several rules distinguish total mass from axle-group
slots used by the [weight finalizer](assembly-finalization.md):

- A rim contributes its full mass to both the whole-car and existing secondary
  accumulator. Spring/shock contributions use half mass for the latter.
- Each brake contributes `max(component_mass, 4)` to those accumulators while
  retaining the actual component mass in its axle slot. For a two-unit brake,
  total mass rises by four, and the stored axle component mass remains two.
- The spring roll contribution runs only for attachments 1 and 3, once per axle.
  With track width `T`, rate `K`, and axle constant `a` (0.76 front, 0.68 rear),
  it adds `(T*a) * K * (T*a) * float32(0.0087265)` to the existing roll value.
  The arm remains unrounded in the x87 register through the multiplication.
- Spring loading leaves component quality unchanged. The enclosing dispatcher
  resets it to one before calling the loader. Other recovered loaders calculate
  quality themselves; omitting that reset would leave new spring records at zero.

Core duty-dependent quality is 0.75 for rounded duty zero, one for duty one,
two for duty two and four for duty three. Engine materials and brake materials
have their own original tables. Brake material also selects the original
225/300/375/450 capacity parameter; its complete physical unit is not established
by this loader alone.

## Transmission and engine startup

The transmission copies eight ratios and eight loss coefficients into both its
component region and the shared tables consumed by [gear binding](gear-binding.md).
Its validation counts nonzero ratios plus one, and compares that with the declared
entry count using truncation. These entries include reverse and neutral; the
declared count is not the number of forward gears.

The installed stock Ford produces five entries: ratios `2.5, 0, 2.5, 1.18, 1.0`,
with a final drive of approximately 4.1 from the rear-end loader. The zero ratio
is retained. The remaining ratio/loss slots remain as copied from the actual
record. No guessed transmission is supplied for an unsupported part.

The engine loader initializes idle/maximum placeholders to 500/7,000 and clears
the original 100-byte curve region. It does not create the final torque curve;
the subsequent original engine-curve finalizer must produce that data before
driving. Original nearest-even validation and truncating stores are distinct:
for example, rounded cylinder validation can accept a fractional observation
whose subsequent stored integer is truncated. The ports preserve this behavior.

Each loader returns original status zero for success, one for wrong value count,
or two for rejected semantics. For these seven functions, such rejections precede
mutation and preserve both images. This is not a universal rule for unrecovered
loaders. Finite-value, buffer-size and text-termination safeguards are authored
boundaries; arbitrary NaN behavior is not claimed recovered.

## Verification and remaining gaps

The current checks establish:

- Mechanical numeric copy: 120 exact original cases across all 2,436 output bytes;
  geometry/display instructions are skipped with an explicit register handoff.
- Original pairing dispatcher: 42 cases of selection, call ordering, allocation
  stride, native links and source vehicle index. Its field-copy callee is replaced
  by an inert callback, separately from the numeric-copy comparisons. The original
  zero-emission underflow path is excluded; the authored API safely returns empty.
- Complete engine loader: 1,201 original cases, including the installed Ford block.
- Other six complete loaders: 1,002 original cases, including eighteen installed
  Ford wheel/driveline parts. All configuration/component bytes and statuses match.
- Nineteen selected Ford loader calls in their original relative dispatch order:
  every resulting configuration/component image matches original execution.
  Other loaders are skipped, so this is a partial assembly comparison.
- C++ ports: 2,184 authored original-comparison cases match Python exactly.

The Ford comparison uses actual catalogue rows with explicitly authored zero
damage/zero wear and temporary fixture IDs. It does not claim those IDs identify
server inventory, reproduce an owned modified car, or demonstrate original-client
runtime driving. Its partial mass accumulator is not total vehicle mass, and it
must not be passed to finalized owner binding as a complete car.

Repeatable local commands:

```powershell
python -m tools.mechanical_parts_oracle '<game>/mcity.exe'
python -m tools.mechanical_pairing_oracle '<game>/mcity.exe'
python -m tools.mechanical_engine_block_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.mechanical_loaders_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.stock_mechanical_oracle '<game>/mcity.exe' '<game>/data/db/Online.mdb'
python -m tools.inspect_stock_mechanical '<game>/data/db/Online.mdb' --damage 0 --wear 0
python -m tools.native_mechanical_loaders_compare build/native-check/mco_mechanical_loaders_compare.exe
```

The native authored corpus runs in Windows/Linux CI without original assets. The
actual-catalogue/original-execution checks remain local. Faithful driving still
requires all component producers, the complete assembly pass, startup geometry
and owner binding, and integrated original-client runtime comparisons.
