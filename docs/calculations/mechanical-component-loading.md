# Mechanical component loading

The reconstructed startup now has thirty-two complete component loaders in Python
and C++: engine block, head, camshaft, crankshaft, rods, pistons, valve train,
transmission, rear end, wheel rims, springs, shocks, brakes, tires, intake manifold,
carburetor, air cleaner, exhaust manifold, pipe, muffler, cooling, electrical and lubrication,
plus the body, six accessory kinds and two axle-bar kinds.
They retain original validation, rounding, mass accumulation, configuration writes
and component quality. The Python [complete assembly](mechanical-assembly.md)
matches eight stock configurations. Other engine/auxiliary/cosmetic families,
geometry/display preparation, native orchestration and driving remain open.

The upstream `0x52c6b0` scratch-buffer allocation is also translated in
`create_mechanical_slot_buffer`. For `n` slots it requests `n * 0x1308` bytes,
which holds two `0x984` records per slot; the original per-record initialization
writes are fully overwritten by its final clear. Five original calls cover
empty input, successful sizes, and a stubbed allocation failure. The pool
allocator itself remains a platform service. Reproduce with
`tools/verify_mechanical_slot_buffer.py <mcity.exe>`.

The presentation pass of `0x52c2e0` is now translated separately by
`transfer_mechanical_presentation`. It copies the eight-byte model key, formats
literal dotted names or a prefixed `.viv` path, transfers the fixed-width
manufacturer field, and forms the bounded `brand name` display text. The path
prefix comes from row 15 of the table initialized by `0x530790`, using the
shipped pointer/type rows and original formatter with synthetic registry
services. Four controlled complete-original calls and all 57 expanded
mechanical records from installed stock vehicle 101 match the complete
0x984-byte destination image. Actual Windows registry results and drive scans
remain platform services. Reproduce the comparisons with
`tools/verify_mechanical_presentation.py <mcity.exe> --data-root <game-root>`.

The integrated stock-owner verifier then feeds those results through original
`0x52c550`, `0x52add0` and the worker's missing-driver fallback `0x52c190`:
installed vehicle 101's 45 DBAPT slots expand into 57 complete `tPartInfo`
records, 57 linked mechanical nodes and one default Driver node. All 58 owner
nodes and owner head/count writes match byte-for-byte. Allocation and
class/attachment resource lookup remain deterministic stubs.
Run `tools/verify_stock_component_owner.py <mcity.exe> --game-root <game-root>`.
The ready-success orchestration `0x52c790` also matches two full original
executions, including the unmatched-stock label and a selected vehicle
identity branch, using `tools/verify_stock_owner_worker.py`.

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
| Cylinder head | `0x54bd70` | `ev_41f23b89a8113651a08e4d8bbc5cb58b42e494f89d0f6037e7e577ef5e5faf44` |
| Camshaft | `0x54bef0` | `ev_5c80889067ad3a42a1322bef2479d699795e37215e7d5edc31781aceac5a01b5` |
| Crankshaft | `0x54bac0` | `ev_f6a2b1d75e22cf1f89071cc05887b695719b57525e5964a74bb2aae3522c9be8` |
| Connecting rods | `0x54bc10` | `ev_2056044b1d883c0dcb83c352d57411a3f3cf57c001e5f437ebfd2cfe2471eaea` |
| Pistons | `0x54b940` | `ev_7331be288fa5f553e48495b0a720d46df91cfb9e118e1b609e8e5ffd74cf656b` |
| Valve train | `0x54c090` | `ev_c97ef21e7605be640a9b7668af508d7c16a4d6c06f48b0c0f70a7b37944bcafa` |
| Tire loader | `0x54e170` | `ev_bdcf6c3a6cfa5cdd074e761081ac6bd2687a460b7744c804bc5af0b10489280e` |
| Tire validation | `0x545030` | `ev_48548f9764fb633c725aaedf17d7f4f9348a247bc5a0b4c091c4694d3fe69e35` |
| Tire post-validation | `0x545110` | `ev_15e833e423670d5e2d7581403e7cdc14b160d350251de577bf581f90a0c4dbc4` |
| Tire auxiliary producer | `0x67e520` | `ev_8431a9a933d00fdf6263e3d4c0b39f08a1f46000afa5ba79bc9e39dc8d19da9c` |
| Intake manifold | `0x54af40` | `ev_e3e692b283f35a09d9f55ae0a4c1ee143ce922fead52ab059d38fe23f7184eb6` |
| Carburetor | `0x54b0a0` | `ev_779783aad82910a8b1f8c2b65415063f2d6e270b4016b9b41dc71fd938b518f8` |
| Air cleaner | `0x54b360` | `ev_dd48cbddb6c12aa5efd9b51e8e5c4551221a67af89fdd6cda7e6aebda24c4588` |
| Exhaust manifold | `0x54c710` | `ev_8db65c323a673c47207ea203501ddd9af1c30f1d126a7f86fa4ab5081aa8d5f6` |
| Exhaust pipe | `0x54c860` | `ev_140819b7af8724cb345ca5ea5d9b910285d6b70363b42e769a155b5c57a9e163` |
| Muffler | `0x54ca90` | `ev_faa26a510b25809e61f735142b9bae5b72e52185473352525627b81c4227efc0` |
| Cooling | `0x54c440` | `ev_52a94512608e44afdb67de7af07f2951ce9f9480f59356b4b7be5d048beb1e4d` |
| Electrical | `0x54c550` | `ev_ed309b8bbfc3a9a9d4332a8a30795ba433f6b0fed62a1723f14480868a2966fa` |
| Lubrication | `0x54c340` | `ev_730e9a267ae0e604e98bf763ac300dcb0cf8887d37957583df0035d0144a793a` |

