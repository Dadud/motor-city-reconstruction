# Installation support helpers

Recovered complete bodies `0x533f60` (drive classification), `0x530a90` (path-slot word address) and `0x5354d0` (installation mode-word accessor). Target mcity.exe SHA-256 and primary instruction/literal Evidence IDs are pinned in the cell manifest. Ghidra 12.1.4; instruction profile `3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`.

Drive classification masks the input to its low byte, adds ASCII A, formats a narrow character plus colon/backslash, and compares the API result exactly with5. It does not restrict the index to0..25. Formatting truncates the character to one byte, including embedded NUL and wrapped nonalphabetic values. The oracle executes the real original sprintf child; GetDriveType alone is synthetic. Cases compare all four output bytes, rather than inferring the string from an intended drive letter.

Path addressing uses unsigned32-bit wrap for `0xa52d48 + index*260`. The returned word is an original address identity; the function does not dereference it or validate an index. The mode accessor preserves all32 bits, including high bits and non-Boolean values.

5,120 synthetic original-instruction cases cover all256 low drive bytes and256 further full-word indices crossed with eight API responses, plus512 path-address and512 mode-word cases. Domain checks reject a missing required API bridge and verify wrapped addressing/full-word flags. These checks do not establish actual drives or complete game startup.
