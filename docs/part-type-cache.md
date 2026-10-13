# Original abstract-type cache references

The loader at `0x64cdd0` allocates one 1596-byte record for each query row plus an
index-zero marker. It clears the allocation, writes `==No Parent Marker==` at
the marker's `0x347`, and loads rows in query order. The query has no `ORDER BY`;
the authored builder preserves caller-supplied row order rather than inventing
a sort order or promising identical database-engine enumeration.

Each data record contains AbstractPartTypeID at zero, ParentAbstractPartTypeID
at four, and DependsOn at eight. Initially its resolved parent and dependency
indexes at `0x600` and `0x604` are -1. After loading, two passes resolve these
references against data records starting at index one:

- An ID of zero becomes index zero, the explicit no-parent/dependency marker.
- A nonzero ID becomes the index of its **first** matching abstract-type record.
- A missing ID preserves its previous index, normally -1. It does not become zero.

The sentinel and unrelated bytes remain unchanged. The original resolution loop
does not reject cycles or missing references; consumers must validate before
following indexes. Root/parent linking now adds that validation as an authored
safeguard. Type-cache parent indexes and owned-component parent indexes occupy
the same offset but refer to different arrays.

`build_part_type_cache` encodes supplied database rows using the previously
recovered encoder and creates the marker before resolution. The C++ port currently
implements reference resolution over already encoded records, not SQL/database
loading or the full row encoder.

## Verification

`tools.part_type_cache_oracle` executes original instructions
`0x64d1e9..0x64d297`, with supplied in-memory records. All 64 cases match every
byte, including duplicate IDs, zero references, missing references and retained
old indexes. The C++/Python comparison uses the same 64 synthetic cases.

```text
python -m tools.part_type_cache_oracle /path/to/original/mcity.exe
python -m tools.native_part_type_cache_compare build/native/mco_part_type_cache_compare
```

The optional original-code oracle checks the executable SHA-256 before emulation:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Static loader evidence:
`ev_ed5a2502085e64bbafd7c247c646e9eb84ab7f6b99537d3db9aa00e54c8efeb6`.
Allocation, original query execution and row conversion are outside this oracle.

A read-only check of the installed Online.mdb on 2026-10-13 produced 64 abstract
types plus the marker, with no unresolved parent/dependency indexes and no parent
cycles. This validates the supplied catalogue through the authored builder; it is
not a live observation of the original database loader or a complete car assembly.
