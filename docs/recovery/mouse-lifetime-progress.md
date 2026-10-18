# Mouse startup and lifetime recovery

The complete mouse initializer `0x6ef890`, resource cleanup `0x6efa90` and bounds setter `0x6effd0` have native implementations. Initialization executes the recovered cleanup on setup failure and the recovered bounds setter before access-mode selection. State setting, wheel callback registration, cleanup callback registration, low-level bounds propagation and Windows/COM calls remain explicit returning bridges. This is not live DirectInput or full startup linkage.

## Static evidence

REA 6.7.0 with Ghidra 12.1.4 supplies these observations for target SHA-256 `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`, analysis profile `3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`:

| Routine | Complete inclusive body | Bytes | Evidence |
| --- | --- | ---: | --- |
| Initialize | `0x6ef890..0x6efa5a` | 459 | `ev_166fbd665212c9f5878eae71fa53c8f2fda09d61223542775a15aa3d2bb64585` |
| Cleanup | `0x6efa90..0x6efacd` | 62 | `ev_cf05ac0cb8f23a3edb91ab8b258b793570739b555e28634afcf09d8a31b8a80e` |
| Bounds setter | `0x6effd0..0x6f001b` | 76 | `ev_6517bc705b520094112198cf4efea5face87ac45cd9f86485e4d50fe3cc6a002` |

Each observed body has one range. Complete original records and snapshots remain private in `evidence/rea-mouse-lifetime-6.7.bundle.json` and `evidence/rea-mouse-lifetime-6.7.snapshot.json`. Pseudocode alone misidentifies the post-query release expression; assembly at `0x6ef919..0x6ef920` reloads and releases the temporary stack identity. Cleanup reloads the device after unacquire, reloads its current virtual table, clears its global after release, then reloads and releases the interface. Handles changed by returning calls therefore affect later calls. The initialization flag and cleanup-registration flag are not cleared by this resource cleanup.

`InputMouseLifetimeState.words` observes fifteen consecutive words at `0xb361fc..0xb36234`; it is not an inferred C++ class. Indices zero through fourteen correspond to timeout, width, height, opaque mode/status, X, Y, opaque word, four packed bytes, left, top, opaque word, interface identity, device identity, initialization flag and cleanup-registration flag. Width/height references additionally observe `0x8c4618/1c`. Names other than established call roles are provisional. The 28-byte mouse-message region at `0xb36574` remains distinct; bounds helper `0x6f0720` is the unresolved connection to that region and recovered mouse update.

One-time setup sets the initialization flag before calling `0x6f06c0` and registering message `0x20a` with callback identity `0x6efa60`. An absent interface triggers module lookup, DirectInput version `0x500`, device GUID `0x84c950`, interface GUID `0x84ca70`, data-format identity `0x84b720` and property two with words `[20,16,0,0,1]`. The temporary interface is released even when querying the requested interface fails. Every setup failure reaches resource cleanup.

After setup, initialization resets five observation words, requests state `(8,2)` and `(9,1)`, forwards current dimensions with timeout 1200, then requests state `(7,4)` only if the interface is still present. Cleanup registration uses identity `0x6efad0` and stores its flag after the call. GetCursorPos's status is ignored; ScreenToClient's status controls coordinate state calls `(3,x)` and `(4,y)`. The initialization flag is reloaded for the return value. These are static control-flow observations, not observed host API calls.

## Verification and gaps

1,400 complete original-instruction cases match MSVC and Zig: 1,280 initializer calls, 40 cleanup calls and 80 bounds-setter calls. Cases include existing interface/device/flag combinations, each setup failure stage, conversion failure, a failed cursor query that still defines both words, temporary identity changes during querying, changed virtual tables, handle mutations during cleanup, dimension changes during state calls and flag mutations during cleanup registration. Bounds calls cover signed extremes and rounding-boundary integer words without interpreting them as floats. Independent native checks verify the descriptor, temporary release, cleanup reload order, resource clearing, registration timing and failed-conversion skip.

Unicorn runs hash-checked original instructions under synthetic returning helper and import bridges. No host Windows input is sent. The supported cursor bridge always writes both POINT words, including failed queries; original behavior with unwritten stack bytes remains unknown. COM output identities are supplied as valid mapped handles in these fixtures. Invalid/null vtables, exceptions, asynchronous activity and actual Windows adapters are outside coverage. The void cleanup and bounds routines have no authored incidental-register return contract. Startup still substitutes this initializer in its existing full-controller traces; state setter `0x6efaf0`, wheel handling, registered shutdown callback and complete platform linkage remain unfinished.

The retained checkpoint now contains 100 implemented cells, 62,376 routine cases and 88 connected traces. Full retained-corpus replays pass on MSVC and Zig. Both new native self-tests and 26 targeted inventory/triage/corpus/layout tests pass. The three new roots bring explicitly reviewed entries to 182. These counts do not establish whole-game completion or live input acceptance.
