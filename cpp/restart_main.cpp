/* VERSION information is kept in utils.h. Please update when a new version is released */

#include "shared/utils.h"
#include "shared/most_common.h"
#include "shared/lrs_test.h"
#include "non_iid/non_iid_test_run.h"
#include "iid/iid_test_run.h"
#include "shared/TestRunUtils.h"
#include "non_iid/collision_test.h"
#include "non_iid/lz78y_test.h"
#include "non_iid/multi_mmc_test.h"
#include "non_iid/lag_test.h"
#include "non_iid/multi_mcw_test.h"
#include "non_iid/compression_test.h"
#include "non_iid/markov_test.h"
#include "iid/chi_square_tests.h"
#include "iid/permutation_tests.h"

#include <cstdint>
#include <cerrno>
#include <getopt.h>
#include <limits.h>
#include <iostream>
#include <fstream>

//Each test has a targeted chance of roughly 0.000005, and we need to witness at least 5 failures, so this should be no less than 1000000
#define DEFAULT_SIMULATION_ROUNDS 5000000UL

// C23 (audit 2026-10-11; superseded reading in OC-27/OC-29, corrected in OC-30).
//
// SP 800-90B 3.1.4.3 step 5 PRINTS the tail of a single Binomial(1000, p),
// p = 2^-H_I. But the value tested, X_max, is the largest count of the
// ROW/COLUMN-SPECIFIC most likely symbol -- the maximum cell count of a
// multinomial -- which is stochastically larger than any one cell's count. So
// the printed formula is not the probability of the event being tested, and a
// cutoff computed from it REJECTS CORRECTLY-OPERATING SOURCES: computed in
// OC-30, the false-reject rate of the printed cutoff on full-entropy data is
// 1.6% at 1 bit, 3.3% at 2, 10.7% at 4 and 82.5% at 8, against the 1% the
// standard targets. Hill/UL formal comments on SP 800-90B (final, v1.9,
// 2019-12-12, www.untruth.org/~josh/sp80090b/) comment 3.a names the same
// mechanism; upstream issue #56 asks for a simulated cutoff for this reason,
// which is why upstream simulates. THE DEFECT IS THE SILENCE: nothing upstream
// records that the implementation deliberately departs from the printed text.
//
// This computes the exact cutoff for the statistic the test actually forms --
// the first of the two exact methods Hill names (Levin, "A Representation for
// Multinomial Cumulative Distribution Functions", Ann. Statist. 9(5), 1981) --
// which is better than both the printed formula and a simulation. For any s>0,
//   P(all cells <= m) = n!/(s^n e^-s) * P(W = n) * prod_j P(Poisson(s p_j) <= m)
// where W sums independent Poisson(s p_j) each conditioned on being <= m.
// Every factor is a probability or a log-domain scalar, so nothing underflows.
// Worst case per Hill 3.a.i, matching the k_effective upstream already used:
// floor(1/p) symbols at probability p plus one holding the remainder.
//
// Anchored in OC-30 against Hill's published Table 3 and against upstream's own
// 5,000,000-round simulation; validated against brute-force enumeration; the
// 32 pinned cutoffs are checked in cpp/selftest/regression-restart.sh. The
// deciding cutoff and the printed-formula cutoff are BOTH reported, so the gap
// and the figure the verdict used are both visible.
//
// Audit-only build knobs, for the matrix that shows each state failing.
// EA_RESTART_WITHOUT_C23_FIX    decide on upstream's simulated cutoff.
// EA_RESTART_C23_PRINTED_BINOMIAL  decide on the printed formula -- the
//     SUPERSEDED repair of commit a5005bd, kept reproducible because it is the
//     state that over-rejects and the record has to be able to show it.
// EA_RESTART_WITHOUT_C16_FIX    restore the old H_I parse.
// All three are for the matrix
// (audits/2026-10-11-independent-audit/reproducers/c16-c23-matrix.sh). No
// Makefile target sets either.
#define RESTART_TRIALS 1000

// SP 800-90B 3.1.4.3 step 5 exactly as printed. Reported as the conformance
// figure; NOT the deciding cutoff, for the reason above.
static int printedBinomialBound(double alpha, double H_I) {
    const int n = RESTART_TRIALS;
    const long double p = powl(2.0L, -(long double) H_I);
    if (p >= 1.0L) return n;
    const long double q = 1.0L - p;
    const long double lgn = lgammal((long double) n + 1.0L);
    long double tail = 0.0L;
    for (int x = n; x >= 0; x--) {
        tail += expl(lgn - lgammal((long double) x + 1.0L) - lgammal((long double) (n - x) + 1.0L)
                     + (long double) x * logl(p) + (long double) (n - x) * logl(q));
        if (tail >= (long double) alpha) return x;
    }
    return 0;
}

// Normalised pmf of Poisson(lam) truncated to 0..m, and log P(Poisson(lam) <= m).
static void truncPoisson(long double lam, int m, vector<long double> &pmf, long double &logTail) {
    pmf.assign(m + 1, 0.0L);
    if (lam <= 0.0L) { pmf[0] = 1.0L; logTail = 0.0L; return; }
    const long double loglam = logl(lam);
    long double mx = -LDBL_MAX;
    vector<long double> lg(m + 1);
    for (int i = 0; i <= m; i++) { lg[i] = (long double) i * loglam - lgammal((long double) i + 1.0L); if (lg[i] > mx) mx = lg[i]; }
    long double tot = 0.0L;
    for (int i = 0; i <= m; i++) { pmf[i] = expl(lg[i] - mx); tot += pmf[i]; }
    for (int i = 0; i <= m; i++) pmf[i] /= tot;
    logTail = -lam + mx + logl(tot);           // e^-lam * sum_i lam^i/i!
}

static void convTrunc(const vector<long double> &a, const vector<long double> &b, int limit, vector<long double> &out) {
    out.assign(limit + 1, 0.0L);
    for (size_t i = 0; i < a.size() && (int) i <= limit; i++) {
        if (a[i] == 0.0L) continue;
        const int jmax = min((int) b.size() - 1, limit - (int) i);
        for (int j = 0; j <= jmax; j++) out[i + j] += a[i] * b[j];
    }
}

