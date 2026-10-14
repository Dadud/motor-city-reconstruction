# Online race synchronization settings

The installed fan-server patch exposes transport and update-rate preferences in
`scripts/MCOExOps.ini`. The reconstruction reads these values as declared
configuration, not as proof of live multiplayer behavior.

| Setting | Observed meaning |
| --- | --- |
| `Fast Join = 1` | Prefer opening the game-server channel on TCP instead of UDP |
| `Positional Updates = 2` | Declared 32 Hz position update rate |

`client/online_sync.py` converts the declared rate into an update interval in
seconds. `client/race_entry.py` includes that interval in the fan-server race
entry probe so live testers can confirm the installed patch matches the
recovered expectations.

Live room negotiation, peer state exchange, corrections and finish reporting
remain unfinished.

