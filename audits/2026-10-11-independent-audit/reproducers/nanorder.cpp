// Pin the NaN-safety of predictionEstimate's three guards, and show which are
// deliberate and which depend on argument order.
#include <cstdio>
#include <cmath>
#include <algorithm>
#include <fenv.h>
int main(){
  double nan_ = std::nan("");
  printf("std::min(1.0, NaN) = %g   <- the form the code uses at utils.h:1043\n", std::min(1.0, nan_));
  printf("std::min(NaN, 1.0) = %g   <- the same expression with arguments swapped\n", std::min(nan_, 1.0));
  printf("fmax(0.5, NaN)     = %g   <- fmax is specified to ignore NaN\n", fmax(0.5, nan_));
  printf("fmax(NaN, 0.5)     = %g\n", fmax(nan_, 0.5));
  printf("(NaN > 0)          = %d   <- the p_global guard: false, so it takes the else branch\n", (int)(nan_ > 0));
  printf("(NaN < 1.0)        = %d   <- the curMax guard: false, so p_local is skipped\n", (int)(nan_ < 1.0));
  printf("!(NaN > 0)         = %d   <- the NaN-safe idiom\n", (int)!(nan_ > 0));
  // does the N==1 path raise FP exceptions the tool never checks?
  feclearexcept(FE_ALL_EXCEPT);
  double p_global = 1.0, N = 1.0;
  double v = std::min(1.0, p_global + 2.5758293035489008*sqrt((p_global*(1.0-p_global))/(N-1.0)));
  int fe = fetestexcept(FE_INVALID|FE_DIVBYZERO|FE_OVERFLOW);
  printf("\nN==1, C==N path: value = %g   FE_INVALID=%d FE_DIVBYZERO=%d\n", v,
         (fe & FE_INVALID) ? 1:0, (fe & FE_DIVBYZERO) ? 1:0);
  feclearexcept(FE_ALL_EXCEPT);
  p_global = 0.5;
  v = std::min(1.0, p_global + 2.5758293035489008*sqrt((p_global*(1.0-p_global))/(N-1.0)));
  fe = fetestexcept(FE_INVALID|FE_DIVBYZERO|FE_OVERFLOW);
  printf("N==1, 0<C<N path: value = %g   FE_INVALID=%d FE_DIVBYZERO=%d\n", v,
         (fe & FE_INVALID) ? 1:0, (fe & FE_DIVBYZERO) ? 1:0);
  return 0;
}
