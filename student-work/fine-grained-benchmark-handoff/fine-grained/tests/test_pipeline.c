#include <stdio.h>
#include "fg_hw.h"
#include "fg_reference.h"
#ifndef FG_TEST_DOT
#define FG_TEST_DOT 1
#endif
#ifndef FG_TEST_DP
#define FG_TEST_DP 1
#endif
static unsigned failures, checks;
static void check(const char *name,uint64_t got,uint64_t want)
{
    ++checks;
    if (got != want) {
        ++failures;
        printf("FAIL %s got=%016llx want=%016llx\n",name,
               (unsigned long long)got,(unsigned long long)want);
    }
}
/* One assembly block per sequence prevents the compiler inserting gaps.
 * t0/t1 are fixed scratch registers solely for explicit hazard tests. */
#define TEST_SEQUENCE(tag, fn, ref) do { \
    uint64_t ac=fg_pack_ac(0x80000001u,0xffffffffu), b=3, out, value; \
    uint64_t want=fg_sext32(ref((uint32_t)ac,(uint32_t)b,(uint32_t)(ac>>32))); \
    __asm__ volatile("addi t0, %1, 0\n\t" FG_INSN(fn,"t1","t0","%2") \
        "addi %0, t1, 1" : "=r"(out) : "r"(ac),"r"(b) : "t0","t1"); \
    check(tag " producer-consumer",out,want+1); \
    value=ac; \
    __asm__ volatile(FG_INSN(fn,"%0","%0","%1") : "+r"(value) : "r"(b)); \
    check(tag " rd=rs1",value,want); \
    value=b; \
    __asm__ volatile(FG_INSN(fn,"%0","%1","%0") : "+r"(value) : "r"(ac)); \
    check(tag " rd=rs2",value,want); \
    __asm__ volatile(FG_INSN(fn,"zero","%1","%2") "addi %0, zero, 0" \
        : "=r"(out) : "r"(ac),"r"(b)); \
    check(tag " x0",out,0); \
    __asm__ volatile("ld t0, 0(%1)\n\t" FG_INSN(fn,"%0","t0","%2") \
        : "=r"(out) : "r"(&ac),"r"(b) : "t0","memory"); \
    check(tag " load-use",out,want); \
    __asm__ volatile(FG_INSN(fn,"t0","%1","%2") FG_INSN(fn,"%0","t0","%2") \
        : "=r"(out) : "r"(ac),"r"(b) : "t0"); \
    check(tag " custom-chain",out,fg_sext32(ref((uint32_t)want,(uint32_t)b,(uint32_t)(want>>32)))); \
    __asm__ volatile("li t0, 123\n\tbeq zero, zero, 1f\n\t" \
        FG_INSN(fn,"t0","%1","%2") "1: mv %0, t0" \
        : "=r"(out) : "r"(ac),"r"(b) : "t0"); \
    check(tag " branch-flush",out,123); \
} while (0)
int main(void)
{
#if FG_TEST_DOT
    TEST_SEQUENCE("dot",FG_DOT_FUNCT7,fg_dot_ref);
#endif
#if FG_TEST_DP
    TEST_SEQUENCE("max",FG_MAX_FUNCT7,fg_max_ref);
    TEST_SEQUENCE("min",FG_MIN_FUNCT7,fg_min_ref);
#endif
#if FG_TEST_DOT && FG_TEST_DP
    /* Back-to-back operations of different families with true result dependencies. */
    uint64_t mixed, ac=fg_pack_ac(0x04030201,10), b=0x08070605, step=7;
    __asm__ volatile(FG_INSN(FG_DOT_FUNCT7,"t0","%1","%2")
        FG_INSN(FG_MIN_FUNCT7,"t1","t0","%3")
        FG_INSN(FG_MAX_FUNCT7,"%0","t1","%3")
        : "=r"(mixed) : "r"(ac),"r"(b),"r"(step) : "t0","t1");
    check("mixed positive dot-min-max",mixed,7);
    ac=fg_pack_ac(0xffffffff,0); b=0x01010101; step=1;
    __asm__ volatile(FG_INSN(FG_DOT_FUNCT7,"t0","%1","%2")
        FG_INSN(FG_MAX_FUNCT7,"t1","t0","%3")
        FG_INSN(FG_MIN_FUNCT7,"%0","t1","%3")
        : "=r"(mixed) : "r"(ac),"r"(b),"r"(step) : "t0","t1");
    check("mixed negative dot-max-min",mixed,UINT64_MAX);
#endif
    printf("checks=%u failures=%u\n",checks,failures);
    if (failures) return 1;
#if FG_TEST_DOT && FG_TEST_DP
    puts("FG PASS pipeline");
#elif FG_TEST_DP
    puts("FG PASS dp-pipeline");
#else
    puts("FG PASS dot-pipeline");
#endif
    return 0;
}
