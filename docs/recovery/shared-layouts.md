# Established shared layouts and startup dependencies

Byte-image offsets, strides, minimum sizes, emulated globals and calling
conventions are **machine-readable and audited** in
[`layouts.json`](layouts.json), which `tools/layout_registry.py` renders into
`native/include/mco/layouts.hpp` and checks against recovered sources. This page
explains what those contracts mean; it no longer restates offsets that the
registry owns, because two documents describing the same offset drift apart.

Start from `python -m tools.layout_registry --check`: it reports the registered
offset count, which sources are audited, and any offset used by more than one
consumer that the registry does not describe. That last number is the one that
matters — a single-file constant cannot drift, a shared one can.

Recovered byte-image contracts used by existing authored modules. They are not a
complete recovery of original C++ classes, vtables or ownership.
All original addresses here refer only to main executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Other binaries, including historical cached clients, have separate address spaces.

## Registered images

| Image | Size | Consumers audited |
| --- | --- | ---: |
| configuration | `0x820` | 10 |
| owner | `0x2000` | 10 |
| startup_record | `0x4a8` | 10 |
| model | `0x1400` | 10 |
| entity_record | `0x1c` | See [entity field batch](entity-table.md) |
| mask_record | `0x54` | See [entity field batch](entity-table.md) |
| state_record | `0x100` | See [record stack batch](record-stack.md) |
| record_machine_image | `0x780` | See [record controller batch](record-transitions.md) |
| record_request | `0x10` | See [record controller batch](record-transitions.md) |

Serialized integers and floats are little-endian; float fields are IEEE-754
binary32. Native code accesses byte images explicitly instead of relying on
compiler structure padding or host pointer size.
Packed byte and word fields carry an explicit width in the registry; legacy
entries default to four bytes. The entity batch also migrates the two existing
entity flag readers to the same checked offsets.

## Mechanical images

`mco::ComponentLoadResult` retains a `0x820`-byte configuration and a `0x984`-byte
component image plus the original loader status. These sizes and writes are
compared against original execution. The `0x984` component image is **not yet in
the registry**: `native/src/mechanical_loaders.cpp` works on component images
rather than the registered startup/entity/state images, so it is not audited and its 194 local
offsets are a separate seeding job.

The component's numeric-count header is at `0x14`, mass at `0x30`, duty at `0x34`,
and numeric values begin at `0x3c`. Header flags and semantic validation vary by
part kind; do not reinterpret every component as one populated structure. The
complete table remains in the recovered loader implementations and
[component loading writeup](../calculations/mechanical-component-loading.md).

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

The [base constructor and connected body phase](../calculations/body-construction.md)
now have Python/C++ translations and byte-exact original comparisons. The base
constructor clears only the first `0x418` owner bytes. Producers and
lifetimes of all prior high-offset geometry observations are not yet established.
Do not reorder this sequence or replace prior state with newly computed values
without an original-execution comparison. Complete startup remains partial even
though individual assembly, bounds and wheel functions have bounded verification.

Next shared-definition work: complete model selection/scaling/centering, owner
main owner initialization, indirect dispatch targets, class boundaries and lifetime contracts.
Raw Ghidra type identities and function signatures are in the private export
browser; they require review before becoming authored headers.

Camera selection has a registered 24-byte image with four presets, selected
index and slot, plus a 12-byte discriminator context. `RecordMachine` carries
all four presets; its previous count/pending field names have been corrected.
See [camera selection](camera-selection.md) for producers and limits.

The camera subject observation window registers the `0x3c` spacing between
current and reference identity tables. Its 120-byte corpus extent is a bounded
observation window, not a recovered array count. See [camera cycling](camera-cycling.md).

Input contracts register the 128-byte raw query/remap images, a 256-byte
release observation window overlapping the raw base, and a 512-byte latch
observation window. These observation extents do not imply recovered original
array sizes. See [input key state](input-key-state.md).
