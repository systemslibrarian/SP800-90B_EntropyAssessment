// C18, measured: n_choose_2() overflows `long int` on LLP64, and the SP 800-90B
// section 5.2.5 LRS decision is then taken against a NaN.
//
// C18 was a SOURCE-ONLY candidate for a year: "n_choose_2 computes
// N = C(L-W+1, 2) in `long int`, which overflows for large L on LLP64 targets
// (Windows) and WOULD corrupt the 5.2.5 decision". The Windows platform-facts
// job measured it instead. For a standards-sized 1,000,000-sample input whose
// longest repeated substring is 40:
//
//   macOS arm64 (LP64)    Pr(X >= 1) = +0.365370   ** Passed
//   Windows MinGW (LLP64) Pr(X >= 1) = -0.000367   ** Failed
//
// Same input, same P_col, same LRS length. This program reproduces the exact
// printed value from the integer arithmetic alone, with no floating-point
// platform difference involved: `long` being 32 bits is sufficient.
//
// WHY THE DECISION IS WORSE THAN THE PRINTED PROBABILITY SUGGESTS.
// lrs_test.h takes its verdict from
//     logCollisionPower >= logl(-expm1l(logl(0.999L) / (long double)N))
// and when N wraps NEGATIVE, log(0.999)/N is positive, -expm1l() of it is
// negative, and logl() of that is NaN. Every comparison against NaN is false,
// so the test returns FAIL **unconditionally, whatever the data**.
//
// Direction: fail-closed. A wrapped N is always smaller in magnitude than the
// true N, so Pr(X >= 1) is understated and the test errs toward rejection; it
// denies an assessment, it never awards one it should not. No published figure
// is wrong. But on Windows every standards-sized assessment is affected, since
// the overflow begins around L - W + 1 = 46,342 and 1,000,000 is the normal
// input size.
//
// Not reproducible on Linux or macOS: both are LP64, where `long` is 64 bits.
// That is why the x86-64 CI job never saw it.
//
//   cc -O0 -o c18 c18_llp64_overflow.c -lm && ./c18
#include <stdio.h>
#include <stdint.h>
#include <math.h>
/* n_choose_2 exactly as cpp/shared/utils.h:997 computes it, with `long int`
   narrowed to 32 bits as LLP64 Windows defines it. */
static int32_t n_choose_2_llp64(int32_t n){ return (int32_t)(((int32_t)(n*n)) - n) / 2; }
int main(void){
  int32_t n = 999961;                       /* L - W + 1 for L=1000000, W=40 */
  long long true_N = 999961LL*999961LL; true_N = (true_N - 999961LL)/2;
  int32_t N = n_choose_2_llp64(n);
  printf("true N                      = %lld\n", true_N);
  printf("N as 32-bit long (Windows)  = %d\n", N);
  long double p_col = 0.5L; int W = 40;
  long double logCollisionPower = (long double)W * logl(p_col);
  long double cp = expl(logCollisionPower);
  printf("p_col^W                     = %.6Lg\n", cp);
  for (int i = 0; i < 2; i++) {
    long double NN = i ? (long double)N : (long double)true_N;
    long double prob = -expm1l(NN * log1pl(-cp));
    long double thr  = logl(-expm1l(logl(0.999L) / NN));
    printf("%-10s Pr(X>=1) = %Lf   threshold = %Lg   decision = %s\n",
           i ? "WINDOWS" : "CORRECT", prob, thr,
           (logCollisionPower >= thr) ? "PASS" : "FAIL");
  }
  return 0;
}
