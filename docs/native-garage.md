# Native garage geometry milestone

The C++20 `mco_native_garage` executable loads the installed original vehicle archive and draws its actual FCE triangles with SDL3 and OpenGL 3.3. It is a geometry inspection milestone, with a neutral shaded surface. Original textures, damaged geometry, animation, garage UI, and gameplay are not implemented here.

Build with `MCO_BUILD_PLATFORM=ON`. SDL3 is the repository's pinned dependency; OpenGL functions are obtained from SDL, without another loader dependency.

```text
mco_native_garage --data "C:\Program Files (x86)\EA Games\Motor City Online" --model data/models/32ford.viv
mco_native_garage --data /path/to/MotorCityOnline --model data/models/32ford.viv --smoke
```

`--data` points to the installation root containing `Data`. `--model` is a relative archive path. ASCII case-insensitive path lookup works on Windows and Linux. Ambiguous case matches, traversal and symlinks escaping the root are rejected. Files are opened read-only; no proprietary assets are copied into this repository.

Drag with the left mouse button to orbit; use the mouse wheel to zoom; press Escape to exit. The window resizes. The initial camera centers and scales all part positions including their FCE origins. Smoke mode loads the model, compiles shaders, uploads triangles, draws a hidden frame and reads its pixels, requiring at least 100 foreground pixels and no GL error. A successful context alone does not pass.

The bounded decoder accepts observed FCE versions `0x101014` and `0x101015`, checks table and part ranges and overlap, local face indices, names and finite positions/UVs. It caps geometry at one million vertices and two million triangles, archive reads at 256 MiB, and FCE members at 64 MiB. It preserves UVs, texture-page identifiers and flags for future rendering work. Non-finite original normals are rebuilt from adjacent faces with a warning, matching the existing Python decoder's repair policy. Unsupported versions and malformed assets produce explicit errors.

`mco_fce_test` uses authored synthetic bytes to exercise a valid triangle, origins, truncation, unsupported format, overlapping tables/parts, out-of-range faces and parts, unterminated names, geometry budgets, non-finite positions and normal repair. `mco_fce_compare ROOT MODEL` emits original local positions and part counts for comparison with `client.fce`; its output should remain outside the public source tree. No original bytes are test fixtures.

For a reproducible local comparison against every installed model:

```text
python tools/compare_native_fce.py build/native-zig/mco_fce_compare.exe "C:\Program Files (x86)\EA Games\Motor City Online"
```

The installed dataset passed comparison for 315 archives and 99,608 local vertex positions, including each part's origin and vertex/triangle count. The Windows original `32ford.viv` smoke rendered 53 parts, 1,369 vertices and 2,294 triangles, with 25,803 foreground pixels. An optional `--capture frame.ppm` saves the actual rendered frame for inspection; keep screenshots of original geometry outside published sources.

CI without original assets can generate an authored tetrahedron:

```text
python tools/native_garage_fixture.py build/garage-fixture
mco_native_garage --data build/garage-fixture --model data/models/synthetic.viv --smoke
```

Linux needs a working OpenGL 3.3 driver/display (for CI, an Xvfb display with Mesa software rendering). This synthetic fixture validates the decoder/upload/shader/render path without implying that original geometry or assembly was exercised. The corresponding Windows smoke passed with 26,274 foreground pixels.
