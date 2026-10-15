# Complete supported mechanical assembly

The Python research runtime now runs the original mechanical assembly sequence
for stock vehicles 101–108. All eight match complete original `0x54e720` execution:
status, all 2,080 configuration bytes, and all component bytes except process
addresses in linked-list pointers. No callees are substituted. Eleven additional
missing-part/rejection/duplicate scenarios match the same comparisons.

This closes mechanical startup for those stock configurations. It does not
complete model geometry, owner initialization, contacts, driving, or native
assembly. Boost, special carburetor mode, and other present unrecovered component
families still fail explicitly. Modified-car acceptance remains open.

## Evidence

External `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`;
REA/Ghidra 12.1.4, bounded x86 emulation on Windows with x87 control word `0x27f`.
Original flow and tire tables are supplied separately; no raw game data or
decompiler output is published.

| Function | Behavior | Evidence |
|---|---|---|
| `0x54e720` | Complete dispatcher and finalization sequence | `ev_f20d56d975c43fb2f81535392e722376837ccf5bd4bb65eae81fd4724b981024` |
| `0x54e5e0` | Presence search; return discarded by assembly | `ev_a8458a383a85be25f29f690c0778d17723d5ff58cfce5bfca28dc1ad094f98ba` |
| `0x54eaa0` | Cross-part quality bonus | `ev_0f09438db7ec0b7e4bb464fc430c8528b9529d52a545bf6bc3a72b06a0e099ca` |
| `0x54a2b0` | Body loader and quality | `ev_3a79338078733c2142589bdba777f31281e8fd3f202a70617f07e1f94c6c93f5` |
| `0x542a00` | Body semantic validator | `ev_c6c3b145adf6e96618242174e2eb32d5b9a0d8206a6f971f687675a3072ac6be` |
| `0x54cce0` | Anti-roll bar | `ev_8d24be689d4b0666db4cf3bbbcefdfdba0cfac8c3e59bc00e616f141d81b099c` |
| `0x54cea0` | Traction bar | `ev_cdbe7a02740b2d561b5dad3936e23b9ce28f22678b2b8deda952d089448d555c` |
| `0x54dd80` | Accessory 22001 | `ev_39dd73f41255a658b9d7b1c460412e0099864ab4b1ac4610bb75454daf8a662f` |
| `0x54d740` | Accessory 23001 | `ev_56645885a6709089064a143a905261b1c06208ed6a187e94cb961e88caffffc6` |
| `0x54de10` | Accessory 31001 | `ev_f9012d52378ffd08fb717ebc297854c52b0887d4004eec37c47be00a45cfa577` |
| `0x54df90` | Accessory 34001 | `ev_f034f79658f95ef1fc215f77d88719111c7ac23b71cb8c81343e7bc5f2808896` |
| `0x54dcb0` | Accessory 35001 | `ev_44cc917da9196ae7892bc0bffac8cf3538fe83c008ccbd1a710b8ed74adbc6ab` |
| `0x54e060` | Accessory 40001 | `ev_b2fc5b82d5d9e25be64b607f16ea713aceb23532a424e8e1f967cd7da0ec3135` |

The nine new loader bodies also match 1,404 standalone original cases, including
nine Ford components. All 32 loader kinds have C++ ports; 7,984 authored cases
match Python exactly. The enclosing assembly and engine finalizer remain Python.

## Selection, failure and quality

The dispatcher has 70 ordered entries. Each identifies an abstract type,
attachment (zero means wildcard), minimum, maximum and a nonzero-mass gate.
Preflight counts required matching entries before changing any configuration or
quality. Missing required parts return failure and preserve the input images.

After preflight, the original clears configuration and visits entries in order.
Each matching component has quality reset to one before its loader or mass check.
Only successful calls consume the maximum count. A rejected first copy therefore
allows another matching copy to load, but the assembly still returns failure.
A successful first copy can leave later copies completely untouched. Repeated
accessories may accumulate mass and drag while overwriting their scalar slots.

The presumed group-quality helper `0x54e5e0` only searches for a type; it writes
nothing. A different helper modifies the first matching transmission from its
flywheel quality, and the first engine block from lubrication quality:

```text
target_quality = float32((1 + source_quality × float32(.01)) × target_quality)
```

These quality writes affect components, not the configuration image. Numeric
postload then applies its fallbacks, mass-derived accumulators and weight
distribution, followed by the [engine finalizer](engine-curve-finalization.md).

## Stock example and inspection

The Ford 32 V-8 Coupe (101) expands 45 catalogue entries into 57 components.
Its dispatcher makes 46 loader calls and produces total mass
**1,134.0198974609375**, idle **1,100 RPM** and maximum **6,500 RPM**. This is
the full mechanical mass accumulator from the original call, replacing earlier
partial totals. The stock driving inspector now carries these finalized values,
axle levers and gear tables, while retaining unresolved owner/contact requirements.

```powershell
python -m tools.mechanical_assembly_oracle '<game>/mcity.exe' '<game>/data/db/Online.mdb' --vehicles 101 102 103 104 105 106 107 108
python -m tools.body_accessory_oracle '<game>/mcity.exe' --database '<game>/data/db/Online.mdb'
python -m tools.inspect_stock_assembly '<game>/data/db/Online.mdb' '<game>/mcity.exe' --damage 0 --wear 0
python -m tools.inspect_stock_driving '<game>' --output build/stock-driving-inputs.json
```

Catalogue fixtures use authored local instance IDs and explicit wear/damage;
they are not server-owned inventory. Native original execution comparisons stay
local. CI uses authored loader fixtures without game assets. Unsafe unterminated
strings and non-finite numeric observations are rejected by the authored boundary.
