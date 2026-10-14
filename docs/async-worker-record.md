# Local asynchronous worker records

The generic worker base is constructed by `0x4a51e0`; the room object embeds it
at offset 12. It initializes two queues with record size `0x80c` (12 header bytes
and 2048 argument bytes), a zero counter at worker offset `0x8c` and a supplied
manager at `0x90`. Room and game workers supply distinct dispatch functions.

## Recovered header

| Record offset | Observed role |
| --- | --- |
| 0 | Worker-specific local task kind |
| 4 | Local operation ID: zero means no completion record requested |
| 8 | Worker return bits, written after dispatch |
| 12 onward | Operation-specific arguments |

`0x4a5390` rejects null operation data or a missing manager by returning zero
without modifying the counter or record. A tracked operation increments the
32-bit counter, wraps it and replaces zero with one, then stores the counter
at record offset 4. An untracked operation writes zero at offset 4 without
changing the counter. Other record bytes are untouched by these header writes.

The routine subsequently adds the operation to the worker queue, adds a worker
reference to the manager queue, signals the manager event and returns the ID.
Those queue/event operations are static observations; their allocation, locks,
copy semantics and runtime ordering have not yet been compared.

Worker routine `0x4a55b0` obtains a record into a `0x80c`-byte local image,
dispatches it through worker vtable offset 4 and writes the returned bits at
record offset 8. It requests completion-queue insertion only for a nonzero
operation ID. This condition does not classify success: negative/error result
bits can also generate a completion record.

`client/async_worker_record.py` reconstructs only these header writes.
`GameNetworkTask.operation_id` and `worker_result_bits` expose the recovered
fields while retaining the existing raw eight-byte header representation.
Result bits must not be used as a completed result before the owner observes
worker completion. Neither IDs nor record layouts are server packets or stable
mod API fields.

Completion query `0x4a5610` rejects operation ID zero with a C++ exception. For
a nonzero ID, it passes that ID's address and the supplied output pointer to
queue method `0x45f440`, using the worker's completion queue at offset `0x48`.
The wrapper preserves that method's return bits in EAX; its decompiled `void`
signature does not erase the assembly-level return. The queue searches from its
head and selects the first comparator return of exactly 1. Its worker comparator
`0x4a51c0` compares the requested ID with record offset 4. A match copies to a
nonnull output, removes/frees that node and returns 1; an empty queue or no match
returns zero. The current header helpers do not implement or invoke this query;
queue ownership and synchronization still need original comparisons.

The [completion follow-up](async-worker-completion.md) now implements first-match
destructive retrieval in an owned-record model and verifies original removal
through a synthetic queue oracle. Real worker scheduling and synchronization
remain separate requirements.

The portable header boundary accepts immutable records of at least 12 bytes and
preserves their entire remaining image. Exact queue-size materialization is a
separate requirement; passing a short header here does not make it safe to pass
to the original queue. Strict uint32 and size checks are authored safeguards.

## Verification

The C++20 header helpers in `native/include/mco/async_worker_record.hpp` belong
to `mco_core`. Native unit checks cover null/absent-manager early returns,
counter wrap, untracked IDs, completion gating, malformed headers and preservation
of input images. They implement the same bounded transforms as the Python module,
without starting threads or signaling host events.

```powershell
python -m tools.async_worker_record_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows bounded execution matches 24 operation-ID writes, three rejected
enqueue paths and 15 worker-result writes. The ID oracle executes
`0x4a554f..0x4a5574` before insertion, the rejection cases execute the original
enqueue routine with diagnostic logging disabled, and result cases stop before
completion-queue insertion. Complete supplied `0x80c` images are compared,
including bytes outside the header. No queue, event, host callback or network
operation runs in these comparisons.

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra 12.1.4 constructor evidence:
`ev_42ab54ed57d72b450250347695e6bc2028e439d82ef3b1824e0659cbd22f72a8`;
enqueue evidence:
`ev_196ddd052b3c413865d30d11e258c5aafc29e09244c8032052a8746977989ad7`;
worker execution evidence:
`ev_7b136bddb2ded67109ec5ddcc2a3fa1f81f3d71d525250c8ddfb7c1a912a14ba`.
Completion wrapper evidence:
`ev_aa6ef245ce763a58b932207ce4e5d9537cdad7a59212547ce4d67b028cd3558f`.
Removal routine evidence:
`ev_39d74d6d5fda338dd8f3e954e9b95d833f4305b9e06d82164e209ee4175d9554`;
worker comparator evidence:
`ev_c62c6e8ba6c270d7c5c9c8bcf845ffc3538c6321f8487d25274fa8274b16154e`.
