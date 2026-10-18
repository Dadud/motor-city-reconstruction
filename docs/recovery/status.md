# Inventory status

Main executable: **25,774 inventoried entries**, including **338 external imports**.

- Boundary inventory: **25,773 retained enumeration entries + 1 explicit supplements**.
- Retained decompilation records indexed: **426 functions**.
- Bulk private pseudocode exports: **25,434 functions**.
- Functions with address mentions in tracked Python/native source: **372** (review candidates).
- Explicitly reviewed entries: **182**.
- Structural triage: game candidates **16,071**, classified non-game **9,703**. **Required after dispositions: 11,760**. An entry is required when its module is in recovery scope and no published disposition removes it; see [triage](triage.md) and [dispositions](dispositions.json).

| Reviewed translation label | Entries |
| --- | ---: |
| missing | 2 |
| native-bounded | 120 |
| partial | 3 |
| python-and-native-bounded | 56 |
| python-complete-supported-domain;native-partial | 1 |
| unreviewed | 25,592 |

These counts do not measure whole-game completion. Most entries await review.
See [label definitions and refresh instructions](README.md) and the sortable
[CSV worksheet](functions.csv). Supporting binaries are outside this enumeration.
