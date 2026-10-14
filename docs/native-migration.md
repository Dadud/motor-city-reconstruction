# Native runtime migration

The target is a C++20 Windows/Linux client, built with CMake, using pinned SDL3,
OpenGL 3.3, OpenSSL and Lua 5.4 dependencies. This document defines module boundaries
and migration gates. It does not claim the Python game or a new native scaffold is
a complete recovered runtime.

## Implemented foundation

The root CMake build contains `mco_core` (owned-part valuation, type-cache resolution,
placeholder insertion/pruning, type/attachment ordering, root selection and
parent/dependency linking, VIV directories, component counts and repair/scrap/price totals,
MCOTS framing), `mco_scripting`
(isolated Lua execution), optional `mco_platform_probe` (SDL/OpenGL context
creation), and `mco_native_garage` (bounded original FCE geometry rendering).
There is no native driving application or native online client yet.
SDL 3.2.28 and Lua 5.4.8 source archives have SHA-256 pins in CMake. OpenSSL
integration remains pending the online port; no TLS compatibility is implied by
this foundation.

The [native garage](native-garage.md) reads separately supplied VIV/FCE models
and renders neutral geometry with orbit/zoom controls. Windows verification
matched the Python reader across 315 installed models and 99,608 vertex
positions; an original 32 Ford frame passed a foreground-pixel smoke check.
This covers geometry, not textures, stock assembly, customization or driving.
Linux CI renders authored tetrahedron geometry separately from original-asset
acceptance. The [data mod kit alpha](mod-kit-tutorial.md) currently runs in the
Python tooling; its registry is not yet loaded by this native application.

The archive decoder ports `tools.viv.inventory`: BIGF/BIG4 headers, bounded
directory entries, Latin-1 names represented as UTF-8, duplicate rejection and
non-overlapping payloads. It does not extract files or resolve filesystem paths.
The MCOTS envelope ports `client.mcots_framing`: little-endian 11-byte headers,
opaque flags/transaction fields, 1..65526-byte payloads, and strict complete-frame
validation. Neither encryption nor socket/session behavior is part of that port.

Local Windows validation on 2026-10-13 used Zig 0.13.0/Clang 18.1.6 and CMake
3.31.6. All four native suites passed, 512 native/Python valuation cases matched,
and all 344 installed VIV/BIG archives matched across 7,876 ordered directory
entries. The existing 345 Python tests also passed. These archive comparisons
verify directories only, not decoding/rendering member contents. Windows/Linux
native CI is configured separately; these local results do not imply Linux or
live-server acceptance.

The optional SDL3 platform probe also built locally and successfully created an
OpenGL 3.3 core context on Windows. It initializes SDL video/audio/gamepad
subsystems, but this check does not exercise audio playback, controller input,
game rendering or driving.

