#ifndef ECE562_DOT_ROCC_H
#define ECE562_DOT_ROCC_H
#include <stdint.h>

/* custom0 = 0x0b; funct3 bits are xd:xs1:xs2, NOT the ALU operation.
 * Model builds test the software adapter only, never hardware performance. */
#ifdef ECE562_ROCC_MODEL
static uint32_t ece562_dot_accumulator;
static inline int32_t ece562_dot_model(uint64_t a, uint64_t b, unsigned lanes)
{
    int32_t sum = 0;
    for (unsigned i = 0; i < lanes; ++i) {
        int32_t ai = (int32_t)((a >> (8*i)) & 255);
        int32_t bi = (int32_t)((b >> (8*i)) & 255);
        if (ai >= 128) ai -= 256;
        if (bi >= 128) bi -= 256;
        sum += ai * bi;
    }
    return sum;
}
static inline int32_t ece562_dot4(uint64_t a, uint64_t b)
{ return ece562_dot_model(a,b,4); }
static inline int32_t ece562_dot8(uint64_t a, uint64_t b)
{ return ece562_dot_model(a,b,8); }
static inline void ece562_dot_clear(void) { ece562_dot_accumulator = 0; }
static inline void ece562_mac4(uint64_t a, uint64_t b)
{ ece562_dot_accumulator += (uint32_t)ece562_dot4(a,b); }
static inline void ece562_mac8(uint64_t a, uint64_t b)
{ ece562_dot_accumulator += (uint32_t)ece562_dot8(a,b); }
static inline int32_t ece562_dot_read(void)
{ return (int32_t)ece562_dot_accumulator; }
#else
#if !defined(__riscv) || __riscv_xlen != 64
#error DotRoCC requires RV64; use ECE562_ROCC_MODEL for host adapter verification
#endif
static inline int32_t ece562_dot4(uint64_t a, uint64_t b)
{
    long result;
    __asm__ volatile(".insn r 0x0b, 7, 0, %0, %1, %2"
                     : "=r"(result) : "r"(a), "r"(b) : "memory");
    return (int32_t)result;
}
static inline int32_t ece562_dot8(uint64_t a, uint64_t b)
{
    long result;
    __asm__ volatile(".insn r 0x0b, 7, 1, %0, %1, %2"
                     : "=r"(result) : "r"(a), "r"(b) : "memory");
    return (int32_t)result;
}
static inline void ece562_dot_clear(void)
{ __asm__ volatile(".insn r 0x0b, 0, 2, x0, x0, x0" ::: "memory"); }
static inline void ece562_mac4(uint64_t a, uint64_t b)
{ __asm__ volatile(".insn r 0x0b, 3, 3, x0, %0, %1" :: "r"(a), "r"(b) : "memory"); }
static inline void ece562_mac8(uint64_t a, uint64_t b)
{ __asm__ volatile(".insn r 0x0b, 3, 4, x0, %0, %1" :: "r"(a), "r"(b) : "memory"); }
static inline int32_t ece562_dot_read(void)
{
    long result;
    __asm__ volatile(".insn r 0x0b, 4, 5, %0, x0, x0" : "=r"(result) :: "memory");
    return (int32_t)result;
}
#endif
#endif
