#ifndef ECE562_BENCH_H
#define ECE562_BENCH_H
#include <stdint.h>
#include <stddef.h>
#define MAX_N 32
#define INF 999
/* Row-major square matrices; signed INT8 inputs, signed INT32 outputs.
 * Optional hardware implementations must finish all work before returning. */
void dot_baseline(size_t n, const int8_t *a, const int8_t *b, int32_t *out);
void dp_baseline(size_t n, int32_t *path);
#ifdef ECE562_CUSTOM
void dot_custom(size_t n, const int8_t *a, const int8_t *b, int32_t *out);
void dp_custom(size_t n, int32_t *path);
#endif
#ifdef ECE562_ROCC
void dot_rocc(size_t n, const int8_t *a, const int8_t *b, int32_t *out);
void dp_rocc(size_t n, int32_t *path);
#endif
#endif
