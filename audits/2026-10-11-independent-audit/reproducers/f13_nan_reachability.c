/* F13 REACHABILITY, not repair.
 *
 * utils.h:1211   if(p_global > 0) p_globalPrime = min(1.0, p_global + ZALPHA*sqrt((p_global*(1.0-p_global))/((double)N-1.0)));
 * most_common.h:26 ubound = min(1.0, pmax + ZALPHA*sqrt(pmax*(1.0-pmax)/(len-1.0)));
 *
 * The question is whether a NaN can reach the min() at all on a supported
 * path, because min(1.0, NaN) returns 1.0 only by argument order and a
 * reviewer would read swapping them as cosmetic. Reachability first.
 */
#include <stdio.h>
#include <math.h>
#define ZALPHA 2.5758293035489008
static double expr(double p, double N) {
    return p + ZALPHA * sqrt((p * (1.0 - p)) / (N - 1.0));
}
static int scan(const char *label, double Nmin, int allow_p_eq_1, long *checked) {
    /* C is an integer count in [0, N], so p = C/N takes only those values.
     * Sample the extremes exactly and a fine grid between. */
    const double Ns[] = { Nmin, Nmin + 1, 1e6, 8e6, 1e9, 2147483647.0 };
    int nan_seen = 0;
    for (unsigned i = 0; i < sizeof(Ns)/sizeof(Ns[0]); i++) {
        double N = Ns[i];
        if (N < Nmin) continue;
        /* exact boundaries: the smallest positive p (C=1) and p=1 (C=N) */
        double ps[4098]; int np = 0;
        ps[np++] = 1.0 / N;
        if (allow_p_eq_1) ps[np++] = 1.0;
        ps[np++] = (N - 1.0) / N;
        for (int j = 1; j < 4095; j++) ps[np++] = (double) j / 4096.0;
        for (int j = 0; j < np; j++) {
            double p = ps[j];
            if (!(p > 0.0)) continue;            /* the guard at the site */
            double v = expr(p, N);
            (*checked)++;
            if (isnan(v)) {
                if (!nan_seen) printf("  %-44s NaN at p=%.17g N=%.17g\n", label, p, N);
                nan_seen = 1;
            }
        }
    }
    if (!nan_seen) printf("  %-44s no NaN\n", label);
    return nan_seen;
}
int main(void) {
    long checked = 0;
    printf("SUPPORTED PATH (N >= 1,000,000 - 1; MIN_SIZE is 1000000):\n");
    int sup = scan("supported: N >= 999999, p in (0,1]", 999999.0, 1, &checked);
    printf("\nLIVE-SENSITIVITY: lift the size constraint and the probe must FIRE.\n");
    int un1 = scan("unsupported: N may be 1, p=1 allowed", 1.0, 1, &checked);
    int un2 = scan("unsupported: N may be 2, p=1 allowed", 2.0, 1, &checked);
    printf("\n  %ld evaluations.\n", checked);
    printf("  supported path NaN: %s\n", sup ? "YES" : "no");
    printf("  probe can detect a NaN at all: %s\n", (un1 || un2) ? "YES (it fired below the size floor)"
                                                                : "NO -- THE PROBE IS BLIND, nothing is concluded");
    if (!sup && (un1 || un2)) { printf("\n  => UNREACHABLE on supported paths, and the probe is not blind.\n"); return 0; }
    if (sup) { printf("\n  => REACHABLE on a supported path: that is the finding.\n"); return 1; }
    printf("\n  => INCONCLUSIVE: the probe never produced a NaN anywhere, so its silence means nothing.\n");
    return 2;
}
