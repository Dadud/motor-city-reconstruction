# Motor City Reconstruction

An open-source reconstruction of the Motor City Online client for modern Windows and Linux. It reads game assets from your own local installation.

**Current status:** the garage and textured vehicle/track renderer work on Windows. The vehicle remains parked. Driving, complete engine simulation, sound, online services and multiplayer are unfinished. Linux runtime support is being developed and has not yet been verified.

## Quick start

Requires Python 3.11+ and an OpenGL 3.3 driver. The stock catalogue uses the optional portable Access database reader.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[catalogue]"
.\.venv\Scripts\motor-city.exe --data 'C:\Program Files (x86)\EA Games\Motor City Online' --vehicle 101 --track Boothill
```

### Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[catalogue]'
.venv/bin/motor-city --data '/path/to/Motor City Online' --vehicle 101 --track Boothill
```

For a model-only garage preview, omit `--vehicle` and `--track`, and use `--model 32ford.viv`.

Drag to orbit, scroll to zoom, Left/Right to browse models, `W` for wireframe, `F11` for fullscreen, and Escape to close. In track view, Home focuses the car and End shows the overview. The data path is remembered after an interactive launch.

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
| `.github/workflows/` | Windows/Linux automated checks |

REA is not included and is not a development dependency. Optional emulation tools require `pip install -e '.[oracle,catalogue]'` and a local original executable; the client does not execute that executable.

## License and assets

The newly authored code is [MIT licensed](LICENSE). Original game files, decompiled pseudocode, textures, models, music and local research outputs are excluded from this repository. Supply your own installation through `--data`; the client leaves that installation unchanged. The MIT license applies to this project's authored code, not to the original game's content.