These are authored reconstructions from shipped instructions, not recovered
original source. Original bytes, decompiler output and private captures are not
distributed. The raw intermediate/configuration adapters are internal research
interfaces, not mod interfaces or network packets.

Engine validation dossiers: piston `0x543790`
(`ev_ec58dca9a272bfd7a1899521ec70dc653cf283b44a40dae03e231c04b2fe448f`),
crank `0x543870`
(`ev_c8009e7c03ae127c859ffc7c8639ddd32b61f9db3252b099c78e7010d0ccb90d`),
rods `0x543930`
(`ev_19b8abdbd63e68c2f38b99e5b4bff05b4f5f394b76b92b22a48f734914723e71`),
head `0x543a10`
(`ev_d95f279cd71d29b35803290a09204748be666f4e8dba7aa2a67ff5e6a75f6e74`),
cam `0x544710`
(`ev_f9de6ab64cd5b84e1b03a4f3a39d63c550181e0e06d554cf5594d9f8835a1eb5`),
valve train `0x544310`
(`ev_7659c8703964a4a7700e047af403f73a23fabf8edda3d31c2478315defed0d35`).
The family helpers compare the block and part IDs and reject zero. The original
execution comparisons include those real helper calls.

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

Auxiliary loaders preserve several non-obvious rules. Carburetor quality uses
truncated duty, while most quality selection rounds. The air cleaner expects zero
numeric values and can suppress its loss through installation metadata. A nonzero
pipe flag clears its contribution before semantic validation, even on a later
failure. Muffler gain depends on the already loaded exhaust manifold, making
dispatch order observable. Electrical RPM metadata truncates; cooling capacity
uses the original float32 `1.07` multiplier. These fields feed the
[engine curve finalizer](engine-curve-finalization.md).

All thirty-two loaders preserve float32 mass accumulator stores. Their component mass
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
or two for rejected semantics. Crankshaft and rod loading modify configuration
before semantic validation; a rejected record retains those changes while leaving
component quality untouched. Tire post-validation also retains changes. Count
rejections preserve images, except that missing tire tables take precedence and
return status four. Finite-value, buffer-size, template-index and text-termination
safeguards are authored boundaries; arbitrary NaN behavior is not claimed recovered.

## Engine parts and compression

