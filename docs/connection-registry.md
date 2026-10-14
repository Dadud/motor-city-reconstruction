# Local server connection IDs

The room selector is a local connection ID. The original connection constructor
takes the registry's current counter and increments it. The counter begins at
zero, so zero is a real first connection ID. This differs from local worker
operation IDs, which skip zero. A configured shard number or account/persona
ID cannot substitute for this connection ID.

Target: original `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4. These descriptions and the portable implementation
are authored work; original instruction bytes and decompiler output are external.

## Creation and retention

The main game-network constructor `0x44fb20` retains the interface returned by
singleton factory `0x730450` at owner offset `+0x6d8`. The factory installs table
`0x84b3fc`; table entry `+4` is server connection routine `0x73a720`. Its
initialization helper `0x7304d0` creates the registry at global `0xb380d0` by
calling constructor `0x73daf0`. That constructor writes zero at registry `+0x2c`.

Connection constructor `0x73f050` performs this sequence:

1. Enter the registry's critical section through virtual entry `+0x24`.
2. Read the uint32 counter at registry `+0x2c`.
3. Write counter plus one back to the registry, using 32-bit wraparound.
4. Leave the critical section through virtual entry `+0x28`.
5. Store the old counter at connection object `+4`.

The increment does not skip zero and does not test for an existing ID in this
instruction range. Counter wrap is reproduced as observed arithmetic; this
does not prove that billions of connections or an ID collision would work.
The game dispatcher treats its returned ID as signed int32, so high-bit results
are negative at that later boundary.

After an accepted connection response, `0x73a720` constructs the connection
object, wraps it in a reference-counted holder, and inserts a pair consisting of
connection ID and holder into the registry. The insertion call is `0x73d490`
with receiver registry `+4`, under the registry lock. It later reads the same
connection object field `+4` into its return value. This is the value forwarded
to the embedded room by the [binding dispatcher](room-server-binding.md).
The return is not the server response's persona/user ID.

## Existing connection lookup

Before creating a socket, `0x73a720` calls `0x73df10` with username, hostname
and port. Lookup walks the existing registry entries and compares:

| Connection object field | Comparison |
| --- | --- |
| `+0x10c` | Username, exact byte-sensitive C-string comparison |
| `+8` | Hostname, exact byte-sensitive C-string comparison |
| `+0x174` | Port, exact 32-bit equality |

It returns the first matching object's ID at `+4`. Empty registry or no match
returns `-20`. The connection routine then uses the nonnegative existing result
instead of creating a new connection. This does not establish DNS equivalence,
case folding or matching by shard ID; neither string comparison normalizes its
input. Bytes after the first NUL do not participate.

## Portable implementation and original comparison

`client/connection_registry.py` implements the counter transition and bounded
identity lookup. Entries are supplied in the original registry's traversal
order; the helper does not invent insertion order or a map balancing policy.
It accepts only terminated byte fields, a deliberate memory-safety boundary
for cases where original unbounded C-string reads would be unsafe.

```text
python -m unittest tests.test_connection_registry
python -m tools.connection_registry_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Local Windows verification matched 64 original counter-range executions and
144 complete original lookup executions. Counter execution covers `0x73f0fb`
through immediately before `0x73f122`, including writing connection `+4`.
It excludes all other constructor work. Lookup executes all original `0x73df10`
branching, C-string comparisons and tree iterator `0x7408d0`; only its two
critical-section calls are inert substitutions. Synthetic ordered tree images
exercise empty and multiple-entry registries, case mismatches, port mismatches,
ID zero, a high-bit ID and empty strings. Three focused unit tests cover image
boundaries, counter boundaries and first-match/C-string behavior.

| Observation | REA Evidence |
| --- | --- |
| Retained interface in main constructor | `ev_08fc5e066aa8d625ac8cf79fc29dc1825f3f5a72d792524ca57e2f8234afe99b` |
| Singleton factory | `ev_7a007479be512bd7e1650828e057a9a411e2f66ad0023e49b132ac493ff7b6eb` |
| Factory initialization and registry creation | `ev_8a91b6f900056d5b8705a5a71ae73feacc026168675ddc52b40d56b5f4533467` |
| Registry constructor and counter initialization | `ev_58b2f794587ddbb1485094e5d4aac4802969158ffa3bc8dec52b324c0adc39bb` |
| Connection constructor and counter arithmetic | `ev_5f77f350622e932f77666a39da638eb8367953941a1e0a9dfc2772e80f92690c` |
| Successful insertion and returned local ID | `ev_39df527653aa4915699923f6f95d53e9aef1c2f0028e934df189e431e99c737e` |
| Existing connection identity lookup | `ev_5b49717e0fd2458f9decec6dad6e38277e44f458d3f5b44486eaf52023bb040f` |
| Original tree iterator | `ev_616314a6bcdbf1dc9919c6a80e9eae0c6d14474a690052a062964679bc6e22cc` |

## Remaining integration work

Connection insertion, reference ownership, actual disconnect removal, socket
shutdown, concurrent access and registry reuse across reconnect remain to be
recovered and integrated. Registry destruction releases entries and critical
sections, but that teardown alone does not establish normal connection lifetime.
The bounded helper is a research model and does not create an authenticated
connection. No packet, room join or live fan-server operation was sent here.

The [disconnect follow-up](connection-disconnect.md) now maps the removal chain
and verifies interface return conversion and communication socket ownership
guards. It does not yet implement complete registry erase/reference lifetime or
live reconnect. [Room disconnect](room-disconnect.md) is a separate local task
and settings reset, rather than a substitute for server logoff.
