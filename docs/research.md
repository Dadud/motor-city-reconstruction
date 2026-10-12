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
python -m tools.verify_exhaust '/path/to/game' --output evidence/exhaust.json
python -m tools.verify_cycle_preparation '/path/to/game' --output evidence/cycle-preparation.json
python -m tools.verify_mass_exchange '/path/to/game' --output evidence/mass-exchange.json
```

Create the `evidence/` directory first. Each command needs your local installation; no binary is downloaded. The oracle uses Unicorn 2.1.4, bounded instruction execution and x87 control word `0x27f`. It does not run the original game entry point, implement Windows imports, connect to game services or prove original hardware behavior. REA is not included or required.

## Current validation snapshot

- 136 synthetic unit tests passed on Windows after cylinder energy terms were introduced.
- Cylinder temperature-dependent capacity and energy terms at 0x47ae8f–0x47af0b matched 20,000 stored float32 fields across 10,000 synthetic positive temperature inputs. This verifies the isolated polynomials under bounded x86 emulation; physical units, accumulated energy and complete temperature evolution remain unverified. Reproduce with `python -m tools.verify_cylinder_energy '/path/to/verified/executable'` and optional Unicorn installed.
- Core builder inputs match 199 supported stock records given identical assembled component fields; native component-loader equivalence remains unproven.
- Geometry, valve events, normalized flow and cam profiles match supported stock inputs.
- 3,582 sampled valve lifts, 2,358 interpolation samples and 5,970 coupled airflow areas matched their native emulated ranges.
- Cylinder initialization matched 4,179 stored fields across 199 engines and three pressure inputs. Only 44.1 is the recovered first-cycle pressure; 15 and 80 are synthetic probes, not recovered running pressures.
- Exhaust preparation matched 16,720 fields across all seven modes, 199 supported engines and 19 RPM knots.
- Coupled charge-temperature selection, cycle preparation, phase factor, exhaust wave and intake boundary evaluation matched 59,342 fields across 199 engines and synthetic mode/boost/boundary probes. Intake scaling preserves intermediate float32 stores, post-store boost addition and native negative values. Physical units and complete cylinder-pressure evolution remain unverified.
- Intake/exhaust mass exchange and intake pressure feedback matched 220,157 float32 fields: 1,800 synthetic probes and 29,651 sampled native cycle states across all 199 supported engines and 19 RPM knots. The sampled transfers include 13,578 positive, 3,925 negative and 41,799 zero deltas. Exact-address emulator hooks observe inputs/outputs without replacing instructions; samples are bounded to every 64th call and at most 32 per RPM. These are stage comparisons, not a portable full-cycle or original hardware validation.
- Thirteen unsupported stock assemblies remain explicitly rejected.
- Complete pressure integration, final engine curves and recovered driving physics remain unfinished.

## Offline driving checks

The authored prototype is independent of the native numerical oracle. A Ford 101 completed the 804.3 m Drag sprint through 28 gates in 23.33 simulation seconds, including the actual Windows input/update/OpenGL rendering path. Steering, reverse, braking, frame-rate independence, support rejection and race order have synthetic tests. This does not establish original force fidelity or Linux graphics compatibility.

The [Linux graphics CI run](https://github.com/Dadud/motor-city-reconstruction/actions/runs/38286486337) also passed the actual client render/capture path with a generated triangle. Its runtime report records Linux x86_64, Python 3.13.16, llvmpipe LLVM 20.1.2 and OpenGL 4.5 Mesa 25.2.8. The test checks visible central-framebuffer pixels. It validates software-rendered garage operation, not original-asset driving, hardware drivers or multiplayer on Linux.

```sh
python -m tools.verify_driving '/path/to/game' --output evidence/drag-sprint.json
motor-city --data '/path/to/game' --vehicle 101 --track Drag --drive --verify-driving --verify-race --screenshot evidence/drag-finish.png
python -m tools.graphics_smoke --output evidence/graphics-smoke.png
```

Re-run the relevant comparison after changing a numerical stage. Detailed private development notes stay under ignored `evidence/`; this document summarizes the reproducible public workflow.
