# Motor City Reconstruction

An open-source reconstruction of the Motor City Online client for modern Windows and Linux. It reads game assets from your own local installation.

**Current status:** Windows supports garage previews and offline driving/time trials on decoded tracks. The Linux OpenGL renderer passes a generated-geometry smoke check under Xvfb/Mesa; original-asset driving on Linux remains unverified. Driving uses an authored prototype bicycle model; recovered engine and force simulation, object collisions, sound, online services and multiplayer remain unfinished.

## Quick start

Requires Python 3.11+ and an OpenGL 3.3 driver. The stock catalogue uses the optional portable Access database reader.

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
| `docs/mod-dev-kit.md` | Planned add-on package format, extension boundaries and developer tools |
| `docs/networking.md` | Configured fan server, protocol research and discovery/certificate checks |
| `docs/nps-transport.md` | TCP connection lifecycle, framing, deadlines and verification limits |
| `docs/binary-login-service.md` | Account login acknowledgement/result sequence and retained client key |
| `docs/https-authorization.md` | Certificate-pinned account authorization and ticket handoff |
| `docs/persona-protocol.md` | Original persona retrieval, identity fields and activation messages |
| `docs/lobby-service.md` | Queue, plaintext lobby login and persistent encrypted message transport |
| `docs/online-account.md` | Integrated authorization, persona selection and lobby entry API |
| `docs/mcots-login.md` | Recovered MCOTS task flow and native login record |
| `docs/mcots-encryption.md` | MCOTS attachment key source and verified persistent RC4 calculation |
| `docs/mcots-responses.md` | Transaction correlation, attachment completion and native error mapping |
| `docs/mcots-login-success.md` | Bounded login-success fields and unresolved service records |
| `docs/mcots-transport.md` | Persistent MCOTS TCP framing and recovered service attachment routing |
| `docs/mcots-compression.md` | PKWARE DCL decoder and original incoming transformation order |
| `.github/workflows/` | Windows/Linux automated checks |

REA is not included and is not a development dependency. Optional emulation tools require `pip install -e '.[oracle,catalogue]'` and a local original executable; the client does not execute that executable.

## License and assets

The newly authored code is [MIT licensed](LICENSE). Original game files, decompiled pseudocode, textures, models, music and local research outputs are excluded from this repository. Supply your own installation through `--data`; the client leaves that installation unchanged. The MIT license applies to this project's authored code, not to the original game's content.
