# Owned component dependency linking

The original pass at `0x662060` links dependencies after root selection and parent
linking. It consumes ordered 1596-byte records and uses the abstract-type cache
lookup at `0x64c720`. This is one assembly stage, not a complete modified-car loader.

For each record, the helper resolves its abstract type's dependency to another
abstract type ID. A resolved ID of zero writes dependency index zero at `0x604`.
Otherwise the pass scans every record. A candidate matches when its abstract ID
matches the dependency and its attachment at `0x61c` is zero or equals the current
record's attachment. Zero on the candidate acts as a wildcard. The last matching
record wins; when no candidate matches, the previous dependency index survives.

For example, a component attached at point 2 can depend on a candidate at point 0
or point 2. A candidate at point 1 does not match. If multiple candidates qualify,
their existing array order determines the result.

The pass also clears the still-unnamed field at `0x634` on every record when the
first record's owned PartID at `0x5f8` is zero. Independently, it clears that field
for abstract types 2001, 20001, and 6001, and for records whose parent at index
`0x600` has abstract type 6001. Its semantic name remains unknown.

The authored function accepts explicitly resolved dependency IDs. It does not
guess missing templates, select/reorder a root, establish parents, or finalize
physical properties. Parent indexes are validated before any writes; this guard
prevents the original's unchecked out-of-bounds access. Inputs remain immutable.

## Evidence and verification

- Executable SHA-256: `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
- Static REA function evidence: `ev_256e0ca862fe04795194d1a03e19cdd28c10c26ff3d278c6f3eb6e0ca02f4391`.
- Static helper evidence: `ev_877a180fd838294d3c7fbceb8025fa33cd403f14491b4f5925c06dc307819945`.
- The local CPU oracle executes the complete original pass and its real cache
  helper against synthetic records/cache data. All 64 deterministic cases matched
  every output byte and the successful return value on 2026-10-13.

```powershell
.\.venv\Scripts\python.exe -m tools.owned_dependencies_oracle 'C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe'
```

These checks do not execute the original game entry point, host imports, prior
finalization/parent-linking passes, or a fan-server session. Invalid parent/template
indexes and original database loading are outside the oracle's valid-input scope.
