# Vehicle predicate used by tire response

The helper at `0x55cfc0` supplies a boolean observation to the wheel-response
routine. It does not directly inspect wheel fields or owner flags. The authored
`client/vehicle_gate.py` reconstructs its comparison from explicit observations;
the virtual-interface operation remains external.

Target: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Bounded local instruction inspection covered the complete entry-to-return range
`0x55cfc0`–`0x55cfe9` using Capstone 5.0.7 and the read-only oracle image. No
original instructions or decompiler text are distributed in this document.

## Observed behavior

A null owner returns false without consulting the interface. With a non-null
owner, the helper calls the interface referenced by global `0xa65bd0`, virtual
slot `+0x10`, passing operation number 5 and the owner. It compares that returned
signed 32-bit integer to global counter `0xaa456c`:

```text
result = current_counter >= interface_operation_5_result
```

Equality returns true. Signed comparison is material: counter −1 versus result
0 returns false, whereas counter 0 versus result −1 returns true. The boolean
return is the low byte of the return register; unused upper bits are not part of
the recovered API.

The helper itself makes no owner-state or counter writes. The called virtual
operation may have behavior beyond its returned value, and its implementation
has not been recovered here. The terms `counter` and `interface_result` remain
neutral; this evidence alone does not establish elapsed-time units or a deadline.

## Four calls are four observations

The tire-response caller invokes this helper per wheel. Each call reads the
interface and current counter again. It is unsafe to collapse the four calls
into one constant observation until the virtual operation and scheduler prove
that their state cannot change across that sequence. A reconstructed driver
should preserve four observations or recover and verify the actual producer.

## Verification and limits

```powershell
python -m tools.vehicle_gate_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m unittest tests.test_vehicle_gate -v
```

The complete-function oracle covers 50 scenarios: null/non-null owners crossed
with signed minimum, −1, zero, one and signed maximum for both observations.
It substitutes only the virtual operation, verifies its receiver and arguments,
checks exact boolean returns and call counts, and checks the full owner image
and counter remain unchanged. The null branch uses a deliberately null interface
pointer to confirm it performs no interface dereference. Four authored tests
cover signed ordering, equality, repeated differing observations and validation.

The virtual operation's producer, any side effects, counter update scheduling,
and integrated live-driving behavior remain unresolved.
