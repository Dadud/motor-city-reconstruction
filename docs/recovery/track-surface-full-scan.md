# Track surface all-row nearest sample

`0x42d530` scans every track row in order and returns the index with the
smallest squared XZ distance to the query. It updates only on a strict
improvement, so the first row wins ties.

`nearest_track_point` translates the full bounded scan and float32 distance
arithmetic. Five hundred twelve direct calls against `mcity.exe` match the
returned index across track sizes and query positions.