// P(every cell count <= m) for the worst-case configuration at this H_I.
static long double maxCellCdf(double H_I, int m) {
    const int n = RESTART_TRIALS;
    if (m >= n) return 1.0L;
    if (m < 0) return 0.0L;
    const long double p = powl(2.0L, -(long double) H_I);
    if (p >= 1.0L) return 0.0L;
    const long long kfloor = (long long) floorl(1.0L / p);
    const long double rem = 1.0L - (long double) kfloor * p;
    const long double s = (long double) n;
    const int mm = min(m, n);

    vector<long double> base, dist(1, 1.0L), tmp;
    long double logp = 0.0L, logTail = 0.0L;
    truncPoisson(s * p, mm, base, logTail);
    long double logprod = (long double) kfloor * logTail;
    for (long long e = kfloor; e > 0; e >>= 1) {       // binary powering
        if (e & 1) { convTrunc(dist, base, n, tmp); dist.swap(tmp); }
        if (e >> 1) { convTrunc(base, base, n, tmp); base.swap(tmp); }
    }
    if (rem > 1e-15L) {
        vector<long double> remPmf;
        truncPoisson(s * rem, mm, remPmf, logp);
        convTrunc(dist, remPmf, n, tmp); dist.swap(tmp);
        logprod += logp;
    }
    if ((int) dist.size() <= n || dist[n] <= 0.0L) return 0.0L;
    const long double logpre = lgammal((long double) n + 1.0L) - (long double) n * logl(s) + s;
    const long double r = expl(logpre + logl(dist[n]) + logprod);
    return (r > 1.0L) ? 1.0L : r;
}

// The deciding cutoff: smallest m with P(max <= m) >= 1 - alpha, so counts equal
// to it pass and larger ones fail -- upstream's own stated convention.
static int exactMultinomialMaxBound(double alpha, double H_I) {
    int m = printedBinomialBound(alpha, H_I);   // the max is never below one cell's quantile
    while (m < RESTART_TRIALS && maxCellCdf(H_I, m) < 1.0L - (long double) alpha) m++;
    return m;
}

// C16 (OC-11/OC-28): the H_I argument. Grammar is a plain decimal -- digits,
// optional fraction, optional exponent -- optionally followed by "/symbol" or
// "/bit". Hex floats, inf, nan, leading whitespace and trailing junk are
// refused. For a symbol wider than one bit the scale MUST be stated, because a
// per-bit figure (0.5) and a per-symbol one (4.0) are both in range and the
// tool cannot tell from the number which was meant; a wrong-scale H_I passes
// every range check and yields a wrong cutoff silently.
enum HIUnit { HI_UNIT_NONE, HI_UNIT_SYMBOL, HI_UNIT_BIT };
static bool parseHIArgument(const char *arg, double &value, HIUnit &unit, const char **why) {
    const char *s = arg;
    size_t n = 0;
    *why = "";
    while (s[n] >= '0' && s[n] <= '9') n++;
    size_t intDigits = n;
    size_t fracDigits = 0;
    if (s[n] == '.') { n++; while (s[n] >= '0' && s[n] <= '9') { n++; fracDigits++; } }
    if (intDigits == 0 && fracDigits == 0) { *why = "not a decimal number"; return false; }
    if (s[n] == 'e' || s[n] == 'E') {
        size_t m = n + 1;
        if (s[m] == '+' || s[m] == '-') m++;
        size_t expDigits = 0;
        while (s[m] >= '0' && s[m] <= '9') { m++; expDigits++; }
        if (expDigits == 0) { *why = "incomplete exponent"; return false; }
        n = m;
    }
    unit = HI_UNIT_NONE;
    if (strcmp(s + n, "/symbol") == 0) unit = HI_UNIT_SYMBOL;
    else if (strcmp(s + n, "/bit") == 0) unit = HI_UNIT_BIT;
    else if (s[n] != '\0') { *why = "trailing characters (only '/symbol' or '/bit' may follow the number)"; return false; }
    char *end = NULL;
    errno = 0;
    value = strtod(std::string(s, n).c_str(), &end);
    if (errno == ERANGE) { *why = "out of range for a double (underflow or overflow)"; return false; }
    if (!std::isfinite(value)) { *why = "not finite"; return false; }
    return true;
}

[[ noreturn ]] void print_usage() {
    printf("Usage is: ea_restart [-i|-n] [-v] [-q] [-s <simulation count>] <file_name> [bits_per_symbol] <H_I>\n\n");
    printf("\t <file_name>: Must be relative path to a binary file with at least 1 million entries (samples),\n");
    printf("\t and in the \"row dataset\" format described in SP800-90B Section 3.1.4.1.\n");
    printf("\t [bits_per_symbol]: Must be between 1-8, inclusive.\n");
    printf("\t <H_I>: Initial entropy estimate, 0 < H_I <= bits_per_symbol. For a symbol wider than one bit\n");
    printf("\t        the scale must be stated: '<value>/symbol' (as assessed) or '<value>/bit' (multiplied\n");
    printf("\t        by bits_per_symbol). A bare number is accepted only for 1-bit symbols.\n");
    printf("\t [-i|-n]: '-i' for IID data, '-n' for non-IID data. Non-IID is the default.\n");
    printf("\t -s <simulation count>: Accepted for compatibility and ignored: the sanity-check cutoff is\n");
    printf("\t        computed exactly from SP 800-90B 3.1.4.3 step 5, not simulated.\n");
    printf("\t -v: Optional verbosity flag for more output.\n");
    printf("\t -q: Quiet mode, less output to screen.\n");
    printf("\n");
    printf("\t Restart samples are assumed to be packed into 8-bit values, where the rightmost 'bits_per_symbol'\n");
    printf("\t bits constitute the sample.\n");
    printf("\n");
    printf("\t This program performs restart testing as described in Restart Tests (Section 3.1.4). The data\n");
    printf("\t consists of 1000 restarts, each with 1000 samples. The data is converted to rows and columns\n");
    printf("\t as described Section 3.1.4.1. The sanity check (Section 3.1.4.3) and the validation test\n");
    printf("\t (Section 3.1.4.2) are performed on this data.\n");
    printf("\n");
    printf("\t If the restart data passes the sanity check and validation test, this program returns\n");
    printf("\t min(H_r, H_c, H_I), which is either the validated entropy assessment or used to derive\n");
    printf("\t 'h_in' if conditioning is used (Section 3.1.5).\n");
    printf("\n");
    printf("\t --version: Prints tool version information");
    printf("\n");
    exit(-1);
}

