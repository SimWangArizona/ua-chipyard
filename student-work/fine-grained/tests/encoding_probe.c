#include "fg_hw.h"
/* Stable C symbols let the encoding test inspect each wrapper separately. */
#ifdef __cplusplus
extern "C" {
#endif
__attribute__((noinline)) uint32_t probe_dot(uint32_t a,uint32_t b,uint32_t c)
{ return dot4_acc_hw(a,b,c); }
__attribute__((noinline)) uint32_t probe_max(uint32_t a,uint32_t b,uint32_t c)
{ return add_max_hw(a,b,c); }
__attribute__((noinline)) uint32_t probe_min(uint32_t a,uint32_t b,uint32_t c)
{ return add_min_hw(a,b,c); }
#ifdef __cplusplus
}
#endif
