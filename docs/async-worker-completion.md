# Retrieving background-operation completion

`client/async_worker_completion.py` models the worker's completed-operation
queue as owned `0x80c`-byte records. It reconstructs operation-ID matching and
destructive retrieval, keeping native node allocation and locks outside the
portable interface.

The original query wrapper `0x4a5610` rejects ID zero with a C++ exception. For
nonzero IDs it queries the completion queue at worker offset `0x48`. The queue
removal routine `0x45f440` walks from the head, using comparator `0x4a51c0` to
compare the requested ID with record offset 4. Only the first match is selected.
Other records retain their order, even when multiple records share an ID.

With a nonnull output, the original copies the selected record before removing
its node. With a null output it still removes the selected node and returns 1.
An empty queue or unmatched ID returns zero without removing anything. A found
record can contain any signed worker result; finding it does not imply success.

`WorkerCompletionQueue.query` returns `found` and an optional complete record.
Its `copy_output=False` branch mirrors destructive null-output retrieval.
`CompletedOperation.from_record` exposes task kind, local operation ID, signed
32-bit result and the complete 2048-byte argument image. Those are private local
worker fields, separate from server packets and stable mod APIs.

The class has one owner and performs no implicit locking or task scheduling.
Original critical sections, payload/node destruction and memory ownership have
different portable representations; their original side effects are checked
separately rather than implemented with original pointers. Owners must serialize
access when integrating a real worker thread. Exact record-size checks and
uint32/type validation are authored boundaries; they do not reproduce arbitrary
original memory faults or the original exception object.

Five portable tests cover head and duplicate matches, preserved remaining order,
empty/unmatched queries, destructive null output, append, signed-result limits
and invalid record/ID boundaries. The [original comparison record](async-worker-completion-evidence.md)
documents its synthetic queue images and substituted callable boundaries.

```powershell
python -m tools.async_worker_completion_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows bounded execution matches 252 queries, including 66 matches and
33 copied records. Six zero-ID paths reach the original C++ throw boundary with
the expected arguments. The original comparator executes. Payload size/copy/free,
node free and exception dispatch are captured substitutions; the original lock
flag is zero. Queue head/tail, node count, marked-node count, dirty state, remaining
links and copy-before-detach/free order are checked as original side effects.
These sequential injections do not prove real thread synchronization or live
room delivery.

Original target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra 12.1.4 query evidence:
`ev_aa6ef245ce763a58b932207ce4e5d9537cdad7a59212547ce4d67b028cd3558f`;
removal evidence:
`ev_39d74d6d5fda338dd8f3e954e9b95d833f4305b9e06d82164e209ee4175d9554`;
comparator evidence:
`ev_c62c6e8ba6c270d7c5c9c8bcf845ffc3538c6321f8487d25274fa8274b16154e`.
Queue completion alone does not establish authenticated room joining or racing.
