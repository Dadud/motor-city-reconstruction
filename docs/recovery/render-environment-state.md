# Environment renderer activity state

`0x478950` reads two global scene-object pointers. If the first pointer is
nonzero, it writes `1` to the object's word at `+0x3c`; if the second is
nonzero, it writes `0` at `+0x3c`. Null pointers are skipped independently.

`client/render_environment.py::set_environment_activity` returns this pair of
optional writes. Four direct executions against the installed `mcity.exe`
cover both pointers null, either pointer null, and both non-null. Pointer
selection and the wider environment setup remain caller behavior.
