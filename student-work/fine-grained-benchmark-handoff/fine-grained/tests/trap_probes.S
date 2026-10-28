#include "fg_encoding.h"
    .section .text
    .option push
    .option norvc
    .macro PROBE name, fn, f3
    .balign 4
    .global fg_probe_\name
    .type fg_probe_\name, @function
fg_probe_\name:
    li t0, 123
    .global fg_pc_\name
fg_pc_\name:
    .insn r FG_OPCODE, \f3, \fn, t0, a0, a1
    mv a0, t0
    ret
    .size fg_probe_\name, .-fg_probe_\name
    .endm
    PROBE dot, FG_DOT_FUNCT7, FG_FUNCT3
    PROBE max, FG_MAX_FUNCT7, FG_FUNCT3
    PROBE min, FG_MIN_FUNCT7, FG_FUNCT3
    PROBE reserved, 127, FG_FUNCT3
    PROBE bad_f3, FG_DOT_FUNCT7, 1
    .option pop
