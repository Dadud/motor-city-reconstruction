# Signed 16.16 ratio

Routine `0x6f2c50` converts a signed int32 numerator/denominator ratio to a
signed 16.16 fixed-point result. It divides the integer quotient and the
remainder-scaled fractional part separately, then wraps the combined result to
32 bits. This matches the client's truncation-toward-zero division semantics
without forming a potentially overflowing `numerator * 65536` intermediate.

`signed_ratio_16_16` reproduces the supported signed arithmetic and int32 wrap.
512 direct original calls compare the returned EAX word exactly, including
negative operands, negative divisors, fractional ratios, and large values.
Denominator zero and `INT_MIN / -1` raise native divide faults and are outside
the normal-return domain.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
