# Motor City Online reconstruction

A growing open-source client that reads a local Motor City Online installation.
The garage and combined vehicle/track renderer run on Windows with OpenGL,
resizable windows, orbit/zoom controls, browsing, and part isolation. Linux
rendering passes a generated-geometry Xvfb/Mesa smoke check; original-asset
driving on Linux remains unverified. Offline driving and time trials use an authored
prototype model. Static track scenery can be previewed with recovered lighting,
textures and detail gates; animated scenery/effects, complete vehicle rendering,
recovered force physics, sound, login, economy and multiplayer remain to implement.

For offline driving, add `--vehicle 101 --track Drag --drive`. Up accelerates,
Down/Space brakes, Left/Right steers, and Shift+Up reverses. R resets and P
pauses/resumes. PageUp/PageDown changes tracks; Home follows the car and End
shows the overview. Pass yellow gates in order. A sprint stops on its finish
screen; R starts again. Lap records last for the current session. Terrain edges
stop the car, but object collisions and airborne motion are not implemented.

The garage defaults to all model parts, including mutually exclusive
customization variants. Body previews select the recovered component groups.
Stock assembly previews place tires, hubcaps and the engine block at body markers.
Tire dimension scaling, suspension stance and nested engine components remain
unfinished; this is not yet a fully reconstructed vehicle assembly.

Requires Python 3.11+ and an OpenGL 3.3 driver. Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\motor-city.exe --data 'C:\Program Files (x86)\EA Games\Motor City Online'
```

Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/motor-city --data '/path/to/Motor City Online'
```

After interactive launch the data folder and model are saved in per-user settings,
allowing subsequent launches to omit `--data`. Asset lookup is case-insensitive on
both platforms. Client settings never write into the installed game folder.

Drag to orbit, scroll to zoom, Left/Right to browse, Tab to isolate a part,
brackets to select a part, W for wireframe, F11 for fullscreen, Escape to close.
Press V to cycle all parts, standard, chopped and convertible body previews,
plus stock selection when a vehicle identity is loaded.
Use `--body-style standard` to select a preview at startup. These profiles choose
visual equipment; they do not represent the recovered stock configuration.
Profiles use available named groups; a car without a separate roof variant
cannot acquire that variant. Attachment markers are excluded from body previews.
Use `--model 64gto.viv` to select an archive at startup. Capture a hidden render:

```sh
motor-city --data /path/to/game --model 32ford.viv --screenshot evidence/garage.png
```

Models use their embedded `part.fsh` when present. Select an external skin with
`--skin 32for001.fsh` (from `Data/Skins`). Stock skin selection, paint customization
and the full original material behavior remain to recover.

Show a stock vehicle at a track's starting road slice:

```sh
motor-city --data /path/to/game --vehicle 101 --track Boothill --skin 32for001.fsh
```

This loads textured base track geometry and the stock body, tires, hubcaps and
engine block. Vehicle geometry has its own texture namespace and world transform.
The spawn pose uses four terrain supports and database tire radii. Home returns
the camera to the car; End shows the track overview. This command keeps the
vehicle parked. Add `--drive` for authored prototype driving and time trials;
recovered suspension settling and force physics remain unfinished.

The following research tools use only the Python standard library:

```sh
python tools/catalog.py /path/to/game evidence/catalog.json
python tools/viv.py /path/to/game/Data/Models/32ford.viv
python -m unittest discover -s tests -v
```

The archive reader validates BIGF/BIG4 directory and member bounds, duplicate
names, and overlapping payloads. It reads members without writing their filenames
to disk. It does not decompress or interpret member contents.

104 tests pass on Windows. All 344 installed VIV archive directories pass
validation; all 315 model archives decode. Two cars contain NaN normals, which
are reported and rebuilt from adjacent triangles. Windows OpenGL renders of
32ford and 64gto were captured and inspected. All 301 model FSH members and 842
standalone FSH files decode. A textured Ford render passed the control checks.
QFS bounds, overlapping backreferences, channel order and DXT alpha have synthetic
fixture tests. Texture decoding covers supported SHPI formats and the first mip
level; successful decoding alone does not prove every material renders correctly.
GitHub Actions runs asset-free checks on Windows and Ubuntu. These checks do
not verify an interactive Linux graphics session; Linux rendering remains
unverified.

