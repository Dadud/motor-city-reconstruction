# Original driving callback scheduler

The recovered scheduler establishes list execution and interleaving, including
the catch-up limit. It does **not** establish a constant wall-clock frequency.
The implementation is in `client/scheduler.py` and `native/src/scheduler.cpp`.
It exposes callback IDs and supplied dispatch functions, rather than original
addresses or internal pointers as a gameplay API.

## Lists and callback execution

Registration at `0x567940` builds two lists. Insertion at `0x565d20` compares
signed 32-bit priorities and inserts before the first strictly larger priority.
Equal priorities keep registration order. Priority is an ordering key; the
executor does not interpret it as an interval, deadline or frequency.

The registration builder now has a direct bounded translation in
`client/game_schedule.py`. It preserves both original capacity formulas,
vehicle/world-object registration order and the flag-gated secondary vehicle
callback. `tools/verify_game_schedule.py` compares complete allocated list
contents against 64 original `0x567940` executions with the allocator and
dynamic service-value producer controlled. This validates list construction
from supplied counts, addresses, flags and service payload; it does not recover
the producers of those global values or the callbacks' full runtime behavior.

The original executor `0x565e40` snapshots the list's signed count on entry.
It walks that many 16-byte records, reading each callback and argument when it
reaches the record. A null callback is skipped; every other callback receives
one 32-bit argument, and its return value is ignored. Changing a later record
during a callback affects the same execution. Increasing the count does not
extend the execution already in progress.

The reconstructed boundary rejects shortening storage during execution. Original
code assumes the records remain addressable; no original safe behavior for
invalid storage is claimed. Allocation, deletion and callback implementation
remain separate from the recovered executor.

## Two-list interleaving

The list calls occur in the state-3/state-4 branch of `0x568390`.
For each selected subiteration, the block `0x56857b–0x5685c5`:

1. Calls the first list only if the simulation counter's low bit is zero.
2. Calls the second list.
3. Calls the post-iteration helper `0x434f90`.
4. Increments the simulation counter with 32-bit wraparound.

A nonzero caller argument inhibits this block. On other state branches,
different callbacks execute; the published helper reconstructs this specific
driving branch, not the full application state machine.

For example, starting at counter 0 with two subiterations produces
`first, second, after, second, after`, ending at counter 2. The first list
contains the force controller and contact processing; the second contains
the active pose update. Consequently force/contact and pose updates are not
called at identical rates in this block. The first list runs once per two
subiterations, while the second runs once per subiteration.

The callback boundary supplies list execution and the post-iteration action.
These callbacks do not write the simulation counter through hidden original
globals. Counter mutation inside those original callback bodies is outside
the present comparison; the helper owns and returns its counter explicitly.

## Selecting subiterations

The selector `0x568523–0x56857b` uses two external observations from `0x55fc10`
and `0x55fc80`, plus the signed frame counter. Their application meanings remain
unassigned until their producers are recovered.

| Adjustment enabled | Observed mode | Selected subiterations |
| --- | --- | --- |
| No | Any | 1 |
| Yes | 0 | 1 when frame is divisible by 4; otherwise 0 |
| Yes | 1 | 1 when frame is divisible by 2; otherwise 0 |
| Yes | 3 | 2 |
| Yes | Other | 1 |

The divisibility checks include negative signed frames. They must not become
a guessed network transmission rate or a newly designed timestep policy.

## Outer catch-up and clock boundary

The outer function `0x568820` computes a wrapping 32-bit subtraction of the
available-clock counter minus the processed counter. It treats the result as
signed, performs no updates for a nonpositive result, and caps positive
catch-up at sixteen outer iterations per invocation. A successful inner call
increments both the processed counter and the frame counter. An inner return
of zero stops the loop before those increments. The published
`pending_iterations` helper verifies the arithmetic and cap; it does not
implement the outer function's input, network, transition or early-exit effects.

Clock production is partially traced. Initialization `0x447e40` starts the
worker at `0x447eb0`. Its instructions call a wait function with argument 7,
increment an intermediate counter, and increment the available-clock counter
on every second pass. A protected compensation count can cause additional
passes before the next wait. The compensation producer `0x447d80` is called
by `0x5788a0`, whose multiplayer path adds 2 when another vehicle's reported
frame counter is ahead. These are static observations, not measured host timing.
They establish why a fixed frequency cannot be inferred from either the wait
argument or the simulation's `1/32` and `1/64` arithmetic constants.

Remaining recovery includes clock/runtime timing, focus/pause behavior, all
mode-observation producers, full callback bodies, asynchronous compensation,
and integrated driving-state comparisons on an original client.

## Comparison evidence

`tools/scheduler_oracle.py` executes the verified original x86 instructions in
a bounded CPU-only emulator. It performs:

- 648 insertion comparisons, including ties, signed limits and the allocation
  sentinel priority.
- 365 executor comparisons, including null callbacks, original order and a
  callback that replaces a later entry and increases count during execution.
- 1,440 selector/interleaving comparisons, including both counter parities,
  wraparound, negative frames, inhibited calls and all recovered selector modes.
- 81 catch-up comparisons around zero, the sixteen-update cap and signed wrap.

Actual executor instructions run inside the interleaving comparison. Game
callback bodies, the post-iteration helper, adjustment observations and the
outer bookkeeping helper are supplied; no clock thread, executable entry point,
Windows services or network connection executes. The native comparison contains
1,521 selector/interleaving/catch-up rows against the Python implementation.

Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
The authoritative harness verifies the exact digest in `tools/native_oracle.py`.
Original bytes and decompiler output are private local inputs.

Evidence IDs:

- Registration: `ev_e4a36a338cd41b44e594b999c015a71ac9673355be94969ab1b18061807422ac`.
- Insertion: `ev_8dd8f9ab99394dc5275d0eb066ef7f3623130ac59e2efb27131b23c3c95c6744`.
- Executor: `ev_afdf81f759a6e78d42210fde74d42fc8dde6717043e93cf31408a3b681076f6c`.
- Inner selector and interleaving: `ev_c997f39b76e5ede8af0cca35b5de9f95d642728c2da00ba3f7d6c4e19e86f6ef`.
- Outer catch-up: `ev_433cdbf3f92e571e31220200b2978201e9e4cbb197011829191dc3f8f735a918`.
- Clock initialization: `ev_c62b8bdfe7eea985b0a93fb98c5806532df4ed415ee4fcea9cf221250f0d623f`.
- Protected compensation: `ev_11536b857377cd0d6fe6436c220e7117340b8b82300a4035c767353e5ab24e88`.
- Multiplayer compensation producer: `ev_9f021d0a6b275b4cd2a5ad9668c10471c842d0724ecc0eaf8df90d67ab5b36de`.
