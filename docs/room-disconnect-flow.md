# Driving the recovered room-disconnect lifecycle

`client/room_disconnect_flow.py` turns original `0x44d750` control flow into a
single-owner action controller. The driver performs requested actions and supplies
their observations; the controller never invokes original pointers, creates
threads, sleeps, pumps the UI, sends packets or assumes a timeout policy.
It remains a private runtime/research interface, not a stable mod API.

The initial actions reset the container at room `+0x2e0`, then the container at
`+0x1fc`. The driver provides the image observed after each reset. Only after both
resets does the controller inspect connected and pending state.

| State | Next action |
| --- | --- |
| Disconnected, including a nonzero pending flag | Reset local settings and finish with zero |
| Connected and pending | Yield; keep yielding while pending remains nonzero |
| Pending becomes zero | Reevaluate connected, then reset settings |
| Still connected | Enqueue task 1 with the old selector/channel pair |
| Untracked enqueue finished | Finish with zero |
| Tracked enqueue finished | Query its completed record before pumping |
| Completion absent | Pump the application |
| Pump returns zero | Query again |
| Pump returns any nonzero int32 | Finish with `-51` |
| Completion present | Return the record's signed result unchanged |

While pending remains nonzero, a change of connected to zero does **not** end
the wait. The original checks connected only after pending clears. Application
pumping belongs to the later tracked-completion loop; it is not called by this
pending-yield loop. No invented cancellation or deadline is added to either.

The controller's `room_image` exposes selective settings resets before enqueue.
Its enqueue action carries only the initialized eight argument bytes and tracking
intent. `enqueued` consumes the operation ID **written into record offset 4**,
not the enqueue function's return value. ID zero reaches the original query's
C++ exception; the portable controller rejects it as an authored input boundary.
An invalid observation leaves the current action available for correction.

For example: pending clears while still connected; the settings reset; task 1
is queued with record ID 17; the first query finds nothing; a pump returns zero;
the next query returns result `-6`. The controller finishes with `-6`, retaining
the already-reset settings. It does not restore a failed room or convert finding
a completed operation into successful removal. An application abort finishes
with `-51` without another query or an invented queue cancellation.

Eight focused tests cover these order and boundary rules, including composition
with owned worker records and completion retrieval. The
[original wait comparison](room-disconnect-wait-evidence.md) executes 308 complete
original producer scenarios and matches controller call order, full final room
images, pre-enqueue images and signed returns. Container, yield, enqueue, query
and pump effects are explicitly supplied substitutions. Logging is disabled.
Actual queue ownership, thread synchronization, socket lifetime and server
acknowledgement remain separate integration requirements.

```text
python -m unittest tests.test_room_disconnect_flow
python -m tools.room_disconnect_wait_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Source identity, function addresses and static control-flow evidence are linked
from [room disconnect](room-disconnect.md). A controller that matches these
bounded scenarios does not establish that the reconstructed client can reconnect
or join a live race.

## Native controller

`native/include/mco/room_disconnect_flow.hpp` exposes equivalent typed actions
and methods, using owned byte storage and fixed-width IDs/results. Sixty-nine
native/Python traces compare every requested action and full image snapshot,
including delayed results, pending changes and aborts. These pass locally on
Windows, alongside the native unit test. The Windows/Linux CI matrix includes
the differential runner; actual Linux acceptance depends on that run.

```text
python -m tools.native_room_disconnect_flow_compare build/native-check/mco_room_disconnect_flow_compare.exe
```
