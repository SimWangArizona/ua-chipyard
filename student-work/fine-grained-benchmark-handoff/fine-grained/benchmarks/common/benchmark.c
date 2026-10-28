#ifndef ECE562_RISCV_COUNTERS
#define _POSIX_C_SOURCE 200809L
#include <time.h>
#endif
#include "bench.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#if defined(ECE562_RISCV_COUNTERS) && (!defined(__riscv) || __riscv_xlen != 64)
#error ECE562_RISCV_COUNTERS currently requires RV64 with accessible cycle/instret CSRs
#endif
#ifndef TRIALS
#define TRIALS 3
#endif
#if TRIALS < 1
#error TRIALS must be positive
#endif
typedef struct { uint64_t cycles, instructions, ns; } Stamp;
static Stamp stamp(void)
{
    Stamp s = {0,0,0};
#ifdef ECE562_RISCV_COUNTERS
    /* Fence drains preceding memory operations. It is not a substitute for
     * waiting for an asynchronous accelerator response in a hardware wrapper. */
    __asm__ volatile("fence rw,rw\n\trdcycle %0\n\trdinstret %1"
                     : "=r"(s.cycles), "=r"(s.instructions) :: "memory");
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    s.ns = (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
#endif
    return s;
}
static int8_t a[MAX_N*MAX_N], b[MAX_N*MAX_N];
static int32_t input[MAX_N*MAX_N], output[MAX_N*MAX_N], gold[MAX_N*MAX_N];
static uint32_t state;
static uint32_t next_random(void)
{
    state = state*UINT32_C(1664525)+UINT32_C(1013904223);
    return state;
}
static void prepare_dot(size_t n)
{
    state = 562;
    for (size_t x = 0; x < n*n; ++x) {
        a[x] = (int8_t)((int32_t)(next_random() >> 24)-128);
        b[x] = (int8_t)((int32_t)(next_random() >> 24)-128);
    }
    a[0] = -128; b[0] = 127;
    if (n > 1) { a[1] = 127; b[1] = -128; a[2] = 0; }
    /* Independent INT64, k-first reference. All sums fit in INT32 for n<=32. */
    int64_t wide[MAX_N*MAX_N] = {0};
    for (size_t k = 0; k < n; ++k)
        for (size_t r = 0; r < n; ++r)
            for (size_t c = 0; c < n; ++c)
                wide[r*n+c] += (int64_t)a[r*n+k]*b[k*n+c];
    for (size_t x = 0; x < n*n; ++x) gold[x] = (int32_t)wide[x];
}
static void prepare_dp(size_t n)
{
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < n; ++j) {
            int32_t cost = (int32_t)(i*j%7+1);
            if ((i+j)%13 == 0 || (i+j)%7 == 0 || (i+j)%11 == 0) cost = INF;
            input[i*n+j] = i == j ? 0 : cost;
        }
    /* Independent all-pairs reference: Dijkstra from each source.
     * Weights are positive, finite shortest paths < INF at these sizes. */
    for (size_t src = 0; src < n; ++src) {
        int32_t dist[MAX_N]; unsigned char visited[MAX_N] = {0};
        for (size_t j = 0; j < n; ++j) dist[j] = INF;
        dist[src] = 0;
        for (size_t step = 0; step < n; ++step) {
            size_t best = n;
            for (size_t j = 0; j < n; ++j)
                if (!visited[j] && (best == n || dist[j] < dist[best])) best = j;
            if (best == n || dist[best] == INF) break;
            visited[best] = 1;
            for (size_t j = 0; j < n; ++j) {
                int32_t edge = input[best*n+j];
                if (edge != INF && dist[best]+edge < dist[j]) dist[j] = dist[best]+edge;
            }
        }
        for (size_t j = 0; j < n; ++j) gold[src*n+j] = dist[j];
    }
}
static const char *names[] = {"baseline",
#ifdef ECE562_CUSTOM
    "custom",
#endif
#ifdef ECE562_ROCC
    "rocc",
#endif
};
static void invoke(int dot, const char *name, size_t n)
{
    if (!strcmp(name,"baseline")) {
        if (dot) dot_baseline(n,a,b,output); else dp_baseline(n,output);
    }
#ifdef ECE562_CUSTOM
    else if (!strcmp(name,"custom")) {
        if (dot) dot_custom(n,a,b,output); else dp_custom(n,output);
    }
#endif
#ifdef ECE562_ROCC
    else if (!strcmp(name,"rocc")) {
        if (dot) dot_rocc(n,a,b,output); else dp_rocc(n,output);
    }
#endif
}
static int verify(size_t n)
{
    for (size_t x = 0; x < n*n; ++x) if (output[x] != gold[x]) return 0;
    return 1;
}
static uint64_t checksum(size_t n)
{
    uint64_t h = UINT64_C(14695981039346656037);
    for (size_t x = 0; x < n*n; ++x) {
        h ^= (uint32_t)output[x]; h *= UINT64_C(1099511628211);
    }
    return h;
}
static int run_workload(int dot)
{
    const size_t sizes[] = {1,4,7,8,16,32};
    int failures = 0;
    for (size_t s = 0; s < sizeof(sizes)/sizeof(sizes[0]); ++s) {
        size_t n = sizes[s];
        if (dot) prepare_dot(n); else prepare_dp(n);
        for (size_t impl = 0; impl < sizeof(names)/sizeof(names[0]); ++impl) {
            /* One warm-up, verified, with the same initialized input. */
            if (dot) memset(output,0,n*n*sizeof(*output));
            else memcpy(output,input,n*n*sizeof(*output));
            invoke(dot,names[impl],n);
            if (!verify(n)) ++failures;
            for (int trial = 1; trial <= TRIALS; ++trial) {
                if (dot) memset(output,0,n*n*sizeof(*output));
                else memcpy(output,input,n*n*sizeof(*output));
                Stamp start = stamp();
                invoke(dot,names[impl],n);
                Stamp end = stamp();
                int passed = verify(n);
                if (!passed) ++failures;
#ifdef ECE562_RISCV_COUNTERS
                uint64_t cycles = end.cycles-start.cycles;
                uint64_t instructions = end.instructions-start.instructions;
                printf("%s,%zu,%s,%d,rocket_rv64,%s,%" PRIu64 ",%" PRIu64 ",",
                       dot ? "int8_matmul" : "floyd_warshall",n,names[impl],trial,
                       passed ? "PASS" : "FAIL",cycles,instructions);
                if (instructions) printf("%.6f",(double)cycles/(double)instructions);
                printf(",,%" PRIu64 "\n",checksum(n));
#else
                printf("%s,%zu,%s,%d,host,%s,,,,%" PRIu64 ",%" PRIu64 "\n",
                       dot ? "int8_matmul" : "floyd_warshall",n,names[impl],trial,
                       passed ? "PASS" : "FAIL",end.ns-start.ns,checksum(n));
#endif
            }
        }
    }
    return failures;
}
int main(void)
{
    int failures = 0;
    puts("workload,size,implementation,trial,platform,status,cycles,instructions,cpi,host_elapsed_ns,checksum");
#ifndef DP_ONLY
    failures += run_workload(1);
#endif
#ifndef DOT_ONLY
    failures += run_workload(0);
#endif
    return failures ? 1 : 0;
}
