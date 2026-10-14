# Selected event connection and lobby join

The recovered `0x5e7ba0` path connects a secondary game-network owner to the
server associated with a selected event, then joins that owner's `LOBBY`
channel. The selected event name and the channel name used for this join are
distinct. This path does not establish a complete race start or position-sync
sequence, and it must not be flattened into guessed local task numbers.

Target: original `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4. All text and portable code here are authored; original
instruction bytes and decompiler output remain external inputs.

## Direct upstream caller

`0x5e7840` obtains the selected record with `0x5e4d90(event_id)`. That lookup
walks a service-provided table with a `0x239`-byte record stride and validates
the selected entry's identifiers, name and several availability fields. The
complete producer and meaning of every record field remain unresolved.

The caller includes an eligibility comparison: when two profile flag bits
`0x18000000` are absent, it compares a profile uint32 at `+0x75` against the
selected record's uint16 at `+0x201` and displays an error when the profile
value is smaller. The units/labels of those fields are not established here.
It rejects an empty selected name at record `+0x0c` and checks the primary
game-network connected field before proceeding.

The sole analyzed incoming reference to `0x5e7ba0` is not a direct call. It is
the callback pointer supplied by `0x5e7840` to dialog helper `0x5c6190`, along
with the selected record. The caller treats dialog result 4 as success.
Its own callers include `0x5cebb0`, `0x5e50f0`, `0x5e5210`, `0x5e6c40` and
`0x5e6eb0`; their full UI/service semantics are outside this bounded recovery.

## Callback order and owner offsets

The callback receives a UI object, reads its selected-record pointer at `+0x84`,
and sets UI field `+0xd0` to 3 through `0x74bed0`. It then follows this order:

1. If the selected pointer is absent, report dialog result 7 and stop.
2. Activate the callback's context value from UI `+4` through `0x5d96e0`.
3. Call `0x44a110` on the primary network owner with the selected record's
   name pointer `record +0x0c`.
4. If setup is nonnegative, call `0x450830("LOBBY")` on the secondary network
   owner, at primary network `+0xdc0`. The selection call's return is ignored.
5. Call `0x44cf80(1, 0, null)` on the secondary owner's embedded room at primary
   network `+0xe60` (`0xdc0 +0xa0`). This requests waiting, no extra flag `0x20`,
   and no password.
6. On a nonnegative join result, apply the selected record through `0x5e4fe0`,
   then report dialog result 4. On a negative result, request secondary server
   disconnect through that owner's virtual entry `+8` with wait argument 0.

The original main network pointer is loaded through global root `0x9e1060`
field `+0x424`. None of these offsets are mod API identifiers or wire fields.

| Observed failure | Callback behavior |
| --- | --- |
| Selected record absent | Dialog result 7, no setup or join |
| Server setup negative, including -51 | Report setup error; dialog result 7 |
| Room join returns -51 | Request secondary disconnect; dialog result 3, no error report |
| Other negative room result | Request secondary disconnect, report join error; dialog result 7 |
| Nonnegative room result | Apply selected event globals; dialog result 4 |

These numeric results belong to the UI callback protocol. They are not race
session IDs, match states, or proof of server acknowledgment.

## Server address, identity and room settings sources

`0x44a110` copies the primary owner's retained identity at `+0x604` into the
secondary owner through virtual entry `+0x0c`, implemented by `0x451770` and
identity copy `0x455e40`. This uses retained login/persona identity rather than
deriving an identity from the selected event record.

The setup helper selects the event name on the primary owner through
`0x450830`, then calls `0x4504b0(name, secondary_owner, 1, 0)`. That function:

- Requires the primary connected field at `+0x5fc` to be nonzero.
- Returns the secondary retained connection ID immediately when the secondary
  connected field is already nonzero.
- Otherwise waits for primary room-list readiness, copies the selected name
  into the secondary owner's saved-name field at `+0x5d4`, and looks up that
  name in the primary room list through `0x44be10` / `0x45f040`.
- If the room-list record's uint32 at `+0x50` is zero, calls `0x450aa0` to obtain
  server information and waits for that record to become ready.
- Calls the secondary server-connect method at virtual entry `+4` with host
  pointer `room_list_record +0x30`, port value `room_list_record +0x24`, primary
  retained identity pointer `primary +0x604`, and final options `(0, 0, 1)`.

The concrete secondary server-connect method is `0x44fe10`, matching the
recovered game-network vtable. The last three arguments are supplied exactly
as observed; this site disables the queue option and enables waiting. The
login key and complete account-service setup still belong to that downstream
connection implementation and must be verified in the integrated path.

On nonnegative setup, `0x44a110` requests the secondary big-room list through
`0x451990` and waits for its list readiness. Application abort requests secondary
disconnect and returns -51. Thus room-list readiness is a separate condition
from the successful connection return. Server-info and list request tasks are
conditional operations; this evidence does not justify one unconditional
sequence of dispatcher task numbers for every race entry.

The subsequent `LOBBY` selection uses the existing `0x450830` settings path,
and `0x44cf80` builds its request from the secondary room image. The secondary
selector must therefore come from that owner's authenticated connection
binding. It is not the primary connection ID, selected event ID, configured
shard number, or dialog result. The already recovered settings transfer and
room producer remain applicable to this owner-specific path.

## Selected event globals after join

`0x5e4fe0` copies several selected-record values into process globals after
the room join succeeds. Observed inputs include unaligned uint32 fields at
`+0x137`, `+0x225`, `+0x143`, `+0x13f`, `+0x203`, `+0x207`, `+0x147`, `+0x14b`,
`+0x14f` and `+0x1b7`; uint16 at `+0x157`; and a float at `+0x153` rounded to an
integer. Two short fields `+0x20d` and `+0x20b` become bit flags 1 and 2.
The record's first two uint32 values are also retained. Their units and effect
on actual race rules remain unresolved; these copies are not newly invented
rules or physics calculations.

## Portable transition and verification

`client/race_join_transition.py` preserves the bounded callback decisions and
ordered intents from explicitly observed setup/join results. It does not
select an event, authenticate, derive addresses, execute a join or apply globals.

```text
python -m unittest tests.test_race_join_transition
python -m tools.race_join_transition_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Three focused unit tests pass. The oracle matched 28 complete original callback
executions, covering missing selected record, setup failure, join abort, other
join errors, and nonnegative setup/join results including int32 boundaries.
Original branching and callback-state write execute unchanged. Explicit inert
substitutions capture context activation, server setup, room selection/join,
disconnect, error-resource handling, event-global application and final UI
reporting. The oracle verifies receiver offsets, original argument values,
error translation tables and call order. It supplies an inert x86 SEH chain;
no PE entry point, host UI or socket is invoked.

