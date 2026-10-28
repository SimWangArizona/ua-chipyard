#ifndef FG_HW_H
#define FG_HW_H
#include "fg_contract.h"
#if !defined(__riscv) || __riscv_xlen != 64
#error "Hardware wrappers require RV64; no software fallback is permitted."
#endif
#define FG_RAW(name, fn) \
static inline uint64_t name(uint64_t ac, uint64_t b) { \
    uint64_t out; \
    __asm__ volatile(FG_INSN(fn, "%0", "%1", "%2") \
                     : "=r"(out) : "r"(ac), "r"(b)); \
    return out; \
}
FG_RAW(fg_dot_raw, FG_DOT_FUNCT7)
FG_RAW(fg_max_raw, FG_MAX_FUNCT7)
FG_RAW(fg_min_raw, FG_MIN_FUNCT7)
#undef FG_RAW
static inline uint32_t dot4_acc_hw(uint32_t a, uint32_t b, uint32_t c)
{ return (uint32_t)fg_dot_raw(fg_pack_ac(a, c), b); }
static inline uint32_t add_max_hw(uint32_t a, uint32_t b, uint32_t c)
{ return (uint32_t)fg_max_raw(fg_pack_ac(a, c), b); }
static inline uint32_t add_min_hw(uint32_t a, uint32_t b, uint32_t c)
{ return (uint32_t)fg_min_raw(fg_pack_ac(a, c), b); }
#endif
