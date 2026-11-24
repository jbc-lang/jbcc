#define _POSIX_C_SOURCE 200809L
#include <time.h>

int test_clock_gettime(clockid_t clock, struct timespec *out)
{
    if (clock != CLOCK_REALTIME) return -1;

    static unsigned sample;
    static const struct timespec times[] = {
        {1704070799, 123456789},
        {1704070799, 999999999},
        {-2, 123456789},
        {1704070800, 123456789}
    };
    if (sample >= sizeof times / sizeof times[0]) return -1;
    *out = times[sample++];
    return 0;
}
