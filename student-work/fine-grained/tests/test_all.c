/* Run both real-instruction suites in one process on the combined Rocket. */
#include <stdio.h>
int fg_run_dot(void);
int fg_run_dp(void);
int main(void)
{
    int dot_failed=fg_run_dot();
    int dp_failed=fg_run_dp();
    if (dot_failed || dp_failed) return 1;
    puts("FG PASS hardware-all");
    return 0;
}
