# Motor City Reconstruction

**Current focus:** source recovery, organization and a repeatable build.
See [source recovery status and directory guide](docs/source-recovery.md).
The [function inventory](docs/recovery/README.md) tracks per-function evidence,
source references and reviewed recovery gaps.
The [installation export report](docs/recovery/export-status.md) covers all
discovered program binaries; the [approved recovery plan](docs/recovery/plan.md)
and [export instructions](docs/recovery/exporting.md) describe the current workflow.
Build the recovered C++ library and checks with `python build.py --test`
(Python 3.11+, CMake 3.24+ and a C++20 compiler required). This does not yet
rebuild the complete original game. The application and mod work below are
existing prototypes and longer-term work, deferred during source recovery.

An open-source reconstruction of the Motor City Online client for modern Windows and Linux. It reads game assets from your own local installation.

**Current status:** Windows supports garage previews and offline driving/time trials on decoded tracks. The Linux OpenGL renderer passes a generated-geometry smoke check under Xvfb/Mesa; original-asset driving on Linux remains unverified. Driving uses an authored prototype bicycle model; recovered engine and force simulation, object collisions, sound, online services and multiplayer remain unfinished.

## Quick start

For a fan-server connection test on Windows, double-click
`test-fan-server.cmd`, enter your fan-server account privately, and press
**Test connection**. On a fresh checkout, run `setup-fan-server-test.cmd` first.
The tester checks login, personas, lobby, primary connection and garage data
using your installed configuration. It does not join or drive a race yet.
Use **Save test report…** to export a report without credentials. See
[fan-server testing](docs/fan-server-testing.md) for instructions and limits.

The C++20 migration is underway. See the [recovery ledger](docs/recovery-ledger.md)
for outstanding systems and the [native migration guide](docs/native-migration.md)
for module boundaries and verification gates. The native build currently contains
recovered valuation, placeholder insertion/pruning, component ordering/linking and count/cost totals, bounded VIV directories, MCOTS packet framing,
plain NPS framing and the channel payload codec, a restricted Lua execution
harness, and an optional SDL/OpenGL asset garage.
The garage renders original FCE geometry and supported FSH textures with orbit/zoom controls; native driving
and complete customization remain unfinished.

The recovered assembly passes are connected through an explicit
[postload research interface](docs/owned-postload.md). Original descriptions
remain incomplete and must be supplied explicitly for enriched comparisons.

With CMake 3.24+ and a C++20 compiler installed:

```sh
cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --config Release --parallel
ctest --test-dir build/native -C Release --output-on-failure
```

The first configuration downloads hash-pinned Lua 5.4.8 sources. Enable
`-DMCO_BUILD_PLATFORM=ON` to also build the SDL3/OpenGL 3.3 garage and context probe
using hash-pinned SDL 3.2.28 sources. Launch the garage with:

```sh
build/native/mco_native_garage --data '/path/to/Motor City Online' --model data/models/32ford.viv
```

On Windows multi-configuration builds, use `build/native/Release/mco_native_garage.exe`.
See [native garage](docs/native-garage.md) for controls and validation limits.
Use `-DMCO_BUILD_SCRIPTING=OFF` for an offline, dependency-free calculation build.
The Python application below remains the playable research harness.

The [data mod kit alpha](docs/mod-kit-tutorial.md) includes versioned manifests,
dependency checks, explicit resource replacements, previews and reproducible
packages. Start with `python -m tools.modkit validate examples/mods/garage`.
Game loading and Lua gameplay hooks remain future integration work.
The [offline Lua registration alpha](docs/mod-lua-alpha.md) provides a typed
native content registry and inspection events. Directory/ZIP script packages now
run through the native sandbox using `python -m tools.modkit script` with the
built `mco_mod_script` runner; game resource loading remains unfinished.

The [standalone unboosted engine core](docs/calculations/cylinder-cycle.md)
reproduces all nineteen dyno knots for verified records. Boost, final curve
corrections and driving-force integration remain unfinished. A
[private local account check](docs/online-account.md) and a
[fan-server flow check](docs/fan-server-testing.md) are available for configured
shard preflight and optional live lobby, primary MCOTS and garage startup checks;
no live race acceptance has yet been demonstrated.

The recovered [vehicle update controller](docs/calculations/vehicle-update.md)
and [callback scheduler](docs/scheduler.md) now have Python/C++ implementations
and original-code comparisons. The controller preserves conditional stage order,
force clearing and motion arithmetic; the scheduler preserves alternating force
and pose dispatch. Authentic child-stage inputs, full integration and measured
clock behavior remain required before replacing the playable driving prototype.

The native calculation library also includes the recovered [engine startup and
mode dispatcher](docs/calculations/engine-update.md), [body resistance](docs/calculations/body-resistance.md),
[axle-load adjustment](docs/calculations/body-vertical-load.md) and
[orientation/support preparation](docs/calculations/vehicle-preparation.md).
Each documents original-function comparisons and remaining input dependencies.
The connected [environment/body calculation](docs/calculations/wind-drafting.md)
now includes original wind and cross-car drafting. [Control smoothing](docs/calculations/control-update.md)
and [engine condition/heat calculations](docs/calculations/drivetrain-links.md)
are also recovered. The next playable milestone is one stock car on one original
track using the connected recovered simulation; it is still unfinished.

