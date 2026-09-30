#include <fenv.h>
__attribute__((constructor)) static void rz(void){ fesetround(FE_TOWARDZERO); }
