# Environment renderer activity state

`0x478950` reads two global scene-object pointers. If the first pointer is
nonzero, it writes `1` to the object's word at `+0x3c`; if the second is
nonzero, it writes `0` at `+0x3c`. Null pointers are skipped independently.

`client/render_environment.py::set_environment_activity` returns this pair of
optional writes. Four direct executions against the installed `mcity.exe`
cover both pointers null, either pointer null, and both non-null. Pointer
selection and the wider environment setup remain caller behavior.

`0x478980` releases the four optional objects held in globals `0x993c34`,
`0x993c38`, `0x993c3c`, and `0x993c40`, in that order, then clears each
non-null global. `client.render_environment.py::release_environment_objects`
captures the ordered release list and final zeroed globals. Sixteen direct
calls against the original executable cover every null/non-null pointer mask.
The native harness replaces only the downstream heap-release wrapper, so this
comparison verifies the cleanup routine while leaving allocator internals
outside the translation.