// Here, we simulate a "worst case" for the restart sanity test. This is "worst case" in the sense that the adopted distribution
// results in the largest acceptable collision bound for a given assessed entropy level, so if a data sample fails this
// test, it is likely to indicate an underlying problem.
//
// This "worst case" uses the "inverted near-uniform" family (see Hagerty-Draper "Entropy Bounds and Statistical Tests" for
// a full definition of this distribution and justification for its use here).
//
// This distribution has as many maximal probability symbols as possible (each occurring with probability p), and possibly one
// additional symbol that contains all the residual probability.
//
// If the probability for the most likely symbol is p, then there are floor(1/p) most likely symbols,
// each occurring with probability p and possibly one additional symbol that has all the remaining (1 - p floor(1/p)) chance.
// In this code, we generate a random unit value in the range [0, 1), and we need to map this to one of the ceil(1/p) possible
// output symbols.
//
// Note that the function x -> floor(x/p) yields
// [0p,1p) -> 0
// [1p, 2p) -> 1
// [2p, 3p) -> 2
// ...
// [(floor(1/p)-1)p, floor(1/p)p) -> floor(1/p)-1
// [ floor(1/p)p, 1 ) -> floor(1/p)
//
// As such, each of the first floor(1/p) symbols (0 through floor(1/p)-1) have probability p of occurring, and
// the symbol floor(1/p) has probability 1-floor(1/p)p of occurring, as desired.
//
// Note that if floor(1/p) = ceil(1/p) = 1/p, then there is no "residual" symbol, only 1/p most likely symbols.
//
// The array is 0-indexed, so we can use this map to establish the index directly.
uint16_t simulateCount(int k_effective, double p, uint64_t *xoshiro256starstarState) {
    uint16_t counts[256] = {0};
    uint16_t max_count = 0;

    for (int j = 0; j < 1000; j++) {
        // Note that (int)floor(randomUnit(xoshiro256starstarState) / p) is the index map discussed in the above comments.
        counts[(int)floor(randomUnit(xoshiro256starstarState) / p)]++;
    }

    // We could have tracked this during the above loop, but that would yield 1000 comparisons,
    // rather than k_effective (<= 256) comparisons, as here.
    for (int j = 0; j < k_effective; j++) {
        if (max_count < counts[j]) max_count = counts[j];
    }

    return max_count;
}

//This returns the bound (cutoff) for the test. Counts equal to this value should pass.
//Larger values should fail.

int simulateBound(double alpha, int k, double H_I, unsigned long int simulation_rounds) {
    uint64_t xoshiro256starstarMainSeed[4];
    uint16_t *results;
    long int returnIndex;
    double p;
    int k_effective;
    int returnValue;

    assert((k > 1) && (k <= 256));

    // A few constraints:
    // This array may be very large (many gigabytes) so can't go onto the stack
    // Many of the C++ STL-derived types are not thread safe. Our mode of access is
    // quite straight forward, but there are clearly issues in some cases.
    // In C, calloc is possibly faster, but this is probably the best we can do
    // using somewhat idiomatic C++.
    results = new uint16_t[simulation_rounds];
    memset(results, 0, sizeof(uint16_t)*simulation_rounds);

    //The probability of the most likely symbol (MLS) only needs to be calculated once...
    p = pow(2.0, -H_I);

    //if floor(1/p) = ceil(1/p) = 1/p, then there are exactly that many symbols (e.g., p=1/2, then there are 2 symbols expected).
    //If ceil(1/p) > 1/p, then ceil(1/p) = floor(1/p)+1, that is there are the floor(1/p) most likely symbols, and then the extra
    //symbol that fills the rest of the space (with probability < p).
    k_effective = ceil(1.0 / p);
    assert(k_effective <= k);

    seed(xoshiro256starstarMainSeed);

#pragma omp parallel
    {
        uint64_t xoshiro256starstarSeed[4];

        memcpy(xoshiro256starstarSeed, xoshiro256starstarMainSeed, sizeof (xoshiro256starstarMainSeed));
        //Cause the RNG to jump omp_get_thread_num() * 2^128 calls
        xoshiro_jump(omp_get_thread_num(), xoshiro256starstarSeed);

#pragma omp for
        for (unsigned long int i = 0; i < simulation_rounds; i++) {
            results[i] = simulateCount(k_effective, p, xoshiro256starstarSeed);
        }
    }

    sort(results, results+simulation_rounds);
    assert((results[0] >= (1000 / k)) && (results[0] <= 1000));
    assert((results[simulation_rounds - 1] >= (1000 / k)) && (results[simulation_rounds - 1] <= 1000));

    returnIndex = ((size_t) floor((1.0 - alpha) * ((double) simulation_rounds))) - 1;
    assert((returnIndex >= 0) && (returnIndex < simulation_rounds));

    returnValue = (int)results[returnIndex];

    // C-01: results is allocated with new[] above and must be released with
    // the matching array form.  Scalar delete is undefined behaviour and was
    // sanitizer-reproducible on a standards-sized 1000 x 1000 restart input.
    delete[] results;

    return returnValue;
}