| Observation | REA Evidence |
| --- | --- |
| Callback branches and secondary-owner offsets | `ev_7c73fa834fb355ce3f34e72bc38a895c8d6f9a7a6e6904e3a39c1622faf77f15` |
| Callback incoming reference | `ev_a835f246e07ccc1c78d1ad49c2151f43d3d9f6b9c7e16274c43700a8862f55a2` |
| Upstream event eligibility and callback registration | `ev_eefe85bd45f783b0c69ba6f59522ec9793af9985d9e2e57a91d39dfb44ceeab6` |
| Selected event table lookup | `ev_10846f829bb4ac302a8bbade21e33744faf5b523ccb254517d1e53e965f6c4ef` |
| Server setup and secondary-list readiness | `ev_4d491c7ff6e0fce4c29afcbbacc1a658350f68efd9db2c4fa2b8e6b58f0a93c6` |
| Address/port/identity derivation | `ev_efb885f2fa98d0e4e3679948ce3c77c81d4f493ddca7be3ae8038ed9022b5953` |
| Identity setter | `ev_1503e86d2d62fb3a5ac0c6480fb37f426f942145495db39b19363b498c7591bb` |
| Room settings selection | `ev_7e2b9ff7c22bf4085d19eb75989bbae9b04588c0e2039102fae1bbb6bbe433cd` |
| Server-information request/wait | `ev_fe254f363fdb3bf686c7a0360ff6e76ff98859a326a0108bdb6db2cf5a937b25` |
| Big-room-list request | `ev_d98ad0888c25f92fb91a39e2c998da643f751153360deebac6d4b38a4aeb5bae` |
| LOBBY literal | `ev_011f2fcd710dc998d924b37bfaae63e3b56645e1de5a6525d956f960b1473f36` |
| Event globals after join | `ev_d3ff82ea517fb7ad97afe6b0c1382244ab213a85d3f18dff31bcc280c0e69991` |

This recovers one concrete entry transition and its conditional sources.
Room-list wire decoding, successful original server-info update, complete
callback/context ownership, race lobby messages, game start, synchronization,
finish reporting and live Revival verification remain required. The comparison
does not claim that an arbitrary selected event can currently be joined.
