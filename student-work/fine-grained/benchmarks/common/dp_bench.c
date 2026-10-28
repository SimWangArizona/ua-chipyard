/* Algorithm reference: PolyBench/C 4.2.1 Floyd-Warshall.
 * Independently written kernel; zero diagonal and guarded INF arithmetic.
 * This is an adaptation, not a reproduction of the Hopper CUDA benchmark. */
#include "bench.h"
void dp_baseline(size_t n, int32_t *path)
{
    for (size_t k = 0; k < n; ++k)
        for (size_t i = 0; i < n; ++i)
            for (size_t j = 0; j < n; ++j) {
                const int32_t a = path[i*n+k], b = path[k*n+j];
                if (a != INF && b != INF) {
                    const int32_t candidate = a+b;
                    if (candidate < path[i*n+j]) path[i*n+j] = candidate;
                }
            }
}
