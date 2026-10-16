// OC-22 harness: C22's bound.  Calls the PRODUCTION headers directly so every
// number is the tool's own arithmetic, not a model of it.
//
//   info                       sizeof(long double), epsilons, ZALPHA
//   pef  <p-hex> <r> <N>       prediction_estimate_function(p, r, N)
//   cpl  <r> <N> <ldomain-hex> calc_p_local(r-1, N, ldomain): p as hex and dec, f(p)
//   pe   <C> <N> <maxrun> <k>  predictionEstimate(...) at verbose 3 (full per-predictor path)
//   comp <Xbar> <sigma> <v> <numblocks> <z>
//                              the compression estimator's step 6-9 solve, copied verbatim
//                              from compression_test.h, with z substitutable
//   compgrid <numblocks> <n>   com_exp(p) on a grid of n points in [1/64, 1]
//
// Build (macOS, the Makefile's own flags):
//   clang++ -std=c++11 -Xpreprocessor -fopenmp -I$(brew --prefix libomp)/include -O2 -ffloat-store \
//     -I/opt/homebrew/include -I/opt/homebrew/opt/openssl@3/include -Icpp/shared -Icpp/non_iid \
//     audits/2026-10-11-independent-audit/reproducers/c22_bound.cpp -o c22_bound \
//     -L/opt/homebrew/lib -L$(brew --prefix libomp)/lib -lomp -ljsoncpp -lcrypto -lbz2 -ldivsufsort -ldivsufsort64
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cfloat>
#include <cmath>
#include "utils.h"
#include "compression_test.h"

static double parse(const char *s) { return strtod(s, NULL); }  // accepts hex floats

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage: see header\n"); return 2; }
  const char *cmd = argv[1];

  if (!strcmp(cmd, "info")) {
    printf("sizeof(long double) = %zu\n", sizeof(long double));
    printf("LDBL_EPSILON = %.17Lg\n", (long double)LDBL_EPSILON);
    printf("DBL_EPSILON  = %.17g\n", DBL_EPSILON);
    printf("ZALPHA       = %.17g\n", ZALPHA);
    printf("log(0.99)    = %.17g\n", log(0.99));
    return 0;
  }
  if (!strcmp(cmd, "pef") && argc == 5) {
    double p = parse(argv[2]); long r = atol(argv[3]); long N = atol(argv[4]);
    double f = prediction_estimate_function((long double)p, r, N);
    printf("%a %.17g\n", f, f);
    return 0;
  }
  if (!strcmp(cmd, "cpl") && argc == 5) {
    long r = atol(argv[2]); long N = atol(argv[3]); double ld = parse(argv[4]);
    double p = calc_p_local(r - 1, N, ld);
    double f = (p > 0.0 && p < 1.0) ? prediction_estimate_function((long double)p, r, N) : NAN;
    printf("%a %.17g %.17g\n", p, p, f);
    return 0;
  }
  if (!strcmp(cmd, "pe") && argc == 6) {
    long C = atol(argv[2]); long N = atol(argv[3]); long maxrun = atol(argv[4]); long k = atol(argv[5]);
    double h = predictionEstimate(C, N, maxrun, k, "T", 3, "H");
    printf("H %a %.17g isnan=%d\n", h, h, (int)std::isnan(h));
    return 0;
  }
  if (!strcmp(cmd, "comp") && argc == 7) {
    // Steps 6-9 of compression_test(), verbatim apart from the z argument.
    double X = parse(argv[2]); double sigma = parse(argv[3]); long v = atol(argv[4]);
    long num_blocks = atol(argv[5]); double z = parse(argv[6]);
    const int b = 6, d = 1000; const unsigned int alph_size = 1 << b;
    double p, entEst;
    double ldomain, hdomain, lbound, hbound, lvalue, hvalue, pVal, lastP;
    int j;
    X -= z * sigma / sqrt(v);
    printf("Xprime %.17g\n", X);
    if (com_exp(1.0 / (double)alph_size, alph_size, d, num_blocks) > X) {
      ldomain = 1.0 / (double)alph_size; hdomain = 1.0;
      lbound = ldomain; hbound = hdomain;
      lvalue = DBL_INFINITY; hvalue = -DBL_INFINITY;
      p = (lbound + hbound) / 2.0;
      pVal = com_exp(p, alph_size, d, num_blocks);
      for (j = 0; j < ITERMAX; j++) {
        if (relEpsilonEqual(pVal, X, ABSEPSILON, RELEPSILON, 4)) break;
        if (X < pVal) { lbound = p; lvalue = pVal; } else { hbound = p; hvalue = pVal; }
        if (lbound >= hbound) { p = fmin(fmax(lbound, hbound), hdomain); break; }
        if (!(INCLOSEDINTERVAL(lbound, ldomain, hdomain) && INCLOSEDINTERVAL(hbound, ldomain, hdomain))) { p = ldomain; break; }
        if (!INCLOSEDINTERVAL(X, lvalue, hvalue)) { p = ldomain; break; }
        lastP = p; p = (lbound + hbound) / 2.0;
        if (!INOPENINTERVAL(p, lbound, hbound)) { p = hbound; break; }
        if (lastP == p) { p = hbound; break; }
        pVal = com_exp(p, alph_size, d, num_blocks);
        if (!INCLOSEDINTERVAL(pVal, lvalue, hvalue)) { p = hbound; break; }
      }
    } else { p = -1.0; }
    if (p > 1.0 / (double)alph_size) { entEst = -log2(p) / b; printf("found 1\n"); }
    else { p = 1.0 / (double)alph_size; entEst = 1.0; printf("found 0\n"); }
    printf("p %a %.17g\nH %a %.17g\n", p, p, entEst, entEst);
    return 0;
  }
  if (!strcmp(cmd, "compgrid") && argc == 4) {
    long num_blocks = atol(argv[2]); int n = atoi(argv[3]);
    const int d = 1000; const unsigned int alph_size = 64;
    double lo = 1.0 / 64.0, hi = 1.0;
    for (int i = 0; i <= n; i++) {
      double p = lo + (hi - lo) * (double)i / n;
      if (p >= 1.0) p = 1.0 - 1e-12;
      printf("%a %.17g %a %.17g\n", p, p, com_exp(p, alph_size, d, num_blocks), com_exp(p, alph_size, d, num_blocks));
    }
    return 0;
  }
  fprintf(stderr, "bad command\n");
  return 2;
}
