# Established shared layouts and startup dependencies

These are recovered byte-image contracts used by existing authored modules.
They are not a complete recovery of original C++ classes, vtables or ownership.
All original addresses here refer only to main executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Other binaries, including historical cached clients, have separate address spaces.

## Mechanical images

`mco::ComponentLoadResult` retains a `0x820`-byte configuration and a `0x984`-byte
component image plus the original loader status. These sizes and writes are
compared against original execution. Serialized integers/floats are little-endian;
float fields are IEEE-754 binary32. Native code accesses byte images explicitly
instead of relying on compiler structure padding or host pointer size.

| Configuration offset | Recovered meaning | Representation / units |
| --- | --- | --- |
| `0x20` | Finalized vehicle mass | float32, kg in catalogue interpretation |
| `0x2c` | Wheelbase | float32, metres |
| `0x30`, `0x34` | Front/rear track width | float32, metres |
| `0x38` | Body height parameter used for COM | float32; conversion documented in owner binding |
| `0x3c` | Finalized front weight fraction | float32, dimensionless |
| `0x48` | Body shape selector | Original stored selector; owner-binding producer required |
| `0x58` | Brake allocation input | float32; wheel initialization halves it |
| `0x60`–`0x63` | Four steering flags | Four separate bytes |
| `0x70` | Finalized maximum RPM | signed 32-bit integer |
| `0x124`, `0x128`, `0x12c` | Front tire width/aspect/rim | float32: mm, percent, inches |
| `0x228`, `0x22c`, `0x230` | Rear tire width/aspect/rim | float32: mm, percent, inches |
| `0x32c` | Populated gear count | signed 32-bit integer; bounded adapters support at most eight |
| `0x334`, `0x354` | Gear ratios / loss coefficients | Separate float32 arrays |
| `0x374` | Final drive | float32 ratio |

The component's numeric-count header is at `0x14`, mass at `0x30`, duty at `0x34`,
and numeric values begin at `0x3c`. Header flags and semantic validation vary by
part kind; do not reinterpret every component as one populated structure. The
complete table remains in the recovered loader implementations and
[component loading writeup](../calculations/mechanical-component-loading.md).

## Owner observations

`mco::StartupOwnerImage` is an authored **observation buffer of `0x2000` bytes**.
It is not evidence that the original owner class has that exact size.

| Owner offset | Established observation |
| --- | --- |
| `0x50`, `0x54` | Mass and inverse mass |
| `0xcc`, `0xd0`, `0xd4` | Model half extents |
| `0x490` | Original pointer/state observation used as a nonzero mass-availability gate |
| `0x6b4 + wheel*0x10c` | Four wheel-record bases used by final initialization |
| `0x18c4`, `0x18c8` | Required prior wheel-marker geometry observations |
| `0x18ec`, `0x18f0` | Front/rear radii consumed by stance and wheel setup |
| `0x1c94` | Original 32-bit configuration pointer in emulated execution |

Host calculations receive the configuration separately; they do not dereference
an original process address or reinterpret it as a 64-bit host pointer. The
assembly-completion assertion records caller responsibility. It does not validate
provenance of arbitrary supplied byte images.

## Original startup dependency order

The retained `0x43a990` startup analysis establishes this sequence:

1. `0x54e720`: mechanical assembly and configuration finalization.
2. `0x554330`: model assembly, including geometry selection/placement.
3. `0x4c6670`, then `0x5602d0`: model restore/final preparation and cache handling.
4. `0x51f440`: base owner construction from mass and model dimensions.
5. `0x43a240`: shape geometry; `0x53b3c0`: stance adjustment.
6. Body-response and COM stores using prior owner observations.
7. `0x53a1f0`: main owner initializer.
8. `0x53b8a0`: final wheel setup, including stance adjustment again.

The base constructor clears only the first `0x418` owner bytes. Producers and
lifetimes of all prior high-offset geometry observations are not yet established.
Do not reorder this sequence or replace prior state with newly computed values
without an original-execution comparison. Complete startup remains partial even
though individual assembly, bounds and wheel functions have bounded verification.

Next shared-definition work: complete model selection/scaling/centering, owner
initialization, indirect dispatch targets, class boundaries and lifetime contracts.
Raw Ghidra type identities and function signatures are in the private export
browser; they require review before becoming authored headers.
