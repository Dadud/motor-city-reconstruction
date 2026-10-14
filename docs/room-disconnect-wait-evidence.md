# Room disconnect wait and application pumping

The complete room disconnect producer `0x44d750` now matches the portable
`RoomDisconnectFlow` controller across 308 bounded original executions. This
comparison covers original branches from entry through return, including pending
state changes, tracked/untracked enqueue, completion queries and application
abort. The boundary operations are scripted substitutions, not working threads
or a live server connection.

Target: original `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: Ghidra 12.1.4. Static producer evidence:
`ev_11eebe917bf56c1fcf4c590a33cde1e3fc0c1f280a7d104b7d81f880484d372f`.
Descriptions and comparison code are authored; original bytes and decompiler
output remain external inputs.

## Observed order

The container-reset calls run first: room `+0x2e0`, then room `+0x1fc`.
Their substituted effects leave the supplied room image unchanged. The producer
then checks the connected uint16 field at `+0xec`.

- Already disconnected: selectively reset settings and return 0. A nonzero
  pending field at `+0x3a8` is preserved and does not cause Sleep or enqueue.
- Connected with a pending operation: call `Sleep(0)` repeatedly and recheck
  pending until it clears. Connected is rechecked only after pending reaches
  zero. Becoming disconnected while pending remains nonzero does not end this
  loop. Once pending clears, a disconnected image follows the reset/return path.
- Stable connected: preserve selector `+0x39c` and channel `+0xc0` in the eight
  initialized argument bytes of local task 1. Reset settings before enqueue.
  Pass worker receiver room `+12` and tracking equal to the wait switch.

Untracked enqueue returns 0 immediately. Tracked enqueue is followed by a
completion query before any application pump. The query's ID comes from the
task record at `+4`, not the enqueue call's return register. The oracle
deliberately returns zero from enqueue while writing a nonzero tracked record
ID, and the original still queries the written record ID.

When completion is absent, the producer calls application virtual entry `+4`.
Any nonzero pump result returns -51 immediately, without another completion
query. A zero pump result is followed by another query. The first present
completion returns the signed int32 record result at `+8`, including negative
errors and positive values. A successful local completion does not establish
delivery or acknowledgment of the downstream channel-close operation.

## Comparison corpus

```text
python -m tools.room_disconnect_wait_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

The corpus has seven starting-state/update sequences and eleven completion
modes, each repeated with four randomized full room images:

- Disconnected with zero or nonzero pending.
- Stable connected.
- Pending cleared while remaining connected, after one or three yields.
- Pending cleared after connection becomes disconnected.
- Connection already becomes disconnected on an earlier yield while pending
  remains nonzero, then pending clears on a later yield.
- Untracked enqueue, immediate completions spanning signed int32 boundaries,
  one/two missing queries followed by success/error, and abort after the first
  or second pump. Abort inputs include 1 and raw high-bit nonzero values.

Every case compares the complete final room image, return result and ordered
boundary calls against independently assembled expectations and the Python
controller. Connected cases also compare the complete room image observed at
enqueue, proving that the selective settings reset occurs before that call.
Tracked IDs include 1, 7, `0x80000000` and `0xffffffff`. All 308 original and
controller comparisons passed locally on Windows.

## Boundaries and limits

`tools/room_disconnect_wait_oracle.py` exposes `observe` for further bounded
research. It returns inert observations: ordered calls, full room image,
enqueue image, signed return and consumed script counts. Scripts provide each
Sleep observation, query result and application pump result. Script exhaustion
fails explicitly rather than fabricating progress. Instruction execution is
bounded and the PE entry point is never invoked.

The oracle substitutes and verifies these calls:

| Boundary | Verified inputs |
| --- | --- |
| Container resets `0x4485f0` / `0x456930` | Exact room-relative receivers and order |
| `Sleep` | Argument zero; scripted pending/connected writes |
| Enqueue `0x4a5390` | Worker receiver `+12`, kind 1, initialized eight argument bytes, tracking |
| Query `0x4a5610` | Worker receiver `+12`, written record ID, same stack-record output pointer |
| Application pump virtual `+4` | Exact inert application receiver and raw result |

Logging is disabled. Container contents, queue mutation, worker scheduling,
completion record bytes other than the consumed result, and task bytes outside
kind/initialized arguments are excluded. The producer does not initialize its
remaining stack record; the oracle does not give those bytes a meaning.

The controller's nonzero tracked-ID validation remains an authored boundary:
the original completion wrapper throws for ID zero. This corpus supplies valid
tracked IDs and does not execute that exception path. There is no invented
timeout for the original pending or completion loop. Actual threading,
application event handling, cancellation ownership and live room removal remain
integration work. This comparison proves recovered control flow under the
declared observations, not fan-server compatibility.
