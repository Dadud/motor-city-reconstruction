# Key-action configuration and cleanup investigation

The verified console checkpoint is `8afbd81`. The next search followed configuration of the recovered key-action router rather than assuming that its tables have a setter. The original executable remains external and read-only, scoped by SHA-256 `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

## Literal-reference evidence

`tools/action_table_audit.py` hash-checks the executable, uses retained entries and body-byte counts to select byte windows, and examines immediate operands and memory displacements with Capstone. The range `[0xb36594, 0xb36898)` covers 65 handler words and the two 256-byte maps. The larger recovered view permits handler indices that alias map bytes and extend beyond this search range; that does not establish a larger dedicated handler allocation.

The scan sampled windows starting at 25,436 nonempty internal entries, with no unmapped windows. It decoded 3,920,409 of 3,945,792 sampled window bytes. These totals can include overlaps and do not measure owned function-body coverage. Exactly three unique instructions reference a literal within the range: low-map read at `0x6f0e8d`, high-map read at `0x6f0ea3`, and handler-word read at `0x6f0eaf`, all in router `0x6f0e80`. No literal setter or table-address immediate was found in this scan. The retained pseudocode search independently found only these router references.

An October 18 REA workflow audit corrected the original claim that these were verified contiguous bodies. A Ghidra body-byte count is not a contiguous extent: only its complete AddressSet establishes owned ranges, including gaps. This Capstone scan remains a secondary search aid, not REA Evidence or proof of function-level absence. Computed addresses, caller-supplied aliases, undecoded window bytes (25,383), omitted body ranges, non-owned bytes, data references, and writes from other modules remain unresolved. No dead-code classification or initialization API is inferred. The synthetic action maps in comparison cases remain fixtures, not recovered startup configuration.

Reproduce from the repository root:

```powershell
.venv/Scripts/python.exe -m tools.action_table_audit 'C:\Program Files (x86)\EA Games\Motor City Online\mcity.exe'
```

The detailed instruction report is private under ignored `build/recovery/action-table-references.json`; the script publishes no original binary bytes.

## Concrete next dependency

Retained startup `0x6bfa10` installs default callback `0x6f0580` through the already recovered setter `0x6f0360` after device initialization. It does not establish an action-table configuration contract. Its graphics and other startup dependencies remain unrecovered.

Device initialization registers cleanup callback `0x6f0350` through `0x6bf450`. That registry is currently a platform bridge in the device comparisons. Retained draft `0x6bf450` searches all 64 slots at `0xb2bbe8` for an existing identity, then inserts into the first empty slot, silently leaving a full registry unchanged. Shutdown `0x6bf410` walks slots 63 down to 0, calls each current nonzero callback, then clears that slot. The order of callback invocation versus clearing matters if callbacks mutate or register entries. These are draft-derived hypotheses requiring instruction review and original comparisons before implementation acceptance.

The next recovery batch should implement this registry and connect actual device registration and shutdown into persistent sessions. Include duplicate registration, zero identity, full capacity, callback mutations, registration into visited/unvisited slots, and result/ABI checks. External callback bodies and nonreturning callbacks must remain explicit. This replaces a known lifecycle bridge without inventing action configuration.

The subsequent registry batch implements and verifies registration/run and connects actual device shutdown; see [cleanup-registry-progress.md](cleanup-registry-progress.md). Action configuration remains unresolved.
