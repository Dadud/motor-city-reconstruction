# Original game-start completion and room polling

The original `mcity.exe` helper at `0x450db0` waits for two separate observations:
completion of worker task 5, then a room status that permits session preparation.
A nonnegative worker result alone does not mean that the race has started.
`client/game_start_flow.py` and the C++ `GameStartFlow` reproduce this ordering
through explicit driver actions. They do not yet send the start request.

## Original sequence

The target SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA Evidence for the helper is
`ev_4379985d0db20df6777b102f37029aa2c36a090e826d68de706683b66e62ce86`.

1. Capture the selector at owner `+0x5cc` and channel at `+0x160` as two
   little-endian 32-bit values in task 5's initialized argument prefix.
2. Enqueue a tracked task using the worker object at owner `+12`.
3. Query completion using the operation ID written into the task record at
   `+4`, rather than the enqueue call's return value.
4. While completion is absent, pump the application and query again. Return
   a negative worker result unchanged when completion arrives.
5. For a nonnegative result, initialize temporary room settings and pump the
   application before the first room-cache lookup.
6. Look up the current channel using the cache at owner `+0x458`. Read room
   settings status at `+0x44`; repeat pumping and lookup until a terminal result.

| Observation | Next action or result |
| --- | --- |
| Completion absent | Pump application, then query completion |
| Worker result negative | Return that signed result |
| Worker result nonnegative | Initialize settings, then pump application |
| Application pump returns any nonzero value | Return `-51` |
| Room lookup fails | Return `-7` |
| Room status is 8 | Return `-20` |
| Room status is 4 | Return `0` |
| Other room status | Pump application, then look up room again |

The task captures its channel once. Each later room lookup rereads the owner's
current channel, so changes during application pumping affect subsequent lookups.
There is no elapsed-time timeout or recovered cancellation packet in this helper.

## Authored driver boundary

The controller owns a copy of the observed network state. A driver supplies
enqueue IDs, optional completion results, pump results and optional room-status
bytes. A pump can also supply an updated state image; its size is validated before
mutation. Out-of-order observations are rejected without advancing the flow.

The authored API rejects a zero enqueue ID. The original completion-query path
throws for that ID; this validation is not a newly recovered server response.
Only the initialized eight-byte argument prefix is represented. Unspecified task
padding is not fabricated. Offsets are private research details, not a mod API.
Room observations represent the relevant status byte, not the entire cache-copy
implementation. Real worker execution, cache updates and transport remain separate.

## Verification

```powershell
python -m tools.game_start_flow_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_game_start_flow
python -m tools.native_game_start_flow_compare build/native-check/mco_game_start_flow_compare.exe
```

Local Windows bounded execution matched 208 scenarios from the original helper's
entry through return. It compares ordered boundary calls, receivers, operation
IDs, signed results and the complete final owner image. The enqueue substitute
returns zero while writing a valid record ID, proving which value the caller uses.
Pumping changes the channel, including unsigned wraparound. The original temporary
settings initializer runs unchanged and the exception-chain head is restored.

The comparison substitutes enqueue, completion lookup, application pumping and
room lookup with controlled observations. Logging is disabled and execution is
instruction-bounded. It does not execute host callbacks, sockets or real threads.
Six focused Python tests and a native unit check cover invalid observations and
ordering. Another 63 C++/Python traces compare every action and full state image.
CI runs the native comparison on Windows and Linux; this local validation was on
Windows.

## Remaining start-request recovery

The worker's interface slot at base `0x84b3fc` plus `0x40` contains `0x7385a0`
(REA Evidence `ev_35472c18ed93e8c638c8cbd4c43c72596037f079f4d465980ff0aefbe7a3a51b`).
The current analyzer has no containing procedure at that address
(`ev_2cabb4841060ed6cae8dddf37dca0411235d815a12e04a31773753c6ce18163e`).
A subsequent byte read confirms mapped executable bytes there; the missing
procedure does not establish that the implementation is absent.

Static decoding of the mapped bytes continues the path through interface offset
`+0x64`, whose table entry is `0x735710`. The caller supplies its first argument,
zero, `0x309`, zero and zero, while retaining the second argument in global state.
The relevant byte-read Evidence is
`ev_c7a7a696fcd784d70e57164bbd379d7a8665082cca3990090c2b0e57e77845c5`.
Inside `0x735710`, a subsequent call uses the object referenced by `0xb380d0`
and interface offset `+0x14`, with pointers to the caller arguments and a local
object (`ev_c0beba10ade23dd0130dca5ed7ffe393c3af5927f31d6677143f11b81c83e161`).
This is a further research path, not evidence that `0x309` is a wire opcode:
the downstream implementation and serialization still need recovery.

The wire operation and its complete layout remain unresolved. Task number 5 is
not evidence of a wire opcode. A live driver must connect recovered worker and
cache behavior to this flow, followed by session preparation. These comparisons
do not establish successful Revival race entry.
