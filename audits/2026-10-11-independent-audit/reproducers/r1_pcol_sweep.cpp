// R-1's blast radius, measured through the PRODUCTION code path.
//
// An earlier version of this file re-implemented calc_proportions() and
// calc_collision_proportion() by hand and reported 117 of 255 alphabet sizes
// aborting on arm64. That was WRONG: the real tool did not abort at k = 25
// where the hand version said it would, because the compiler may contract
// `p_col += powl(p,2)` into a fused multiply-add, which is more accurate than
// the separate operations and absorbs the rounding deficit. A re-implementation
// is not the instrument; the production functions compiled with the project's
// own flags are. This version calls them.
//
// What the assert tests: by Cauchy-Schwarz sum p_i^2 >= (sum p_i)^2 / k = 1/k,
// with equality exactly at the uniform distribution, so any shortfall is
// rounding. p[] is accumulated in DOUBLE by calc_proportions() while the
// threshold 1/k is formed in LONG DOUBLE, so on a wider long double the
// threshold is the more accurate of the two and the comparison is stricter.
//
// Build with the Makefile's own flags; see the audit's log for the command.
#include <cstdio>
#include <cfloat>
#include <vector>
#include "utils.h"
#include "lrs_test.h"   // calc_collision_proportion lives here

int main(){
    printf("sizeof(long double)=%zu LDBL_MANT_DIG=%d FLT_EVAL_METHOD=%d\n",
           sizeof(long double), LDBL_MANT_DIG, (int)FLT_EVAL_METHOD);
    printf("exact balance, L chosen divisible by k and >= 1,000,000\n");
    printf("| k | L | p_col (production) | 1/k | assert |\n|---:|---:|---|---|---|\n");
    int nab = 0;
    std::vector<int> aborting;
    for(int k = 2; k <= 256; k++){
        long L = (1000000/k + 1) * (long)k;
        std::vector<uint8_t> data(L);
        for(long i = 0; i < L; i++) data[i] = (uint8_t)(i % k);
        std::vector<double> p(k, 0.0);
        calc_proportions(data.data(), p, (int)L);        // production
        long double p_col = 0.0L;
        calc_collision_proportion(p, p_col);             // production
        long double thr = 1.0L / ((long double) k);
        if(!(p_col >= thr)){
            nab++; aborting.push_back(k);
            printf("| %d | %ld | %.21Lg | %.21Lg | **ABORTS** |\n", k, L, p_col, thr);
        }
    }
    printf("\naborting alphabet sizes at exact balance: %d of 255\n", nab);
    printf("aborting k:");
    for(size_t i = 0; i < aborting.size(); i++) printf(" %d", aborting[i]);
    printf("\n");
    // Powers of two are safe by arithmetic, not by luck: 1/2^j is exactly
    // representable, so p = 1/k exactly and p_col = k*(1/k)^2 = 1/k exactly.
    printf("powers of two:");
    for(int k = 2; k <= 256; k *= 2){
        bool ab = false;
        for(size_t i = 0; i < aborting.size(); i++) if(aborting[i] == k) ab = true;
        printf(" %d=%s", k, ab ? "ABORTS" : "safe");
    }
    printf("\nwidth 1 can only give k=1 (refused earlier) or k=2, so width 1 is unaffected.\n");
    // One sample off exact balance: does it clear?
    int still = 0;
    for(size_t i = 0; i < aborting.size(); i++){
        int k = aborting[i];
        long L = (1000000/k + 1) * (long)k;
        std::vector<uint8_t> data(L);
        for(long j = 0; j < L; j++) data[j] = (uint8_t)(j % k);
        data[0] = 1;                                   // move one sample: 0 -> 1
        std::vector<double> p(k, 0.0);
        calc_proportions(data.data(), p, (int)L);
        long double p_col = 0.0L;
        calc_collision_proportion(p, p_col);
        if(!(p_col >= 1.0L/((long double)k))) still++;
    }
    printf("of those, still aborting with ONE sample moved off exact balance: %d of %d\n",
           still, nab);
    return 0;
}
