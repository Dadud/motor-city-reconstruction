# Track surface neighbor selection

`0x42d3e0` compares a track sample with the points four slots forward and
backward, wrapping at the track count, and returns the nearest XZ candidate.
Strict comparison keeps the original sample on a forward tie; the final
comparison keeps the current winner on a backward tie.

`nearest_track_neighbor` translates this selection and its float32 squared
distance behavior. Five hundred twelve direct calls against `mcity.exe` match
the returned index across varied track sizes, sample positions, and query
points. Invalid indices and undersized tracks are outside the modeled domain.
