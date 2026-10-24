# Track surface four-point scan

`0x42d4b0` checks track rows 0, 4, 8, and so on, selecting the row with the
smallest squared XZ distance to the query. Its strict comparison preserves
the first row on ties.

`nearest_track_quarter_point` translates that scan and its float32 distance
rounding. Five hundred twelve direct calls against `mcity.exe` match the
returned track index across varied row counts and queries.
