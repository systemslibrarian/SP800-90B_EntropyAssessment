// Outside-the-battery check for SP 800-90B assessments.
//
// WHY THIS EXISTS
//
// The SP 800-90B non-IID verdict is the MINIMUM over ten estimators. On
// near-uniform binary data the Compression estimator binds (~0.855 bit/bit on a
// perfect fair coin) and the other nine sit 0.06-0.14 bit above it. A defect
// must therefore move an estimator by MORE than that estimator's headroom
// before it can change the reported figure.
//
// Measured consequence (audits/2026-10-11-independent-audit, Part 8, OC-15): a
// stream with a +40 sigma autocorrelation at lag 5000 produced a min-entropy
// figure of 0.856713, sitting inside the clean-control range [0.843936,
// 0.865774]. The only estimator that detected it (LRS, -0.0223) reads 0.973 --
// 0.116 bit above the binding minimum -- so its detection never reached the
// verdict. The battery's own sampling noise exceeded its largest true detection.
//
// This tool looks where the battery does not: linear correlation at long lags,
// and periodic lines in the spectrum. It is NOT an entropy estimator and
// produces no entropy figure. It answers one question: does this stream contain
// structure the battery's aggregation would discard?
//
// WHAT IT DOES NOT COVER -- read this before relying on it
//
//   * It finds LINEAR correlation only. A stream whose samples are pairwise
//     uncorrelated but dependent (e.g. x_i = x_{i-k} XOR x_{i-m}) has zero
//     autocorrelation at every lag and passes this check. Nonlinear structure
//     needs a different instrument.
//   * It finds correlation at the lags TESTED. Structure at a lag above --max-lag
//     is not examined and not reported as absent.
//   * A pass is not an entropy claim and not a compliance statement. It is the
//     absence of one specific kind of evidence.
//   * It says nothing about whether the source is physically sound.
//
// PRE-REGISTERED THRESHOLDS, AND HOW THEY WERE CALIBRATED
//
// Autocorrelation: Bonferroni over the number of lags tested. Sample
// autocorrelations of a white process are asymptotically independent across
// lags, so this is right and mildly conservative. Default family-wise alpha
// 0.001 over 100,000 lags gives 5.73 sigma. MEASURED on 25 independent clean
// streams (5 Mersenne Twister, 20 os.urandom, 1,000,000 samples each): max |z|
// observed 5.18, mean 4.47, sd 0.28. Zero exceedances. The 40-sigma reference
// defect (lag 5000) reads 40.21 -- seven times the threshold.
//
// Spectrum: the analytic Exp(1) periodogram model WAS MEASURED AND REJECTED,
// and the measurement is stated precisely because the rate depends on alpha:
//
//   analytic, alpha = 0.01   -> 18.5x threshold -> 2 of 25 clean streams fired
//                               (8%, against a nominal 1%)  *** TAIL IS WRONG
//   analytic, alpha = 0.001  -> 20.8x threshold -> 0 of 25 fired, but the
//                               observed clean max was 20.3x: a 2% margin
//   empirical, 30x           -> 0 of 25 fired, margin 1.48x over the clean max
//
// The rejection is of the model's TAIL SHAPE, demonstrated at alpha = 0.01, not
// merely of one threshold: 2x zero-padding correlates adjacent bins, so the
// observed maxima (13.0 .. 20.3) have a fatter tail than Exp(1) predicts and no
// alpha can be trusted to deliver the stated rate. At alpha = 0.001 it happens
// to pass on this calibration set, by 2%, which is not a margin worth relying
// on. The default is therefore the empirical 30x.
//
// It fires on narrowband modulation with enormous margin -- a period-5000 bias
// oscillation reads 8538x and is localised to 59.938 Hz, i.e. the tool recovers
// the 60 Hz mechanism directly -- and on a strong lag correlation at 44.5x.
// Shown failing: lowering it to 20x fires on 2 of 25 clean streams and to 13x
// on 24 of 25.
//
// THE TWO CHECKS ARE COMPLEMENTARY AND NEITHER ALONE SUFFICES. The weak
// long-lag reference defect (E) reads 40.21 sigma on autocorrelation but only
// 15.7x on the spectrum, BELOW the clean maximum: the spectrum does not see it.
// Conversely the spectrum localises a periodic mechanism to a frequency, which
// autocorrelation does not do as directly. Run both.
//
// EXIT STATUS
//   0  no structure found above the pre-registered threshold
//   1  STRUCTURE FOUND -- the stream carries correlation or a spectral line the
//      SP 800-90B battery may report as clean. Investigate before use.
//   2  usage or input error
//
// BUILD   c++ -std=c++11 -O2 -o outside-battery-check outside-battery-check.cpp
// USAGE   outside-battery-check [options] <file>
//         One byte per sample, values 0 or 1 (the same layout ea_non_iid reads
//         for 1-bit symbols).

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <complex>
#include <string>
#include <algorithm>

typedef std::complex<double> cplx;

