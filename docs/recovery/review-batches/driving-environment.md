# Controls and force-consumer audit

Seven additive existing-source dispositions were reviewed on 2026-10-15,
identified by main-executable hash and address in the accompanying JSON. These
are reconciled implementations, not newly translated functions or seven new
integrated driving features. None overlaps the 43 legacy reviews or the separate
engine-dispatch batch.

| Original body | Original module | Cases | Maximum numeric error |
|---|---|---:|---:|
| `0x540fd0` controls | `tools.control_update_oracle` | 844 | 0 |
| `0x536250`, rear selector `0x536f80` | `tools.body_vertical_load_oracle` | 486 combined | 0 |
| `0x540520` force orientation | `tools.wheel_force_orientation_oracle` | 243 | 0 |
| `0x540710` moments | `tools.body_moments_oracle` | 1,440 | 1.1920928955078125e-7 |
| `0x53f630`, `0x53f830` response curves | `tools.tire_response_oracle` | 1,728 combined | 0 |

Every listed original command was freshly run as:

```powershell
.venv/Scripts/python.exe -m tools.control_update_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Substitute each table module for `tools.control_update_oracle`; the same sole
executable argument applies. The exact verified original bytes load into bounded
CPU emulation. No host game entry point, imports or network services execute.

The matching native/Python commands were freshly run against existing MSVC
runners, all passing the same respective case counts with zero numeric error:

```powershell
.venv/Scripts/python.exe -m tools.native_control_update_compare build/msvc-check/mco_control_update_compare.exe
.venv/Scripts/python.exe -m tools.native_body_vertical_load_compare build/msvc-check/mco_body_vertical_load_compare.exe
.venv/Scripts/python.exe -m tools.native_body_moments_compare build/msvc-check/mco_wheel_force_orientation_compare.exe --kind orientation
.venv/Scripts/python.exe -m tools.native_body_moments_compare build/msvc-check/mco_body_moments_compare.exe
.venv/Scripts/python.exe -m tools.native_tire_response_compare build/msvc-check/mco_tire_response_compare.exe
```

This audit did not rebuild the runners or execute Linux. Full integration must
rebuild the current tree and retain cross-platform CI.

## Coverage and limits

Controls retain the original rate, steering, clamping and override helpers.
Remote/gear effects, external queries and trace delivery are explicit supplied
operations. Original child-entry snapshots check preceding owner writes before
supplied mutations; final owner/configuration bytes and call order are also
checked. Authentic input acquisition, gear state machines and query producers
remain open.

Vertical-load and moment tests substitute no children. The original moment test
retains cross products and the actual support-correction helper. The rear
selector is folded into the authored vertical-load routine; its acceptance is
observed through complete parent calls, not an exhaustive standalone test of
the unstored x87 return. Orientation runs actual original trigonometric helpers.
These tests supply upstream forces, geometry, qualities and support values;
they do not establish those producers or full vehicle integration.

Response curves run both complete original bodies and their original floor
helper with synthetic 26-knot tables. Only stored outputs are compared; original
table construction, malformed-pointer behavior and whole-tire state changes are
not certified. The two functions share the combined case count; it must not be
counted twice. Table/sign/load/alternate-mode boundaries are exercised.

Owner/configuration remainder checks exist for controls, vertical loads and
moments; orientation checks remaining owner bytes. The tire oracle compares
response values rather than asserting complete wheel/table memory immutability.
Numeric tolerances are coded in each oracle, generally
`max(0.00025, abs(original)*3e-7)` for forces. Zero numeric error is not a blanket
bitwise guarantee. The nonzero moment discrepancy remains visible and prevents
a bit-exact claim.

## Evidence provenance and next gate

The JSON lists retained REA Evidence IDs. Control, orientation and moment records
contain matching target digests. Both tire records were located in the private
saved snapshot and their exact procedure and target hash checked. The two aero
records are reduced Evidence-ID/pseudocode extracts without subject metadata;
their target binding is instead corroborated here by the current hash-checked
original execution and address-scoped export. No stronger digest validation of
those reduced records is claimed. Private pseudocode and captures stay outside
the public batch.

Complete initialized-car parameter production, steering/gear/input producers,
slip/contact/grip/response-table production, scheduler and downstream linear/
angular integration remain required. Field names and physical units remain
explicitly unresolved where documented. Original malformed/nonfinite behavior
is excluded; the authored interfaces reject such inputs. The next acceptance
gate is to feed these consumers from authentic recovered producers and compare
carried driving state against original-client traces.
