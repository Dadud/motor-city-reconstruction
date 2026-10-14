# Room request production and worker scheduling

The recovered room request originates in `0x44cf80`, rather than in the worker
dispatcher or the wire serializer. `client/room_join_request.py` implements its
bounded argument construction from explicit room state. It creates a private
native-layout research image, not a ready-to-send packet or a stable mod API.

Target: original `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4. The observations below are authored descriptions;
original pseudocode and executable bytes remain private external inputs.

## Object and interface adjustment

Constructor `0x44cce0` installs a room-worker subobject vtable at base object
offset `0x0c`; table `0x83bc94 + 4` leads to dispatcher `0x44e820`. Worker task
zero explicitly adjusts `this` by -12 before calling join helper `0x44eba0`.
Therefore worker-relative interface `0x3a8` and base-relative interface `0x3b4`
identify the same interface field. They are distinct from the base-relative
pending flag also located at `0x3a8`. This resolves the apparent field reuse
when the two object pointers were treated as identical.

## Actual argument producer

`0x44cf80` takes a wait switch, a switch affecting flag `0x20`, and an optional
password pointer. Before argument construction, it checks these guards:

- A nonzero room-connected short at base `0xec` returns 0 without scheduling.
- A nonzero base pending field `0x3a8` refuses another request and returns -1.
- Server selector zero combined with the exact name `LOBBY` is rejected as the
  original diagnostic's PLS lobby restriction. Other names are not classified
  by this one test.

On the permitted path, it sets pending `0x3a8` to 1 and clears base result/state
fields `0x3a4` and `0x3a0`. Two local containers are reset. It writes task kind
zero and clears all 87 uint32 words of the `0x15c` task argument region before
copying its inputs. Unlike the channel allocation constructor, this producer's
argument zero initialization is directly observed.

| Source | Argument offset | Observed value |
| --- | --- | --- |
| Base `0x39c` | `0x00` | Server selector |
| Base `0xcc` | `0x04` | Requested protocol |
| Base `0xc0` | `0x08` | Requested channel ID |
| Password presence and second switch | `0x0c` | Mode 1 for nonempty password, otherwise 2; OR `0x20` for nonzero switch |
| Base `0xa0` | `0x10` | NUL-terminated room name |
| Optional password argument | `0x34` | NUL-terminated password; empty when absent |
| Base `0xf4..0x1f3` | `0x50..0x14f` | Exactly 256 opaque room bytes |
| Base `0xe6` | `0x150` | Short labelled `maxReady` by the join diagnostic |
| Password mode | `0x152` | 1 for nonempty password, otherwise 2 |
| Waiting branch only | `0x154` | Original cancellation function `0x44d740` |
| Waiting branch only | `0x158` | Base owner pointer |

Requested-port offset `0x30`, opaque constructor inputs `0x48` and `0x4c`, and
other unwritten argument fields remain zero on the bounded input domain. Their
zero values here are producer behavior, not inferred channel-allocation defaults.

Original name/password copying has no local length guard. The authored boundary
accepts names up to 31 bytes with no embedded NUL and passwords up to 16 bytes
with no embedded NUL. This ensures a bounded source name and termination within
the downstream 17-byte password copy. Oversize inputs are rejected; original
overflow behavior is not reproduced. A 30/31-byte name can still expose the
channel constructor's untouched allocation tail, as documented separately.

The waiting image contains an explicit owner token. It is not inferred as zero.
The original callback address and token are opaque research data and are never
executed by this module. A portable caller supplies a callable cancellation
interface instead of invoking these bytes as a host address.

## Scheduling and cancellation

The nonwaiting branch enqueues task zero through `0x4a5390` with worker receiver
`base + 12` and a zero wait flag. The waiting branch sets its two callback fields
and invokes the same enqueue method with wait flag 1. It then repeatedly queries
task completion with `0x4a5610` while pumping an application virtual method.
A nonzero pump result sets base cancellation field `0x08` to 1. The installed
callback `0x44d740` returns exactly the uint32 value at supplied owner `+8`.
After completion the producer clears that field and returns the task result.
Queue allocation, completion removal, application-pump meaning and real
thread scheduling are separate recovery boundaries.

This local room-worker task zero must not be confused with game-network task
kinds from another dispatcher. These observations establish one producer's
enqueue path; they do not establish the complete race-entry task sequence.

## Upstream settings path

One direct caller, `0x4509c0`, disconnects the old room, initializes a local
settings structure using `0x44a460`, copies a supplied room name, copies an
explicit-length opaque data region through `0x44ad60`, sets the readiness short
and requested channel field, and transfers settings with `0x44db80`.
The [settings-transfer comparison](room-settings-transfer.md) now verifies the
selective assignment and preserved destination tails against both original
functions, including the fields consumed by the request builder.
That transfer calls `0x44a9d0` with destination `base + 0xa0`. It then invokes
`0x44cf80` with waiting enabled, flag-`0x20` switch zero, and its password input.
Thus this path derives its argument values from supplied room settings, not
hard-coded guessed packet defaults. The underlying settings constructor defaults
the protocol to `0x21`. Other callers can produce different room state.

Recovered direct callers of `0x44cf80` include `0x4509c0`, `0x5e5370`,
`0x5e7ba0` and `0x6018f0`. Authenticated room selection, their full ordering,
and the source of base server selector `0x39c` still require tracing. This port
does not invent a fan-server channel name, server selector or room metadata.

## Evidence and bounded execution

| Observation | REA Evidence |
| --- | --- |
| Producer `0x44cf80` | `ev_0da8e044fa08de272419ff8959e78f34f678f37ac84a40e8f457828e7b519b61` |
| Owner constructor `0x44cce0` | `ev_78bcc28c73bf0682446833d51b09ca9ac7d9cd2300a4de0acdf5712abac226c7` |
| Worker `0x44e820` | `ev_909326c29111fb1725c9250b25bede9c8a4f9c5b5b8a0ed1cfbcb7120df3a135` |
| Join helper `0x44eba0` | `ev_2d59c497f973b38df2333e2d6d77873c1b72a5cf4c63cf8820a84ceaefd20745` |
| Cancellation callback `0x44d740` | `ev_c14e9f1a717d88b807434001087308cf3317741263e775ef0fe9c51fa2912c00` |
| Upstream caller `0x4509c0` | `ev_30a7fdbaae68a4c70f8ed085fcd42ee41c41b89e8de61b638ef153090d238e09` |
| Settings transfer `0x44db80` | `ev_97fcba5c2b678c79ae65f05b4f0afb8f7e0c611bce3af05fbb76b9eb803e4c0a` |
| Settings initializer `0x44a460` | `ev_18ae39c595a52405841e8439bba7e17c089742b9c045360b3cdcde77fa4463b4` |
| Opaque copy `0x44ad60` | `ev_0efbb053d2639ca972852dbadc00daa32a6a60db5a785ba57cc313b230415b51` |
| Field transfer `0x44a9d0` | `ev_7917edcd0050a8d8a9510f5803bdecff729f0b8eedbb4ac18233d35f2de0c43b` |

```powershell
python -m tools.room_join_request_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows bounded execution matched 80 complete argument images and enqueue
wait flags, 3 guard cases, and 4 original cancellation-callback results. The
corpus varies name lengths 0, 1, 29, 30 and 31; absent/empty/one-byte/16-byte
passwords; both flags; both waiting modes; random source fields and opaque data.
Stack locals are deliberately poisoned to verify clearing. Each run is bounded.

