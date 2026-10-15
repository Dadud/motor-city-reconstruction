# Source recovery and build status

Current priority (2026-10-15): recover and organize original behavior as readable
source with a repeatable build. New gameplay, presentation, mod APIs and fan-server
integration are deferred while this is the active scope. Existing prototypes are
retained as reference work.

## What is here

| Location | Contents |
| --- | --- |
| `native/include/mco/`, `native/src/` | Authored C++20 ports of recovered calculations, formats and protocol helpers; also optional garage and scripting code |
| `client/` | Python recovery implementations and research application; `driving.py` and `racing.py` contain prototype handling and race rules |
| `tools/` | Inspectors, original-function comparison runners, Python/native comparisons and other development tools |
| `native/tests/`, `tests/` | Bounded native checks and Python regression tests |
| `docs/calculations/` | Calculation descriptions, original addresses, evidence references and known gaps |
| `docs/recovery-ledger.md` | Feature-level recovery status and remaining work |
| `evidence/` (ignored, local) | Private decompiler results and original-executable comparison records |
| `examples/` | Existing example mods; outside the current recovery priority |

This is a partial source reconstruction, not the original game's extracted source
or a complete rebuildable game. Recovery checkpoint `35df8de` established complete
supported stock mechanical assembly. Subsequent
bounded recovery includes [wheel initialization](calculations/owner-wheel-setup.md)
and [part bounds](calculations/model-bounds.md), with complete-original-function
comparisons. These do not establish complete startup or integrated driving.
The [body constructor and startup-body phase](calculations/body-construction.md)
now also have verified Python/C++ implementations, including catalogue sample
customization and native owner inertia/COM producers.

The repository already has native ports for portions of assembly, engine updates,
tires, suspension, brakes, drivetrain, body forces, collisions and networking.
Their bounded verification does not establish full subsystem recovery. Complete
startup, interconnected driving, rendering/audio and service behavior remain
incomplete. The [function inventory](recovery/README.md) separates analyzed
functions, retained decompilation records, source references and explicitly
reviewed completion claims. Unreviewed entries are not counted as complete;
a whole-game extraction percentage remains unestablished.

## Build the recovered code

Requirements: Python 3.11+, CMake 3.24+, and a C++20 compiler. On Windows, use a
Visual Studio Developer shell with the C++ tools installed; on Linux, install a
C/C++ build toolchain and CMake. No game installation, REA, Ghidra, SDL or Lua is
required for this default build. CMake and the compiler must already be installed.

From the repository root, on Windows or Linux:

```sh
python build.py --test
```

Use `python3` where that is your Python command. The script configures, builds
`mco_core` and native checks, then runs CTest. Without `--test`, it builds only
the recovered library. Outputs go to `build/recovered`; this is a library and
test executables, not a playable original client. Default options disable optional
platform and scripting targets, avoiding their dependency downloads.

To select a toolchain or generator:

```sh
python build.py --test --build-dir build/recovered-ninja -- -G Ninja
```

Use a separate build directory when changing toolchains. `--cmake PATH` selects
an explicit CMake installation. Extra CMake options after `--` can override the
default options deliberately. The existing full CMake commands and optional
garage remain documented in the README.

## Recovery workflow

1. Inventory original executable/library functions, imports and data. Record
   target hashes, addresses, callers and unresolved dependencies in local evidence.
2. Group functions by original subsystem; identify shared structures and globals
   before renaming or translating them. Keep unknown fields explicit.
3. Preserve decompiler output privately as evidence. Publish readable authored
   source with original addresses and links to calculation notes. Decompiled C-like
   text still contains unresolved types, runtime calls and globals; it is not
   automatically buildable C++ and does not recover comments or original files.
4. Build each recovered module in `mco_core`. Verify its supported behavior against
   original execution where possible; document substitutions and uncovered branches.
5. Track function coverage separately from integration. A complete source recovery
   requires all necessary functions, data layouts, external interfaces and startup
   wiring; passing the current tests does not establish that completion.

Preserve original files as external read-only inputs. Do not publish original
assets, credentials, captures or raw decompiler output. REA and Ghidra remain
research tools only. Existing broad game milestones remain in the roadmap for
later work; they are not the current build deliverable.
