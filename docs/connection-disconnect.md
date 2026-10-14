# Server disconnect and connection lifetime

Normal server disconnect removes the local connection registry entry. It first
requests removal of the connection's communication objects, then erases the
server entry and releases its temporary reference. Disconnect does not reset
the connection ID counter in this observed path. Reconnecting can therefore
receive the next local ID; it must not assume ID zero every time.

Target: original `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4. This is authored recovery documentation; original
instruction bytes and decompiler text remain external inputs.

## Interface, removal and references

The lobby interface table `0x84b3fc` entry `+0x24` contains address `0x730b20`.
Game-network task 1 forwards its single caller value through this entry.
The interface loads registry global `0xb380d0` and calls `0x73e2a0` with that
value as a local connection ID. Ghidra reports decoded instructions but no
containing function for `0x730b20`; the entry and bounded runtime comparison
are established from the vtable, analyzed bytes and original execution, rather
than a recovered function signature.

Wrapper `0x73e2a0` calls removal `0x73e000`. A nonzero removal result maps to
interface result 0; zero maps to -20. The removal function follows this order:

1. Enter registry lock through virtual entry `+0x24`.
2. Retrieve the requested ID through virtual entry `+0x14`, copying a reference
   holder into a local value.
3. On a found entry, call `0x73fe20` with the connection object at holder `+8`.
4. Erase the matching registry range using `0x7409d0`, `0x741060` and `0x740920`.
5. Leave the registry lock through virtual entry `+0x28`.
6. Release the copied holder reference with `InterlockedDecrement` at holder
   `+4`; invoke its virtual deleting destructor with argument 1 only when the
   count reaches zero. Return 1 on found entry, or 0 when no entry was found.

Both branches perform the final local reference release. Actual map lookup,
tree balancing, and reference counts need original comparison before a complete
portable removal implementation is claimed. Removing the registry entry does
not mean that all thread-held references have already been released.

## Communication removal and socket ownership

`0x73fe20` calls `0x743890(0)` with the connection's communication collection
at connection `+0x180`. A zero argument first calls `0x743c80`, which removes
nonzero communication IDs before processing ID zero. Communication removal
marks the selected communication object's uint16 field `+0x198` as 1, reports
an event through `0x743810`, erases that collection's entry, unlocks, and releases
its copied reference. The zero-ID event is `0x2a0` with a four-byte payload;
nonzero-ID removal uses event `0x208` with an eight-byte payload. These are local
callback dispatch IDs, not newly inferred network opcodes.

Actual socket closure happens in communication destructor `0x743e40`, subject
to this observed guard:

```text
field194 != 0 AND (channel_id == 0 OR field19c != 0)
```

The channel ID is communication `+8`. The two other uint32 fields are at
`+0x194` and `+0x19c`; their full upstream semantics remain unresolved.
When the guard passes, the destructor supplies the socket field at `+0x34`
to close helper `0x7e2260`, between construction/destruction of a local transport
helper. The destructor always installs its table `0x84b6b4` and deletes the
communication critical section at `+0x3a4`.

Static socket helper evidence shows that `0x7e2260` accepts a nullable socket
pointer. Null pointer or handle `0xffffffff` returns 0 without closing. Otherwise
it writes `0xffffffff` into the caller's socket field before calling
`shutdown(old_handle, 2)` then `closesocket(old_handle)`. A closesocket result
of -1 produces -1; other closesocket results produce 0. The shutdown return is
not tested. This helper's host behavior was not executed in the bounded oracle.

Connection destructor `0x73f2d0` calls the communication removal again, releases
owned helper objects, deletes its own critical section at `+0x204`, and releases
crypto objects through `0x73f940` and `0x73fda0`. Thus socket lifetime depends on
reference ownership and communication teardown, not solely the disconnect
interface's immediate return value.

## Portable calculations and verification

`client/connection_disconnect.py` implements only the recovered interface
result conversion and communication socket-close predicate. It performs no
registry mutation, reference release, callback or socket action.

```text
python -m unittest tests.test_connection_disconnect
python -m tools.connection_disconnect_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Local Windows verification passed two focused unit tests and matched:

- 24 complete original interface/result paths from `0x730b20` through
  `0x73e2a0`, with registry removal substituted. The oracle verifies forwarded
  ID, registry receiver, and native return conversion, including ID zero and
  high-bit ID values.
- 216 complete original communication destructor executions. The oracle varies
  all three guard fields, compares the entire communication image, and checks
  close-helper pointer, critical-section pointer and boundary call order.
  Transport construction/destruction, socket closure and critical-section
  deletion are inert substitutions; their effects are excluded.

Logging is disabled explicitly and an inert x86 SEH chain is supplied. These
comparisons do not execute a PE entry point, authenticate, remove a live registry
entry, close a host socket or exercise concurrent threads.

| Observation | REA Evidence |
| --- | --- |
| Interface entry `+0x24` | `ev_e2d160710e08501745fa495cdd383ec022252d35288cfe4e14c24c1cab3deda0` |
| Interface analyzed bytes | `ev_7280ce1050e7f5f231baaf6cc0f6a50f33c8660a55578740089b58dac39e993c` |
| Missing containing function boundary | `ev_0c1db01293424b4036baef33f65ba8b69a8c6ddb459d4a0fba5d17bc845118c4` |
| Wrapper result conversion | `ev_66c7dad873d02a77b3c4cbd4814cd597e6c0dc6edd973493de83d2ab9dbcbc5e` |
| Server registry removal and copied-reference release | `ev_7e9a713259dc0e7ce77967dec5077d0207ec6f7abcd47e09eb3f462ace0c5e72` |
| Connection communication removal call | `ev_6a829d1ba878cb06a31c598dcb9ef6dd8116b969a1e3248e8254e7053a4130e9` |
| Communication removal and events | `ev_3932c67a5886632bcfdae1f577f196f7ebe471cb75d7d39966706894d5c26199` |
| Remove nonzero communication IDs | `ev_cf6154b4cd6df14099d306e8f5940bb727255b28450a56a547a6cfc5cd5172fd` |
| Callback forwarding helper | `ev_ffda17901695851f9d88401c20d547f709b4d3456e11be26cc07086a7cebd99c` |
| Communication destructor and guard | `ev_d0221a26e49c7b2f2db018fb7554cb1c76a4cc876418c39e4c5219bf62746085` |
| Socket close helper | `ev_3eac244b626ad2a1e969803d49c5eece095304fbb35fa0a73f7ac96dd1175ecb` |
| Connection destructor | `ev_027a9a3b04b5d3a1cca254a38f33a4b5c0faa31632e8fc30c22fb358fe46cd5d` |

The recovered disconnect/removal functions have no observed counter reset.
Counter initialization remains at registry construction, as recorded in
[connection registry recovery](connection-registry.md). A reconnect after an
entry has been removed therefore follows the new-connection allocation path;
remaining stale entries, failed asynchronous cleanup, process restart and
reference leaks still require integrated verification. A successful interface
return alone does not prove the reconstructed client reconnects correctly.
