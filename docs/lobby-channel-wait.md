# Channel reply wait order and units

`client/lobby_channel_wait.py` reconstructs the bounded wait helper `0x73a360`
with explicit sleep, connection-lookup, cancellation and reply-release boundaries.
It does not send a request, construct authenticated room arguments or own sockets.
The default online tester remains an account/garage-data test.

## State and precedence

At entry the original helper clears the reply and completion fields, then marks
the server object waiting. It checks completion at the top of each iteration.
A completed slot with a reply returns zero; a completed slot without a reply
returns -1. Both clear waiting, while retaining the completion field.

Otherwise it sleeps, increments the poll count and applies the following order:

1. After poll 80, select timeout (-2) without calling cancellation again.
2. On polls 1–80, a supplied cancellation callback cancels only when it returns
   exactly 1, selecting -51. Other return values continue polling.
3. Look up the connection. A missing connection returns -6, even when timeout
   or cancellation was selected, and leaves the pending object fields untouched.
4. On connected timeout/cancellation, release a nonnull pending reply, clear its
   reference and clear waiting. Retain the completion field.
5. When still polling, check completion at the start of the next iteration.

A reply delivered during the 81st sleep can therefore lose to timeout. A reply
delivered during a sleep can also lose to cancellation or a disconnected lookup.
The reconstructed behavior keeps these original decisions visible; it does not
replace them with a guessed deadline or preferred error precedence.

`wait_for_channel_reply` returns the native code and number of sleeps. It takes
an existing `ChannelReplyMailbox`, plus injected boundaries for reproducible
comparison. Calls must have one owner. Overlapping requests, callbacks that raise
exceptions, synchronization and connection retirement require orchestration
outside this function. A disconnected slot must not be reused by a later listener
without explicit connection cleanup. Neither this function nor the original
comparison proves that complete room entry works.

## Units

Sleep helper `0x7e3e50` converts its unsigned input using integer division by 1000
and calls Windows `Sleep` with the result. The wait helper supplies 250000, giving
250 milliseconds. Timeout follows 81 sleeps, a nominal 20.25 seconds; actual
elapsed time includes scheduling and callback/lookup work. This is a wait-loop
rate, unrelated to vehicle simulation or network position-update rates.

The conversion oracle checks 12 values, including zero, the 1000 boundary, the
wait input and signed/unsigned 32-bit limits. It executes original arithmetic
while replacing only the Windows Sleep import with argument capture and return;
no host sleeping or networking occurs.

```powershell
python -m tools.lobby_sleep_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

Local Windows result: all 12 conversions match unsigned integer division. Seven
portable tests exercise ordering, boundary replies, cancellation, disconnects,
null completions and cleanup. The [wait-loop original comparisons](lobby-channel-wait-evidence.md)
record their separate substituted boundaries and coverage.

## Evidence

The C++20 port in `native/include/mco/lobby_channel_wait.hpp` belongs to
`mco_core`. It uses an opaque reply token and explicit host boundaries; it never
dereferences original pointers. Required sleep/lookup boundaries are validated
before changing the slot. This boundary validation and callback exception
propagation are authored safeguards, not recovered original error codes.

```powershell
python -m tools.native_lobby_channel_wait_compare build/native-check/mco_lobby_channel_wait_compare.exe
```

Local Windows CMake verification matches 428 Python/native scenarios and rejects
six malformed runner inputs. Comparison covers complete event order, return
code, poll count and final slot state. All 20 native checks and 532 Python tests
pass. CI includes the comparison on Windows and Linux; local results do not
establish a Linux run or successful live join.

Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Ghidra 12.1.4 wait helper dossier:
`ev_7f5a0622b416f8eba8c5c80cdb862a562339106d5ac2b0c766483a7e15c97c1c`.
Sleep conversion dossier:
`ev_067558dd64e17e839b9e39c4422105f92b550dbe00ffe6d43bec95ac7d2e8bc8`.
Published source and prose are authored reconstructions; original instruction
bytes, pseudocode, credentials and captures remain external.
