# Inventory status

Main executable: **25,779 inventoried entries**, including **338 external imports**.

- Boundary inventory: **25,773 retained enumeration entries + 6 explicit supplements**.
- Retained decompilation records indexed: **501 functions**.
- Bulk private pseudocode exports: **25,434 functions**.
- Functions with address mentions in tracked Python/native source: **465** (review candidates).
- Explicitly reviewed entries: **277**.
- Structural triage: game candidates **16,076**, classified non-game **9,703**. **Required after dispositions: 11,760**. An entry is required when its module is in recovery scope and no published disposition removes it; see [triage](triage.md) and [dispositions](dispositions.json).

| Reviewed translation label | Entries |
| --- | ---: |
| native-bounded | 148 |
| partial | 33 |
| python-and-native-bounded | 69 |
| python-bounded | 26 |
| python-complete-supported-domain;native-partial | 1 |
| unreviewed | 25,502 |

These counts do not measure whole-game completion. Most entries await review.
See [label definitions and refresh instructions](README.md) and the sortable
[CSV worksheet](functions.csv). Supporting binaries are outside this enumeration.
