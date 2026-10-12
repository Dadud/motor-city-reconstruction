# Verification and research

The repository contains newly authored reconstruction code. Original binaries, raw decompilation output, database exports and generated evidence remain local and are excluded from Git and packages.

## Evidence standards

Separate static interpretation, CPU-emulated observations and actual game/client runtime checks. Record the source hash, input coverage, numerical precision and known limitations. Address references in code identify the source instruction ranges, not original source-code recovery.

Asset tests use synthetic fixtures. Runtime decoding of local original assets is a separate development check. The current numerical comparisons use one verified x86 executable build with SHA-256 `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`; they reject other builds.

## Optional CPU oracle

```sh
python -m pip install -e '.[oracle,catalogue]'
python -m tools.verify_stock_dyno '/path/to/game' --vehicle 101 --output evidence/stock-dyno.json
python -m tools.verify_dyno_work '/path/to/game' --geometry-only --output evidence/preparation.json
python -m tools.verify_dyno_lift '/path/to/game' --output evidence/lift.json
python -m tools.verify_dyno_flow '/path/to/game' --output evidence/flow.json
python -m tools.verify_dyno_area '/path/to/game' --output evidence/area.json
python -m tools.verify_cylinder_state '/path/to/game' --output evidence/cylinder-state.json
```

Create the `evidence/` directory first. Each command needs your local installation; no binary is downloaded. The oracle uses Unicorn 2.1.4, bounded instruction execution and x87 control word `0x27f`. It does not run the original game entry point, implement Windows imports, connect to game services or prove original hardware behavior. REA is not included or required.

## Current validation snapshot

- 104 synthetic unit tests passed on Windows before initial publication.
- Core builder inputs match 199 supported stock records given identical assembled component fields; native component-loader equivalence remains unproven.
- Geometry, valve events, normalized flow and cam profiles match supported stock inputs.
- 3,582 sampled valve lifts, 2,358 interpolation samples and 5,970 coupled airflow areas matched their native emulated ranges.
- Cylinder initialization matched 4,179 stored fields across 199 engines and three pressure inputs. Only 44.1 is the recovered first-cycle pressure; 15 and 80 are synthetic probes, not recovered running pressures.
- Thirteen unsupported stock assemblies remain explicitly rejected.
- Complete pressure integration, final engine curves and playable driving remain unfinished.

Re-run the relevant comparison after changing a numerical stage. Detailed private development notes stay under ignored `evidence/`; this document summarizes the reproducible public workflow.
