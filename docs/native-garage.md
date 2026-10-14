# Native garage geometry milestone

The C++20 `mco_native_garage` executable loads the installed original vehicle archive and draws its actual FCE triangles with SDL3 and OpenGL 3.3. It is a geometry and texture inspection milestone. Where an archive contains `part.fsh`, the renderer samples its decoded texture pages using original FCE UV coordinates. Missing pages retain a neutral shaded surface. Damaged geometry, animation, assembled wheels, garage UI, and gameplay are not implemented here.

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

CI without original assets can generate an authored tetrahedron and checker texture:

```text
python tools/native_garage_fixture.py build/garage-fixture
mco_native_garage --data build/garage-fixture --model data/models/synthetic.viv --smoke
```

Linux needs a working OpenGL 3.3 driver/display (for CI, an Xvfb display with Mesa software rendering). This synthetic fixture validates geometry/texture decoding, GPU upload, sampling and rendering without implying that original geometry or assembly was exercised. The corresponding Windows smoke passed with one texture page and 26,274 foreground pixels.


Native texture support accepts direct-color SHPI types BGRA8888 (`0x7d`), BGR888 (`0x7f`), ARGB1555 (`0x7e`), RGB565 (`0x78`) and ARGB4444 (`0x6d`), including bounded outer-container and per-image RefPack/QFS decompression. It decodes only the first mip level. Indexed/paletted images and DXT compression remain explicit unsupported errors. Input is capped at 64 MiB, directory entries at 4,096, total pixels at 16,777,216 (64 MiB RGBA), and archive reads at 256 MiB. Attachment offsets and entry boundaries are checked before pixel reads.

All 254 installed `part.fsh` images (5,242,880 RGBA pixels) matched the existing Python decoder's names, dimensions and FNV64 decoded-byte checksums. Those images use ARGB1555, RGB565 and BGRA8888; one observed per-image QFS case is `69superbee.viv`. Reproduce without saving original pixel data:

```text
python tools/compare_native_textures.py build/native-zig/mco_textures_test.exe "C:\Program Files (x86)\EA Games\Motor City Online"
mco_native_garage --data "C:\Program Files (x86)\EA Games\Motor City Online" --model data/models/69superbee.viv --smoke --capture build/garage-textured.ppm
```

The textured Super Bee smoke passed with one texture page and 15,043 foreground pixels. Its captured frame was visually inspected. Original FCE page numbers select SHPI image order, matching the existing Python viewer; UV components are `uv[corner]` and `uv[corner+3]`. The diagnostic renderer samples RGB with opaque output. Alpha, triangle flags, visibility and authentic material/paint behavior are deliberately not inferred; decoded alpha remains preserved for later work. Separate skin selection is not implemented.

Asset-free texture tests cover all five direct-color types, compressed literal/backreference images, compressed outer containers, malformed sizes/offsets/dimensions/links, unsupported codecs, truncated QFS commands, invalid backreferences and output sizes. These tests validate decoding, while the original texture smoke exercises the GPU upload and sampling path.
