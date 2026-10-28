#include <stdint.h>
#include <assert.h>

int32_t dot4_ref(uint32_t a, uint32_t b)
{
    int32_t sum = 0;

    for (int i = 0; i < 4; i++)
    {
        int8_t ai = (int8_t)(a >> (8 * i));
        int8_t bi = (int8_t)(b >> (8 * i));

        sum += (int32_t)ai * (int32_t)bi;
    }

    return sum;
}

int main(void)
{
    assert(dot4_ref(0x04030201, 0x08070605) == 70);

    assert(dot4_ref(0x04FD02FF, 0xF807FA05) == -70);

    assert(dot4_ref(0x7F7F7F7F, 0x7F7F7F7F) == 64516);

    return 0;
}
