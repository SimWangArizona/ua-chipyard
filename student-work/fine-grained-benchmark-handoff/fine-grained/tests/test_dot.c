/* S5 focused hardware validation. Define FG_SOFTWARE_ONLY for host vector checks. */
#include <stdio.h>
#include "fg_reference.h"
#ifndef FG_SOFTWARE_ONLY
#include "fg_hw.h"
#endif
#ifndef FG_RANDOM_CASES
#define FG_RANDOM_CASES 128
#endif
static unsigned checks,failures;
static uint32_t state=UINT32_C(0x05622026);
static uint32_t random32(void)
{
    state^=state<<13; state^=state>>17; state^=state<<5;
    return state;
}
static void check(const char *name,uint32_t a,uint32_t b,uint32_t c,uint64_t got,uint64_t want)
{
    ++checks;
    if (got!=want) {
        if (failures<8)
            printf("FAIL %s a=%08lx b=%08lx c=%08lx got=%016llx want=%016llx\n",
                name,(unsigned long)a,(unsigned long)b,(unsigned long)c,
                (unsigned long long)got,(unsigned long long)want);
        ++failures;
    }
}
/* Byte extraction and wide mathematical sum independent of fg_dot_ref. */
static uint32_t oracle(uint32_t a,uint32_t b,uint32_t c)
{
    int64_t sum=c<=UINT32_C(0x7fffffff)?(int64_t)c:(int64_t)c-INT64_C(4294967296);
    for (unsigned i=0;i<4;++i) {
        int x=(int)(a&255u),y=(int)(b&255u);
        if (x>=128) x-=256;
        if (y>=128) y-=256;
        sum+=(int64_t)x*y;
        a>>=8; b>>=8;
    }
    return (uint32_t)sum;
}
static void test(uint32_t a,uint32_t b,uint32_t c,uint32_t want)
{
    check("dot-reference",a,b,c,fg_dot_ref(a,b,c),want);
#ifndef FG_SOFTWARE_ONLY
    uint64_t ac=fg_pack_ac(a,c);
    check("dot-raw",a,b,c,fg_dot_raw(ac,b),fg_sext32(want));
    check("dot-upper",a,b,c,fg_dot_raw(ac,UINT64_C(0xa5a5a5a500000000)|b),fg_sext32(want));
    check("dot-api",a,b,c,dot4_acc_hw(a,b,c),want);
#endif
}
#ifdef FG_COMBINED
int fg_run_dot(void)
#else
int main(void)
#endif
{
    static const uint32_t known[][4]={
        {0,0,0,0},{0,0,0xffffffff,0xffffffff},
        {0x04030201,0x08070605,10,80},
        {0x80808080,0x80808080,0,65536},
        {0x7f7f7f7f,0x7f7f7f7f,0,64516},
        {0x80808080,0x7f7f7f7f,0,0xffff0200},
        {0xffffffff,0x01010101,0,0xfffffffc},
        {0x01ff7f80,0x01010101,0,0xffffffff},
        {1,1,0x7fffffff,0x80000000},
        {0xff,1,0x80000000,0x7fffffff},
        {0x80808080,0x80808080,0x7fffffff,0x8000ffff},
        {0x80808080,0x7f7f7f7f,0x80000000,0x7fff0200},
        {0x04030201,0,0x80000000,0x80000000},
        {0x80808080,0x80808080,0xffff0000,0},
        {0x7f7f7f7f,0x7f7f7f7f,0xffff03fc,0}
    };
    static const uint32_t patterns[]={0,0xffffffff,0x01010101,0x7f7f7f7f,0x80808080,0x807f01ff};
    static const uint32_t accumulators[]={0,1,0xffffffff,0x7fffffff,0x80000000};
    printf("S5 dot seed=0x05622026 random_cases=%u\n",(unsigned)FG_RANDOM_CASES);
    for (unsigned i=0;i<sizeof(known)/sizeof(known[0]);++i)
        test(known[i][0],known[i][1],known[i][2],known[i][3]);
    puts("Dot known answers completed");
    for (unsigned i=0;i<4;++i)
        for (unsigned j=0;j<4;++j) {
            uint32_t a=UINT32_C(0x80)<<(8*i),b=UINT32_C(0x7f)<<(8*j);
            uint32_t want=i==j?UINT32_C(0xffffc080)+17:17;
            test(a,b,17,want);
        }
    for (unsigned i=0;i<6;++i)
        for (unsigned j=0;j<6;++j)
            for (unsigned k=0;k<5;++k) {
                uint32_t a=patterns[i],b=patterns[j],c=accumulators[k];
                test(a,b,c,oracle(a,b,c));
            }
    puts("Dot lane and accumulator boundaries completed");
    for (unsigned i=0;i<FG_RANDOM_CASES;++i) {
        uint32_t a=random32(),b=random32(),c=random32();
        test(a,b,c,oracle(a,b,c));
    }
    printf("checks=%u failures=%u\n",checks,failures);
    if (failures) return 1;
#ifdef FG_SOFTWARE_ONLY
    puts("FG PASS dot-vectors-host");
#else
    puts("FG PASS hardware-dot");
#endif
    return 0;
}