int main(int argc, char* argv[]) {
    bool iid;
    int verbose = 1; //verbose 0 is for JSON output, 1 is the normal mode, 2 is the NIST tool verbose mode, and 3 is for extra verbose output
    bool quietMode = false;
    char *file_path;
    int r = 1000, c = 1000;
    int counts[256];
    unsigned long int simulation_rounds = DEFAULT_SIMULATION_ROUNDS;
    int X_cutoff;
    int X_cutoff_printed;
    int i, j;
    int X_i, X_r, X_c, X_max;
    double H_I, H_r, H_c, alpha, ret_min_entropy;
	double rawmean, translated_symbol_median;
    uint8_t *rdata, *cdata, *crawdata;
    unsigned long int inul;
    data_t data;
    int opt;
    bool iid_test_suite_pass = true;

    iid = false;
    data.word_size = 0;

    bool jsonOutput = false;
    string timestamp = getCurrentTimestamp();
    string outputfilename = timestamp + ".json";
    string commandline = recreateCommandLine(argc, argv);

    for (int i = 0; i < argc; i++) {
        std::string Str = std::string(argv[i]);
        if ("--version" == Str) {
            printVersion("restart");
            exit(0);
        }
    }

    while ((opt = getopt(argc, argv, "invqo:s:")) != -1) {
        switch (opt) {
            case 'i':
                iid = true;
                break;
            case 'n':
                iid = false;
                break;
            case 'v':
                verbose++;
                break;
            case 'q':
                quietMode = true;
                break;
            case 'o':
                jsonOutput = true;
                outputfilename = optarg;
                break;
            case 's':
                if (!parse_unsigned_decimal(optarg, inul)) {
                    printf("Simulation count must be an unsigned decimal integer.\n");
                    print_usage();
                }
		if((inul == 0) || (inul == ULONG_MAX) || (inul < simulation_rounds)) {
                    print_usage();
                } else {
                    simulation_rounds = inul;
                }
                break;
            default:
                print_usage();
        }
    }

    argc -= optind;
    argv += optind;

    // Parse args
    if ((argc != 3) && (argc != 2)) {
        printf("Incorrect usage.\n");
        print_usage();
    }

    // get filename
    file_path = argv[0];
    argv++;
    argc--;

    if (quietMode) verbose = 0;

    IidTestRun testRunIid;
    testRunIid.type = "Restart";
    testRunIid.timestamp = timestamp;
    testRunIid.filename = file_path;
    testRunIid.commandline = commandline;

    NonIidTestRun testRunNonIid;
    testRunNonIid.type = "Restart";
    testRunNonIid.timestamp = timestamp;
    testRunNonIid.filename = file_path;
    testRunNonIid.commandline = commandline;

    if (argc == 2) {
        // get bits per word
        if (!parse_unsigned_decimal(argv[0], inul) || inul < 1 || inul > 8) {
            printf("Invalid bits per symbol: expected an unsigned decimal integer from 1 through 8.\n");
            if (jsonOutput) {
                if (iid) {
                    testRunIid.errorLevel = -1;
                    testRunIid.errorMsg = "Invalid bits per symbol: expected an unsigned decimal integer from 1 through 8.";
                    writeJsonReport(outputfilename, testRunIid.GetAsJson());
                } else {
                    testRunNonIid.errorLevel = -1;
                    testRunNonIid.errorMsg = "Invalid bits per symbol: expected an unsigned decimal integer from 1 through 8.";
                    writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
                }
            }

            print_usage();
        }
        data.word_size = (int)inul;
        argv++;
        argc--;
    }

    // get H_I
    //
    // atof() cannot report a failure: it returns 0.0 for text it cannot parse,
    // so "abc" was accepted as H_I = 0 and the run reported a verdict for an
    // entropy the operator never supplied. Worse, it accepts "nan" and "inf".
    // Every comparison with NaN is false, so a NaN H_I passes both the
    // "H_I < 0" check here and the "H_I > word_size" check further down. It
    // then reaches p = pow(2.0, -H_I), which is NaN, and the index expression
    // (int)floor(randomUnit(...) / p) in simulateCount() and simulateBound()
    // converts that NaN to int. That conversion is undefined behaviour and the
    // result indexes counts[] out of bounds; the observed effect is a crash.
    //
    // Parse strictly: the whole argument must be consumed and the value must
    // be finite. C16: the grammar is explicit (no hex floats, no whitespace),
    // underflow/overflow is refused, the value must be positive, and for a
    // multi-bit symbol the scale must be stated (resolved after the data is
    // read, when bits_per_symbol is known).
    HIUnit H_I_unit = HI_UNIT_NONE;
    {
        const char *why = "";
        bool ok = parseHIArgument(argv[0], H_I, H_I_unit, &why);
#ifdef EA_RESTART_WITHOUT_C16_FIX
        // pre-repair parse: strtod, whole argument consumed, finite
        {
            char *H_I_end = NULL;
            errno = 0;
            H_I = strtod(argv[0], &H_I_end);
            ok = !((H_I_end == argv[0]) || (*H_I_end != '\0') || !std::isfinite(H_I));
            H_I_unit = HI_UNIT_SYMBOL;
        }
#endif
        if (!ok) {
            printf("H_I must be a finite decimal number: '%s' (%s).\n", argv[0], why);

            if (jsonOutput) {
                string msg = "H_I must be a finite decimal number: '" + string(argv[0]) + "' (" + string(why) + ").";
                if (iid) {
                    testRunIid.errorLevel = -1;
                    testRunIid.errorMsg = msg;
                    writeJsonReport(outputfilename, testRunIid.GetAsJson());
                } else {
                    testRunNonIid.errorLevel = -1;
                    testRunNonIid.errorMsg = msg;
                    writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
                }
            }

            print_usage();
        }
    }

#ifdef EA_RESTART_WITHOUT_C16_FIX
    if (H_I < 0) {
#else
    if (H_I <= 0) {
#endif
        printf("H_I %g must be greater than zero: an initial estimate of no entropy makes both restart gates vacuous.\n", H_I);
        if (jsonOutput) {
            string msg = "H_I must be greater than zero: " + std::to_string(H_I) + ".";
            if (iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = msg;
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = msg;
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }

        print_usage();
    }

    int bitsPerSymbolGiven = data.word_size;
    if (!read_file(file_path, &data, &testRunNonIid)) {
        printf("Error reading file.\n");

        if (jsonOutput) {
            if (iid) {
                // The error level used to be set on testRunNonIid while
                // testRunIid was the object written, so an -i run that could
                // not read its input produced a report saying errorLevel 0.
                // read_file() also reports into testRunNonIid whatever the
                // mode, so its message is carried across here rather than
                // lost.
                testRunIid.errorLevel = -1;
                if (testRunIid.errorMsg.empty()) testRunIid.errorMsg = testRunNonIid.errorMsg;
                if (testRunIid.errorMsg.empty()) testRunIid.errorMsg = "Error reading file.";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                if (testRunNonIid.errorMsg.empty()) testRunNonIid.errorMsg = "Error reading file.";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }

        print_usage();
    }

    testRunIid.sha256 = testRunNonIid.sha256;
    testRunIid.assessedSampleCount = testRunNonIid.assessedSampleCount;
    testRunIid.bitsPerSymbol = data.word_size;
    testRunIid.bitsPerSymbolInferred = (bitsPerSymbolGiven == 0);
    testRunNonIid.bitsPerSymbol = data.word_size;
    testRunNonIid.bitsPerSymbolInferred = (bitsPerSymbolGiven == 0);
    if (verbose > 1) printf("Loaded file: '%s' (SHA-256 hash %s of assessed bytes)\n", file_path, testRunNonIid.sha256.c_str());

    if (verbose > 1) printf("Loaded %ld samples made up of %d distinct %d-bit-wide symbols.\n", data.len, data.alph_size, data.word_size);

#ifndef EA_RESTART_WITHOUT_C16_FIX
    // C16: resolve the stated scale now that the symbol width is known.
    if (H_I_unit == HI_UNIT_BIT) {
        H_I = H_I * data.word_size;
    } else if (H_I_unit == HI_UNIT_NONE && data.word_size > 1) {
        printf("H_I '%s' must state its scale for a %d-bit symbol: '%s/symbol' (the per-symbol estimate) or '%s/bit' (per bit, multiplied by %d). A bare number is accepted only for 1-bit symbols, where the two coincide.\n",
               argv[0], data.word_size, argv[0], argv[0], data.word_size);
        if (jsonOutput) {
            string msg = "H_I '" + string(argv[0]) + "' must state its scale ('/symbol' or '/bit') for a " + std::to_string(data.word_size) + "-bit symbol.";
            if (iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = msg;
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = msg;
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        free_data(&data);
        exit(-1);
    }
#endif

    if (H_I > data.word_size) {
        printf("H_I (%f) must be at most 'bits_per_symbol' (%d).\n", H_I, data.word_size);
        if (jsonOutput) {
            if(iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = "H_I (" + std::to_string(H_I) + ") must be at most 'bits_per_symbol' (" + std::to_string(data.word_size) + ").";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = "H_I (" + std::to_string(H_I) + ") must be at most 'bits_per_symbol' (" + std::to_string(data.word_size) + ").";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        free_data(&data);
        exit(-1);
    }

    if (data.alph_size <= 1) {
        printf("Symbol alphabet consists of 1 symbol. No entropy awarded...\n");
        if (jsonOutput) {
            if(iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = "Symbol alphabet consists of 1 symbol. No entropy awarded...";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = "Symbol alphabet consists of 1 symbol. No entropy awarded...";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        free_data(&data);
        exit(-1);
    }

    if (data.len != MIN_SIZE) {
        printf("\n*** Error: data (len = %ld) does not contain %d samples ***\n\n", data.len, MIN_SIZE);
        if (jsonOutput) {
            if (iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = "*** Error: data (len = " + std::to_string(data.len) + ") does not contain " + std::to_string(MIN_SIZE) + " samples ***";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = "*** Error: data (len = " + std::to_string(data.len) + ") does not contain " + std::to_string(MIN_SIZE) + " samples ***";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        exit(-1);
    }

    if (verbose > 1) {
        if (data.alph_size < (1 << data.word_size)) printf("\nSymbols have been translated.\n\n");
    }

    rdata = data.symbols;
    cdata = (uint8_t*) malloc(data.len);
    crawdata = (uint8_t*) malloc(data.len);
    if ((cdata == NULL) || (crawdata == NULL)) {
        printf("Error: failure to initialize memory for columns\n");
        if (jsonOutput) {
            if(iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = "Error: failure to initialize memory for columns";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = "Error: failure to initialize memory for columns";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        if(cdata != NULL) free(cdata);
        if(crawdata != NULL) free(crawdata);
        exit(-1);
    }

    printf("H_I: %f\n", H_I);

    // 3.1.4.3 step 1 sets alpha = 0.000005, which is what Hill's published
    // cutoffs target too; the Sidak value 1 - 0.99^(1/2000) upstream used gives
    // the same cutoffs at every H_I in 1..8 (OC-7).
    alpha = 0.000005;
    X_cutoff_printed = printedBinomialBound(alpha, H_I);
#ifdef EA_RESTART_WITHOUT_C23_FIX
    {
        const double alpha_sim = 1 - exp(log(0.99) / (r + c));
        X_cutoff = simulateBound(alpha_sim, data.alph_size, H_I, simulation_rounds);
        if (verbose > 0) printf("ALPHA: %.17g, X_cutoff: %d (upstream simulated maximum over symbols)\n", alpha_sim, X_cutoff);
    }
#elif defined(EA_RESTART_C23_PRINTED_BINOMIAL)
    (void) simulation_rounds;
    X_cutoff = X_cutoff_printed;        // SUPERSEDED (a5005bd): over-rejects, see OC-30
    if (verbose > 0) printf("ALPHA: %.17g, X_cutoff: %d (printed binomial formula -- SUPERSEDED, rejects correctly-operating sources)\n", alpha, X_cutoff);
#else
    (void) simulation_rounds;                   // -s is accepted and ignored
    X_cutoff = exactMultinomialMaxBound(alpha, H_I);
    if (verbose > 0) {
        printf("ALPHA: %.17g, X_cutoff: %d (exact distribution of the multinomial maximum, the statistic 3.1.4.3 forms)\n", alpha, X_cutoff);
        printf("X_cutoff_printed_binomial: %d (SP 800-90B 3.1.4.3 step 5 as printed; conformance figure, not the verdict -- it rejects correctly-operating sources, see OC-30)\n", X_cutoff_printed);
    }
#endif

    // get maximum row count
    X_r = 0;
    for (i = 0; i < r; i++) { //row
        memset(counts, 0, 256 * sizeof (int));
        X_i = 0;
        for (j = 0; j < c; j++) {//column
            //[i*r+j] is row i, column j
            //So, we're fixing a row, and then iterate through various columns
            if (++counts[rdata[i * r + j]] > X_i) X_i = counts[rdata[i * r + j]];
        }
        if (X_i > X_r) X_r = X_i;
    }

    // construct column data from row data and get maximum column count
    X_c = 0;
    for (j = 0; j < c; j++) { //columns
        memset(counts, 0, 256 * sizeof (int));
        X_i = 0;
        for (i = 0; i < r; i++) {
            //[i*r+j] is row i, column j
            //So, we're fixing a column and iterating through various rows
            cdata[j * c + i] = rdata[i * r + j];
            crawdata[j * c + i] = data.rawsymbols[i * r + j];
            if (++counts[cdata[j * c + i]] > X_i) X_i = counts[cdata[j * c + i]];
        }
        if (X_i > X_c) X_c = X_i;
    }

    // perform sanity check on rows and columns of restart data (Section 3.1.4.3)
    X_max = max(X_r, X_c);
    if (verbose > 0) printf("X_max: %d\n", X_max);
    // The sanity-check inputs and verdict go into the report so a consumer can
    // recompute the decision (OC-11 item 4, XR-10) instead of trusting it.
    testRunIid.restartHI = H_I;            testRunNonIid.restartHI = H_I;
    testRunIid.restartAlpha = alpha;       testRunNonIid.restartAlpha = alpha;
    testRunIid.restartXmax = X_max;        testRunNonIid.restartXmax = X_max;
    testRunIid.restartXcutoff = X_cutoff;  testRunNonIid.restartXcutoff = X_cutoff;
    testRunIid.restartXcutoffPrintedBinomial = X_cutoff_printed;
    testRunNonIid.restartXcutoffPrintedBinomial = X_cutoff_printed;
#ifdef EA_RESTART_WITHOUT_C23_FIX
    testRunIid.restartCutoffMethod = "upstream-simulated-multinomial-maximum";
#elif defined(EA_RESTART_C23_PRINTED_BINOMIAL)
    testRunIid.restartCutoffMethod = "printed-binomial-SUPERSEDED";
#else
    testRunIid.restartCutoffMethod = "exact-multinomial-maximum";
#endif
    testRunNonIid.restartCutoffMethod = testRunIid.restartCutoffMethod;
    testRunIid.restartSanityCheckPassed = (X_max <= X_cutoff) ? 1 : 0;
    testRunNonIid.restartSanityCheckPassed = testRunIid.restartSanityCheckPassed;
    if (X_max > X_cutoff) {
        if (verbose > 0) printf("\n*** Restart Sanity Check Failed ***\n");
        if (jsonOutput) {
            if(iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = "Restart Sanity Check Failed.";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = "Restart Sanity Check Failed.";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        exit(-1);
    } else if (verbose > 1) printf("\nRestart Sanity Check Passed...\n");


    // Calculate baseline statistics
    int alphabet_size = data.alph_size;
    int sample_size = data.len;

    if ((verbose == 1) || (verbose == 2))
        printf("Calculating baseline statistics...\n");

    calc_stats(&data, rawmean, translated_symbol_median);

    // The maximum min-entropy is -log2(1/2^word_size) = word_size
    H_c = data.word_size;
    H_r = data.word_size;
    if (verbose > 0) {
        if (iid) printf("\nRunning IID tests...\n\n");
        else printf("\nRunning non-IID tests...\n\n");

        printf("Running Most Common Value Estimate...\n");
    }

    // Section 6.3.1 - Estimate entropy with Most Common Value

    NonIidTestCase tc631nonIid;
    tc631nonIid.testCaseNumber = "Most Common Value";
    tc631nonIid.data_word_size = data.word_size;

    IidTestCase tc631Iid;
    tc631Iid.testCaseNumber = "Most Common Value";
    tc631Iid.data_word_size = data.word_size;

    ret_min_entropy = most_common(rdata, data.len, data.alph_size, verbose, "Literal");
    if (verbose > 1) printf("\tMost Common Value Estimate (Rows) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
    tc631nonIid.h_r = ret_min_entropy;
    tc631Iid.h_r = ret_min_entropy;

    H_r = min(ret_min_entropy, H_r);

    ret_min_entropy = most_common(cdata, data.len, data.alph_size, verbose, "Literal");
    if (verbose > 1) printf("\tMost Common Value Estimate (Cols) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
    tc631nonIid.h_c = ret_min_entropy;
    H_c = min(ret_min_entropy, H_c);

    testRunNonIid.testCases.push_back(tc631nonIid);

    IidTestCase tcOverallIid;
    tcOverallIid.h_r = H_r;
    tcOverallIid.h_c = H_c;
    tcOverallIid.h_i = H_I;
    tcOverallIid.testCaseNumber = "Overall";
    tcOverallIid.raw_mean = rawmean;
    tcOverallIid.translated_symbol_median = translated_symbol_median;


    if (!iid) {

        if (data.alph_size == 2) {

            if (verbose > 0) printf("\nRunning Entropic Statistic Estimates (bit strings only)...\n");

            // Section 6.3.2 - Estimate entropy with Collision Test (for bit strings only)

            NonIidTestCase tc632;
            tc632.testCaseNumber = "Collision Test (for bit strings only)";
            tc632.data_word_size = 1;
            // collision_test() became fallible when it was given the v >= 2
            // guard SP 800-90B 6.3.2 step 5 requires. It cannot decline on a
            // restart dataset, which is always 1,000,000 samples, but the
            // guard is here so the two programs treat it alike.
            ret_min_entropy = collision_test(rdata, data.len, verbose, "Literal");
            if (ret_min_entropy >= 0) {
                if (verbose > 1) printf("\tCollision Test Estimate (Rows) = %f / 1 bit(s)\n", ret_min_entropy);
                tc632.h_r = ret_min_entropy;
                H_r = min(ret_min_entropy, H_r);
            }

            ret_min_entropy = collision_test(cdata, data.len, verbose, "Literal");
            if (ret_min_entropy >= 0) {
                if (verbose > 1) printf("\tCollision Test Estimate (Cols) = %f / 1 bit(s)\n", ret_min_entropy);
                tc632.h_c = ret_min_entropy;
                H_c = min(ret_min_entropy, H_c);
            }

            testRunNonIid.testCases.push_back(tc632);

            // Section 6.3.3 - Estimate entropy with Markov Test (for bit strings only)

            NonIidTestCase tc633;
            tc633.testCaseNumber = "Markov Test (for bit strings only)";
            tc633.data_word_size = 1;

            ret_min_entropy = markov_test(rdata, data.len, verbose, "Literal");
            if (verbose > 1) printf("\tMarkov Test Estimate (Rows) = %f / 1 bit(s)\n", ret_min_entropy);
            tc633.h_r = ret_min_entropy;
            H_r = min(ret_min_entropy, H_r);

            ret_min_entropy = markov_test(cdata, data.len, verbose, "Literal");
            if (verbose > 1) printf("\tMarkov Test Estimate (Cols) = %f / 1 bit(s)\n", ret_min_entropy);
            tc633.h_c = ret_min_entropy;
            H_c = min(ret_min_entropy, H_c);

            testRunNonIid.testCases.push_back(tc633);

            // Section 6.3.4 - Estimate entropy with Compression Test (for bit strings only)

            NonIidTestCase tc634;
            tc634.testCaseNumber = "Compression Test (for bit strings only)";
            tc634.data_word_size = 1;

            ret_min_entropy = compression_test(rdata, data.len, verbose, "Literal");
            if (ret_min_entropy >= 0) {
                if (verbose > 1) printf("\tCompression Test Estimate (Rows) = %f / 1 bit(s)\n", ret_min_entropy);
                tc634.h_r = ret_min_entropy;
                H_r = min(ret_min_entropy, H_r);
            }

            ret_min_entropy = compression_test(cdata, data.len, verbose, "Literal");
            if (ret_min_entropy >= 0) {
                if (verbose > 1) printf("\tCompression Test Estimate (Cols) = %f / 1 bit(s)\n", ret_min_entropy);
                tc634.h_c = ret_min_entropy;
                H_c = min(ret_min_entropy, H_c);
            }
            testRunNonIid.testCases.push_back(tc634);

        }


        if (verbose > 0) printf("\nRunning Tuple Estimates...\n");

        // Section 6.3.5 - Estimate entropy with t-Tuple Test

        NonIidTestCase tc635;
        tc635.testCaseNumber = "T-Tuple Test";
        tc635.data_word_size = data.word_size;

        double row_t_tuple_res, row_lrs_res;
        double col_t_tuple_res, col_lrs_res;
        SAalgs(rdata, data.len, data.alph_size, row_t_tuple_res, row_lrs_res, verbose, "Literal");
        SAalgs(cdata, data.len, data.alph_size, col_t_tuple_res, col_lrs_res, verbose, "Literal");

        // SAalgs() returns -1 for an estimate that could not be computed
        // (SP 800-90B 6.3.6 step 2: "If v < u, this estimate cannot be
        // computed"). Folding that sentinel in as an entropy drove H_r to -1
        // and failed an otherwise valid restart dataset. Every other fallible
        // estimator here is already guarded this way.
        if (row_t_tuple_res >= 0) {
            if (verbose > 1) printf("\tT-Tuple Test Estimate (Rows) = %f / %d bit(s)\n", row_t_tuple_res, data.word_size);
            tc635.h_r = row_t_tuple_res;
            H_r = min(row_t_tuple_res, H_r);
        }

        if (col_t_tuple_res >= 0) {
            if (verbose > 1) printf("\tT-Tuple Test Estimate (Cols) = %f / %d bit(s)\n", col_t_tuple_res, data.word_size);
            tc635.h_c = col_t_tuple_res;
            H_c = min(col_t_tuple_res, H_c);
        }

        testRunNonIid.testCases.push_back(tc635);
        // Section 6.3.6 - Estimate entropy with LRS Test

        NonIidTestCase tc636;
        tc636.testCaseNumber = "LRS Test";
        tc636.data_word_size = data.word_size;

        if (row_lrs_res >= 0) {
            if (verbose > 1) printf("\tLRS Test Estimate (Rows) = %f / %d bit(s)\n", row_lrs_res, data.word_size);
            tc636.h_r = row_lrs_res;
            H_r = min(row_lrs_res, H_r);
        }

        if (col_lrs_res >= 0) {
            if (verbose > 1) printf("\tLRS Test Estimate (Cols) = %f / %d bit(s)\n", col_lrs_res, data.word_size);
            tc636.h_c = col_lrs_res;
            H_c = min(col_lrs_res, H_c);
        }

        testRunNonIid.testCases.push_back(tc636);

        if (verbose > 0) printf("\nRunning Predictor Estimates...\n");

        // Section 6.3.7 - Estimate entropy with Multi Most Common in Window Test

        NonIidTestCase tc637;
        tc637.testCaseNumber = "Multi Most Common in Window Test";
        tc637.data_word_size = data.word_size;

        ret_min_entropy = multi_mcw_test(rdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tMulti Most Common in Window (MultiMCW) Prediction Test Estimate (Rows) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc637.h_r = ret_min_entropy;
            H_r = min(ret_min_entropy, H_r);
        }

        ret_min_entropy = multi_mcw_test(cdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tMulti Most Common in Window (MultiMCW) Prediction Test Estimate (Cols) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc637.h_c = ret_min_entropy;
            H_c = min(ret_min_entropy, H_c);
        }

        testRunNonIid.testCases.push_back(tc637);
        // Section 6.3.8 - Estimate entropy with Lag Prediction Test

        NonIidTestCase tc638;
        tc638.testCaseNumber = "Lag Prediction Test";
        tc638.data_word_size = data.word_size;

        ret_min_entropy = lag_test(rdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tLag Prediction Test Estimate (Rows) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc638.h_r = ret_min_entropy;
            H_r = min(ret_min_entropy, H_r);
        }

        ret_min_entropy = lag_test(cdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tLag Prediction Test Estimate (Cols) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc638.h_c = ret_min_entropy;
            H_c = min(ret_min_entropy, H_c);
        }
        testRunNonIid.testCases.push_back(tc638);

        // Section 6.3.9 - Estimate entropy with Multi Markov Model with Counting Test (MultiMMC)
        NonIidTestCase tc639;
        tc639.testCaseNumber = "Multi Markov Model with Counting Test (MultiMMC)";
        tc639.data_word_size = data.word_size;

        ret_min_entropy = multi_mmc_test(rdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tMulti Markov Model with Counting (MultiMMC) Prediction Test Estimate (Rows) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc639.h_r = ret_min_entropy;
            H_r = min(ret_min_entropy, H_r);
        }

        ret_min_entropy = multi_mmc_test(cdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tMulti Markov Model with Counting (MultiMMC) Prediction Test Estimate (Cols) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc639.h_c = ret_min_entropy;
            H_c = min(ret_min_entropy, H_c);
        }
        testRunNonIid.testCases.push_back(tc639);

        // Section 6.3.10 - Estimate entropy with LZ78Y Test

        NonIidTestCase tc6310;
        tc6310.testCaseNumber = "LZ78Y Test";
        tc6310.data_word_size = data.word_size;

        ret_min_entropy = LZ78Y_test(rdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tLZ78Y Prediction Test Estimate (Rows) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc6310.h_r = ret_min_entropy;
            H_r = min(ret_min_entropy, H_r);
        }

        ret_min_entropy = LZ78Y_test(cdata, data.len, data.alph_size, verbose, "Literal");
        if (ret_min_entropy >= 0) {
            if (verbose > 1) printf("\tLZ78Y Prediction Test Estimate (Cols) = %f / %d bit(s)\n", ret_min_entropy, data.word_size);
            tc6310.h_c = ret_min_entropy;
            H_c = min(ret_min_entropy, H_c);
        }
        testRunNonIid.testCases.push_back(tc6310);

    } else { /* IID tests */

        // Compute chi square stats
        bool chi_square_test_pass_row = chi_square_tests(rdata, sample_size, alphabet_size, verbose);
        bool chi_square_test_pass_col = chi_square_tests(cdata, sample_size, alphabet_size, verbose);
        bool chi_square_test_pass = chi_square_test_pass_row && chi_square_test_pass_col;

        tcOverallIid.ran_chi_square_tests = true;
        tcOverallIid.passed_chi_square_tests = chi_square_test_pass;

        if ((verbose == 1) || (verbose == 2)) {
            if (chi_square_test_pass) {
                printf("** Passed chi square tests\n\n");
            }
            else {
                printf("** Failed chi square tests\n\n");
            }
        }
        else if (verbose > 2) {
            if (chi_square_test_pass) {
                printf("Chi square tests: Passed\n");
            }
            else {
                printf("Chi square tests: Failed\n");
            }
        }

        tcOverallIid.ran_longest_repeated_substring_test = true;
        bool len_LRS_test_pass_row = len_LRS_test(rdata, sample_size, alphabet_size, verbose, "Rows");
        bool len_LRS_test_pass_col = len_LRS_test(cdata, sample_size, alphabet_size, verbose, "Columns");
        bool len_LRS_test_pass = len_LRS_test_pass_row && len_LRS_test_pass_col;
        tcOverallIid.passed_longest_repeated_substring_test = len_LRS_test_pass;
        if (verbose > 0) printf("** %s length of longest repeated substring tests\n\n", len_LRS_test_pass ? "Passed" : "Failed");

        bool perm_test_pass = false;
        if (chi_square_test_pass && len_LRS_test_pass) {
            tcOverallIid.ran_iid_permutation_tests = true;
            bool perm_test_pass_row = permutation_tests(&data, rawmean, translated_symbol_median, verbose, tcOverallIid, "rows");

            data_t data_col;
            // The rest of data_col is invariant under permutation.
            memcpy(&data_col, &data, sizeof(data));
            data_col.symbols = cdata;
            data_col.rawsymbols = crawdata;
            bool perm_test_pass_col = permutation_tests(&data_col, rawmean, translated_symbol_median, verbose, tcOverallIid, "columns");
            perm_test_pass = perm_test_pass_row && perm_test_pass_col;
            tcOverallIid.passed_iid_permutation_tests = perm_test_pass;
            if (verbose > 0) printf("** %s IID permutation tests\n\n", perm_test_pass ? "Passed" : "Failed");
        } else if (verbose > 0) {
            printf("** Skipped IID permutation tests after an earlier required IID test failure\n\n");
        }

        iid_test_suite_pass = chi_square_test_pass && len_LRS_test_pass && perm_test_pass;
        testRunIid.assessmentComplete = true;
        testRunIid.iidClaimAccepted = iid_test_suite_pass;


    }

    if (iid && !iid_test_suite_pass) {
        tcOverallIid.h_r = -1.0;
        tcOverallIid.h_c = -1.0;
        tcOverallIid.h_i = -1.0;
        testRunIid.testCases.push_back(tcOverallIid);
        testRunIid.errorLevel = 2;
        testRunIid.errorMsg = "IID restart test suite failed; no IID restart entropy estimate was awarded.";
        if (verbose > 0) printf("IID restart test suite failed: no IID restart entropy estimate was awarded.\n");
        if (jsonOutput && !writeJsonReport(outputfilename, testRunIid.GetAsJson())) {
            free(cdata);
            free(crawdata);
            free_data(&data);
            return -1;
        }
        free(cdata);
        free(crawdata);
        free_data(&data);
        return 1;
    }

    if (verbose > 0) {
        printf("\n");
        printf("H_r: %f\n", H_r);
        printf("H_c: %f\n", H_c);
        printf("H_I: %f\n", H_I);
        printf("\n");
    }

    if (min(H_r, H_c) < H_I / 2.0) {
        if (verbose > 0) printf("*** min(H_r, H_c) < H_I/2, Validation Testing Failed ***\n");
        if (jsonOutput) {
            if(iid) {
                testRunIid.errorLevel = -1;
                testRunIid.errorMsg = "min(H_r, H_c) < H_I/2, Validation Testing Failed.";
                writeJsonReport(outputfilename, testRunIid.GetAsJson());
            } else {
                testRunNonIid.errorLevel = -1;
                testRunNonIid.errorMsg = "min(H_r, H_c) < H_I/2, Validation Testing Failed.";
                writeJsonReport(outputfilename, testRunNonIid.GetAsJson());
            }
        }
        exit(-1);
    }


    testRunIid.testCases.push_back(tcOverallIid);
    testRunIid.errorLevel = 0;

    NonIidTestCase tcOverallNonIid;
    tcOverallNonIid.h_r = H_r;
    tcOverallNonIid.h_c = H_c;
    tcOverallNonIid.h_i = H_I;
    tcOverallNonIid.testCaseNumber = "Overall";
    testRunNonIid.testCases.push_back(tcOverallNonIid);
    testRunNonIid.errorLevel = 0;


    if (jsonOutput) {
        // This is the success path, so a report that cannot be written is the
        // only failure of the run and must be its exit status.
        if (!writeJsonReport(outputfilename, iid ? testRunIid.GetAsJson() : testRunNonIid.GetAsJson())) {
            // rdata aliases data.symbols, so it must not be freed here;
            // free_data() owns it. The normal exit below frees exactly these.
            free(cdata);
            free(crawdata);
            free_data(&data);
            exit(-1);
        }
    }
    if (verbose > 0) {
        printf("Validation Test Passed...\n\n");
        printf("min(H_r, H_c, H_I): %f\n\n", min(min(H_r, H_c), H_I));
    }
    free(cdata);
    free(crawdata);
    free_data(&data);
    return 0;
}
