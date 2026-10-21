# World-collision dispatcher `0x45abe0`

The Python implementation in `client/collision_dispatch.py` translates the
observed order of the original world's per-object collision callback. The
dispatcher clears the 60-byte contact record, invokes the contact-field
initializer, decrements the positive collision countdown, and returns early for
inactive owners. Active owners then follow the support counter and high-speed
correction branches, inactive-object update, collision eligibility gate,
ordered candidate AABB checks, repeated pair filter (at most 33 calls),
fallback-direction normalization and pair response, global candidate-count
publication, contact follow-ups, and final active-object updates.

The implementation takes mutable owner images and prior candidate images in
their observed order. It rounds the radii sum and normalized fallback vector to
binary32 and keeps the source's signed counter and strict distance comparisons.
All child behavior is an explicit required callback. In particular, this file
does not claim to implement terrain triangle selection, pair filtering,
pair-response geometry, shared impact-record mutation, contact correction,
or final object maintenance. The mode-record array and contact-neighbor rows are
explicit caller inputs because their global producers and lifetimes are not
recovered here.

The unit tests cover inactive reset/countdown behavior, ordered rejection and
acceptance, the 33-attempt limit, fallback normalization, and contact-neighbor
range filtering:

```powershell
python -m unittest tests.test_collision_dispatch -v
```

This is a source translation guided by static shipped-binary Evidence, not a
direct original-execution comparison. Until that comparison and the downstream
children are connected, original collision behavior remains partial and the
playable client must not treat this dispatcher as an accepted collision solver.

Target: `mcity.exe`, x86, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Current static dossier: `ev_a3e8c8ca580cb74b356cf4e6e8f29b089af96dc4324d4fa58da73616eac52e99`.
The observed function body is the inclusive range `0x45abe0..0x45af23`
(836 bytes); pseudocode remains provider-generated evidence, not original
source.
