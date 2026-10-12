# Contributing

Start with the [architecture map](docs/architecture.md) and [roadmap](docs/roadmap.md). This is an early reconstruction; keep implemented behavior distinct from experiments and unfinished features.

## Set up a development environment

Clone the repository and create a virtual environment with Python 3.11 or newer.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[catalogue]"
```

Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[catalogue]'
```

Run `python -m unittest discover -s tests -v` and `motor-city --help`. Launch instructions are in the README. Catalogue and graphics dependencies are installed from the package metadata; tests do not require game assets.

## Make a change

1. Create a branch for one concrete behavior or fix.
2. Read the relevant module and tests before changing it.
3. Keep decoding and numerical code independent of the UI. Reject malformed inputs with useful errors and bounded reads.
4. Add meaningful synthetic tests for behavior changes. Do not commit original assets, native binaries, database exports, decompiled code, credentials or personal settings.
5. Run the tests and describe what you verified. For rendering changes, check a real window locally and record the driver/platform; headless tests do not prove rendering works.
6. Update the relevant usage or architecture document when behavior changes.

## Fidelity and numerical changes

Preserve original storage precision and operation order where recovered behavior depends on them. Evidence comments in the numerical modules identify native address ranges. A passing comparison covers its sampled inputs; it does not establish a complete game or hardware-equivalent execution.

Optional developer comparisons use Unicorn, not REA. See [research.md](docs/research.md). Keep their output under ignored `evidence/`.

## Build

```sh
python -m pip wheel . --no-deps --wheel-dir dist
```

The wheel contains authored Python modules and the license. Original game content stays external. `dist/`, virtual environments, generated evidence and local settings are ignored.

## Pull requests

Explain the concrete problem, resulting behavior and relevant validation. Note any remaining fidelity or platform limitations. Windows and Ubuntu CI run asset-free checks; manual graphics verification is separate.
