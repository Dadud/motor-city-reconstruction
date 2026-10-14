# Disk script bridge verification

On Windows, the native `mco_mod_script` executable built with the existing Zig
C++20/Ninja configuration in `build/native-check`. Lua is the existing pinned
5.4.8 dependency. This implementation connects authored disk packages to the
existing typed offline sandbox; it does not recover game physics or server packets.

Local checks:

- Native build and CTest: all 16 native checks passed.
- Python suite with `MCO_SCRIPT_RUNNER` set: all 494 tests passed.
- Authored example: native execution returned the seeded vehicle metadata,
  Lua-registered UI metadata, and the inspect event note.
- Directory/ZIP equivalence, exact script selection, reproducible packaging,
  no-overwrite behavior, invalid identities/paths, duplicate JSON keys, invalid
  UTF-8, source limits and malformed bridge lengths were exercised.
- Real native execution rejected infinite loops, unavailable process access,
  duplicate resource registration and script errors. Inspect/preview handler
  isolation was checked in separate fresh states.

Reproduce from the repository root after building:

```powershell
$env:MCO_SCRIPT_RUNNER = (Resolve-Path build/native-check/mco_mod_script.exe).Path
python -m unittest discover -s tests -q
python -m tools.modkit script examples/mods/garage-script --runner $env:MCO_SCRIPT_RUNNER
```

The Windows/Linux native CI matrix now runs the disk bridge tests with its built
runner. Linux execution is not claimed by the local Windows results; inspect the
published CI run before declaring that platform verified.

Remaining completion gates: script dependencies/replacements, actual game
resource loading, race lifecycle events, read-only gameplay state and independent
developer acceptance. Online baseline behavior is unchanged.
