# Shared-state wheel load sequence

`tools/wheel_load_pipeline_oracle.py` checks the recovered load helpers in order
on one original owner/configuration memory image:

```text
0x53d920 initial normal loads
    → 0x53e680 acceleration-driven transfer
    → 0x53e980 attitude/torque correction
```

The Python chain passes each stage's computed loads into the next through typed
inputs. The original execution retains the owner image between calls. Every
stage compares all four loads, the other force components and all remaining
owner/configuration bytes, rather than checking only the final output.

```powershell
python -m tools.wheel_load_pipeline_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
```

On Windows, 1,728 shared-state scenarios and 5,184 stage comparisons match with
zero maximum stored-load difference. The synthetic matrix covers all support
masks, attitude gates, bank signs, the speed-6 boundary and opposing longitudinal
and lateral accelerations. The original trigonometric helpers run unchanged;
no callable boundaries are substituted. Inputs require the documented source
SHA-256 and executable remains external/read-only.

This comparison excludes the original caller and the intervening motion,
surface, engine and other driving helpers. It does not establish that every
supplied combination is reached in a real driving tick. The bounded function-call
CPU context, including x87 state, is reset between stages; the owner and component
images are retained. It therefore verifies the specified memory handoff and
calculation composition, not complete caller precision or scheduling.

The original caller's branch gates, intermediate state producers and complete
force update must still be recovered. In particular, this tool is not a new
simulation loop that should be applied unconditionally to airborne cars.
See [initial loads](calculations/normal-load.md),
[load transfer](calculations/load-transfer.md),
[suspension correction](calculations/suspension-load-correction.md) and the
[driving recovery map](driving-recovery-map.md).
