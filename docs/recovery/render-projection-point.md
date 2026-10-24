# Track projection point fallback

When projection context word `+0x0c` is zero, `0x42dc50` uses the track index
in context word `+0` to copy the selected `0x54`-byte track row's first three
float32 values to its output vector. `track_point_without_cached_geometry`
implements that branch; 512 direct calls against the installed executable
match all three output words across varied track records and row selections.

Contexts with cached geometry use a separate polygon/normal calculation and
remain outside this translation.
