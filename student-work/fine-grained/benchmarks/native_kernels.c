#include "bench.h"
#include "fg_hw.h"

void dot_custom(size_t n, const int8_t *a, const int8_t *b, int32_t *out)
{
    for (size_t r = 0; r < n; ++r)
        for (size_t c = 0; c < n; ++c) {
            uint32_t sum = 0;
            for (size_t k = 0; k < n; k += 4) {
                uint32_t pa = 0, pb = 0;
                for (size_t lane = 0; lane < 4 && k+lane < n; ++lane) {
                    pa |= (uint32_t)(uint8_t)a[r*n+k+lane] << (8*lane);
                    pb |= (uint32_t)(uint8_t)b[(k+lane)*n+c] << (8*lane);
                }
                sum = dot4_acc_hw(pa, pb, sum);
            }
            out[r*n+c] = (int32_t)fg_signed32(sum);
        }
}

void dp_custom(size_t n, int32_t *path)
{
    for (size_t k = 0; k < n; ++k)
        for (size_t i = 0; i < n; ++i)
            for (size_t j = 0; j < n; ++j) {
                int32_t a = path[i*n+k], b = path[k*n+j];
                if (a != INF && b != INF)
                    path[i*n+j] = (int32_t)fg_signed32(add_min_hw(
                        (uint32_t)a, (uint32_t)b, (uint32_t)path[i*n+j]));
            }
}
