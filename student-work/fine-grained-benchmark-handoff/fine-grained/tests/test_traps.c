/* HTIF ABI verified against the installed trap_entry:
 * a0=mepc, a1=mcause, a2=mtval, a3=saved GPR frame; return a0=new mepc.
 * Override the weak handler; the runtime saves/restores all integer registers. */
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include "fg_contract.h"
#ifndef FG_ENABLE_DOT
#define FG_ENABLE_DOT 0
#endif
#ifndef FG_ENABLE_DP
#define FG_ENABLE_DP 0
#endif
#define DECLARE(name) \
    extern uint64_t fg_probe_##name(uint64_t,uint64_t); \
    extern const unsigned char fg_pc_##name[]
DECLARE(dot); DECLARE(max); DECLARE(min); DECLARE(reserved); DECLARE(bad_f3);
static volatile uintptr_t expected_pc;
static volatile uint32_t expected_word;
static volatile unsigned expecting_trap, trap_count;

uintptr_t handle_trap(uintptr_t pc,uintptr_t cause,uintptr_t tval,uintptr_t *regs)
{
    (void)regs;
    uint32_t word=0;
    if (expecting_trap && cause==2 && pc==expected_pc)
        word=*(const volatile uint32_t *)pc;
    if (!expecting_trap || cause!=2 || pc!=expected_pc || word!=expected_word ||
        (tval!=0 && tval!=(uintptr_t)word)) {
        printf("FAIL trap cause=%lu pc=%lx expected_pc=%lx word=%08lx mtval=%lx\n",
            (unsigned long)cause,(unsigned long)pc,(unsigned long)expected_pc,
            (unsigned long)word,(unsigned long)tval);
        _exit(1);
    }
    ++trap_count;
    return pc+4; /* All probe encodings are 32-bit; skip exactly the faulting instruction. */
}
static uint32_t encoding(unsigned fn,unsigned f3)
{
    return ((uint32_t)fn<<25)|(11u<<20)|(10u<<15)|((uint32_t)f3<<12)|(5u<<7)|FG_OPCODE;
}
struct Probe {
    const char *name;
    uint64_t (*call)(uint64_t,uint64_t);
    const unsigned char *pc;
    unsigned fn,f3,enabled;
    uint64_t result;
};
int main(void)
{
    const struct Probe probes[]={
        {"dot",fg_probe_dot,fg_pc_dot,FG_DOT_FUNCT7,FG_FUNCT3,FG_ENABLE_DOT,19},
        {"max",fg_probe_max,fg_pc_max,FG_MAX_FUNCT7,FG_FUNCT3,FG_ENABLE_DP,0x02030405},
        {"min",fg_probe_min,fg_pc_min,FG_MIN_FUNCT7,FG_FUNCT3,FG_ENABLE_DP,9},
        {"reserved",fg_probe_reserved,fg_pc_reserved,127,FG_FUNCT3,0,123},
        {"bad-funct3",fg_probe_bad_f3,fg_pc_bad_f3,FG_DOT_FUNCT7,1,0,123}
    };
    unsigned failures=0, checks=0, expected_traps=0;
    printf("Trap profile dot=%u dp=%u\n",FG_ENABLE_DOT,FG_ENABLE_DP);
    for (unsigned i=0;i<5;++i) {
        unsigned repeats=i<3?2:1;
        for (unsigned j=0;j<repeats;++j) {
            const struct Probe *p=&probes[i];
            unsigned before=trap_count;
            expected_pc=(uintptr_t)p->pc;
            expected_word=encoding(p->fn,p->f3);
            expecting_trap=!p->enabled;
            expected_traps+=!p->enabled;
            __asm__ volatile("fence rw,rw" ::: "memory");
            uint64_t got=p->call(fg_pack_ac(0x01020304,9),0x01010101);
            expecting_trap=0;
            ++checks;
            if (trap_count-before!=(unsigned)!p->enabled || got!=(p->enabled?p->result:123)) {
                ++failures;
                printf("FAIL %s trap_delta=%u expected=%u result=%lx\n",p->name,
                    trap_count-before,(unsigned)!p->enabled,(unsigned long)got);
            }
        }
    }
    if (trap_count!=expected_traps) ++failures;
    printf("probes=%u traps=%u expected_traps=%u failures=%u\n",checks,trap_count,expected_traps,failures);
    if (failures) return 1;
    puts("FG PASS traps");
    return 0;
}
