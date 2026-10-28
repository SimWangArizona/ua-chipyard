#ifndef FG_REFERENCE_H
#define FG_REFERENCE_H
#include "fg_contract.h"
static inline int fg_lane(uint32_t x, unsigned lane)
{
    unsigned v = (x >> (lane * 8)) & 255u;
    return v < 128 ? (int)v : (int)v - 256;
}
static inline uint32_t fg_dot_ref(uint32_t a, uint32_t b, uint32_t c)
{
    int64_t sum = fg_signed32(c);
    for (unsigned i = 0; i < 4; ++i)
        sum += fg_lane(a, i) * fg_lane(b, i);
    return (uint32_t)sum;
}
static inline uint32_t fg_max_ref(uint32_t a, uint32_t b, uint32_t c)
{
    uint32_t sum = a + b;
    return fg_signed32(sum) > fg_signed32(c) ? sum : c;
}
static inline uint32_t fg_min_ref(uint32_t a, uint32_t b, uint32_t c)
{
    uint32_t sum = a + b;
    return fg_signed32(sum) < fg_signed32(c) ? sum : c;
}
#endif