All six additional engine loaders require a nonzero family equal to the loaded
block family. Head loading also restricts that family to 1–26. Material validation
can truncate while quality selection rounds to nearest even. For example, an
authored piston material value 7.9 passes the truncating exclusion of 8/9, then
rounds to quality entry eight (0.93). Replacing both operations with one cast
would change accepted configurations.

Pistons and rods add `cylinder_count * individual_mass` to total mass. The original
stores a rounded float32 copy in the component aggregate slot but retains the
unrounded product for the total addition. An eight-cylinder fixture with 0.6 kg
pistons adds approximately 4.8 kg, rather than 0.6 kg.

Head loading sets the base compression value. Piston loading later adds its
compression contribution. An authored head value 8.0 and piston contribution
0.25 therefore yield 8.25. Their original relative dispatch order is preserved;
the full engine curve still requires the remaining intake/exhaust/auxiliary
loaders and finalization.

## Tire tables and axle configuration

The saved Jet query `GetTireAuxData` selects `Pacejka_TireModel.*`, ordered by
`TireTypeID`. The installed external database contains eighteen records. Column
IDs establish query order; the parser's dictionary order instead moves the
variable text field to the end and must not be used as Jet ordinal order.

The original allocates twenty 376-byte records plus a handle and count. It packs
identity, tire type and rain flag first, followed by 36 numeric values, 25 lateral
force samples, 25 aligning moment samples and five parameters. The text field is
bound separately and excluded from this packed block. Authored code reads these
values from the separately supplied database; no original tables are bundled.

Tire value four truncates to an ordinal into that allocation. The loader writes
front configuration for attachments 1/2 and rear configuration otherwise. Each
axle receives two 26-entry curves: zero at entry zero and the 25 database samples
at entries 1–25. Growth is multiplied by the float32 constant 0.01. Widths above
215 mm add `clamp(float32((width-215)*float32(0.00004)), 0, float32(0.005))`
to configuration field zero; the physical meaning of that accumulator remains
unresolved. A 225 mm fixture adds approximately 0.0004 on each load.

Peak friction must lie in [0.7, 2] and template section width in [127, 508]. These
checks occur after mass, curves and quality are written. A selector exactly 4.0
sets quality to 0.96; a fractional selector truncating to four still uses quality
one. Out-of-allocation indices are safely rejected by the authored API; the
original unchecked memory behavior is not reproduced.

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
- Six additional engine loaders: 1,700 original cases, including six actual Ford
  components, with actual family validators and rejection side effects.
- Tire loader: 631 original cases, including four actual Ford tires and all
  statuses, comparing both complete output images.
- Auxiliary packing: six original runs for 0/1/2/6/20 authored records and all
  eighteen installed records. Allocator and typed database services are replaced;
  packing/clearing/control flow runs original instructions. Every table byte
  except the process-specific allocation handle matches. Jet execution is untested.
- Nine auxiliary loaders: 2,093 original cases, including nine actual Ford components.
  Validators, installation overrides, family checks and pre-rejection writes execute
  original instructions; statuses and both complete output images match.
- Thirty-eight selected Ford loader calls in their original relative dispatch order:
  every resulting configuration/component image matches original execution.
  Other loaders are skipped, so this is a partial assembly comparison.
- Body/accessories/axle bars: 1,404 original cases including nine Ford components.
- C++ ports: 7,984 authored original-comparison cases match Python exactly.

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
python -m tools.engine_component_loaders_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.engine_auxiliary_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.body_accessory_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.tire_loader_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.tire_templates_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.stock_mechanical_oracle '<game>/mcity.exe' '<game>/data/db/Online.mdb'
python -m tools.inspect_stock_mechanical '<game>/data/db/Online.mdb' --damage 0 --wear 0
python -m tools.native_mechanical_loaders_compare build/native-check/mco_mechanical_loaders_compare.exe
```

The native authored corpus runs in Windows/Linux CI without original assets. The
actual-catalogue/original-execution checks remain local. Faithful driving still
requires all component producers, the complete assembly pass, startup geometry
and owner binding, and integrated original-client runtime comparisons.
