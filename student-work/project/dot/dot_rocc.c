#include "../benchmark/bench.h"
#include "dot_rocc.h"
#include <assert.h>

#ifndef ROCC_LANES
#define ROCC_LANES 8
#endif
#if ROCC_LANES != 4 && ROCC_LANES != 8
#error ROCC_LANES must be 4 or 8
#endif
#ifndef ROCC_ACCUMULATE
#define ROCC_ACCUMULATE 1
#endif

void dot_rocc(size_t n, const int8_t *a, const int8_t *b, int32_t *out)
{
    assert(n <= MAX_N);
    /* Stack-local packing is included in the timed call. B's columns become
     * contiguous packed operands. Explicit byte packing is alignment-safe,
     * alias-safe and zero-pads partial groups (including n=1 and n=7). */
    uint64_t packed_a[MAX_N][(MAX_N+ROCC_LANES-1)/ROCC_LANES];
    uint64_t packed_b[MAX_N][(MAX_N+ROCC_LANES-1)/ROCC_LANES];
    const size_t groups = (n+ROCC_LANES-1)/ROCC_LANES;
    for (size_t r = 0; r < n; ++r)
        for (size_t g = 0; g < groups; ++g) {
            uint64_t pa = 0, pb = 0;
            for (size_t lane = 0; lane < ROCC_LANES; ++lane) {
                const size_t k = g*ROCC_LANES+lane;
                if (k < n) {
                    pa |= (uint64_t)(uint8_t)a[r*n+k] << (8*lane);
                    pb |= (uint64_t)(uint8_t)b[k*n+r] << (8*lane);
                }
            }
            packed_a[r][g] = pa;
            packed_b[r][g] = pb;
        }
    for (size_t r = 0; r < n; ++r)
        for (size_t c = 0; c < n; ++c) {
#if ROCC_ACCUMULATE
            ece562_dot_clear();
#else
            int32_t sum = 0;
#endif
            for (size_t g = 0; g < groups; ++g) {
#if ROCC_ACCUMULATE
#if ROCC_LANES == 8
                ece562_mac8(packed_a[r][g], packed_b[c][g]);
#else
                ece562_mac4(packed_a[r][g], packed_b[c][g]);
#endif
#else
#if ROCC_LANES == 8
                sum += ece562_dot8(packed_a[r][g], packed_b[c][g]);
#else
                sum += ece562_dot4(packed_a[r][g], packed_b[c][g]);
#endif
#endif
            }
#if ROCC_ACCUMULATE
            /* A register dependency on READ waits for all preceding commands.
             * The wrapper finishes before benchmark counters are sampled. */
            out[r*n+c] = ece562_dot_read();
#else
            out[r*n+c] = sum;
#endif
        }
}