// ---- iterative radix-2 FFT, in place. No external dependency on purpose: this
// ---- tool must be runnable by a consumer who did not build the rest of the repo.
static void fft(std::vector<cplx> &a, bool inverse) {
    const size_t n = a.size();
    for (size_t i = 1, j = 0; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (size_t len = 2; len <= n; len <<= 1) {
        double ang = 2.0 * M_PI / (double)len * (inverse ? 1.0 : -1.0);
        cplx wl(cos(ang), sin(ang));
        for (size_t i = 0; i < n; i += len) {
            cplx w(1.0, 0.0);
            for (size_t j = 0; j < len / 2; j++) {
                cplx u = a[i+j], v = a[i+j+len/2] * w;
                a[i+j] = u + v;
                a[i+j+len/2] = u - v;
                w *= wl;
            }
        }
    }
    if (inverse) for (size_t i = 0; i < n; i++) a[i] /= (double)n;
}

static void usage(const char *p) {
    fprintf(stderr,
      "usage: %s [options] <file>\n"
      "  --max-lag N      highest lag to test (default 100000)\n"
      "  --min-lag N      lowest lag to test (default 1)\n"
      "  --alpha A        family-wise false-positive rate for lags (default 0.001)\n"
      "  --spec-ratio R   spectral threshold, x mean power (default 30, empirical)\n"
      "  --spec-analytic  use the REJECTED Exp(1) model (8%% false positives at a=0.01)\n"
      "  --sigma S        override the computed threshold with S sigma\n"
      "  --no-correction  test at 3 sigma with NO multiple-comparison correction\n"
      "                   (demonstration only -- this WILL fire on clean data)\n"
      "  --rate HZ        sample rate, for reporting lags as frequencies\n"
      "  --no-spectrum    skip the spectral check\n"
      "  --quiet          verdict lines only\n", p);
}

int main(int argc, char **argv) {
    long maxlag = 100000, minlag = 1;
    double alpha = 0.001, forced = -1.0, rate = 0.0, specratio = 30.0;
    bool nocorr = false, spectrum = true, quiet = false;
    const char *path = NULL;

    for (int i = 1; i < argc; i++) {
        std::string s(argv[i]);
        if (s == "--max-lag" && i+1 < argc) maxlag = atol(argv[++i]);
        else if (s == "--min-lag" && i+1 < argc) minlag = atol(argv[++i]);
        else if (s == "--alpha" && i+1 < argc) alpha = atof(argv[++i]);
        else if (s == "--spec-ratio" && i+1 < argc) specratio = atof(argv[++i]);
        else if (s == "--spec-analytic") specratio = -1.0;
        else if (s == "--sigma" && i+1 < argc) forced = atof(argv[++i]);
        else if (s == "--no-correction") nocorr = true;
        else if (s == "--rate" && i+1 < argc) rate = atof(argv[++i]);
        else if (s == "--no-spectrum") spectrum = false;
        else if (s == "--quiet") quiet = true;
        else if (s == "-h" || s == "--help") { usage(argv[0]); return 2; }
        else if (s[0] == '-') { fprintf(stderr, "unknown option %s\n", argv[i]); return 2; }
        else path = argv[i];
    }
    if (!path) { usage(argv[0]); return 2; }

    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return 2; }
    std::vector<unsigned char> raw;
    { unsigned char buf[65536]; size_t g;
      while ((g = fread(buf, 1, sizeof buf, f)) > 0) raw.insert(raw.end(), buf, buf+g); }
    fclose(f);

    const long N = (long)raw.size();
    if (N < 1000) { fprintf(stderr, "need at least 1000 samples, got %ld\n", N); return 2; }
    for (long i = 0; i < N; i++)
        if (raw[i] > 1) { fprintf(stderr,
            "%s: sample %ld is %u; this tool reads one byte per sample, values 0/1\n",
            path, i, raw[i]); return 2; }

    if (maxlag >= N/2) maxlag = N/2 - 1;        // keep >= N/2 pairs at every lag
    if (minlag < 1) minlag = 1;
    if (minlag > maxlag) { fprintf(stderr, "empty lag range\n"); return 2; }

    // ---- pre-registered threshold.
    // Sample autocorrelations of a white process are asymptotically independent
    // across lags, so Bonferroni over the number of lags tested is the right
    // correction and is mildly conservative. Two-sided per-lag alpha is
    // alpha/L; the z threshold inverts the normal tail.
    const long L = maxlag - minlag + 1;
    double thresh;
    if (forced > 0)      thresh = forced;
    else if (nocorr)     thresh = 3.0;
    else {
        double per = alpha / (double)L / 2.0;           // two-sided
        // invert the upper normal tail by bisection on erfc
        double lo = 0.0, hi = 12.0;
        for (int it = 0; it < 200; it++) {
            double mid = 0.5*(lo+hi);
            if (0.5*erfc(mid/sqrt(2.0)) > per) lo = mid; else hi = mid;
        }
        thresh = 0.5*(lo+hi);
    }

    double mean = 0.0;
    for (long i = 0; i < N; i++) mean += raw[i] ? 1.0 : -1.0;
    mean /= (double)N;

    size_t M = 1; while (M < (size_t)(2*N)) M <<= 1;
    std::vector<cplx> a(M, cplx(0.0, 0.0));
    for (long i = 0; i < N; i++) a[i] = cplx((raw[i] ? 1.0 : -1.0) - mean, 0.0);

    fft(a, false);
    std::vector<double> power(M);
    for (size_t i = 0; i < M; i++) power[i] = std::norm(a[i]);

    // ---- spectral check, from the same transform.
    // For white input the periodogram bins are ~Exp(1) after normalising by the
    // mean, so P(max over K bins > t) ~= K*exp(-t); invert for the threshold.
    int spec_hits = 0; double spec_top = 0.0; size_t spec_bin = 0;
    double spec_thresh = 0.0;
    if (spectrum) {
        const size_t K = M/2;                     // positive frequencies
        double tot = 0.0;
        for (size_t i = 1; i <= K; i++) tot += power[i];
        double mp = tot / (double)K;
        // Analytic Exp(1) model, retained only to report alongside the
        // empirical threshold that replaced it. Measured false-positive rate
        // 8% on 25 clean streams; see the header.
        double analytic = log((double)K / alpha);
        spec_thresh = (specratio > 0.0) ? specratio : analytic;
        for (size_t i = 1; i <= K; i++) {
            double r = power[i] / mp;
            if (r > spec_top) { spec_top = r; spec_bin = i; }
            if (r > spec_thresh) spec_hits++;
        }
    }

    for (size_t i = 0; i < M; i++) a[i] = cplx(power[i], 0.0);
    fft(a, true);
    const double c0 = a[0].real();
    if (c0 <= 0.0) { fprintf(stderr, "degenerate input (zero variance)\n"); return 2; }

    // ---- scan the lag range
    long hits = 0, worst_lag = 0; double worst_z = 0.0;
    std::vector< std::pair<double,long> > top;
    for (long k = minlag; k <= maxlag; k++) {
        double r = a[k].real() / c0;
        double z = r * sqrt((double)(N - k));
        if (fabs(z) > fabs(worst_z)) { worst_z = z; worst_lag = k; }
        if (fabs(z) > thresh) { hits++; top.push_back(std::make_pair(fabs(z), k)); }
    }
    std::sort(top.rbegin(), top.rend());

    if (!quiet) {
        printf("file            %s\n", path);
        printf("samples         %ld\n", N);
        printf("lags tested     %ld .. %ld  (L = %ld)\n", minlag, maxlag, L);
        if (nocorr)
            printf("threshold       3.000 sigma  *** NO CORRECTION -- expect ~%.0f false hits ***\n",
                   (double)L * erfc(3.0/sqrt(2.0)));
        else if (forced > 0)
            printf("threshold       %.3f sigma  (forced)\n", thresh);
        else
            printf("threshold       %.3f sigma  (Bonferroni, family-wise alpha = %g over %ld lags)\n",
                   thresh, alpha, L);
        printf("largest |z|     %.2f sigma at lag %ld", fabs(worst_z), worst_lag);
        if (rate > 0.0) printf("  (= %.3f Hz)", rate / (double)worst_lag);
        printf("\n");
        printf("lags over thr   %ld\n", hits);
        for (size_t i = 0; i < top.size() && i < 10; i++) {
            printf("   lag %-8ld |z| = %8.2f", top[i].second, top[i].first);
            if (rate > 0.0) printf("   %.3f Hz", rate / (double)top[i].second);
            printf("\n");
        }
        if (spectrum) {
            printf("spectrum        top line %.1fx mean power at bin %zu", spec_top, spec_bin);
            if (rate > 0.0 && spec_bin > 0)
                printf("  (= %.3f Hz)", rate * (double)spec_bin / (double)M);
            printf("\n");
            if (specratio > 0.0)
                printf("                threshold %.1fx  (EMPIRICAL: 1.48x the observed clean max of\n"
                       "                20.3 over 25 clean streams. The analytic Exp(1) model was\n"
                       "                rejected: at alpha=0.01 it thresholds at 18.5x and fired on\n"
                       "                2 of those 25.) lines over: %d\n",
                       spec_thresh, spec_hits);
            else
                printf("                threshold %.1fx  (analytic Exp(1), alpha = %g over %zu bins)\n"
                       "                *** REJECTED MODEL: 8%% measured false positives at alpha=0.01 ***\n"
                       "                lines over: %d\n",
                       spec_thresh, alpha, M/2, spec_hits);
        }
    }

    bool found = (hits > 0) || (spectrum && spec_hits > 0);
    if (found) {
        printf("VERDICT         STRUCTURE FOUND -- %ld lag(s) and %d spectral line(s) above threshold.\n",
               hits, spec_hits);
        printf("                The SP 800-90B battery may report this stream as clean:\n");
        printf("                its verdict is a minimum, and a detection that is not the\n");
        printf("                minimum does not reach the figure. Investigate before use.\n");
        return 1;
    }
    printf("VERDICT         no linear correlation or spectral line above threshold\n");
    printf("                NOT an entropy claim. Linear structure only, lags %ld..%ld only.\n",
           minlag, maxlag);
    return 0;
}
