/* Owned test process for checking Windows x86 instrumentation, never game code. */
#include <windows.h>
__declspec(dllexport) __declspec(noinline) unsigned int mco_trace_canary(unsigned int value) {
    return value + 7;
}
int main(void) {
    volatile unsigned int result = 0;
    Sleep(1000);
    for (unsigned int i = 0; i < 500; ++i) {
        result = mco_trace_canary(i);
        Sleep(20);
    }
    return result == 506 ? 0 : 1;
}
