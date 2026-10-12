# Architecture

The client separates file decoding, catalogue interpretation, scene assembly, numerical work and rendering. The application entry point is `client.app:main`, exposed as `motor-city`.

```mermaid
flowchart LR
    Files[Local game installation] --> Assets[assets.py: path lookup]
    Assets --> Decode[Archive / model / texture / track decoders]
    Assets --> Catalogue[catalogue.py: stock database]
    Decode --> Scene[scene.py / world.py: assembled scene]
    Catalogue --> Scene
    Catalogue --> Physics[Engine / tires / suspension / dyno inputs]
    Scene --> App[app.py: OpenGL renderer and controls]
    Physics --> Reports[Headless reports and verification]
```

## Module map

| Area | Modules | Responsibility |
| --- | --- | --- |
| Entry and preferences | `app.py`, `settings.py` | CLI, OpenGL window, camera controls, per-user preferences |
| Local content | `assets.py`, `tools/viv.py` | Explicit asset root, case-insensitive lookup, bounded archive reads |
| Vehicle geometry | `fce.py`, `textures.py` | Geometry and supported texture decoding, normal repair |
| Track geometry | `track.py`, `track_mesh.py`, `track_spatial.py`, `track_surface.py` | Track sections, rendered meshes, spatial lookup, road support |
| Catalogue | `catalogue.py`, `physics_data.py` | Portable database reading, stock components, typed physics rows |
| Assembly | `assembly.py`, `scene.py`, `world.py` | Body selection, attachments, vehicle/track world scene |
| Motion and contact | `motion.py`, `contact.py` | Recovered pose/velocity updates and wheel support geometry |
| Components | `engine.py`, `tires.py`, `suspension.py` | Component interpretation, dimensions and recovered calculations |
| Engine simulation | `dyno.py`, `dyno_solver.py` | External flow templates, input record, portable solver stages |
| Developer inspection | `tools/catalog.py`, `tools/query_fields.py` | Asset inventory and database-query metadata |
| Optional oracle | `tools/native_oracle.py`, `tools/verify_*.py` | Bounded CPU comparisons against a local verified executable |

## Boundaries

Decoders consume bytes or local paths and return typed data. Scene modules combine that data without importing the graphics window. Rendering is concentrated in `app.py`; it currently also owns input handling and should be split into rendering/input modules when the driving loop is introduced.

The runtime imports no emulation dependency. The optional oracle executes selected original instructions in an isolated CPU emulator for developer comparisons; it supplies no Windows services or original game entry point. The executable and comparison results are not packaged.

## Engine pipeline

`catalogue.py` assembles component-derived inputs. `dyno.py` loads the supported executable's local templates and serializes the core dyno record. `dyno_solver.py` implements verified geometry, timing, flow normalization, cam profiles, lift, interpolation, pressure correction, airflow areas and output conversion.

The thermodynamic loop joining those stages is incomplete. Original solver curves captured during development are comparison evidence, not a replacement for the portable solver. The client has no driving force loop yet.
