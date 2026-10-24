# Track-row camera state

Routine `0x42f0c0` populates the active camera state from one `0x54`-byte track
row. It stores the track index and its eight-row group, copies the row's
position and orientation values, and sets the unit scale. Mode 1 advances along
the row normal by `(row[13] - 0.5)`; mode 0 retreats by `(row[12] - 0.5)`; other
modes preserve the row position after the supplied vertical offset. The routine
also sets the camera-state dirty flag.

`build_track_camera_state` translates those writes when the optional matrix
normalization argument is zero. The 512-case direct comparison covers all
three movement modes, varied row fields and vertical offsets, exact index and
untouched-byte behavior, and scale-aware float outputs. The nonzero
normalization path through `0x6f1850`, active camera scheduling, and renderer
integration remain outside this bounded scope.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
