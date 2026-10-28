#include "../dot_rocc.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(ece562_dot4(UINT64_C(0x04030201), UINT64_C(0x08070605)) == 70);
    assert(ece562_dot4(UINT64_C(0x04fd02ff), UINT64_C(0xf807fa05)) == -70);
    assert(ece562_dot4(UINT64_C(0x80808080), UINT64_C(0x80808080)) == 65536);
    assert(ece562_dot8(UINT64_C(0x8080808080808080), UINT64_C(0x8080808080808080)) == 131072);
    assert(ece562_dot8(UINT64_C(0x8080808080808080), UINT64_C(0x7f7f7f7f7f7f7f7f)) == -130048);
    ece562_dot_clear();
    assert(ece562_dot_read() == 0);
    ece562_mac4(UINT64_C(0x04030201), UINT64_C(0x08070605));
    ece562_mac8(UINT64_C(0x8080808080808080), UINT64_C(0x7f7f7f7f7f7f7f7f));
    assert(ece562_dot_read() == -129978);
    ece562_dot_clear();
    for (int i = 0; i < 100; ++i) ece562_mac4(UINT64_C(0x80808080), UINT64_C(0x80808080));
    assert(ece562_dot_read() == 6553600);
    ece562_dot_clear();
    assert(ece562_dot_read() == 0);
    puts("DotRoCC smoke: PASS");
    return 0;
}