Requires Python 3.11+ and an OpenGL 3.3 driver. The stock catalogue uses the optional portable Access database reader.


### Test MotorCity Revival (fan server)

If your installed client already points at the fan shard, you can verify the reconstructed login path without replacing the original game.

**Windows (easiest):**

1. Clone or open this repo: [motor-city-reconstruction](https://github.com/Dadud/motor-city-reconstruction)
2. **One-time setup:** double-click `setup-fan-server-test.cmd` (creates `.venv` and installs `network` + `catalogue` extras for login and optional part enrichment)
3. **Preflight only** (no password): from the repo, run fan-server check without `--login` (see [fan-server testing](docs/fan-server-testing.md)).
4. **Live connection test**: double-click `test-fan-server.cmd` for the GUI, or `test-fan-server-live.cmd` for command-line login and garage-data access.

Enter your fan-server account when prompted. Passwords are not saved or logged.
The window reports the stage of any failure. Use **Save test report…** to export
a report without credentials or persona names. Racing is not yet implemented in
this tester; a successful connection test does not establish race compatibility.

See [fan-server testing](docs/fan-server-testing.md) for success fields and CLI
flags. The optional race-entry probe reports missing recovery work; it does not
join a race.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[catalogue]"
.\.venv\Scripts\motor-city.exe --data 'C:\Program Files (x86)\EA Games\Motor City Online' --vehicle 101 --track Drag --drive
```

### Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[catalogue]'
.venv/bin/motor-city --data '/path/to/Motor City Online' --vehicle 101 --track Drag --drive
```

For a model-only garage preview, omit `--vehicle` and `--track`, and use `--model 32ford.viv`.

Drag to orbit, scroll to zoom, Left/Right to browse models, `W` for wireframe, `F11` for fullscreen, and Escape to close. In track view, Home focuses the car and End shows the overview. The data path is remembered after an interactive launch.

In driving mode, Up accelerates, Down/Space brakes, Left/Right steers, and Shift+Up reverses. Use R to reset, P to pause/resume and PageUp/PageDown to change tracks. Losing window focus pauses driving. Pass yellow checkpoint frames in order to finish a sprint or record a lap. Missing wheel support stops the car; original object collision response is not implemented. Omit `--drive` for a parked scene.

## Develop

```sh
python -m pip install -e '.[catalogue]'
python -m unittest discover -s tests -v
motor-city --help
```

The tests use synthetic fixtures and run without original game assets or a graphics window. See [CONTRIBUTING.md](CONTRIBUTING.md) for environment setup, conventions and validation.

## Find your way around

| Location | Purpose |
| --- | --- |
| `client/` | Portable application, asset decoders, scene assembly and simulation code |
| `tools/` | Asset inspection and optional CPU-emulation comparisons |
| `tests/` | Asset-free unit tests |
| `docs/architecture.md` | Module map and data flow |
| `docs/usage.md` | Detailed controls, command examples and supported formats |
| `docs/roadmap.md` | Work needed to reach a playable client |
| `docs/research.md` | Evidence standards and optional verification workflow |
| `docs/calculations/` | Explanations of recovered original engine, gas-flow and vehicle calculations |
| `docs/mod-dev-kit.md` | Mod kit implementation status and extension boundaries |
| `docs/mod-kit-tutorial.md` | Working data package, preview and replacement examples |
| `docs/networking.md` | Configured fan server, protocol research and discovery/certificate checks |
| `docs/nps-transport.md` | TCP connection lifecycle, framing, deadlines and verification limits |
| `docs/binary-login-service.md` | Account login acknowledgement/result sequence and retained client key |
| `docs/https-authorization.md` | Certificate-pinned account authorization and ticket handoff |
| `docs/persona-protocol.md` | Original persona retrieval, identity fields and activation messages |
| `docs/lobby-service.md` | Queue, plaintext lobby login and persistent encrypted message transport |
| `docs/online-account.md` | Integrated authorization, persona selection, lobby and primary entry API |
| `docs/mcots-login.md` | Recovered MCOTS task flow and native login record |
| `docs/mcots-encryption.md` | MCOTS attachment key source and verified persistent RC4 calculation |
| `docs/mcots-responses.md` | Transaction correlation, attachment completion and native error mapping |
| `docs/mcots-login-success.md` | Bounded login-success fields and unresolved service records |
| `docs/mcots-transport.md` | Persistent MCOTS TCP framing and recovered service attachment routing |
| `docs/mcots-compression.md` | PKWARE DCL decoder and original incoming transformation order |
| `docs/mcots-session.md` | Integrated persistent encryption, decompression and keepalive handling |
| `docs/mcots-primary-service.md` | Integrated primary attachment and encrypted login exchange |
| `docs/post-login-data.md` | Original post-login data managers, requests and local cache boundaries |
| `docs/owned-part-loading.md` | Owned-instance fields and original car population before metadata enrichment |
| `.github/workflows/` | Windows/Linux automated checks |

REA is not included and is not a development dependency. Optional emulation tools require `pip install -e '.[oracle,catalogue]'` and a local original executable; the client does not execute that executable.

## License and assets

The newly authored code is [MIT licensed](LICENSE). Original game files, decompiled pseudocode, textures, models, music and local research outputs are excluded from this repository. Supply your own installation through `--data`; the client leaves that installation unchanged. The MIT license applies to this project's authored code, not to the original game's content.


