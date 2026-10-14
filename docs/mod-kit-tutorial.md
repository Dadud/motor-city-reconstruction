# Data mod kit alpha tutorial

The portable Python kit is usable now, without an original installation or extra
dependencies. Python 3.11 or newer is required. These packages are separate data
resources consumed by the kit registry and SVG preview tool. They do not yet
add cars, tracks, physics, audio playback or Lua hooks to the game runtime.
The C++ runtime and native game resource loaders do not consume this format yet.

## Edit, preview and distribute

Run from the repository root on Windows or Linux:

```sh
python -m tools.modkit validate examples/mods/garage
python -m tools.modkit inspect examples/mods/garage
python -m tools.modkit preview examples/mods/garage --resource example.garage:body --output body.svg
python -m tools.modkit package examples/mods/garage --output garage.zip
python -m tools.modkit validate garage.zip
python -m tools.modkit preview garage.zip --resource example.garage:road --output road.svg
```

Open `body.svg` in a browser. Edit `examples/mods/garage/body.json`: change
`color` to `#22c55e`, or change a vertex's first coordinate, then validate and
preview again. Use a fresh archive filename when packaging: existing archive
outputs are refused. The entire package directory is included, including its
license; distribute only files you authored or have permission to redistribute.
The examples contain wholly original geometry and metadata under MIT.
Packaging writes a temporary archive and atomically publishes it without
replacing an existing file. The output filesystem must support hard links
(for example NTFS or ext4); unsupported filesystems fail without publishing.

## Manifest contract

`manifest.json` must be at the root, with that exact case. Required fields are
`schema_version: 1`, `api_version: "data-alpha-1"`, `id`, `version`, `license`,
`author`, `dependencies` and `resources`. Unknown fields are errors. License
and author are declarations, not a legal compliance check. Versions use exact
`major.minor.patch` numbers without ranges or suffixes. IDs use lowercase ASCII
letters/numbers, with dots, underscores or hyphens between segments; each ID
starts with a letter and has at most 80 characters.

`dependencies` maps package IDs to exact versions. Each resource declares `id`
(`package-id:local-name`), `kind`, and exact-case relative JSON `path`. Supported
kinds are `vehicle`, `component`, `track`, `material`, `sound`, `ui`. All six
use the same limited alpha data envelope. No recovered numeric field semantics
are claimed. Namespaced IDs isolate authored packages from original numeric IDs.

## Resource data contract

Required resource fields: `schema_version: 1`, nonempty `label`. Optional fields:
`color` (`#RRGGBB`), `metadata` (an inert JSON object), `references` (a list of
namespaced IDs), `mesh` (vehicle/track only). Every reference must resolve in the
combined registry and reference an own resource or a declared direct dependency.
Metadata, including component/sound/UI metadata, is inspectable but does not
drive gameplay. Material colors are inspectable; the preview uses the geometry
resource's own color, not a material binding.

Mesh fields are `vertices` and `triangles`: three finite coordinates per vertex,
three distinct zero-based vertex indices per triangle. Limits are 3..10000
vertices, 1..20000 triangles, coordinates within +/-100000 author units. No
physical size conversion is established. Authoring axes are +X right, +Y up,
+Z forward, with a top-down preview showing +X right and +Z up. These are kit
conventions, not recovered game conventions. No collision, attachment/wheel
markers, normals, textures, material bindings or simulation assembly are promised.
The SVG is a simple triangle projection with outlines; it does not perform
hidden-surface removal. Resources without meshes get an informative SVG label.

## Dependencies and explicit replacements

```sh
python -m tools.modkit inspect examples/mods/garage-red examples/mods/garage
python -m tools.modkit preview examples/mods/garage-red examples/mods/garage --resource example.garage:body --output red.svg
python -m tools.modkit package examples/mods/garage-red examples/mods/garage --output red.zip
python -m tools.modkit validate red.zip garage.zip
```

The red example declares an exact dependency and a `replaces` object with target
`id` and target package `version`. The target must exist and have the same kind.
The replacement's own ID remains available; looking up the target ID returns
the replacement provider. Two replacements for one target are rejected, even
when ordered. Dependencies load first; independent packages are visited in
lexicographic ID order. Input order cannot select a winner. Missing dependencies,
wrong versions, cycles, duplicate package IDs and conflicts fail with diagnostics.
Packaging validates the combined registry but packages only the first supplied
package. Dependencies must be distributed separately and supplied when loading.

The portable loader is directly usable by other Python tools:

```python
from client.mod_registry import load_package, build_registry
ordered, registry = build_registry([load_package("garage.zip"), load_package("red.zip")])
body = registry["example.garage:body"]
assert body.provider == "example.red"
print(body.data["mesh"])
```

## Boundary and limits

Directories and ZIPs are loaded into memory without extracting ZIP entries.
Paths use forward slashes, exact case, and portable filenames. Traversal,
absolute paths, duplicate/case-colliding files, symlinks/junctions, encrypted ZIP
entries and nonregular files are rejected. File size is bounded at 8 MiB,
combined bytes at 32 MiB, directory/ZIP entries including directories at
512, compressed archive bytes at 33 MiB, ZIP expansion ratio at 1000:1,
resource declarations at 256 and resource JSON nesting at 64 levels. Paths
are at most 1024 UTF-8 bytes with segments at most 255 bytes.
Duplicate JSON keys and nonfinite numbers
are rejected. Packages produce deterministic archives and content digests.
Use stable package directories: concurrent filesystem mutation is outside this
alpha's trust model. Original game resources stay external and read-only; this
loader neither reads nor copies them automatically.

Executable scripts/plugins, recovered component units/ranges, game attachment
contracts, C++ integration and online negotiation remain pending. The existing
restricted Lua `mco::run_script` interface gains no mod hooks from this kit.
