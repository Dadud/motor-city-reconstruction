# Original channel wait lifecycle

`tools/lobby_channel_wait_oracle.py` compares original `0x73a360` against
`client/lobby_channel_wait.py` using supplied server images, argument bytes and
reply injection. The original function executes from entry through return.
No game startup, socket, logger, host callback or actual wait is executed.

Target executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA function evidence:
`ev_7f5a0622b416f8eba8c5c80cdb862a562339106d5ac2b0c766483a7e15c97c1c`.
Sleep-helper evidence:
`ev_067558dd64e17e839b9e39c4422105f92b550dbe00ffe6d43bec95ac7d2e8bc8`.

## Ordering and result precedence

The supplied pointer holder leads to a server object. Entry clears its reply
pointer `0x18c` and completed flag `0x190`, then sets waiting flag `0x194` to 1.
It copies selector field `0x04` for later registry lookup. Previous reply state
is reset without releasing the previous pointer in this function.

At each loop entry, completed state is checked. A completed nonnull reply yields
0; a completed null reply yields -1. Both clear waiting and retain completed
state. Successful completion retains the reply pointer for its consumer.

An incomplete loop sleeps for the helper argument 250000, then increments the
poll count. The helper converts unsigned microseconds to Windows milliseconds
by division by 1000, so this interval is 250 ms. More than 80 polls selects -2
before checking cancellation. There are 81 sleep calls on timeout, nominally
20.25 seconds before scheduling and callback overhead.

On polls 1 through 80, an optional callback is read from argument `0x154` and
called with argument value `0x158`. Only return value exactly 1 selects -51;
2 and `0xffffffff` do not cancel. These addresses are represented by explicit
portable callbacks, never called as original host addresses.

Each continuing poll and each cancellation/timeout exit performs registry
lookup of the copied selector. Original code tests the returned low byte
`AL`. Zero selects -6, overriding cancellation or timeout. This disconnect exit
leaves waiting at 1 and preserves a supplied pending pointer. The portable API
receives a boolean connectivity decision, corresponding to that low-byte test.

When cancellation or timeout occurs while lookup still succeeds, waiting is
cleared. A nonnull pending reply is released, then its pointer is cleared.
Completed state is retained. A reply arriving during a sleep is still subject
to cancellation and lookup before the next completion check. A reply injected
on sleep 81 loses to timeout. These precedence rules are preserved explicitly;
they should not be replaced by an inferred elapsed-time deadline.

## Bounded oracle substitutions

Four external boundaries are intercepted with argument capture and explicit
return/stack cleanup:

- `0x7e3e50`: records its microsecond argument and injects scripted reply state.
- Registry virtual lookup: checks the supplied registry object and selector.
- The supplied cancellation callback: checks the supplied opaque argument.
- `0x6992c5`: checks the pending pointer and that waiting was cleared before free.

Diagnostic logging is disabled by supplying zero at logging-enable global
`0xb38014`. The oracle supplies registry/vtable images and callback addresses
within its emulator-owned memory. Original allocation, real callbacks, real
registry state and actual deallocation are not executed. Instruction-count and
elapsed-time limits bound each run.

```powershell
python -m tools.lobby_channel_wait_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows comparison matched 25 scenarios. It compares return code, poll
count, reply retention, waiting/completed flags, boundary arguments, boundary
counts and their exact order. Scenarios cover completion on polls 1, 2 and 80,
null completion, timeout and cleanup, completion on poll 81, cancellation,
disconnect overriding cancellation and timeout, preservation of a pending reply
on disconnect, noncancelling callback returns, omitted callbacks and the low-byte
lookup decision. Initial stale state is deliberately supplied to verify reset.

These are controlled sequential injections, not evidence of real thread races,
clock scheduling, listener delivery or server acceptance. The function's native
pointer-holder layout and arbitrary callback addresses remain private research
details. Live channel lifecycle integration, ownership after disconnect and
concurrent listener synchronization remain separate recovery work.
