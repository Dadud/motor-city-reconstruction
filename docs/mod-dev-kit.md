# Mod development kit design

The project targets both a faithful portable client and a mod development kit
with better add-on support. This document describes the intended architecture;
the package loader, stable extension API and kit are not implemented yet.

The [calculation writeups](calculations/README.md) explain recovered original
behavior. They will be reference material for component authors and developers
implementing extensions. Native offsets are research references, not an API that
add-ons should depend on.

## First supported extension areas

| Add-on area | Intended capability | Work needed before support is promised |
| --- | --- | --- |
| Vehicles | New body geometry, materials, attachment markers and assembly definitions | Document geometry conventions, attachment requirements and component bindings |
| Components | New engine, tire and suspension configurations | Complete relevant behavior and publish typed fields with established units/ranges |
| Tracks | Geometry, road support, placement and declared race metadata | Recover object collision and race behavior; separate visual and physical geometry |
| Presentation | Skins, audio and localization | Define resource lookup and presentation interfaces as those subsystems are implemented |
| Behavior | Explicit alternative simulation or gameplay rules | Establish stable interfaces, isolation and online compatibility policy |

Data-driven packages are the initial priority. Executable scripts or native
plug-ins need a separate design; neither is implicitly supported by this plan.
Unknown original units must remain marked unknown rather than being converted
into a misleading public field definition.

## Package identity and layout

Use an add-on directory or archive with a versioned manifest, separate from the
user's original installation. The following layout is illustrative, not a
currently accepted package format:

```text
example-vehicle/
  manifest.json
  vehicles/example.json
  models/body.*
  textures/body.*
  README.md
  LICENSE
```

The manifest should declare a stable package ID, package version, supported kit
schema/API versions, required client versions, dependencies and entry resources.
Packages should declare ownership and licensing of their distributed content.
Provide original examples so developers can use the kit without redistributing
game files.

Keep package-local resource names and namespaced object IDs. Two packages must
not accidentally replace each other's vehicle or component because both chose
the same short filename or legacy numeric ID. Where compatibility needs original
IDs, translate them through an explicit mapping at the boundary.

## Resource resolution and overrides

The base game remains an external read-only resource source. Add-ons register
resources in a separate layer. Explicit replacement declarations identify the
target and required version; deterministic ordering and conflict diagnostics
make the result reviewable. Do not silently select an arbitrary winner.

Reject paths that escape a package root. Keep asset size limits and format
validation at the loading boundary. Support case-consistent resource names
across Windows and Linux. A missing dependency or invalid model should produce
a useful error naming the package and resource.

## Developer tools and examples

The kit should provide commands to validate a package, list its dependencies,
inspect decoded assets, preview vehicles/tracks and build a distributable archive.
Validation should cover schema versions, finite numbers, established field ranges,
resource references, wheel/attachment markers and package conflicts.

Ship a minimal vehicle, component and track example as the relevant interfaces
become stable. Include a tutorial that edits an example, previews it, validates
it and packages it. The existing asset decoders and headless tests provide a
starting point; their current internal Python interfaces are not a stable SDK.

Document coordinate axes, scale, attachment names, supported material formats,
units and simulation responsibilities. Show how each documented component field
feeds the original calculations, with links to the writeups and executable
comparison coverage. This makes tuning explainable rather than trial and error.

## Behavior and online compatibility

Recovered Motor City Online behavior is the default simulation profile. Packages
that change forces or race rules must declare those changes. Keep cosmetic
resources distinguishable from simulation-affecting resources, while validating
which fields actually affect the simulation.

Once the unofficial server protocol and patch expectations are recovered, define
which add-ons are allowed online and how peers agree on required content and
simulation versions. Content digests can identify exact package revisions, but
a matching digest alone does not prove equal simulation or server permission.
Until that work is done, new package support must not claim server compatibility.

## Delivery order and acceptance

1. Finish documenting recovered asset/component interfaces and their unknowns.
2. Implement manifest parsing, namespaced registration and read-only resource
   layering, with an original example package and asset-free validation tests.
3. Add preview, validation and packaging commands plus a developer tutorial.
4. Expand vehicle/component/track contracts as their runtime behavior is verified.
5. Define behavior extensions and online negotiation using actual protocol evidence.

A first usable kit should load an example without editing the original
installation, explain invalid inputs, diagnose dependency and override conflicts,
and produce a package that another Windows/Linux client can load. A document
or an archive builder alone does not meet that milestone.
