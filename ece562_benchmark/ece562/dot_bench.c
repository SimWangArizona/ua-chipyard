/* Algorithm reference: Gemmini (Genc et al., DAC 2021), matmul reference in
 * gemmini-rocc-tests/include/gemmini_testutils.h. Independently written
 * fixed INT8/INT32 kernel; no bias, scaling, activation, or Gemmini commands. */
#include "bench.h"
void dot_baseline(size_t n, const int8_t *a, const int8_t *b, int32_t *out)
{
    for (size_t r = 0; r < n; ++r)
        for (size_t c = 0; c < n; ++c) {
            int32_t sum = 0;
            for (size_t k = 0; k < n; ++k)
                sum += (int32_t)a[r*n+k] * (int32_t)b[k*n+c];
            out[r*n+c] = sum;
        }
}
