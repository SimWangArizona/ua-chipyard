#ifndef FG_CONTRACT_H
#define FG_CONTRACT_H
#include <stdint.h>
#include "fg_encoding.h"

/* Contract v1 candidate. All arithmetic inputs/results are bit patterns. */

static inline uint64_t fg_pack_ac(uint32_t a, uint32_t c)
{
    return ((uint64_t)c << 32) | a;
}
static inline uint32_t fg_pack_lanes(int a0, int a1, int a2, int a3)
{
    return (uint32_t)(uint8_t)a0 | ((uint32_t)(uint8_t)a1 << 8) |
           ((uint32_t)(uint8_t)a2 << 16) | ((uint32_t)(uint8_t)a3 << 24);
}
/* Avoid implementation-defined unsigned-to-signed conversions. */
static inline int64_t fg_signed32(uint32_t x)
{
    return (x & UINT32_C(0x80000000)) ? (int64_t)x - INT64_C(4294967296) : (int64_t)x;
}
static inline uint64_t fg_sext32(uint32_t x)
{
    return (uint64_t)fg_signed32(x);
}
#endif
