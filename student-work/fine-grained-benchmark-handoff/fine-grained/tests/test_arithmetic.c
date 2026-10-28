#include <stdio.h>
#include "fg_reference.h"
#ifdef FG_HARDWARE
#include "fg_hw.h"
#endif
#ifndef FG_TEST_DOT
#define FG_TEST_DOT 1
#endif
#ifndef FG_TEST_DP
#define FG_TEST_DP 1
#endif
#ifndef FG_RANDOM_CASES
#define FG_RANDOM_CASES 2000
#endif
static unsigned checks, failures;
static uint32_t rng = UINT32_C(0x5622026);
static uint32_t random32(void)
{
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
    return rng;
}
static void check(const char *op, uint32_t a, uint32_t b, uint32_t c,
                  uint64_t got, uint64_t want)
{
    ++checks;
    if (got != want) {
        if (failures < 12)
            printf("FAIL %s a=%08lx b=%08lx c=%08lx got=%016llx want=%016llx\n",
                   op, (unsigned long)a, (unsigned long)b, (unsigned long)c,
                   (unsigned long long)got, (unsigned long long)want);
        ++failures;
    }
}
/* Independent oracle: explicit mathematical integers, not the reference helpers. */
static int64_t signed_value(uint32_t x)
{ return x <= UINT32_C(0x7fffffff) ? (int64_t)x : -(int64_t)(UINT32_MAX - x) - 1; }
static inline uint64_t expected(uint32_t x) { return (uint64_t)signed_value(x); }
static void case_check(uint32_t a, uint32_t b, uint32_t c)
{
#if FG_TEST_DOT
    int64_t dot = signed_value(c);
    uint32_t aa = a, bb = b;
    for (unsigned i = 0; i < 4; ++i) {
        int av = (int)(aa % 256), bv = (int)(bb % 256);
        if (av >= 128) av -= 256;
        if (bv >= 128) bv -= 256;
        dot += av * bv;
        aa /= 256; bb /= 256;
    }
    check("dot-ref", a, b, c, fg_sext32(fg_dot_ref(a,b,c)), expected((uint32_t)dot));
#ifdef FG_HARDWARE
    check("dot-hw", a,b,c, fg_dot_raw(fg_pack_ac(a,c), b), expected((uint32_t)dot));
    check("dot-upper", a,b,c, fg_dot_raw(fg_pack_ac(a,c), UINT64_C(0xa5a5a5a500000000)|b), expected((uint32_t)dot));
#endif
#endif
#if FG_TEST_DP
    int64_t sum = signed_value(a) + signed_value(b);
    if (sum > INT32_MAX) sum -= INT64_C(4294967296);
    if (sum < INT32_MIN) sum += INT64_C(4294967296);
    uint64_t hi = (uint64_t)(sum > signed_value(c) ? sum : signed_value(c));
    uint64_t lo = (uint64_t)(sum < signed_value(c) ? sum : signed_value(c));
    check("max-ref", a,b,c, fg_sext32(fg_max_ref(a,b,c)), hi);
    check("min-ref", a,b,c, fg_sext32(fg_min_ref(a,b,c)), lo);
#ifdef FG_HARDWARE
    check("max-hw", a,b,c, fg_max_raw(fg_pack_ac(a,c), b), hi);
    check("min-hw", a,b,c, fg_min_raw(fg_pack_ac(a,c), b), lo);
    check("max-upper", a,b,c, fg_max_raw(fg_pack_ac(a,c), UINT64_C(0xa5a5a5a500000000)|b), hi);
    check("min-upper", a,b,c, fg_min_raw(fg_pack_ac(a,c), UINT64_C(0xa5a5a5a500000000)|b), lo);
#endif
#endif
}
int main(void)
{
    static const uint32_t edges[] = {0,1,UINT32_MAX,0x7fffffff,0x80000000,
        0x7f7f7f7f,0x80808080,0xff00ff00,0x01020304,0x807f01ff};
    printf("seed=0x05622026 random_cases=%u\n", (unsigned)FG_RANDOM_CASES);
    check("pack-lanes",0,0,0,fg_pack_lanes(-128,127,-1,1),UINT32_C(0x01ff7f80));
    check("pack-ac",0,0,0,fg_pack_ac(0x12345678,0x89abcdef),UINT64_C(0x89abcdef12345678));
    check("signed32",0,0,0,fg_sext32(0x80000000),UINT64_C(0xffffffff80000000));
    check("known-dot",0,0,0,fg_dot_ref(0x04030201,0x08070605,10),80);
    check("known-dot-min",0,0,0,fg_dot_ref(0x80808080,0x80808080,0),65536);
    check("known-max-wrap",0,0,0,fg_max_ref(0x7fffffff,1,0),0);
    check("known-min-wrap",0,0,0,fg_min_ref(0x7fffffff,1,0),0x80000000);
    for (unsigned i=0; i<sizeof(edges)/sizeof(edges[0]); ++i)
        for (unsigned j=0; j<sizeof(edges)/sizeof(edges[0]); ++j)
            for (unsigned k=0; k<sizeof(edges)/sizeof(edges[0]); ++k)
                case_check(edges[i],edges[j],edges[k]);
    for (unsigned i=0; i<4; ++i)
        for (unsigned j=0; j<4; ++j)
            case_check(UINT32_C(0x80)<<(8*i),UINT32_C(0x7f)<<(8*j),17);
    for (unsigned i=0; i<FG_RANDOM_CASES; ++i) {
        uint32_t a=random32(), b=random32(), c=random32();
        case_check(a,b,c);
    }
    printf("checks=%u failures=%u\n",checks,failures);
    if (failures) return 1;
#ifdef FG_HARDWARE
#if FG_TEST_DOT && FG_TEST_DP
    puts("FG PASS hardware-all");
#elif FG_TEST_DOT
    puts("FG PASS hardware-dot");
#else
    puts("FG PASS hardware-dp");
#endif
#else
    puts("FG PASS reference");
#endif
    return 0;
}