Original string-copy and field-write instructions execute. Only local reset
calls `0x456930`/`0x4485f0` and enqueue `0x4a5390` are substituted. The oracle
checks reset receivers/order, worker receiver, task kind, complete arguments,
enqueue wait flag and pending-state writes. Permitted runs stop at enqueue,
before queue allocation or completion waiting. Logging is explicitly disabled.
Guard cases return normally. The cancellation callback executes separately
without imports. Four focused authored unit tests also pass.

This establishes bounded producer parity, not a live join or complete offline/
online race flow. The next integration needs actual authenticated room settings,
the recovered queue lifecycle, connection ownership and live server acceptance.

## C++20 port

`native/include/mco/room_join_request.hpp` supplies equivalent typed inputs,
bounded room-image extraction and argument construction. Integer values use
fixed-width unsigned C++ types; external wider/signed values must be validated
before narrowing them. The opaque data field is exactly 256 bytes by type.
Both ports require an explicit owner token only for the waiting branch, reject
oversize or embedded-NUL string inputs, and retain original callback addresses
as inert research-image bytes. Neither implementation schedules or joins a room.

Local Windows Zig C++20 compilation with warning flags and the standalone unit
test passed. The native comparison matched 60 arguments, 5 rejected input cases,
and 3 malformed harness inputs against the original-verified Python producer:

```text
python -m tools.native_room_join_request_compare build/native-check/mco_room_join_request_compare.exe
```

This native comparison reuses the Python/original evidence above; it does not
execute the original binary or contact the server itself. Linux builds and
integration into a complete native service lifecycle remain separate checks.
