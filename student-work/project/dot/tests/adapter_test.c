#include "../../benchmark/bench.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    int8_t a[MAX_N*MAX_N], b[MAX_N*MAX_N];
    int32_t expected[MAX_N*MAX_N], guarded[MAX_N*MAX_N+2];
    uint32_t state = 562;
    for (size_t n = 0; n <= MAX_N; ++n)
        for (int pattern = 0; pattern < 5; ++pattern) {
            for (size_t i = 0; i < n*n; ++i) {
                state = state*UINT32_C(1664525)+UINT32_C(1013904223);
                a[i] = (int8_t)((int32_t)(state >> 24)-128);
                state = state*UINT32_C(1664525)+UINT32_C(1013904223);
                b[i] = (int8_t)((int32_t)(state >> 24)-128);
                if (pattern == 1) a[i] = b[i] = -128;
                if (pattern == 2) { a[i] = -128; b[i] = 127; }
                if (pattern == 3) a[i] = b[i] = 0;
                if (pattern == 4) b[i] = (i/n == i%n) ? 1 : 0;
            }
            for (size_t i = 0; i < MAX_N*MAX_N+2; ++i) guarded[i] = INT32_C(0x13579bdf);
            dot_baseline(n,a,b,expected);
            dot_rocc(n,a,b,guarded+1);
            assert(guarded[0] == INT32_C(0x13579bdf));
            assert(guarded[n*n+1] == INT32_C(0x13579bdf));
            for (size_t i = 0; i < n*n; ++i) assert(guarded[i+1] == expected[i]);
        }
    puts("Dot adapter: all sizes 0..32 and 5 input patterns PASS");
    return 0;
}
