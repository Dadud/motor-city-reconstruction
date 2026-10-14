# Offline Lua content research alpha

`mco::run_mod_script` adds an explicit research lifecycle to the existing bounded
Lua implementation. This is **script-alpha-1**, a separate API from the Python
kit's **data-alpha-1**. Neither API claims gameplay loading, original component
units, vehicle assembly, native offsets, simulation control or online compatibility.

## Typed host package definition

The host passes a `ModScriptPackage` from `mco/mod_script.hpp`: `api_version`,
package `id`, exact package `version`, declared `resources` and Lua text `source`.
Each `ModResourceDefinition` has string `id`, `kind`, `label`. IDs follow the
data kit's lowercase ASCII namespaced convention. Exact versions have three
numeric components with no leading zeros, and at most 64 bytes. Labels and
notes are 1..1024 printable ASCII bytes. Supported kinds are vehicle, component,
track, material, sound and UI (`ui`); these are catalogue classifications with
no simulation semantics. Declared and scripted resources share one namespace.

```cpp
mco::ModScriptPackage package{
    "script-alpha-1", "example.garage", "1.0.0",
    {{"example.garage:body", "vehicle", "Original authored body"}},
    R"(
        mco.register_resource('ui', 'example.garage:title', 'Original garage')
        mco.on('inspect', function(event)
            assert(event.offline)
            mco.emit_note('Authored resources inspected')
        end)
    )"
};
auto result = mco::run_mod_script(package, mco::ModResearchEvent::inspect,
                               mco::ModExecutionMode::offline);
// Check result.success before consuming result.resources or result.notes.
```

The host is responsible for obtaining an owned package definition, resolving its
dependencies and applying resource replacements through an appropriate loader.
This function does not read directories, ZIPs or manifests. The disk adapter below
validates a separate script manifest and passes owned values to this native API.
The data-alpha-1 manifest contract remains unchanged. Game loading is still pending.

## Run a disk script package

Build with scripting enabled (the default), then validate or execute the authored
example from the repository root:

```sh
python -m tools.modkit script examples/mods/garage-script
python -m tools.modkit script examples/mods/garage-script --runner build/native/mco_mod_script
python -m tools.modkit script examples/mods/garage-script --runner build/native/mco_mod_script --event preview
python -m tools.modkit script examples/mods/garage-script --output garage-script.zip
```

On Windows multi-configuration builds, use `build/native/Release/mco_mod_script.exe`.
Without `--runner`, this validates the manifest and source encoding only. With a
runner, it executes real Lua initialization and the chosen event inside the native
sandbox. A failed run has no partial resource output. The child process has a
10-second host timeout in addition to the native memory and instruction budgets.

Directory and ZIP packages use the same bounded, portable file reader as the data
kit. They require exactly these manifest fields:

```json
{
  "schema_version": 1,
  "api_version": "script-alpha-1",
  "id": "example.script",
  "version": "1.0.0",
  "license": "MIT",
  "resources": [{"id": "example.script:body", "kind": "vehicle", "label": "Authored body"}],
  "script": "scripts/init.lua"
}
```

`script` names one package-local UTF-8 file of at most 1 MiB. The reader selects
that exact file; it never substitutes a resource file. Declarative resources need
exactly `id`, `kind`, and `label`; an empty resource list is allowed for scripts
that register all content during initialization. Labels use printable ASCII,
including spaces. Package and resource suffix IDs are at most 80 bytes each;
versions are at most 64 bytes. Duplicate JSON keys and unknown manifest fields
fail validation. Script dependencies and replacements are not supported by this
research contract yet.

`--output` creates a reproducible ZIP from the validated package snapshot and
refuses to overwrite an existing file. If a runner is supplied, execution must
succeed before packaging occurs.

The executable reads a private length-prefixed bridge from standard input. It
always selects offline execution and produces JSON resource/note output. That
bridge is an internal adapter, not a stable mod API or a game network protocol.

## Lifecycle and functions

Every call creates a fresh state, seeds the declared resources, executes Lua
initialization, dispatches exactly one selected research event, then closes the
state. Resource output is sorted by ID; handlers and notes retain registration
order. Failure returns an error and empty output, discarding all partial content.

`mco.api_version` is `script-alpha-1`.

`mco.register_resource(kind, id, label)` registers a typed catalogue entry during
initialization only. The ID must belong to this package. Duplicate IDs, including
duplicates of declarative entries, fail. No overrides or external namespaces are
allowed at this boundary. It accepts no arbitrary table or executable native handle.

`mco.on('inspect'|'preview', function(event) ... end)` registers a research event
handler during initialization. `event` is a fresh table with `name`, `package_id`
and `offline=true`. Inspect and preview are host research phases, not game hooks.
A preview handler may annotate output but does not invoke a renderer.

`mco.emit_note(text)` appends a bounded diagnostic note during an event only.
Handlers cannot register additional resources or handlers. There is no persistent
state between calls; initialization runs again when the host selects another event.

## Safety boundary

Host mode must be explicitly offline; online and invalid modes are refused before
creating Lua state. This is an enforced API boundary, not server permission or
network detection. The host must supply its actual execution mode.

The state cap is 8 MiB and source cap is 1 MiB. There are at most 256 total
resources, 16 handlers per event, and 64 emitted notes. The instruction budget
is shared by initialization and event execution and must be 1..100000000. Like
the existing research runtime, it counts Lua instructions, not wall time inside
library calls. Only textual chunks are accepted. Base/math/string/table/UTF-8
libraries are restricted; file/process/package/debug/coroutine access, dynamic
loaders, collection controls, metatable access, host printing, exception-catching functions and
string bytecode dumping are unavailable. `string.find`, `match`, `gmatch` and
`gsub` are also unavailable: pattern backtracking executes in C outside VM hooks.
Metatable access prevents user-created finalizers, whose Lua execution disables
hooks during state cleanup. Raw pointers used internally by the
host are never exposed to Lua. Returned entries and notes are owned C++ values.

The tests exercise seeded/scripted registration, deterministic ordering, separate
events, online refusal, invalid identity/API versions, duplicates/foreign IDs,
unknown game events, lifecycle restrictions, count limits, memory limits,
instruction exhaustion, bytecode rejection and clean recovery after failure.
Native gameplay events and game resource integration remain research work.
