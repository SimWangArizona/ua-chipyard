#ifndef FG_ENCODING_H
#define FG_ENCODING_H
/* Pure preprocessor constants shared by C/C++ and assembly probes. */
#define FG_OPCODE 0x0b
#define FG_FUNCT3 0
#define FG_DOT_FUNCT7 1
#define FG_MAX_FUNCT7 2
#define FG_MIN_FUNCT7 3
#define FG_STR_INNER(x) #x
#define FG_STR(x) FG_STR_INNER(x)
#define FG_INSN(f, rd, r1, r2) \
    ".insn r " FG_STR(FG_OPCODE) ", " FG_STR(FG_FUNCT3) ", " FG_STR(f) ", " rd ", " r1 ", " r2 "\n\t"
#endif