GitHub native Windows/Linux builds, differential valuation checks and the Linux
Mesa/Xvfb SDL/OpenGL probe passed for commit `1fce19c` in
[native checks run 38466840304](https://github.com/Dadud/motor-city-reconstruction/actions/runs/38466840304).
The subsequent component passes are covered by additional native suites;
its original-code comparison is documented separately in
[owned component dependencies](owned-component-dependencies.md).

Local validation of the insertion port on 2026-10-13 passed all nine native suites
and 387 Python tests. Its 96-case corpus matches Python/C++ byte-for-byte and the
bounded original insertion prefix with explicit allocation/formatting substitutions.
This covers an isolated assembly stage; full car loading and aggregation remain
unfinished. The native CI matrix runs the asset-free insertion comparisons on both
operating systems.

The subsequent numeric aggregation port passes ten native suites and 397 Python
tests locally. Each of its three passes matches complete original functions in
97 controlled cases, including whole-record output, existing totals and 32-bit
wrapping. See [owned-component aggregates](calculations/owned-component-aggregates.md)
for traversal order and the repeated-accumulation behavior. This does not prove
mechanical aggregation, complete garage loading or live economy compatibility.

The ordering port reproduces the original cache-driven depth-first traversal and
fixed attachment sequence. Its caller accepts reordered records on count equality
alone, including repeated selections. The original recursive function matches 96
controlled cases with allocation/free substitutions and isolated SEH state; the
loader's acceptance gate is derived from static evidence. See
[owned-component ordering](calculations/owned-component-ordering.md) for examples
and the boundary between candidate ordering and complete car loading.
Local validation passed eleven native suites and 407 Python tests. All 96
candidate and accepted/rejected ordering outputs match Python/C++ byte-for-byte;
the Windows/Linux CI matrix runs the same asset-free comparison.

The recovered postload sequence now connects these stages with the original skip
flags and ordering. Enriched processing requires an explicit description callback
because original descriptions remain incomplete. All 96 controlled sequence
fixtures match original-code execution and Python/C++ with that boundary
substituted. Local validation passes twelve native suites and 414 Python tests.
See [postload sequence](owned-postload.md) for exact exclusions and safeguards.

The outer description pass now implements template copying, assembly child lists,
spacing and whole-line length limits. Its 96 original-code cases and native/Python
comparisons retain explicit leaf-rendering and localization substitutions. See
[component descriptions](calculations/owned-component-descriptions.md); original
part-specific renderers and localized resource loading remain unfinished.

Repeat the external-asset check without persisting original bytes:

```sh
python -m tools.native_viv_compare build/native/mco_viv_compare --root '/path/to/Motor City Online'
```

`mco::calculate_owned_valuation` accepts a 1596-byte record and explicit server
rates. It preserves little-endian fields, float32 stores, signed low-32-bit
conversion and original body-value boundaries. Strict floating-point build flags
disable contraction and fast math. The port is compared against the recovered
Python calculation using 512 deterministic cases:

```sh
python -m tools.native_valuation_compare build/native/mco_valuation_compare
```

On Visual Studio builds use `build/native/Release/mco_valuation_compare.exe`.
This verifies the port against the Python reference; the original CPU oracle
remains a separate evidence layer.

`mco::run_script` currently executes text in a fresh Lua state with an 8 MiB
allocation cap, 1 MiB source cap and explicit instruction budget. Host file,
process, dynamic-library and debug interfaces are unavailable. No content
registration or gameplay hooks are implemented yet. Instruction counting does
not bound time spent inside Lua library calls, so this harness is not yet a
complete hostile-script isolation boundary. Lifecycle integration must add
appropriate cancellation/isolation before treating untrusted scripts as safe.

Lua and SDL retain their upstream licenses; release packaging must include
their notices. Downloaded dependency sources stay under ignored build folders.

## Dependency and module boundaries

Use explicit versioned dependency declarations with recorded hashes/locks. Select
patch releases in the build configuration and keep this document aligned with that
configuration; do not use floating branches. Produce dependency/license notices in
release packages. Python, REA and Ghidra are research tools, not native dependencies.

| Module | Inputs and outputs | Dependencies |
| --- | --- | --- |
| Content | Bounded bytes/read-only paths → typed archive, mesh, texture, track and sound data | Standard library; format-specific decoders |
| Catalogue and assembly | Typed catalogue/instance records → component graph and validated simulation inputs | Content-neutral typed data; no renderer or network calls |
| Simulation | Initial state + ordered controls + fixed steps → vehicle/race state and events | Recovered numerical kernels; no window, wall clock or socket access |
| Presentation | Typed meshes/materials, simulation snapshots and audio events → pixels/sound | SDL3, OpenGL; owns graphics/audio resources |
| Online | Explicit connection/account commands → typed service events and authoritative state | OpenSSL, platform sockets, bounded protocol codecs |
| Mods | Manifest/resources/scripts → validated registry overlays and lifecycle hooks | Content registry and restricted Lua API |
| Application | User input/configuration → module commands and lifecycle | Composes modules; owns shutdown/cancellation and user-visible errors |

Use stable identifiers and typed structs across boundaries. Preserve original raw
fields only where their meanings remain unknown, with explicit byte widths and
endianness. Do not expose internal pointers, native offsets or mutable transport
buffers through public mod APIs. Do not turn unresolved fields into guessed defaults.

## Porting order and parity contracts

Owned root selection, parent/family linking and type-cache reference resolution
are now available in the native core. Their comparison tools preserve every
record byte and use the same asset-free corpora as the optional original CPU
oracles. These modules remain isolated until preceding component finalization
and subsequent aggregation are recovered; they do not yet define a drivable car.
The finalizer's induction-pruning tail is also ported with byte/count comparisons;
its earlier missing-part insertion and call conditions remain separate work.

1. Establish the CMake build, asset-free headless tests and Windows/Linux CI before
   porting runtime behavior. Keep build products outside source and original files.
2. Port bounded decoders and recovered pure calculations. Feed identical fixtures
   to Python and C++; compare typed results and required binary layouts.
3. Port complete catalogue/owned component loading only after original linking and
   finalization are recovered. Preserve the distinction between provisional slots
   and usable complete vehicles.
4. Add garage rendering and input, then recovered simulation and event flow. The
   existing Python driving model remains explicitly a prototype comparison harness.
5. Port recovered protocol codecs and transports with independent encrypted peers,
   then asynchronous service orchestration and live scenario checks.
6. Integrate mod overlays and Lua hooks against stable application boundaries;
   package the native application after real original-asset verification.

Keep Python fixtures and native-instruction oracle tools during migration. Each
ported subsystem must state its source identity, cases, tolerance and unsupported
branches. Do not delete the reference harness merely because the native build runs.
When behavior changes, update the [recovery ledger](recovery-ledger.md) with evidence.

## Numerical, timing and online behavior

Represent on-wire and saved fields with fixed-width types and explicit codecs; do
not serialize C++ object memory. Preserve recovered float-store boundaries, integer
wrap/truncation and calculation order with dedicated helpers and tests. Disable
unsafe fast-math for fidelity kernels; verify compiler/platform differences rather
than assuming C++ expressions match x87 behavior.

The application supplies elapsed time and controls to a deterministic headless
simulation runner. Recover the actual step schedule and update order before making
them the baseline. The prototype's 120 Hz step is not evidence of the original
schedule, and network transmission cadence does not define physics cadence.

Network I/O runs outside the rendering/simulation thread. Typed commands/events
cross bounded queues; one owner maintains each connection's cipher, parser and
transaction state. Cancellation closes owned resources, failures expose sanitized
errors, and retries follow recovered transaction semantics. Do not automatically
replay purchases or other state-changing requests. Use standard TLS verification
by default and retain any explicitly scoped legacy certificate policy as a documented
endpoint-specific compatibility setting.

## Lua and content contracts

The package loader validates API version, dependencies, namespaced IDs, resource
paths and explicit replacements before changing the active registry. Loading is
deterministic and leaves base assets read-only. A rejected package must not partially
replace active content. Publish schemas and examples alongside the tools.

Lua receives stable content registration and race lifecycle APIs plus read-only
vehicle snapshots. Gameplay mutations use explicit supported commands. Remove
unrestricted file/process/native-library access, restrict script loading to package
resources, and enforce execution budgets. Define callback errors and package unload
cleanup without abandoning the baseline simulation state.

Default online mode uses verified baseline behavior. Altered simulation and gameplay
scripts run offline unless the server explicitly supports them. A content digest
identifies content; it does not establish server permission or protocol compatibility.

## Release gates

- Fresh Windows/Linux builds pass decoder, calculation, malformed-input and protocol
  tests, plus differential comparison fixtures.
- Actual original assets render and drive correctly with audio and controllers on
  both systems; generated geometry alone is insufficient.
- End-to-end online scenarios pass against the configured fan server, with failures,
  cancellation and reconnect tested independently from local peers.
- Installable packages include licenses, configuration/help and no original assets,
  credentials, raw decompiler output or research runtime dependency.
- An outside developer builds the client and makes a working content/script mod from
  published documentation without private setup knowledge.