Newly authored tools are MIT licensed. This license does not cover the original
game binaries, recovered pseudocode, third-party mods, artwork, or music.
Original assets stay in the user's installation and the client loads an explicit
local data path. Redistribution of assets needs its own license.

The FCE layout was corroborated against the MIT-licensed
[LibOpenNFS parser](https://github.com/OpenNFS/LibOpenNFS/tree/main/NFS4/PC/FCE)
and supplied files. This parser implementation is newly authored. REA pseudocode
stays in local research evidence, separate from client source.

See [research.md](research.md) for validation methods and [roadmap.md](roadmap.md) for remaining work.

Optional stock vehicle catalogue (portable Jet file reader):

```sh
python -m pip install -e ".[catalogue]"
motor-city --data /path/to/game --list-vehicles
motor-city --data /path/to/game --vehicle 101 --skin 32for001.fsh
motor-city --data /path/to/game --vehicle 101 --stock-parts
```

Vehicle selection joins stock assembly rows to their body archive. The component
recipe preserves attachment IDs and configuration flags; components are not yet
fully assembled in the renderer. Of 212 stock vehicle entries here, 204 resolve to an
available body archive, seven reference absent archives, and one has no stock
assembly. Missing bodies report an error. The parser reports unsupported system
metadata chunks and verifies stock table column lengths against declared row counts.

`--vehicle` defaults to stock body-group selection: the recovered flag rules use
component types, front/rear attachment IDs, filename choices and available mesh
groups. They cover roof, fenders, bumpers, boards, skirts, hood/scoops, cage and
mirrors. `--body-style standard` overrides this with a preview choice. Stock
selection includes body groups and an attachment preview; wheel sizing, nested engines, paint and
the full original rendering behavior still need reconstruction.

Track road-corridor preview:

```sh
motor-city --data /path/to/game --track Boothill
motor-city --data /path/to/game --track Boothill --track-mesh
motor-city --data /path/to/game --track Boothill --track-mesh --track-textures --track-view start
motor-city --data /path/to/game --track Boothill --track-objects --track-view start --track-detail 2
motor-city --data /path/to/game --track Boothill --track-objects --track-animation-tick 12 --track-view start
```

This reads original FRD road-slice positions, basis vectors and limits. Left/Right
browse the 27 day tracks. All 58 supplied FRD variants pass slice parsing. The
corridor is a preview. `--track-mesh` renders decoded base track block geometry;
`--track-textures` applies recovered UV-table references and day FSH pages.
`--track-objects` combines base geometry with scenery, applies the
selected `Tr.ini` ambient vertex colors, and loads the day texture pages. It
accepts native detail presets `0..4` through `--track-detail`; the default 0
keeps all detail gates visible. Type-3 animated objects are omitted unless
`--track-animation-tick` selects an integer sample time; at that tick, the
recovered quaternion transform is applied to their vertices. This is a sampled
preview, not a real-time animation loop. Track-and-vehicle world views enable
the scenery preview automatically.
Home focuses the first road slice; End returns to the overview. Animated material
material effects, continuous animation playback, object collision response and
original driving physics are not implemented.
The final slice is not automatically joined to the
first, and the corridor limits do not establish pavement widths.

The recovered FRD spatial-index reader also passes all 58 track variants and
consumes each file exactly through EOF. It preserves nested cells and leaf IDs;
REA confirms that each leaf ID pairs a block index with a surface-descriptor
index, which refers to a high-detail quad. The surface reader validates all such
references across all 58 tracks. Its native X/Z containment lookup identifies
upward-facing surfaces at 60,637 of 61,976 road-slice positions. All those hits
produce finite heights and unit normals using the native quad diagonal and plane
projection. The 1,339 lookup misses persist with the upward-facing filter disabled;
their cause and vehicle collision response still need investigation.

An optional authored contact lookup selects the containing surface nearest a
reference height, avoiding the wrong level at overlapping roads. With an explicit
0.001-track-unit edge tolerance, it samples 61,472 of 61,976 road positions across
all 58 tracks. The maximum difference from stored road height is 0.154 track units.
Exact native candidate-order lookup remains available; 504 positions still miss.

The contact module transforms all four recovered FCE wheel markers into world
coordinates and samples terrain independently at each wheel. It reports height,
normal and vertical tire-bottom clearance, with explicit missing contacts.
Tire radii must be supplied to the low-level contact API; the stock contact report
resolves them from recovered tire dimensions. Suspension forces remain unfinished.
The Ford body at Boothill resolves all four contacts, but does not establish
production ride height or driving behavior.

The recovered tire formula now converts named width/aspect/rim dimensions into
physical radius. It separately preserves the original large-tire stance allowance
above 0.37 meters. REA confirms the database binding for tire Val1/Val2/Val3;
all 540 tire records validate. The stock catalogue resolves explicit wheel or
front/rear axle tires for 211 vehicles, rejecting missing or ambiguous physics.
Automatic sizing in the rendered assembly and suspension response remain unfinished.

Inspect stock tire contacts and initial track placement without opening a window:

```sh
motor-city --data /path/to/game --vehicle 101 --track Boothill --contact-report
```

This reports four wheel contacts, verified tire dimensions, stock spring/shock
configuration for each wheel, and core engine-block dimensions, plus an authored
spawn pose that clears every tire above its sampled terrain by at least 0.02 meters.
Missing wheel supports fail explicitly. It preserves orientation and does not
simulate suspension settling. The authored offline driving mode uses a separate
terrain-following model; recovered suspension and tire forces remain unfinished.

`client.motion` implements recovered arithmetic with distinct intervals:
velocity increments use 1/32 second, position/rotation increments use 1/64 second,
and terrain look-ahead uses 1/48 second. Pose updates preserve the moving center
of mass during rotation. These helpers supply no force law or inactive-motion
behavior; the complete native scheduling frequency is still under investigation.
Python arithmetic is not claimed to reproduce the original x87 precision exactly.

Stock engine-block resolution validates the recovered mass, bore, stroke,
displacement and cylinder-count fields for 211 assembled vehicles. Stored
displacement is preserved even when it differs from a dimensional calculation.
`client.engine.TorqueCurve` implements the native assembled-table interpolation
and power conversion; generating stock torque tables from the recovered dyno
solver and engine components remains unfinished. Physics rows are not torque curves.


Optional dyno emulation checks (development only):

```powershell
python -m pip install -e ".[oracle]"
python -m tools.verify_dyno "C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe" --output evidence/dyno-intake-oracle-comparison.json
```

This compares a recovered solver term with CPU emulation of your local executable. It does not launch the game and is not required to run the client. Full torque generation remains unfinished.

The portable mechanical-loss and work-to-output stages match all 18,905 float32
fields across 199 supported stock engines. This comparison supplies intermediate
work values from the original emulated solver; pressure/airflow integration is
still unfinished. Reproduce the development comparison with:

```powershell
python -m tools.verify_dyno_work "C:\Program Files (x86)\EA Games\Motor City Online" --output evidence/dyno-work-output-comparison.json
```

The cylinder geometry and valve-event setup each match all 1,194 fields across
those engines. Seventy-two synthetic timing/advance/valve-count variants also
match the original event preparation. Use `--geometry-only` with the same
command for the faster geometry and valve-event comparison.
That comparison now also verifies 4,179 normalized flow fields across the
199 engines. Cam-profile construction matches another 2,388 fields across
the same engines, plus 18 synthetic timing/train/advance variants.
Valve-lift evaluation matches 3,582 sampled double values across the stock
engines, plus 36 synthetic boundary/clamp cases. Airflow interpolation matches
2,358 sampled doubles across all 131 distinct supported stock tables; the
adjacent pressure correction matches 64 synthetic cases. Their coupled valve
areas match 5,970 float32 samples across 199 engines with synthetic pressure
ratios. Cylinder-pressure integration remains unfinished.

```powershell
python -m tools.verify_dyno_lift "C:\Program Files (x86)\EA Games\Motor City Online" --output evidence/dyno-valve-lift-comparison.json
python -m tools.verify_dyno_flow "C:\Program Files (x86)\EA Games\Motor City Online" --output evidence/dyno-flow-interpolation-comparison.json
python -m tools.verify_dyno_area "C:\Program Files (x86)\EA Games\Motor City Online" --output evidence/dyno-airflow-area-comparison.json
```


Capture a stock-derived core dyno result for comparison while developing the portable solver:

```powershell
python -m tools.verify_stock_dyno "C:\Program Files (x86)\EA Games\Motor City Online" --vehicle 101 --output evidence/ford-stock-core-dyno-oracle.json
```

The core record excludes unported special carb/boost cases and final curve corrections. Builder byte equality is verified for 199 supported stock-derived assembled records under CPU emulation. Original component-loader equivalence remains unverified.
