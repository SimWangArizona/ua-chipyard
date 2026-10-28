# Native Arithmetic Contract v1 (Candidate)

Status: S4 ADD_MAX/ADD_MIN and S5 DOT4_ACC arithmetic/dependency hardware tests passed independently; S6 focused combined-core arithmetic and cross-family dependency tests also passed. The optional large full suite remains uncompleted after timeout. Team alignment remains pending. The PDF does not fix the following encoding/overflow choices.

S7 feature-gate/precise-trap matrix, selected ordinary ISA regressions and
fresh-output reproduction also passed. These are functional checks, not a
physical-timing or performance result.

| Property | Definition |
| --- | --- |
| Architecture | RV64 Rocket, integer register operands |
| Source 1 | `rs1[31:0]=a`, `rs1[63:32]=c` |
| Source 2 | `rs2[31:0]=b`; bits 63:32 ignored |
| Dot operands | Four signed INT8 lanes in each of `a`/`b`; lane 0 is bits 7:0 |
| DP operands and accumulator | Signed 32-bit values represented in software by `uint32_t` bit patterns |
| DOT4_ACC | Low 32 bits of `signed(c) + sum(signed8(a_i)*signed8(b_i))` |
| ADD_MAX | Signed maximum of the wrapped 32-bit `a+b` and `c` |
| ADD_MIN | Signed minimum of the wrapped 32-bit `a+b` and `c` |
| Result | Sign-extend result32 to all 64 bits of `rd`; discard writes to x0 |
| Arithmetic | Two's-complement wraparound; no saturation or flags |
| Memory/state | No memory access or persistent accumulator state |
| Exceptions | Disabled/unallocated instruction traps as illegal; S7 verifies exact PC/word, cause 2, preserved destination and controlled continuation |

| Operation | Opcode | funct3 | funct7 | Candidate internal ALU control |
| --- | --- | --- | --- | --- |
| DOT4_ACC | 0x0b | 0 | 1 | 21 |
| ADD_MAX | 0x0b | 0 | 2 | 22 |
| ADD_MIN | 0x0b | 0 | 3 | 23 |

ALU control codes are internal implementation choices, not instruction bits. Codes 21–23 are unused in inspected Rocket revision `55bcad0f59436de98ea510334121de8546b9e9d7`; inspect their interaction with shared ALU logic when implementing them. Code 20 remains available for the course clamp8 example. The inspected tree had no clamp8 patch applied.

Native patterns have distinct funct7 values and avoid CLAMP8's funct7=0 encoding. They still overlap generic RoCC custom-0 decode: native and RoCC configurations must be separate initially. Native funct3=0 is a private encoding choice, not the RoCC operand-use flags.

`include/fg_encoding.h` is the encoding constant source shared by assembly and C/C++, included by `fg_contract.h` with packing/sign helpers. `fg_hw.h` exposes raw 64-bit results for writeback tests and 32-bit bit-pattern wrappers for C/C++ callers. Hardware must match this contract; revise the version and affected tests together if the team selects different semantics.

## Change history

- 2026-10-14: Created candidate v1 and executable software/encoding gates. No hardware latency or clock frequency has been validated.
- 2026-10-14: Implemented ADD_MAX/ADD_MIN in Rocket ALU with codes 22/23, two-source integer decode, and the `useFineGrainedDP` gate. No contract bits changed. Physical timing remains unmeasured.
- 2026-10-14: DOT4_ACC with code 21 and independent `useFineGrainedDot` gate passed S5 arithmetic/dependency tests; rebuilt DP-only core passed S4 regression. Arithmetic/encoding contract unchanged; physical timing remains unmeasured.
