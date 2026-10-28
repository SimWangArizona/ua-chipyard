/* Focused S4 instruction test: actual RV64 assembly, no dot-product work.
 * Full reference semantics remain in fg_reference.h and S1 tests. */
#include <stdio.h>
#include "fg_reference.h"
#include "fg_hw.h"
#ifndef FG_RANDOM_CASES
#define FG_RANDOM_CASES 128
#endif
static unsigned checks, failures;
static uint32_t state = UINT32_C(0x05622026);
static uint32_t random32(void)
{
    state ^= state << 13; state ^= state >> 17; state ^= state << 5;
    return state;
}
static void check(const char *name, uint32_t a,uint32_t b,uint32_t c,uint64_t got,uint64_t want)
{
    ++checks;
    if (got != want) {
        if (failures < 8)
            printf("FAIL %s a=%08lx b=%08lx c=%08lx got=%016llx want=%016llx\n",
                name,(unsigned long)a,(unsigned long)b,(unsigned long)c,
                (unsigned long long)got,(unsigned long long)want);
        ++failures;
    }
}
static void test(uint32_t a,uint32_t b,uint32_t c,uint32_t hi,uint32_t lo)
{
    uint64_t ac=fg_pack_ac(a,c);
    check("max",a,b,c,fg_max_raw(ac,b),fg_sext32(hi));
    check("min",a,b,c,fg_min_raw(ac,b),fg_sext32(lo));
    check("max-upper",a,b,c,fg_max_raw(ac,UINT64_C(0xa5a5a5a500000000)|b),fg_sext32(hi));
    check("min-upper",a,b,c,fg_min_raw(ac,UINT64_C(0xa5a5a5a500000000)|b),fg_sext32(lo));
    check("max-api",a,b,c,add_max_hw(a,b,c),hi);
    check("min-api",a,b,c,add_min_hw(a,b,c),lo);
}
#ifdef FG_COMBINED
int fg_run_dp(void)
#else
int main(void)
#endif
{
    static const uint32_t known[][5] = {
        {0,0,0,0,0}, {3,4,10,10,7}, {3,4,5,7,5},
        {0xffffffff,0xfffffffe,0xfffffffc,0xfffffffd,0xfffffffc},
        {0xffffffff,1,0xffffffff,0,0xffffffff},
        {0x7fffffff,1,0,0,0x80000000},
        {0x80000000,0xffffffff,0,0x7fffffff,0},
        {0x7fffffff,0x7fffffff,0xffffffff,0xffffffff,0xfffffffe},
        {0x80000000,0x80000000,1,1,0},
        {0x80000000,0,0x7fffffff,0x7fffffff,0x80000000},
        {0x7fffffff,0,0x80000000,0x7fffffff,0x80000000},
        {1,1,2,2,2}, {0,0,0x80000000,0,0x80000000},
        {0x80000000,0,0x80000000,0x80000000,0x80000000},
        {0x7fffffff,0,0x7fffffff,0x7fffffff,0x7fffffff}
    };
    static const uint32_t edges[] = {0,1,0xffffffff,0x7fffffff,0x80000000};
    printf("S4 DP hardware seed=0x05622026 random_cases=%u\n",(unsigned)FG_RANDOM_CASES);
    for (unsigned i=0;i<sizeof(known)/sizeof(known[0]);++i)
        test(known[i][0],known[i][1],known[i][2],known[i][3],known[i][4]);
    puts("DP known answers completed");
    for (unsigned i=0;i<5;++i)
        for (unsigned j=0;j<5;++j)
            for (unsigned k=0;k<5;++k) {
                uint32_t a=edges[i],b=edges[j],c=edges[k];
                test(a,b,c,fg_max_ref(a,b,c),fg_min_ref(a,b,c));
            }
    puts("DP boundary combinations completed");
    for (unsigned i=0;i<FG_RANDOM_CASES;++i) {
        uint32_t a=random32(),b=random32(),c=random32();
        test(a,b,c,fg_max_ref(a,b,c),fg_min_ref(a,b,c));
    }
    printf("checks=%u failures=%u\n",checks,failures);
    if (failures) return 1;
    puts("FG PASS hardware-dp");
    return 0;
}
