# Original completion-query comparisons

The repeatable runner is `tools/async_worker_completion_oracle.py`. It executes
the original worker query at `0x4a5610`, linked-queue removal at `0x45f440`, and
ID comparator at `0x4a51c0` against independently constructed queue images.
The executable SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

Seven queue layouts cover empty, singleton, ordered, duplicate IDs, repeated IDs,
unsigned boundary IDs, and records with ID zero. Each is queried with six
nonzero selectors, with and without output copying, and with three marked-node
patterns. All 252 queries match the portable model; 66 find a record and 33 copy
one. Six additional zero-selector cases reach the original exception boundary
without changing the queue or output buffer.

Checks compare returns, the entire output record, remaining record order,
head/tail links, node and marked-node counts, dirty state, and boundary-call
order. The original comparator runs unchanged. Output copying occurs before
detachment; payload and node destruction occur after detachment.

The virtual record-size, copy and payload-free functions, node free at
`0x6992c5`, and C++ exception dispatch at `0x69b30f` are captured substitutions.
The queue lock flag is explicitly zero. These are synthetic sequential queues,
not host thread, allocator, lock, account, or server executions. The portable
implementation uses owned records instead of original nodes and pointers.

Run from the repository with the optional oracle dependencies installed:

```powershell
python -m tools.async_worker_completion_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

The C++ implementation separately checks matching/removal, duplicate order,
destructive null output, signed result boundaries and record-size validation.
It has not been compared directly with the original across the full corpus.
