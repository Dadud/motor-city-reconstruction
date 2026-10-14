# Race-room selection and the actual join caller

Original callback `0x5e4870` is the observed direct caller of room-settings/join
routine `0x4509c0`. It supplies selected session data and prepared race metadata,
then starts and waits for the game server. This is evidence for one concrete
race-entry path, not a universal task order or proof of live acceptance.

Target executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`,
original path `C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe`.
Provider: Ghidra 12.1.4. All descriptions and portable code are authored;
proprietary pseudocode and executable bytes are not redistributed.

## Inbound data and object identities

The callback input has a descriptor pointer at offset `0x84`. A null descriptor
selects terminal state value 7 without reaching room joining. On the permitted
path, the password argument is the NUL-terminated string at descriptor `+0x41`.
Its complete descriptor type, ownership and authenticated producer remain
unrecovered; it is not identified as an account password.

The application global at `0x9e1060` supplies a client component at its offset
`0x424`. The race callback reaches the game-network object at component `+0xdc0`.
Its embedded room object is component `+0xe60`, or network object `+0xa0`.
The room-settings cache used for early name validation is component `+0x1218`,
or network object `+0x458`. These different receivers must not be collapsed into
one object pointer.

| Local source | Observed use |
| --- | --- |
| Global `0x9aa9d4` | Selected NUL-terminated room name |
| Global `0x9aa9d0` | Requested channel ID; also supplies some mode-specific room names |
| Global `0x9aa9b0` | Mode value controlling the name override |
| Global `0x9aaa48` | Readiness value; downstream settings retain its low uint16 |
| Input descriptor `+0x41` | Password string passed to room joining |
| Metadata helper `0x62f740` | Initial 204-byte race metadata snapshot |
| Global `0x9aa92c` | uint32 replacement at metadata offset `0x78` |
| Global `0x9aa978` | uint32 replacement at metadata offset `0x90` |
| Global `0x9aa97c` | uint32 replacement at metadata offset `0xa8` |

These are frontend/session state inputs, not configured fan-server constants.
The connection selector used later by the room producer comes from the connected
network object's binding. A configured shard number is not substituted for it.

## Observed order before joining

The callback updates its progress/state and registers a local callback. If the
current room name is nonempty, it initializes temporary settings and queries
the room cache through `0x44be10`. A nonzero result shows an error and exits to
state 7. Empty names skip this cache-validation branch.

After two local preparation calls, metadata helper `0x62f740` produces a
204-byte image. The caller clears metadata bits 1 through 4 at byte offset
`0x64` using `value & 0xe1`, and writes the three uint32 replacements above in
little-endian form. It then calls room disconnect `0x44d750` with waiting enabled.
A negative disconnect result prevents joining and selects the error path.

For modes `0x13` and `0x19`, a nonzero requested channel causes the global room
name to be replaced with its **unsigned** decimal representation. Helper
`0x6af9d6` calls conversion `0x6af950` with the signed-conversion switch zero.
Thus `0xffffffff` becomes `4294967295`, not `-1`. Other modes and channel zero
retain the prior name. Complete gameplay meanings for these two mode values
remain unresolved.

The name change occurs after metadata construction and validation. Metadata
therefore retains its previously prepared name bytes. Rebuilding it from the
new decimal room name would change the observed request. The metadata helper
places its initial room name at byte offset 4; the authored final-edit helper
preserves the whole supplied metadata image except its four recovered patches.

## Actual call arguments and composition

At `0x5e4a72`, the six arguments passed to `0x4509c0` are:

1. The current global room-name pointer.
2. Descriptor pointer plus `0x41`, as the password string.
3. The patched metadata buffer.
4. Metadata byte count `0xcc`, or 204.
5. The readiness source value from global `0x9aaa48`.
6. The requested channel ID from global `0x9aa9d0`.

`0x4509c0` initializes settings with protocol `0x21`, copies the explicit
204-byte metadata into its cleared 256-byte data region, retains the low
uint16 readiness value, applies settings to the room object, and requests a
waiting room join with flag-`0x20` switch zero. The remaining 52 data bytes are
therefore zero on this path. The separate producer `0x44cf80` constructs local
room-worker task zero from those settings.

`client/race_room_selection.py` implements the final metadata patches and name
selection using explicitly supplied inputs. Its `RaceRoomSelection.room_inputs`
requires a supplied connection selector and composes the verified settings
padding/protocol into `RoomJoinInputs`. The caller can pass its separately
retained password to the recovered room-argument producer. The helper does not
perform cache validation, disconnect, queue scheduling or network I/O.

This authored boundary requires names up to 31 bytes and passwords up to 16
bytes without embedded NUL, matching the downstream portable safety limits.
Original string copies are unbounded; these limits are deliberate reconstruction
validation, not claims about original caller checks. Password and metadata are
excluded from the result's default representation.

## What happens after a successful room join

The callback invokes `0x450db0` after a nonnegative room-join result. That helper
constructs **game-network worker task 5**, using connection selector at network
`+0x5cc` and joined room channel at network `+0x160`, and requests tracking.
It queries completion and pumps the application. Abort yields -51; a negative
worker result is returned unchanged.

It then repeatedly queries room settings with `0x44be30` for the joined channel.
The observed room-status byte at settings `+0x44` selects failure -20 when 8,
success 0 when 4, and continued polling otherwise. Missing room settings yields
-7. The helper has no inferred elapsed-time timeout in this path.

On zero from that helper, race callback `0x5e4870` calls `0x5e4c10` for subsequent
session preparation. Its result selects terminal state values 4 or 7. A -51
from joining or starting selects state 3. Other failures take error paths.
These state numbers are preserved as observed values; their UI labels are not
assigned by this research. Session setup, start request wire semantics, server
state updates and race synchronization remain separate recovery work.

## Evidence and comparison scope

| Observation | REA Evidence |
| --- | --- |
| Race callback `0x5e4870` | `ev_f0e2cbd1eb5bb667dc25cd76e016f1a13382213ee7538767014f5e8a99a220af` |
| Metadata builder `0x62f740` | `ev_7d99e91bcdad639504d27d47319227185f4f73768701aaa82db23a2701ed833b` |
| Unsigned conversion wrapper `0x6af9d6` | `ev_6a26fd0f60b45f0000b25d5f634e62841f8ddc357b10df737131b2a79c1e6889` |
| Settings/join caller `0x4509c0` | `ev_30a7fdbaae68a4c70f8ed085fcd42ee41c41b89e8de61b638ef153090d238e09` |
| Start-and-wait helper `0x450db0` | `ev_4379985d0db20df6777b102f37029aa2c36a090e826d68de706683b66e62ce86` |
| Subsequent preparation `0x5e4c10` | `ev_4990671edd540b6c86382b99b87a8a89a417f1396f452af6529ad84615349b8c` |

```powershell
python -m tools.race_room_selection_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows bounded execution matched 210 final-selection scenarios, including
48 unsigned name overrides. Four focused Python tests pass. The oracle executes
original caller ranges `0x5e4948..0x5e497b` and `0x5e4a13..0x5e4a72`, including
the original decimal conversion helper. It checks all patched metadata bytes,
name selection, receiver adjustment and the six complete join-call arguments.
Each invocation has execution limits. No callable boundary is substituted in
these ranges; their earlier state is supplied explicitly.

The oracle starts after metadata creation and assumes prior disconnect success.
It does not execute the full metadata builder, name validation, disconnect,
descriptor ownership, room join, task 5, status polling or subsequent session
setup. No credentials or live captures are used. Authenticated production of the
descriptor/global state, complete metadata-field meanings, asynchronous room
updates and live fan-server race acceptance remain unresolved. Synthetic
selection parity is not a successful online race.
