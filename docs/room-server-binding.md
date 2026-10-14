# Connecting the room to its server connection

The room request's server selector comes from the successful server-connection
interface return. It is not supplied by the patch's configured shard number.
The game-network dispatcher stores that return directly into its embedded room.
This establishes an upstream source for the request field; it does not establish
that a reconstructed connection has completed authentication or owns an original
compatible connection-registry entry.

Target: original `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA provider: Ghidra 12.1.4. All descriptions here are authored observations.
Original instruction bytes and decompiler output remain external inputs.

## Pointer adjustment and assignment

Constructor `0x44fb20` calls the room constructor `0x44cce0` with `this + 0xa0`.
The room therefore begins at main owner offset `0xa0`. Its initial selector at
room `+0x39c` is `0xffffffff`, as documented in the room producer investigation.

Task-zero dispatcher `0x454d50` receives the main owner's worker subobject at
main `+0x0c`. Assembly explicitly subtracts 12 before retaining the connection
result. This distinction matters: the decompiler presents some fields relative
to the unadjusted worker pointer, whereas the actual writes below are relative
to the main owner.

| Main owner field | Observed task-zero behavior |
| --- | --- |
| `+0x5cc` | Always stores the connection-interface signed int32 return |
| `+0x43c` | On nonnegative return, stores that return as embedded-room selector (`0xa0 + 0x39c`) |
| `+0x5fc` | On nonnegative return, stores 1 |
| `+0x5f4` | On negative return, stores the negative return |
| `+0x600` | Clears to zero on either branch |

On failure, the previous room selector and the previous connected field are
preserved by this dispatcher. On success, the previous error is preserved. The
reconstruction does not add resets that this function does not perform.

Success then calls `0x451860` with the main owner, followed by `0x456b20` with
receiver main `+0x4a0` and two values: connection result and zero. `0x451860`
enqueues game-network task 8 when the connected field is nonzero. `0x456b20`
enqueues observer task 1 with the two supplied values. These helpers schedule
separate local work; they do not provide a new selector assignment.

Thus the recovered production chain is connection-interface return → main
`+0x43c` / embedded room `+0x39c` → room producer argument `+0x00`. Passing the
configured shard ID into that argument would bypass this observed source.
The [connection registry investigation](connection-registry.md) now recovers
ID allocation and existing-connection lookup. Registry insertion, lifetime and
authentication remain necessary before turning this chain into a live room operation.

## Authored implementation and verification

`client/room_server_binding.py` reproduces the bounded dispatcher image writes,
return value and success helper intents. It uses explicit byte images and inert
values for research; it does not authenticate, send a packet, enqueue work or
dereference an interface token. The state transition is integrated with the
existing room-input image reader in a focused unit test.

```text
python -m unittest tests.test_room_server_binding
python -m tools.room_server_binding_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Local Windows execution passed three focused unit tests and matched 80 bounded
original dispatcher executions. The oracle varies random preexisting bytes and
returns spanning the negative boundary, common errors, zero, small successful
IDs and the positive int32 boundary. It compares the complete owner image,
return, helper receivers, argument values and helper call order.

Only the connection-interface call, mini-room helper `0x451860`, and observer
helper `0x456b20` are substituted. Their effects are excluded, while original
dispatcher branching and all result writes execute unchanged. The PE entry point,
authentication, sockets, queue execution and live server are never invoked.

| Observation | REA Evidence |
| --- | --- |
| Main owner constructor and embedded room at `+0xa0` | `ev_08fc5e066aa8d625ac8cf79fc29dc1825f3f5a72d792524ca57e2f8234afe99b` |
| Task-zero connection result and adjusted owner writes | `ev_9170e4e2a5da0fe611eab3362980db11b6754d741438a80273e9aad306288681` |
| Mini-room request scheduling helper | `ev_252a04c4d3b711058c72b926a0c6581b026899dca5f3bc689eba3976fdfeab35` |
| Observer enqueue helper | `ev_c3737a4abdf4b270ec69831af3b0e1fd989d17ae6dbff843749fb381f9df3dea` |
| Observer constructor and retained interface | `ev_3b62811995d67ee866181c44c1b1eb8f2b9406e2171488cd564b025d6f222c2b` |

The original-function comparison proves this bounded binding transition. Live
fan-server acceptance, listener integration, room settings and race entry remain
separate verification requirements.

## Native port

`native/include/mco/room_server_binding.hpp` provides equivalent full-image
state writes and explicit helper intents. The C++20 port preserves prior errors
on success and prior selector/connected fields on failure. Its unit test and
80 native/Python full-image, signed-return and helper-intent comparisons pass
locally on Windows. The differential corpus covers ten return values and eight
image lengths; it does not execute a live connection.

```text
python -m tools.native_room_server_binding_compare build/native-check/mco_room_server_binding_compare.exe
```
