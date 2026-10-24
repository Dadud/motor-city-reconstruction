# Inventory status

Main executable: **25,780 inventoried entries**, including **338 external imports**.

- Boundary inventory: **25,773 retained enumeration entries + 7 explicit supplements**.
- Retained decompilation records indexed: **611 functions**.
- Bulk private pseudocode exports: **25,434 functions**.
- Functions with address mentions in tracked Python/native source: **569** (review candidates).
- Explicitly reviewed entries: **390**.
- Structural triage: game candidates **16,077**, classified non-game **9,703**. **Required after dispositions: 11,767**. An entry is required when its module is in recovery scope and no published disposition removes it; see [triage](triage.md) and [dispositions](dispositions.json).

| Reviewed translation label | Entries |
| --- | ---: |
| native-bounded | 144 |
| partial | 56 |
| python-and-native-bounded | 81 |
| python-bounded | 108 |
| python-complete-supported-domain;native-partial | 1 |
| unreviewed | 25,390 |

These counts do not measure whole-game completion. Most entries await review.
See [label definitions and refresh instructions](README.md) and the sortable
[CSV worksheet](functions.csv). Supporting binaries are outside this enumeration.
