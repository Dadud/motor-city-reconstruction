# Mouse input recovery

Four native routines now preserve the original mouse/cursor path on bounded, explicit state views:

| Original | Native | Original cases matched by MSVC and Zig |
| --- | --- | ---: |
| `0x582fe0` | `input_cursor_warp` | 336 |
| `0x6f08d0` | `input_mouse_update` | 336 |
| `0x584670` | `input_mouse_press` | 594 |
| `0x5846d0` | `input_mouse_motion` | 594 |

The registered mouse image starts at original `0xb36574`: maximum X/Y, minimum Y/X, buttons, cached Y/X. The separate mouse enable flag and button callback identity are explicit fields. The window/global image is shared with the recovered dispatcher; mouse updates use its dispatch synchronizer and target window.

Coordinates are clamped with signed integer comparisons before entering synchronization. Reversed bounds preserve the original outcome instead of relying on a standard clamp with incompatible preconditions. The update stores supplied buttons, warps if clamped coordinates differ, updates cached coordinates, leaves synchronization using the reloaded identity, and only then reloads and invokes a nonzero notification identity when requested. Disabling the mouse during enter does not invent a new mid-call guard. Notifications receive the original supplied buttons, even if a callback changed the stored button field.

Cursor warping calls the explicit ClientToScreen bridge with a mutable local point. Success uses the converted point; failure uses the original coordinates even when the bridge modified its point. SetCursorPos return status is ignored and SetCursor(0) follows it. Native APIs expose these operations through callbacks rather than performing host OS calls during comparisons.

Mouse message handlers accept enabled, matching-window messages, map flag bits 1/2/16 to button bits 1/2/4, and zero-extend both packed 16-bit coordinates. Press/double-click notifications request button callbacks; motion/release handling does not. Both handlers return zero. The actual recovered update and warp routines execute beneath these handlers.

Original comparisons substitute only lock imports, ClientToScreen, SetCursorPos, SetCursor, and declared notification callbacks. All four original bodies and their substantive children run unchanged. Callback scripts mutate bounds, enabled state, window/synchronizer/callback identities, cached coordinates and button state at specific observation points. Complete window/mouse images and callback arguments/order are compared. Native tests additionally pin failed-conversion fallback, coordinate calculation before enter, callback reload after leave, unsigned packed coordinates, button mapping, and wrong-window/disabled guards.

The retained corpus now contains 85 cells and 40,991 routine cases, plus 44 connected traces. Checkpoint verification on 2026-10-18 passes 166 MSVC tests, 168 Zig tests and 989 Python tests (seven skipped). Both aggregate comparisons pass all 85 cells, 40,991 routine cases and 44 connected traces, including fresh hash-checked original execution under MSVC. Queue consumption, actual host cursor/locking behavior, and remaining registered handlers remain unfinished. These bounded results do not establish live Windows integration or whole-game completion.

## Initialized dispatch integration

Four additional 19-operation traces now match original observations under both compilers. They use actual initialization, registration, search/sort, general/Windows dispatch, mouse messages, state update and cursor warp. The production `window_mouse_binding.hpp` connects recovered mouse identities to their implementations and rejects other identities. Traces cover repeated initialization, presses/motion/releases/double-clicks, nested locks, conversion success/failure, callback mutation during leave, disabled dispatch, and default fallback. Shared state and callback arguments are compared after every operation. Synchronizer allocation/locks, cursor imports, notification callbacks and default procedure remain declared substitutions. The refreshed inventory records 149 explicitly reviewed main-executable entries. These counts do not measure whole-game completion.
