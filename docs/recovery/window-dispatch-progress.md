# Window input recovery checkpoint

The recovered native path now connects input initialization, handler registration, message dispatch, actual key-down/release handling, and free-camera updates. This is verified against bounded CPU-only original execution. Live Windows behavior and a fully linked game client remain unverified.

| Original entry | Native implementation | Verified routine cases |
| --- | --- | ---: |
| `0x583210` | `window_message_dispatch` | 1,653 |
| `0x583290` | `window_procedure` | 2,381 |
| `0x582e40` | `window_handler_register` | 813 |
| `0x583c30` | `window_input_initialize` | 75 |

## Preserved behavior

The routines share the queue/global observation image. The table starts at offset `0x28`, contains at most 128 eight-byte records, and uses count `0x4f4`, initialization flag `0x51c`, and dispatch synchronizer `0x524`. The queue synchronizer at `0x520` is distinct. Handler/lock/result identities are explicit values passed to bridges; original addresses are never dereferenced as host pointers.

Dispatch tests enable state, enters synchronization, reloads the table count, searches, invokes the selected handler with six original arguments, reloads the synchronizer for leave, and returns the handler flag. Disabling during enter does not cancel the current dispatch. The original owner identity `0xacada0` and caller result identity are forwarded unchanged.

The Windows procedure initializes its local result to zero and passes a writable reference to its handler bridge. After leave, a nonzero handled flag returns that local value; otherwise the explicit default-procedure bridge runs. Disabled dispatch goes directly to default handling. The handler flag is never substituted for the local result.

Search preserves the lower midpoint and wrapping signed-subtraction comparator. Registration preserves original insertion/replacement/removal and specialized CRT sorting, including pivot choice, small-range maximum selection, swaps and sentinel removal. Missing zero handlers are no-ops; full tables reject insertions but permit replacements. Creating a synchronizer that returns zero does not invent an early failure return.

Initialization creates the queue synchronizer, resets capacity to 32 and cursors to zero, installs the original 28 message/handler pairs in order, and sets the initialization flag. Nonzero initial flags return zero without touching state. Registration failures are ignored, as in the original. Installing handler identities does not establish recovery of all 28 callback bodies.

## Connected verification

Four additional traces each execute 37 operations through general dispatch or the Windows procedure. They cover initialization/reinitialization, ordinary/system key messages, scan remapping, raw/translated queue modes, both shifts, disabled dispatch, unknown-message fallback, nested locks, camera rotation/movement, modifiers, reset hold/repress, and resizing. Shared state and new lock/default observations are compared after every operation.

The oracle runs actual original initialization, registration, search, sort, dispatch, key handlers, camera, math, and spatial children. Only synchronizer creation, lock operations, and DefWindowProcA are substituted in the connected traces. Standalone dispatcher/procedure cases additionally substitute declared synthetic handler bodies to exercise return/result/mutation behavior. Local result contents are observed without pretending a host stack address equals the original emulated address.

`native/include/mco/window_keyboard_binding.hpp` supplies the production binding for recovered key-down/release/character identities. Other handler identities throw rather than being silently treated as handled. The lifecycle runner uses that binding and shared queue/dispatch memory.

## Verification status

The retained corpus contains 85 cells, 40,991 routine cases and 44 connected traces. MSVC and Zig pass all added routine and connected comparisons. Full native suites pass 166 MSVC tests and 168 Zig tests. Python discovery passes 989 tests with seven skips. Fresh hash-checked original execution passes the complete MSVC aggregate. The inventory records 149 explicitly reviewed main-executable entries; these counts are not a whole-game completion percentage.

The oracle call budget remains 4096 instructions by default. Sorting/initialization explicitly request a bounded limit up to one million; invalid limits are rejected. Tests also pin callee cleanup to prevent double argument removal for registration's RET 8 ABI.

## Remaining integration

Actual synchronizer allocation/operations, live window creation/message pumping, platform adapters, other registered handlers, and camera-controller/frame ownership remain unfinished. Invalid original pointer/function-pointer faults, arbitrary aliasing, and platform exception behavior are outside the bounded contracts. Original assets, linked-client startup, and full documented gameplay acceptance remain required by `plan.md`.

## Character messages

Character handler `0x584370` now queues repeated low-16-bit character values with the original scan/extended bits, capacity clamping, overwrite-oldest rule, synchronization and store order. It does not update raw keys, remap scan codes, or alter the last raw key code. Its 822 original observations match MSVC and Zig, including lock mutations, zero/full capacities, disabled/wrong-window guards, maximum characters, and event aliases to capacity/cursor/head fields. The common append helper retains the different late-flag order required by translated key-down events; all 816 prior key-down observations still match both compilers.

The production keyboard binding now also routes the registered character callback. The four initialized-dispatch traces append two character operations each, retaining all prior operations; 37 operations per trace match both compilers. Targeted native checks pass for character packing, repeat bounds, unchanged raw/remap state, disabled guarding, key-down behavior, and the extended connected traces. Full checkpoint-wide native, Python and aggregate comparisons now pass for this addition. Mouse state/update handlers and initialized mouse routing are now recovered; queue consumption remains unfinished.
