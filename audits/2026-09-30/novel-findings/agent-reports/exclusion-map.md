# Known-findings exclusion map — usnistgov/SP800-90B_EntropyAssessment

Source: `SCR/gh/all.md` (all 270 items #1–#270, bodies, conversation comments, inline PR review comments) read completely; long log dumps (#2, #31, #161) skimmed for non-log text, all comments read. PR merge state and close reasons taken from `SCR/gh/issues.json` (`pull_request.merged_at`, `state_reason`). Current-code locations were checked against the extracted upstream tree `SCR/audit/rel/cpp` at `87c104d` (read only). Local audit: `/workspaces/SP800-90B_EntropyAssessment/AUDIT-2026-09-30.md` (F01–F30).

Accounts: **celic** (Chris Celi, NIST, COLLABORATOR, maintainer since 2018), **kerrymckay** (NIST, python era 2016-18), **andrewmccaffreynist** (NIST, MEMBER), **skbhaskarla** (COLLABORATOR, Windows10 branch), **joshuaehill** (Joshua Hill, UL / KeyPair; CONTRIBUTOR, author of most of the current C++ code; his positions were merged by celic and are treated as de facto maintainer positions). **systemslibrarian** = this user (#253–#270, comment on #214).

Legend for *direction*: **HIGH** = reported entropy too high / IID or restart wrongly passed (dangerous). **LOW** = too low / wrongly failed. **either**. **verdict** = IID/restart pass/fail wrong (sign given if known). **crash** (abort/segfault). **mem** (memory-safety: overflow, over-read, leak, UB). **hang** (non-termination or pathological run time). **reporting** (value OK, text/JSON/provenance wrong). **perf** (slow/memory, expected). **none**. "py" = legacy Python tool (2016 draft), removed from the repo; still counts as known history.

Items **not in the BRIEF's KNOWN list that must also be treated as known** (open or recently merged): **#251** (open PR: ea_iid JSON `hAssessed` = word_size at default verbosity; still present at 87c104d, `iid_main.cpp:285-313`), **#252** (open PR: ea_iid prints/returns a min-entropy even when IID tests fail), **#244/#250** (restart IID tests ran on row data twice; fixed in master 2026-05-26), **#246/#248** (`calc_proportions` rounding → assert in `len_LRS_test`; fixed 2026-05-26), **#195** (open: ea_restart `assert(k_effective <= k)` abort, no JSON), **#219** (open: Windows ea_iid LRS test Pr(X≥1) negative), **#238** (open: JSON lacks sample/symbol counts), **#236** (open but fixed by #237).

---

## 1. Defect / spec-question / behaviour-change table

| # | ISSUE/PR | open/closed | title (short) | executable/component | file/function | root cause | symptom | affects entropy value? | direction | fix PR / resolution |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | I | closed | markov test crashes | py non-IID | markov.py markov_test / util90b.to_dataset | input packed 8 bits/byte; tool expects 1 symbol/byte | IndexError crash | no | crash | not a bug: input format (kerrymckay) |
| 3 | I | closed | LZ78Y TypeError dict>int | py non-IID | SP90Bv2_predictors.py LZ78Y | py3 dict/int comparison | crash | no | crash | fixed in py code 2016-07-11 |
| 4 | I | closed | chi-square T index uses q not i | py IID | chi_square_tests.py:147 | wrong index in T sum | wrong chi-square stat | IID verdict | verdict | PR #5 (merged) |
| 5 | PR | closed | fixes #4 | py IID | chi_square_tests.py | — | — | — | — | merged |
| 6 | I | closed | conversion2 pads extra zero byte when len%8==0 | py IID | permutation_tests.py conversion2 | `8 - len%8` = 8 | wrong perm stats | IID verdict | verdict | PR #7 (merged) |
| 7 | PR | closed | fixes #6 | py IID | permutation_tests.py | — | — | — | — | merged |
| 8 | I | closed | >8 bits/sample rejected | py (and C++: width 1..8) | noniid_main assert bits_per_symbol<=8 | by design (guidance sample-space limit) | assert | n/a | none | by design (kerrymckay): map down per §6.4 first |
| 12 | I | closed | assert df>0 in chi-square | py IID | chi_square_tests.py chi_square_cutoff | 10k-sample dataset too small | AssertionError | no | crash | use ≥1M samples (celic); PR #14 not merged |
| 13 | I | closed | "impossible" Markov p(max)=1e-206 | py non-IID | markov | p is prob. of most likely 128-symbol string | tiny p(max) printed | no | none | by design (joshuaehill) |
| 14 | PR | closed | handle df==0, reorder tests, verbosity-independent result | py IID | chi_square_tests.py | — | — | — | — | not merged |
| 15 | I | closed | runs-based-on-median used conversion II on binary | py IID | permutation_tests.py | spec 5.1.5/5.1.6 use original data, median 0.5 | wrong perm stat | IID verdict | verdict | fixed (py) |
| 16 | I | closed | altSequence2 drops last element | py IID | permutation_tests.py altSequence2 | range(L-1) | wrong S' | IID verdict | verdict | fixed (py) |
| 17 | I | closed | binary-search closeness epsilon inconsistent | py + C++ non-IID | collision/compression/predictor searches | absolute epsilon | inaccurate p | yes (small) | either | PR #25 (py, not merged) → C++ PR #69 |
| 18 | I | closed | collision F evaluation terminates badly | py non-IID | collision F (continued fraction) | k iterations, error accumulation | small error | yes (tiny) | either | PR #26 (py); final 90B k=2 → F(z)=2z³+2z²+z (#57/#69) |
| 19 | I | closed | binary searches should fail/return bound conservatively | py + C++ | all binary searches | endpoint back-off, no iteration cap | wrong/ fragile p | yes | either | PR #25 / C++ PR #69 |
| 20 | I | closed | Markov alpha exponent (k²+k, 1/·) | py (2016 draft) | markov.py | draft spec formula | confidence wrong | yes | either | addressed in final 90B (no ε term) |
| 21 | I | closed | Markov Hoeffding uses log2 not ln | py (2016 draft) | markov.py | draft spec | confidence wrong | yes | either | addressed in final 90B |
| 22 | I | closed | z_alpha rounded to 2.576 | py + C++ all estimators | ZALPHA (now `shared/utils.h`) | spec prints 2.576 | bounds differ ≤5e-6 bit | yes (tiny) | HIGH (tiny, vs printed spec) | full precision 2.5758293035489008 adopted: PR #26 (py), PR #69 (C++); joshuaehill: "applies to the 90B-final C++ version as well" = **F07** |
| 23 | I | closed | Decimal package unnecessary in predictors | py | SP90Bv2_predictors.py | underflow handling | abort on underflow | no | crash | PR #25; NIST log-domain approach in C++ |
| 24 | I | closed | verbose output inconsistent | py | all | — | messy output | no | reporting | closed: python retired (celic) |
| 25 | PR | closed | conservative binary search, isclose, no Decimal | py | predictors/compression/collision | — | — | — | — | not merged (resolves #17 #19 #23 in py) |
| 26 | PR | closed | full-precision z_alpha + new collision F | py | — | — | — | — | — | not merged (resolves #18 #22 in py) |
| 27 | PR | closed | umbrella of joshuaehill py fixes | py | — | — | — | — | — | merged 2019 |
| 28 | I | closed | binary chi-square independence (5.2.3 draft) overlapping tuples, df | py IID / spec | chi_square_tests.py | draft spec construction | type-I ≈3% | IID verdict | verdict (LOW) | addressed in final 90B text |
| 29 | I | closed | binary GOF (5.2.4 draft) omits 0s term | py IID / spec | chi_square_tests.py | draft spec | wrong stat | IID verdict | verdict | addressed in final 90B text |
| 32 | I | closed | LRS estimate takes days (py) | py non-IID | LRS | 2.5M samples, slow algorithm | apparent hang | no | perf/hang | trim to 1M (kerrymckay) |
| 33 | I | closed | output has no units | py | output | — | naked number | no | reporting | PR #35 not merged; closed |
| 34 | I | closed | Markov (6-bit map) lowers 8-bit assessment | py (2016 draft) / spec | markov | draft mapped to 6 bits | low figure | yes | LOW | by design (joshuaehill); percentages misleading; map down per §6.4 |
| 35 | PR | closed | display units | py | — | — | — | — | reporting | not merged |
| 41 | PR | closed | packed data input, perm-test early exit, start/read_amount | py IID/restart | permutation_tests.py, util90b.py | — | — | — | — | not merged; early exit later adopted (#55/#98); joshuaehill: perm FP ≈1–2%/round |
| 44 | I | closed | LRS via suffix array/LCP | C++ shared | lrs_test.h | — | slow | no | perf | joshuaehill: current code SA/LCP, O(v·L); worst case all-ones input |
| 45 | PR | closed | srand() before every shuffle; rand() not thread-safe | C++ ea_iid (early) | permutation shuffle | time-seeded per shuffle, threads share sequence | non-random permutations | IID verdict | verdict | not merged; superseded by #77 (xoshiro256**) |
| 46 | I | closed | per-test early stop in perm tests | C++ ea_iid | permutation_tests | — | slow | no | perf | redundant with #41; closed |
| 48 | PR | closed | biased Fisher-Yates (rand()%) | C++ ea_iid | FYshuffle | modulo bias | biased shuffle | IID verdict | verdict | not merged; superseded by #77 (Lemire bounded ints) |
| 49 | I | closed | compression estimate alph_size used as 2^b and 2^b−1 | ea_non_iid | compression_test.h com_exp / compression_test | `alph_size*G(q)` and `q=(1-p)/alph_size` | mismatch vs UL tool | yes | either | PR #69 (merged) |
| 50 | I | closed | binary searches inaccurate, fragile, slow | ea_non_iid | collision/compression/predictors (utils.h) | ad hoc bound adjustment, abs-diff compare | inaccurate p | yes | either | PR #69 (merged) |
| 51 | I | closed | no debug output of spec variables | all | — | — | — | no | reporting | joshuaehill 2018UL → PR #98/#118 (-v levels) |
| 52 | I | closed | LRS/t-tuple faster with SA/LCP | shared | lrs_test.h SAalgs | naive algorithm | slow | no | perf | PR #98 (divsufsort), #112 (Kaufer) — **KNOWN (BRIEF)** |
| 53 | I | closed | LRS memory huge (5.3 GB) | shared | lrs_test.h | old algorithm | memory blow-up | no | perf | PR #98 SA/LCP |
| 54 | I | closed | rand() in Fisher-Yates can yield i+1 | ea_iid | FYshuffle | `(rand()/RAND_MAX)*(i+1)` | OOB swap (buffer overflow), bias | IID verdict | mem | PR #77 (xoshiro256** + Lemire) |
| 55 | I | closed | short-circuit passing perm tests | ea_iid | permutation_tests | — | slow | no | perf | PR #98 |
| 56 | I | closed | restart test more failure-prone than desired | ea_restart / spec | restart cutoff | Jan-2018 binomial assumption | excess false fails | restart verdict | verdict (LOW) | PR #98 simulation cutoff; later #224 |
| 57 | I | closed | collision F unnecessarily complicated | ea_non_iid | collision_test.h F | continued fraction | none (precision) | tiny | none | PR #69 polynomial |
| 58 | I | closed | compression FP error accumulation | ea_non_iid | compression_test.h G / kahan_add | naive sums | FP drift | tiny | either | PR #69 (Kahan) |
| 59 | I | closed | calc_p_local x as long double | ea_non_iid | utils.h calc_p_local | precision | — | tiny | either | PR #69 |
| 60 | I | closed | chi-square critical-value table → p-value | ea_iid | chi_square_tests.h chi_square_pvalue | table | — | IID verdict (edge) | verdict | PR #98 (cephes igamc) |
| 61 | I | closed | excursion/covariance/compression perm tests not translation-invariant | ea_iid | permutation_tests.h (rawdata vs symbols) | tests run on translated data | different stats | IID verdict | verdict | PR #80 (dup #76) |
| 62 | I | closed | non-binary independence expectation L/2 not floor(L/2) | ea_iid | chi_square_tests.h independence_calc_expectations | off by 0.5 pair | wrong stat | IID verdict | verdict | PR #80 |
| 63 | I | closed | non-binary chi-square sort ill-defined on ties | ea_iid | chi_square_tests.h expectationOrder/tupleOrder | unstable sort | non-deterministic binning | IID verdict | verdict | fixed (2018UL → PR #98) |
| 65 | I | closed | Output_Entropy n should be min(n_out,nw,n_in) | ea_conditioning | conditioning_main.cpp Output_Entropy | narrowest width | h_out possibly too high when n_in < nw | yes | HIGH (likely) | fixed via PR #87 |
| 66 | I | closed | command line processing odd → getopt | all | *_main.cpp | ad hoc argv parsing | — | no | none | PR #99 |
| 69 | PR | closed | compression fix + Kahan + binary search + z full precision + F poly + p_local | ea_non_iid | compression/collision/utils | — | — | yes | — | merged; "corner cases flagged as failure (thus assigned full entropy, as per the standard)" |
| 70 | I | closed | 1-bit results silly (collision 0.32, compression 0.089, t-tuple 0.034 with -t, MultiMMC >1) | ea_non_iid | several (old tool) | pre-#69 bugs; user ran stale binary | extreme under/over estimates | yes | either | fixed by PR #69; joshuaehill: -t/-a only affect H_bitstring; binary data has no H_bitstring; collision/compression expected to underestimate; old MultiMMC lacked 1/k floor |
| 71 | I | closed | bitstring built from translated data | ea_non_iid/iid/conditioning | utils.h read_file_subset (bsymbols) | translation before bit expansion | H_bitstring on wrong bits | yes | either | PR #72; MSB-first ordering declared a convention (90B unspecified) |
| 72 | PR | closed | bitstring from non-translated data | shared I/O | utils.h | — | — | yes | — | merged |
| 76 | I | closed | dup of #61 | ea_iid | — | — | — | — | — | dup |
| 77 | PR | closed | xoshiro256** + Lemire range | shared | utils.h seed/xoshiro/randomRange64/FYshuffle | — | — | — | — | merged; resolves #54 |
| 78 | I | closed | number of runs off by 1 | ea_iid | permutation_tests.h runs functions | counts transitions | wrong stat | IID verdict | verdict | PR #80/#98 |
| 79 | I | closed | compression perm test compresses empty string; BZ2 buffer too small | ea_iid | permutation_tests.h compression | `resize` vs `reserve`; strlen of NUL-prefixed | nonsense stat; buffer too small | IID verdict | verdict/mem | PR #80 |
| 80 | PR | closed | first perm-test fixes | ea_iid | permutation_tests.h | — | — | — | — | merged; closes #78 #79 #82 #61 |
| 82 | I | closed | median assumes even count; binary median 0.5 | ea_iid | utils.h calc_stats | median formula | wrong median | IID verdict | verdict | PR #80 |
| 86 | I | closed | OpenMP gives little benefit; parallelise perm tests | ea_iid | permutation_tests | — | slow | no | perf | PR #98 |
| 87 | PR | closed | README deps, Makefile targets, usage; conditioning n fix | build, ea_conditioning | Makefile, conditioning_main.cpp | — | — | yes (#65) | — | merged; closes #64 #65 #68 #73 #74 #83 #84 #85 |
| 88 | I | closed | non-binary chi-square independence slow | ea_iid | chi_square_tests.h chi_square_independence | 2^16 passes | slow | no | perf | PR #98 |
| 89 | I | closed | divide(int,int) used on doubles | ea_iid (chi) | utils.h divide | implicit truncation | wrong values | IID verdict | verdict | PR #98 |
| 90 | I | closed | GOF chi-square memory leak | ea_iid | chi_square_tests.h goodness_of_fit | new without delete | leak | no | mem | PR #98 |
| 91 | I | closed | non-binary GOF expectation when L%10≠0 | ea_iid / spec | chi_square_tests.h goodness_of_fit | expectation base | wrong stat | IID verdict | verdict | PR #98; tool deliberately uses (c_i/L)·floor(L/10) — deviates from 90B text (joshuaehill) |
| 92 | I | closed | LRS computed wrongly ("banana" → 4) | shared | lrs_test.h (old) | broken LRS code | wrong LRS | yes | either | PR #98 SA/LCP rewrite |
| 93 | I | closed | binary_chi_square_independence statistic nonsense | ea_iid | chi_square_tests.h binary_chi_square_independence | iterates tuples not blocks | wrong stat | IID verdict | verdict | PR #98 |
| 94 | I | closed | need known-answer tests | all | selftest/ | — | — | no | none | PR #118 selftest; perm tests non-deterministic; cross-compiler deltas expected |
| 95 | I | closed | restart alpha = 0.01/(r+c) wrong | ea_restart | restart_main.cpp | not spec alpha 0.000005 | wrong cutoff | restart verdict | verdict | PR #98 (simulation) |
| 96 | I | closed | bad_alloc on 10M-byte file | ea_non_iid | lrs_test.h (old) | memory | crash | no | crash/perf | "machine limit"; SA/LCP (#98) fixed |
| 97 | I | closed | segfault in iid path on 12.5M samples | ea_iid | permutation_tests.h (large stack arrays + OpenMP) | stack arrays | segfault | no | crash | PR #99 (dynamic alloc) |
| 98 | PR | closed | OpenMP perms, divsufsort SA, chi fixes, restart simulation | ea_iid, shared, ea_restart | many | — | — | yes | — | merged; closes #51 #52 #53 #55 #56 #61 #78 #79 #82 #86 #88–#93 #95; "fixes a problem in the underlying SP" (restart) |
| 99 | PR | closed | perm tests large datasets, getopt, relEpsilonEqual overflow corner | ea_iid, all | permutation_tests.h, *_main.cpp, utils.h relEpsilonEqual | — | — | — | — | merged; closes #97 #66 #100 #101 #102 |
| 100 | I | closed | ea_iid verbose flag not optional | ea_iid | iid_main.cpp argc check | — | usage failure | no | none | PR #99 (options must precede file on macOS getopt) |
| 101 | I | closed | 1-bit data: H_original printed as 1.000000 | ea_non_iid | non_iid_main.cpp | no estimator updated H_original | meaningless H_original | yes (report) | HIGH (report) | PR #99 |
| 102 | I | closed | ea_conditioning accepts non-integer n_in/n_out/nw | ea_conditioning | conditioning_main.cpp input parsing | no integer check | bad inputs accepted | yes | either | PR #99 |
| 103 | I | closed | predictors: skip P_local search when irrelevant | ea_non_iid | utils.h predictionEstimate | — | slow | no | perf | PR #104 |
| 104 | PR | closed | speedups (predictors, compression G, binary MultiMMC/LZ78Y) | ea_non_iid | utils.h, compression_test.h, multi_mmc/lz78y | — | — | no (a pre-merge LZ78Y N off-by-15 bug found & fixed in review) | — | merged; resolves #103 #105 #106 |
| 105 | I | closed | compression G can stop early | ea_non_iid | compression_test.h G | — | slow | no | perf | PR #104 |
| 106 | I | closed | binary MultiMMC/LZ78Y fast tables 2^(A+2) | ea_non_iid | multi_mmc_test.h binaryMultiMMCPredictionEstimate, lz78y_test.h binaryLZ78Y… | — | slow | no | perf | PR #104/#118 (this is the code of #257) |
| 107 | I | closed | conversion2 applied before numRunsMedian/lenRunsMedian | ea_iid | permutation_tests.h consecutive_runs_tests | spec 5.1.5/5.1.6: no conversion | wrong stats (binary) | IID verdict | verdict | PR #111 |
| 108 | I | closed | binary len%8≠0 → alt_sequence lengths wrong | ea_iid | permutation_tests.h conversion1/2 users | length L/8 not ceil | wrong stats | IID verdict | verdict | PR #111 |
| 109 | I | closed | find_collisions simpler | ea_iid | permutation_tests.h find_collisions | — | slow | no | perf | PR #111 |
| 110 | I | closed | conversion2 bit shift wrong | ea_iid | permutation_tests.h conversion2 | `<<(8-((i+1)%8))` | values up to 382, LSB always 0 | IID verdict | verdict | PR #111 |
| 111 | PR | closed | binary permtest fixes | ea_iid | permutation_tests.h | — | — | — | — | merged; resolves #107–#110 |
| 112 | PR | closed | Kaufer t-tuple/LRS algorithm | shared | lrs_test.h SAalgs | — | — | no | perf | merged |
| 114 | I | closed | wide MultiMMC new postfixes | ea_non_iid | multi_mmc_test.h (generic) | (none) | — | — | none | **not a bug** (retitled by joshuaehill); closed via #118 |
| 115 | I | closed | wide LZ78Y adds prefixes in wrong order | ea_non_iid | lz78y_test.h LZ78Y_test (generic) | increasing not decreasing B (§6.3.10 3a) | different dictionary | yes | either | PR #118 |
| 116 | I | closed | 1-bit data: H_original labelled H_bitstring | ea_non_iid | non_iid_main.cpp | labeling | wrong label | no | reporting | PR #118 |
| 117 | I | closed | LRS memset uses sizeof (32 bytes) | shared | lrs_test.h | typo | possible heap overflow if v small | no | mem | PR #118 |
| 118 | PR | closed | self tests, harmonized binary/non-binary MMC/LZ78Y, width inference, -l subset, epsilon, transpose | all | utils.h read_file_subset, multi_mmc, lz78y, non_iid_main, iid_main | — | — | yes | — | merged; resolves #94 #114 #115 #116 #117 #119 #121 #122; introduced width inference (→ #254) and -l (→ #260) |
| 119 | I | closed | ea_iid never computes H_bitstring | ea_iid | iid_main.cpp | missing | H_bitstring absent | yes | HIGH (possible) | PR #118 |
| 120 | PR | closed | stray stderr debug; LRS "v<u" message gated | ea_iid, shared | chi_square_tests.h, lrs_test.h | — | — | no | reporting | merged; joshuaehill: v<u message should print even non-verbose (no information from LRS) |
| 121 | I | closed | tools can't support IID claim (no column dataset) | ea_restart/ea_transpose | — | missing column-data IID testing | IID claim incomplete | IID claim | verdict | PR #118 adds ea_transpose; later #222/#244/#250 |
| 122 | I | closed | uninitialized max_key in max_map | shared | utils.h max_map | uninit var | static-analysis warning | no | none | removed in PR #118 |
| 124 | I | closed | print version number | all | — | — | provenance | no | reporting | `--version` on all executables (celic 2022-07) |
| 125 | I | closed | silly t-tuple (t=5878) on 84M-sample file | ea_non_iid | lrs_test.h SAalgs | user converter buffer overrun duplicated data | 0.0036 bit/bit | yes (correctly) | none | **not a bug** (joshuaehill verified repeat of 6373 exists); intra-symbol bit reversal changes results (expected) |
| 127 | I | closed | -t doesn't truncate non-binary data | ea_non_iid | non_iid_main.cpp:242 | by design | -t = -a results | no | none | **by design**: -t truncates only bitstring for H_bitstring (§3.1.3); use -l |
| 128 | I | closed | double/long double insufficient in ea_conditioning | ea_conditioning | conditioning_main.cpp | precision near full entropy | wrong epsilon/h_out | yes | either | PR #129 → #136 (MPFR) |
| 129 | PR | closed | MPFR conditioning + restart docs | ea_conditioning | conditioning_main.cpp | — | — | — | — | not merged; split into #136/#137 |
| 131 | I | closed | const char* → char* cast into bzip | ea_iid | permutation_tests.h compression | API mismatch | potential UB | no | mem | PR #134 |
| 132 | I | closed | collision step 7 is a quadratic; clamp X̄'<2 | ea_non_iid | collision_test.h col_exp / collision_test | search vs closed form | nonsensical result if X̄'<2 | yes | either | PR #134 (UL comment 19) |
| 133 | I | closed | predictors: x from 10 fixed iterations | ea_non_iid | utils.h prediction_estimate_function | spec says 10 iterations | inadequate/unneeded precision | tiny | either | PR #134: iterate until stable — **intended deviation** = **F08** |
| 134 | PR | closed | compression cast fix, P_local, collision closed form, lag ring buffer, Markov | ea_iid/ea_non_iid | several | — | — | tiny | — | merged 2020-08-13; joshuaehill lists spec deviations for celic |
| 136 | PR | closed | ea_conditioning arbitrary precision | ea_conditioning | conditioning_main.cpp | — | — | yes | — | merged 2021-12-10; resolves #128, fixes #168 |
| 139 | PR | closed | -t with -i doesn't truncate data.len (t-tuple on 1-bit > 1M) | ea_non_iid | non_iid_main.cpp:242 | by design | different result vs expectation | yes | either | **declined**: -t is §3.1.3 bitstring truncation; use -l; under -c all data is bitstring (§3.1.5.2) |
| 140 | I | closed | -t description misleading | ea_iid/ea_non_iid | usage text | — | confusion | no | reporting | PR #137 |
| 141 | I | closed | Lag predictor needs fewer comparisons | ea_non_iid | lag_test.h | — | slow | no | perf | PR #134 (ring buffer) |
| 144 | PR | closed | JSON output (ACVP-like ESV API) | ea_iid/ea_non_iid | *_main.cpp, TestRun/TestCase | — | — | no | reporting | merged; review: getopt `l:` lost (→ #191) |
| 149 | I | closed | why constant 35 in t-tuple/LRS | spec | lrs_test.h | spec constant | — | — | none | spec-mandated (joshuaehill) |
| 150 | I | closed | why windows 63/255/1023/4095 | spec | multi_mcw_test.h | spec constant | — | — | none | spec-mandated, somewhat arbitrary (joshuaehill) |
| 151 | PR | closed | ea_iid LRS test Pr(X≥1)=0 from double precision | ea_iid | lrs_test.h len_LRS_test | 1−p_col^W rounds to 1 | test verdict wrong | IID verdict | verdict | not merged; superseded by #152 |
| 152 | PR | closed | log-domain LRS test precision | ea_iid | lrs_test.h len_LRS_test | — | — | — | — | merged; resolves #153 |
| 153 | I | closed | LRS IID test precision (p_col^W < DBL_EPSILON / DBL_MIN) | ea_iid | lrs_test.h len_LRS_test | precision | incorrect verdicts | IID verdict | verdict | PR #152 |
| 155 | I | open | Windows10 selftest deltas >1e-10 | all (Windows) | selftest compare | platform math; long int 32-bit | deltas ~1e-10 | tiny | either | not supported on Windows (celic); tolerance empirical |
| 161 | I | closed | ea_restart H_r 0.02 vs per-row ea_non_iid ≥3.9 | ea_restart | restart_main.cpp | user misunderstanding | low H_r | yes (correct) | none | **not a bug**: H_r computed on single 1M row dataset (§3.1.4.1), not min of per-row runs |
| 162 | PR | open | bit-packed input (-p), read_file refactor, deterministic seed | shared I/O, ea_transpose | utils.h read_file_subset, seed | — | — | — | — | open, unmerged; joshuaehill: packing order must be explicit |
| 163 | I | closed | stuck in LRS estimate (1–20 MB) | ea_non_iid | lrs_test.h SAalgs | O(n·v), v = 656,384 | hours/days | no (value ~0 correct) | hang/perf | **not a bug** (joshuaehill) — **KNOWN (BRIEF)** |
| 166 | PR | closed | subset reporting; compression −1 used in min | ea_non_iid, ea_iid, ea_transpose | non_iid_main.cpp compression block | error return −1 folded into min | overall assessment −1.0 | yes | LOW (−1) | merged 2021-12-03 |
| 168 | I | open | ea_conditioning h_out = nan | ea_conditioning | conditioning_main.cpp (p_low) | p_low underflows to 0 | nan | yes | either | fixed by PR #136 (merged); issue left open |
| 170 | I | closed | LRS P_W denominator overflows 32-bit long | shared (LLP64) | lrs_test.h / utils.h n_choose_2 | C(L−W+1,2) in long | H_original inf, H_bitstring 0.13 | yes | either | PR #175 (int64 + rollover asserts); **tool requires 64-bit long** |
| 171 | I | closed | collision perm tests record j not j+1 | ea_iid | permutation_tests.h find_collisions | index convention | C=[2,3,1] vs spec [3,4,2] | no (order-preserving) | none | PR #173 |
| 173 | PR | closed | fix #171 | ea_iid | — | — | — | — | — | merged |
| 175 | PR | closed | 64-bit binomial + rollover asserts | shared | lrs_test.h / utils.h | — | — | — | — | merged; resolves #170 |
| 177 | I | closed | JSON merge dropped compression validity check | ea_non_iid | non_iid_main.cpp compression block (~296) | missing `ret >= 0` | −1 folded into min | yes | LOW (−1) | fixed in v1.1.1 (celic) |
| 178 | I | closed | check invalid (<0) results for all estimators | ea_non_iid, ea_conditioning | non_iid_main.cpp LRS block; conditioning_main.cpp bin_lrs_res | missing `>= 0` guards | −1 folded into min | yes | LOW (−1) | fixed (guards at non_iid_main.cpp:375/381, conditioning_main.cpp:410) |
| 179 | I | closed | JSON TestCase values incomplete/inconsistent; only literal saved | ea_non_iid | non_iid_main.cpp / non_iid_test_case.h | JSON struct | missing bitstring intermediates | no | reporting | PR #182 (partial); PR #174 review comments |
| 182 | PR | closed | JSON both hBitstring and hOriginal | ea_non_iid | non_iid_main.cpp | — | — | no | reporting | merged |
| 183 | I | closed | ea_restart JSON may not flag failure | ea_restart | restart_main.cpp | failure paths w/o JSON | no/incorrect JSON on fail | restart verdict (report) | reporting | PR #187 |
| 184 | I | closed | JSON patches change outputs at some verbose levels | all | *_main.cpp | verbosity | output change | no | reporting | PR #187 |
| 185 | I | closed | booleans compared with −1 | all | test case code | tri-state bool | UB | no | mem (UB) | PR #187 |
| 186 | I | closed | `optarg == "iid"` pointer compare | ea_conditioning | conditioning_main.cpp | char* compare | option never matches | yes (iid path unreachable) | either | PR #187 |
| 187 | PR | closed | verbose levels 0–3, quiet mode, restart JSON error, bool fix | all | — | — | — | — | — | merged; resolves #183–#186 |
| 189 | I | closed | segfault: compression msg buffer off-by-one (NUL) | ea_iid | permutation_tests.h compression (~297) | missing +1 | heap overflow, k≤10 | no | mem/crash | PR #190 |
| 190 | PR | closed | fix #189 + ea_iid verbose consistency | ea_iid | — | — | — | — | — | merged |
| 191 | I | closed | segfault when -l used | ea_iid, ea_non_iid | *_main.cpp getopt string | `l` lost its `:` in JSON merge | segfault | no | crash | PR #192 |
| 192 | PR | closed | getopt `l:` regression fix | — | — | — | — | — | — | merged |
| 194 | PR | closed | bugfix/duplicate output (NIST) | ? | ? | (no body) | duplicate output | no | reporting | merged 2022-08-23 |
| 195 | I | open | ea_restart core dump: assert k_max ≤ k when data narrower than declared | ea_restart | restart_main.cpp simulateBound `assert(k_effective <= k)` (:133) | H_I implies more symbols than alphabet | SIGABRT, no JSON | no figure | crash | open; joshuaehill: expected to reduce claim — lower H_submitter |
| 197 | I | open | n·H_bitstring < H_original meaning | spec | — | — | — | — | none | joshuaehill: binary-only estimators; dj-on-github (non-maintainer): compression "over-punishes positive serial correlation — a bug in the spec" |
| 198 | PR | closed | bugfix/duplicate output (celic) | ? | ? | (no body) | duplicate output | no | reporting | merged 2022-09-09 |
| 199 | I | closed | ea_iid JSON perm counts differ from terminal | ea_iid | permutation_tests.h populateTestCase | wrong indices into JSON | wrong JSON C[i,*] | IID verdict in JSON | verdict (HIGH possible) | PR #200; joshuaehill: ESV IID JSON was broken and "could cause IID testing to incorrectly pass" |
| 200 | PR | closed | fix #199 | ea_iid | — | — | — | — | — | merged |
| 201 | PR | closed | avoid deprecated OpenSSL SHA256 API | all | TestRunUtils.h sha256_file | — | — | no | reporting | merged; introduced bugs → #202–#206 |
| 202 | PR | closed | sha256_file fileLength/fileLen compile | all | TestRunUtils.h | — | build break | no | none | not merged; superseded by #204 |
| 203 | I | closed | selftest: double free in sha256_file | all | TestRunUtils.h sha256_file | two fclose() | abort | no | crash/mem | PR #204 |
| 204 | PR | closed | fix sha256_file (compile, const, leak, errors, double fclose); conditioning h' and leaks | all, ea_conditioning | TestRunUtils.h, conditioning_main.cpp | — | — | yes (#210) | — | merged 2023-01-10; resolves #203 #205 #206 #210 #211 |
| 205 | I | closed | compile error fileLen | all | TestRunUtils.h | — | build break | no | none | dup #202 → PR #204 |
| 206 | I | closed | TestRunUtils.h bugs (fileLen, double fclose) | all | TestRunUtils.h | — | abort | no | crash | PR #204 |
| 208 | I | closed | v1.1.5 master "double free or corruption" | all | TestRunUtils.h | same as #203 | abort | no | crash | use release; PR #204 |
| 209 | I | closed | why X_cutoff instead of §3.1.4.3 formula | ea_restart / spec | restart_main.cpp simulateBound | — | — | — | none | **intentional deviation**: spec binomial formula incorrect; cutoff by simulation |
| 210 | I | closed | ea_conditioning non-vetted h' statistic wrong (binary always 1.0; IID wrong) | ea_conditioning | conditioning_main.cpp computeEntropyOfConditionedData | wrong logic | h'=1.0 for binary | yes | HIGH | PR #204 |
| 211 | I | closed | ea_conditioning mpfr/data leaks | ea_conditioning | conditioning_main.cpp | missing clears/free_data | leaks | no | mem | PR #204 |
| 212 | I | closed | X_cutoff differs Windows vs CentOS | ea_restart | simulateBound | stochastic + unsupported platform | 631 vs 608 | restart verdict | either | expected variation; Windows unsupported (LLP64) |
| 213 | I | closed | whole 8 MB file 0.156 vs ~7.35 per 1M block | ea_non_iid | lrs_test.h SAalgs (t-tuple) | real duplicates in data | low figure | yes (correct) | none | **not a bug** (joshuaehill, celic); 35 cutoff needs no scaling |
| 214 | I | closed | ea_non_iid "hangs" on 8 MB (v = 2,097,152) | ea_non_iid | lrs_test.h SAalgs :273/:495 | O(n·v) | days | no | hang/perf | **not an issue with ea_non_iid** (celic); user comment 2026-09-30 re-measured at 87c104d — **KNOWN (BRIEF)** |
| 217 | PR | closed | large files > 2G samples | shared | lrs_test.h, utils.h | — | — | — | — | not merged; superseded by #226 |
| 218 | PR | closed | missing SHA256 in conditioning output | ea_conditioning | conditioning_main.cpp | — | missing hash | no | reporting | merged |
| 219 | I | open | Windows MinGW: ea_iid LRS test Pr(X≥1) negative → Failed | ea_iid (Windows) | lrs_test.h len_LRS_test (+ user seed() change) | platform / library | wrong IID verdict | IID verdict | verdict (LOW) | open; Windows not supported |
| 220 | I | closed | ea_iid results unstable run-to-run | ea_iid | permutation tests | stochastic by design | pass/fail flips | IID verdict | none | **by design** (joshuaehill) |
| 221 | PR | closed | propagate file-read errors into JSON | all | utils.h read_file_subset / JSON | — | — | no | reporting | merged |
| 222 | PR | closed | restart: run IID tests on row/column data | ea_restart | restart_main.cpp | — | — | IID claim | — | merged 2023-06-15 (introduced the #244 bug) |
| 224 | PR | closed | faster adjustable restart simulation (inverted near-uniform worst case) | ea_restart | restart_main.cpp simulateBound/simulateCount | — | — | restart verdict | — | merged |
| 225 | PR | closed | full-entropy report per IG D.K Resolution 19 | ea_conditioning | conditioning_main.cpp | — | — | report | — | merged |
| 226 | PR | closed | large files (>2GS), divsufsort64; conditioning init fix | shared, ea_conditioning | lrs_test.h SAalgs64, utils.h | — | — | — | — | merged 2023-10-30 |
| 228 | I | closed | bad_alloc on 2.4 GB | ea_non_iid | lrs_test.h | ~25 B/symbol, bitstring 8× | abort | no | crash/perf | **"don't do that"** (joshuaehill) |
| 230 | PR | closed | JSON error for unexpected data width | shared/JSON | utils.h read_file_subset | — | — | no | reporting | merged (related #254) |
| 232 | PR | closed | better error messages (NIST) | all | — | — | — | no | reporting | merged |
| 233 | I | closed | restart passed though H_r ≪ H_c | ea_restart | restart_main.cpp | criterion misread | — | — | none | **not a bug**: fail iff min(H_r,H_c) < H_I/2 |
| 235 | PR | closed | always run both chi-square tests | ea_iid | chi_square_tests.h chi_square_tests | short circuit | — | no | reporting | merged |
| 236 | I | open | --version reports 1.1.7 on v1.1.8 | all | utils.h VERSION | manual macro | wrong provenance | no | reporting | fixed by PR #237 (VERSION "1.1.8" at 87c104d); issue open |
| 237 | PR | closed | VERSION 1.1.8 | all | utils.h | — | — | — | — | merged |
| 238 | I | open | JSON lacks samples tested / distinct symbols / width | JSON | test_run_base.h | — | missing fields | no | reporting | open (related #254 #255) |
| 239 | PR | closed | perm tests: run all 10,000, p-values | ea_iid | permutation_tests.h | — | — | — | — | not merged; early exit intentional (joshuaehill) |
| 244 | I | closed | restart IID perm tests on column data re-test row data; column rawsymbols missing | ea_restart | restart_main.cpp (~787-793, rdata vs cdata) | wrong buffer | column IID never tested | IID claim | verdict (HIGH: IID wrongly supported) | PR #250 (merged 2026-05-26); §3.1.2 bullet 3 |
| 245 | I | closed | ringOsc-nist.bin entropy too small | ea_non_iid | — | ring oscillators mostly deterministic | 0.126 | yes (correct) | none | **not a bug** |
| 246 | I | closed | ea_iid assert p_col ≥ 1/k fails | ea_iid | lrs_test.h:626 len_LRS_test; utils.h calc_proportions | Σ(1/n) rounding | SIGABRT | no | crash | PR #248 (merged 2026-05-26) |
| 247 | I | closed | ea_iid fails some ideal files; same file flips | ea_iid | permutation tests | stochastic, FP 1/1000 per test, ~2%/round | failures on good data | IID verdict | none | **by design**; verified vs Theseus n=100,000; notes #244 |
| 248 | PR | closed | calc_proportions integer counts | shared | utils.h calc_proportions | — | — | — | — | merged; resolves #246 |
| 250 | PR | closed | Section 5 testing on restart column data | ea_restart | restart_main.cpp | — | — | IID claim | — | merged; resolves #244 |
| 251 | PR | **open** | ea_iid JSON hAssessed at default verbosity | ea_iid | iid_main.cpp:285-313 (min() only inside `verbose > 2`) | reduction gated on verbosity | JSON hAssessed = word_size (8.0 vs 0.3197 on biased-random-bytes.bin) | yes (JSON) | HIGH (JSON) | **open, unmerged; present at 87c104d** |
| 252 | PR | **open** | ea_iid returns min-entropy even if IID tests fail | ea_iid | iid_main.cpp | no gate on IID pass | figure printed/JSON for failed IID | report | reporting (HIGH if consumed) | **open, unmerged** |
| 253 | I | open | two-valued multi-bit data assessed as binary; n×H_bitstring omitted | ea_non_iid (same gate in iid_main.cpp:280/289/299) | non_iid_main.cpp gates `alph_size > 2`/`== 2` (:244,263,285,292,305,312,325,334,351,375,395,…) | observed alphabet used instead of width | 0.9216 vs 0.1796 | yes | HIGH | PR #256 (open) — **KNOWN (BRIEF)** = F01 |
| 254 | I | open | default width inference narrows width; not in JSON | shared I/O | utils.h read_file_subset (:264-277, :429-443) | OR-of-bytes highest bit | n×H_bitstring changes up to 2.4× | yes | HIGH | open — **KNOWN** = F02 |
| 255 | I | open | sub-minimum samples & skipped estimators invisible in JSON | ea_non_iid / JSON | non_iid_main.cpp:245, `if (ret >= 0)` guards; test_run_base.h | warnings stdout-only; errorLevel 0 | JSON same as compliant run | yes | HIGH | open — **KNOWN** = F03+F05 (related #238) |
| 256 | PR | open | gate bitstring estimators on width | ea_non_iid | non_iid_main.cpp | — | — | yes | — | open, fixes #253 |
| 257 | I | open | heap over-read binaryMultiMMC 4≤L≤16 | ea_non_iid | multi_mmc_test.h:38 binaryMultiMMCPredictionEstimate | init loop reads S[d+1] to S[16] | ASan heap-buffer-overflow | yes (tiny L) | mem | PR #268 (open), dup PR #269 — **KNOWN** = F16 |
| 258 | I | open | literal MultiMCW skipped 64≤L≤4095; off-by-one message | ea_non_iid | multi_mcw_test.h:16-18 | `len < 4096` guard | estimator omitted | yes | HIGH | open (dup #265) — **KNOWN** = F04 |
| 259 | I | open | sha256_file unbounded read: hang on /dev/zero, FIFO | all executables | TestRunUtils.h:62+ sha256_file; call non_iid_main.cpp:179 (also iid_main.cpp:199, restart_main.cpp:247, conditioning_main.cpp:521) | read to EOF, no S_ISREG | hang, no output | no | hang | open (dup #266) — **KNOWN** = F18 |
| 260 | I | open | -l offset overflow; SHA-256 of whole file | shared I/O | utils.h:212/221 read_file_subset; non_iid_main.cpp:179 | unchecked index*size; hash of whole file | wrong block assessed; hash misidentifies | report | reporting/either | open (dup #267) — **KNOWN** = F19 |
| 261 | I | open | assert aborts on tiny/repeat-free inputs | ea_non_iid (asserts live) | lrs_test.h:149, multi_mmc_test.h:21, lz78y_test.h:17-18 | no length validation at intake | SIGABRT, no JSON | no | crash | open (dup #262) — **KNOWN** = F15 |
| 262 | I | closed | same as #261 (LZ78Y/MultiMMC checks disagree) | ea_non_iid | multi_mmc_test.h:156/158 order; lz78y_test.h:125-127 message | — | — | — | crash | closed not_planned as dup of #261 |
| 263 | I | open | compression admits 1001 blocks (v=1): σ̂ /0 | ea_non_iid | compression_test.h:106 guard, :131 | `num_blocks <= d` guard | σ̂ NaN→1.0 or inf→−0 | yes (tiny L) | either | PR #270 (open) — **KNOWN** (F11) |
| 264 | I | open | collision v≤1: σ̂ NaN, prints 1.0 | ea_non_iid | collision_test.h:42 | no v≥2 check | NaN compared vs 2.0/2.5 | no (aborts later) | HIGH (latent) | open — **KNOWN** (F12) |
| 265 | I | closed | MultiMCW skipped L<4096 (drift example) | ea_non_iid | multi_mcw_test.h | — | 3.19 vs 1.77 | yes | HIGH | dup of #258 |
| 266 | I | closed | sha256_file hang | all | TestRunUtils.h | — | hang | no | hang | dup of #259 |
| 267 | I | closed | -l samples=0, wrap, whole-file hash, short final block | shared I/O | utils.h:209-222 | — | — | report | reporting | dup of #260 |
| 268 | PR | open | guard binaryMultiMMC init loop `d+1 < L` | ea_non_iid | multi_mmc_test.h | — | — | — | — | open; fixes #257 |
| 269 | PR | closed | same fix as #268 | ea_non_iid | multi_mmc_test.h | — | — | — | — | closed (dup) |
| 270 | PR | open | compression requires ≥2 test blocks | ea_non_iid | compression_test.h | — | — | — | — | open; fixes #263 |

**Non-defect items** (pure usage/spec questions, build/platform help, docs-only, thanks, merges, style, cosmetic, declined features): usage/questions #2 #9 #10 #11 #30 #31 #37 #38 #39 #40 #42 #43 #47 #123 #130 #138 #147 #154 #159 #160 #165 #167 #196 #207 #223 #231; build/platform help #64 #68 #73 #74 #75 #83 #85 #113 #145 #148 #158 #164 #169 #180 #181 #216 #227 #229 #234 #241 #242 #243 #249; docs-only #36 #84 #137 #172 #176 #188; code style (open) #67 #81; cosmetic output #126 #135 #142; merges/discussion #146 #156 #157 #174; declined/new features #143 #193 #215 #240. (Several of these carry maintainer positions — see §3: #2/#31/#40 memory, #34/#123/#138/#147/#196 input format and width, #130/#207 restart format, #145/#180 platforms, #167/#223 interpretation, #174 JSON review comments.)

---

## 2. Indexes

### 2a. By source file / function (current tree at 87c104d)

- **non_iid_main.cpp / main**
  - bitstring-vs-literal gates on `alph_size > 2 / == 2` (not width): #253 #256 (history: #101 #116 #119)
  - `-t` truncation (:242, applies to `data.blen` only, also under `-c`): #127 #139 #140 #70
  - `< 1,000,000 samples` warning (:245) and `ret >= 0` skip guards: #255 #166 #177 #178 #120
  - SHA-256 call (:179): #259 #260 #266 #267 #201 #204
  - JSON test cases: #144 #179 #182 #174 #184 #187 #194 #198 #221 #232
  - getopt: #66 #99 #191 #192 (#144 review)
  - H_original/H_bitstring for 1-bit data: #101 #116
- **iid_main.cpp / main**: #100 #119 #191 #199 #200 #235 #251 (hAssessed only computed at verbose>2) #252 (min-entropy printed despite IID fail); same `alph_size > 2` bitstring gate as #253 at :280/:289/:299; #118 (processing aligned with 90B)
- **restart_main.cpp**
  - `simulateBound` / `simulateCount` (X_cutoff, simulation; `assert(k_effective <= k)` :133): #56 #95 #98 #209 #212 #224 #195 #247
  - IID tests on row/column restart data (~:737-815): #121 #222 #244 #250
  - JSON / failure reporting: #183 #187
  - compile (SIZE): #73 #74 #75 #85
  - semantics (row dataset, pass criterion): #161 #233 #130 #207 #37
- **conditioning_main.cpp**: Output_Entropy n #65 #87; integer inputs #102; precision/MPFR #128 #129 #136 #168; `bin_lrs_res` guard #178; `optarg=="iid"` #186; non-vetted h' statistic #210; leaks #211; init fix #217/#226; SHA256 #218; full-entropy report #225; question #159
- **transpose_main.cpp**: #121 #118 #162 #166
- **shared/utils.h**
  - `read_file_subset` / `read_file`: translation #147; bitstring from raw MSB-first #71 #72; width inference #118 #123 #254 #230 #195; `-l` offset/overflow/sentinel #260 #267 (#191 crash was getopt); packed input #162 #193; errors to JSON #221; large files #217 #226
  - `seed` / `xoshiro256starstar` / `randomRange64` / `FYshuffle`: #45 #48 #54 #77 #180 (needs __uint128_t) #219 (user replaced seed) #162
  - `calc_stats` (median): #82
  - `calc_proportions`: #246 #248
  - `divide`: #89
  - `max_map` (removed): #122
  - `relEpsilonEqual`: #99
  - `n_choose_2` / 64-bit: #170 #175
  - `prediction_estimate_function` / `calc_p_local` / `predictionEstimate`: #17 #19 #23 #50 #59 #103 #104 #133 #134 (F08, F24, F25)
  - ZALPHA: #22 #69 (F07)
  - VERSION: #124 #236 #237
- **shared/lrs_test.h**
  - `SAalgs32/64` (t-tuple + LRS estimates; accumulation loops :273/:495; assert :149): #44 #52 #53 #92 #96 #98 #112 #117 #120 #125 #139 #163 #170 #175 #213 #214 #217 #226 #228 #261 #262 (F15, F17, F30)
  - `len_LRS_test` / `calc_collision_proportion` (IID LRS test; assert :626): #151 #152 #153 #219 #246 #248
- **shared/TestRunUtils.h `sha256_file`**: #201 #202 #203 #204 #205 #206 #208 #259 #266 #260 #267
- **shared/test_run_base.h, test_case_base.h, TestCase.h, non_iid_test_case.h, iid_test_case.h (JSON)**: #144 #179 #182 #185 #187 #238 #255 #254
- **shared/most_common.h**: #22 (z) #182 (JSON fields); no C++ MCV defect filed
- **iid/permutation_tests.h**: shuffle/RNG #45 #48 #54 #77; stats #61 #76 #78 #79 #82 #107 #108 #109 #110 #131 #171 #173 #189 #190; threading/large data #86 #97 #99; early exit #41 #46 #55 #239; JSON counts #199 #200; progress #126 #135 #142; stochasticity #220 #247
- **iid/chi_square_tests.h**: #60 #62 #63 #88 #89 #90 #91 #93 #97 (calc_observed crash) #120 #235 (py: #4 #12 #28 #29)
- **non_iid/collision_test.h** (`F`, `col_exp`, `collision_test`): #17 #18 #19 #57 #69 #132 #134 #264 (F12)
- **non_iid/compression_test.h** (`G`, `com_exp`, `compression_test`): #49 #58 #69 #104 #105 #166 #177 #263 #270 #197 (non-maintainer spec claim) (F06, F11, F14)
- **non_iid/markov_test.h**: #134 (refinement); py history #13 #20 #21 #34 (F26)
- **non_iid/lag_test.h**: #134 #141; asserts :40-42 (F15 row)
- **non_iid/multi_mcw_test.h**: #258 #265 #150 (F04)
- **non_iid/multi_mmc_test.h**: #106 #114 #118 #257 #268 #269 #261 #262; py #2 #31 #40 (F09, F10, F16)
- **non_iid/lz78y_test.h**: #104 #106 #115 #118 #261 #262; py #3
- **Makefile / build**: #64 #68 #73 #75 #83 #87 #113 #158 (-ffloat-store) #164 #169 #181 #188 #216 #227 #229 #234 #241 #242 #243 #249
- **Legacy Python (removed)**: #1 #3–#7 #12–#29 #31–#35 #37–#41

### 2b. By executable

- **ea_non_iid**: #17–#23(py) #49 #50 #51 #52 #53 #57 #58 #59 #69 #70 #71 #72 #92 #96 #101 #103 #104 #105 #106 #112 #114 #115 #116 #117 #118 #120 #125 #127 #132 #133 #134 #139 #140 #141 #155 #163 #166 #170 #175 #177 #178 #179 #182 #191 #192 #213 #214 #217 #226 #228 #245 #253–#270
- **ea_iid**: #4–#7 #12 #14–#16 #28 #29 (py) #45 #46 #48 #54 #55 #60 #61 #62 #63 #76 #77 #78 #79 #80 #82 #86 #88 #89 #90 #91 #93 #97 #99 #100 #107–#111 #119 #120 #131 #135 #142 #151 #152 #153 #171 #173 #189 #190 #191 #199 #200 #219 #220 #235 #239 #246 #247 #248 #251 #252 (+ shared: #253-style gate in iid_main.cpp, #254, #259, #260)
- **ea_restart**: #37 #41 (py) #56 #73 #74 #75 #85 #95 #98 #121 #130 #161 #183 #187 #195 #207 #209 #212 #222 #224 #233 #244 #247 #250 (+ shared #259)
- **ea_conditioning**: #65 #87 #102 #128 #129 #136 #159 #168 #178 #186 #187 #204 #210 #211 #217 #218 #225 #226
- **ea_transpose**: #118 #121 #162 #166
- **shared I/O** (read_file_subset, translation, width, -l, sha256_file): #71 #72 #118 #123 #147 #162 #166 #191 #193 #201–#206 #208 #215 #217 #221 #226 #230 #254 #259 #260 #266 #267
- **JSON / reporting**: #124 #144 #146 #156 #157 #174 #179 #182 #183 #184 #185 #187 #194 #198 #199 #200 #218 #221 #230 #232 #236 #237 #238 #251 #252 #254 #255 #260
- **platform/portability (LLP64, 32-bit, Windows, ARM, flags)**: #155 #158 #164 #170 #175 #180 #212 #219

---

## 3. Maintainer positions (re-reporting these = rediscovery)

"J" = joshuaehill (principal code author; merged by NIST), "C" = celic (NIST), "K" = kerrymckay (NIST).

1. **Sample width ≤ 8 bits; wider data must be mapped down by the submitter (§6.4) before the tool** — K #8; J #34 #138 #196 ("splitting a 64-bit sample into 8 bytes … would cause the tool to produce nonsense").
2. **Input is 1 symbol per byte, in production order; packed/bit ordering must be explicit** — J #123 #125 #147 #193 #162 #196; K #1.
3. **Default width = smallest width that contains all observed values (inference is the design)** — J #123 (PR #118); C added only a JSON error for unexpected width (#230). Filed disagreement: #254.
4. **Symbols are translated to [0,k−1]; non-IID estimators are categorical or order-invariant, so translation doesn't matter** — J #147.
5. **H_bitstring is built from raw (untranslated) values, MSB-first; the bit order is a free convention, 90B doesn't specify it** — J #71/#72; **bit-reversing samples changes results (expected); encoding the final symbols {0,1} vs {0,0x80} should not change non-IID results (may change permutation tests)** — J #125. ⇒ F21, F22 known/by design.
6. **`-t` only truncates the bitstring used for H_bitstring (§3.1.3 para 3), never H_original data; no effect on binary data; use `-l` to subset; J recommends not using `-t`; under `-c` (§3.1.5.2) all data is treated as a bitstring and only H_bitstring is assessed** — J #70 #127 #139 #140 (PR #139 declined).
7. **z_α uses full double precision 2.5758293035489008, not the printed 2.576** — J #22 (resolved PR #69; "applies to the 90B-final C++ version as well"). ⇒ F07.
8. **Prediction estimators iterate the x recurrence to convergence rather than the spec's 10 iterations ("resolves a nominal scientific computing issue present within the original 90B specification")** — J #133/#134, accepted by C. ⇒ F08.
9. **Collision step 7 solved in closed form (quadratic; F(z)=2z³+2z²+z for k=2); X̄′<2 clamps to p=1; lag step 3 done via ring buffer — "fancy ways of implementing exactly what is written"** — J #57 #132 #134 #141.
10. **When a search cannot find p, the estimator falls back to the bound that yields full entropy "as per the standard"** — J #69. (Related: "Could Not Find p. Proceeding with the lower bound for p" in #263/#264.) ⇒ F06 context.
11. **Collision and compression estimators are expected to commonly underestimate (Hagerty–Draper worst-case construction); for other source types all 90B estimators overestimate; black-box estimation is impossible (a PRNG scores high); H_submitter design analysis is required** — J #70 #223 #47 #138. ⇒ F28, F29 are spec limitations.
12. **Estimators that return < 0 ("could not run") are excluded from the minimum — that is intended; the bugs fixed were cases where −1 leaked into the minimum** — J/C #166 #177 #178. **The LRS "v<u" condition should be reported even in non-verbose mode ("no information from the LRS test")** — J #120. (Visibility gap filed as #255.)
13. **LRS/t-tuple run in O(n·v) (v = LRS length); near-quadratic run time on long repeats is expected and "not an issue with ea_non_iid but … the low-entropy file"** — J #44 #163 #214; C #214. ⇒ F17.
14. **t-tuple 35-occurrence cutoff needs no scaling with L; large-L results are correct** — J #213 (C agreed). **Constants 35 and MultiMCW windows 63/255/1023/4095 are spec-mandated** — J #149 #150.
15. **Memory exhaustion on very large inputs is a machine limit (~25 B/symbol; bitstring up to 8×): "don't do that"** — J #96 #228; J #31 (MultiMMC memory by spec); K #40 (final MultiMMC caps counters).
16. **Non-binary GOF expectation is deliberately (c_i/L)·floor(L/10), deviating from the 90B text** — J #91. **Non-binary independence uses floor(L/2)** — J #62.
17. **Restart X_cutoff is computed by simulation (inverted near-uniform worst case) because the §3.1.4.3 binomial formula is incorrect ("fixes a problem in the underlying SP"); the cutoff is stochastic (default ≈2e6 rounds, `-s` to raise)** — J #56 #95 #98 #209 #212 #224 #247.
18. **Restart: H_r/H_c are computed on the single 1,000,000-sample row/column datasets, not the minimum of per-row assessments; fail iff min(H_r,H_c) < H_I/2; no H_r-vs-H_c comparison** — J #161 #233. **Data narrower than the declared width (assert k_effective ≤ k) means the claim must be lowered, not a tool bug** — J #195 (open).
19. **§3.1.2 bullet 3 requires Section 5 IID tests on restart row AND column datasets** — J #244 (fixed #250). Earlier J briefly argued the tests were not required, then retracted.
20. **Permutation tests are stochastic: per-test type-I rate 1/1000, ≈1.9–2.1 % per full round; failures on ideal data and run-to-run flips are expected; §5.1 says so; there is no failure-rate threshold; KATs don't apply** — J #41 #94 #220 #247. **Early exit once a test's pass is decided is intentional (all 10,000 rounds run only on failure)** — J #239 (PR declined).
21. **Collision permutation-test statistic off by one does not affect verdicts (order-preserving)** — J #171.
22. **Tool assumes LP64 (64-bit `long`); Windows/LLP64 and 32-bit platforms are unsupported and may give wrong results; rollover is caught by asserts, not fixed** — J #155 #170 #212; C #145 #155 #180; `randomRange64` needs `__uint128_t` (J #180).
23. **`-ffloat-store` and OpenMP are expected; cross-compiler/platform deltas ≈1e-10 are expected; selftest tolerance 1e-10 is empirical** — J #94 #155 #158.
24. **Python tool is obsolete (2016 draft), unsupported, "a bunch of bugs that aren't fixed"; only C++ is supported; use tagged releases, not master** — J #163 #176 #205; C #143 #176 #227.
25. **Markov: p_max is the probability of the most likely 128-symbol string (tiny value is expected)** — J #13; **final 90B Markov has no confidence term** (draft issues #20/#21 "addressed in the final document"). ⇒ F26 spec-consistent.
26. **Wide MultiMMC counting of new postfixes is correct** — J #114.
27. **n·H_bitstring < H_original is legitimate (binary-only estimators)** — J #197. (Non-maintainer claim in #197 by dj-on-github: compression "over-punishes positive serial correlation … a bug in the algorithm in the spec".)
28. **IID JSON counts on the ESV server were wrong and "could cause IID testing to incorrectly pass"** — J #199 (fixed #200). **IID path returns a min-entropy only meaningful if IID passes** — open PR #252.
29. **Conditioning: n = min(n_out, nw, n_in)** — J #65; **full-entropy verdict per IG D.K Resolution 19, arbitrary-precision MPFR** — J/C #136 #225.
30. **Draft-era spec questions resolved by the final 90B text (not code bugs)**: binary chi-square independence/GOF construction #28 #29; Markov α / Hoeffding #20 #21; 6-bit Markov mapping #34; draft restart construction "really very flawed" #37.

---

## 4. Local audit rows F01–F30 → upstream mapping

- **F01** two-valued multi-bit data assessed as binary → **#253** (PR #256 open). Same root cause also in `iid_main.cpp:280/289/299` (H_bitstring gate) — treat as duplicate of #253.
- **F02** default width inference → **#254**; design stance J #123 / PR #118; related #230, #195, #238.
- **F03** sub-minimum sample count invisible in JSON → **#255** (related #238).
- **F04** literal MultiMCW skipped 64≤L≤4095 + off-by-one text → **#258** (dup #265).
- **F05** skipped (−1) estimators silently omitted → **#255**; intended-skip stance #166/#177/#178; "v<u should be reported" J #120. De Bruijn LRS v<u ≥1e6 claim not filed (unverified).
- **F06** compression step 8 → 1.0 on sampling-without-replacement sources → **no upstream item**; spec-literal (J #69 "assigned full entropy, as per the standard"; J #70/#223 estimator limits; #197 non-maintainer claim about compression). Spec limitation.
- **F07** Z_α = 2.5758293035489008 vs printed 2.576 → **#22** (closed; full precision intentionally adopted via PR #69).
- **F08** P_local x iterated to convergence → **#133 / PR #134** (merged; intentional deviation).
- **F09** generic MultiMMC: Null prediction doesn't reset run → **no upstream item** (nearest: #114 "not a bug", #118 harmonization, UL cross-check ≤2e-11). Unverified.
- **F10** generic MultiMMC lookup skips deeper orders when a shallower prefix is absent → **no upstream item** (nearest: #114, #118, #40 counter cap). Unverified.
- **F11** compression v=1 (1001 blocks) divide-by-zero → **#263** (PR #270 open) — filed despite local "did not reproduce dangerous direction".
- **F12** collision v≤1 NaN → **#264**.
- **F13** NaN folded by `std::min` → **no upstream item for NaN**; producers #263/#264; −1-leak analogues #166 #177 #178.
- **F14** compression `dict[]` unsigned int index above 2^32 blocks → **no upstream item** (adjacent: large-file support #217/#226, 64-bit overflow asserts #170/#175, LP64 stance).
- **F15** assert aborts on tiny/repeat-free inputs → **#261** (dup #262); related #246/#248 (assert in `len_LRS_test`, fixed), #195 (restart assert, open).
- **F16** binary MultiMMC heap over-read 4≤L≤16 → **#257** (PR #268 open; dup PR #269).
- **F17** quadratic LRS on repetitive input → **#214 / #163 / #52** (+#44 #53 #96; user comment on #214). Known, maintainer "not an issue".
- **F18** hang on /dev/zero, FIFO (sha256_file) → **#259** (dup #266).
- **F19** `-l` overflow / samples=0 / short block / whole-file SHA-256 → **#260** (dup #267); distinct from fixed #191.
- **F20** `-t` truncation also applied under `-c` → **no exact upstream item**; semantics of `-t` fixed by maintainers in #127/#139/#140 (and J #139: under `-c` all data is a bitstring). Treat as adjacent; the `-c`+`-t` combination itself was never discussed.
- **F21** MSB-first bit order within a symbol → **#71** (J: convention, 90B unspecified); **#125** (bit reversal changes results — expected). Known/by design.
- **F22** H_bitstring from raw values → encoding-dependent → **#71 / PR #72** (deliberate design), #125, #147.
- **F23** JSON/reporting: only literal intermediates in JSON; `-c` JSON hAssessed = word_size×h′ vs text h′; `%f` rounding → partially **#179 / #182 / PR #174 review** (literal-only JSON); IID analogue **#251** (hAssessed at default verbosity). The `-c` hAssessed and 6-decimal rounding points have no upstream item.
- **F24** prediction_estimate_function converges to x=1/p; FMA NaN vs −inf → **no upstream item** (nearest #133/#134, #23, #59).
- **F25** calc_p_local exits / precision for large N → **no upstream item** (nearest #50 #59 #133 #134; cross-platform deltas #155).
- **F26** Markov point estimate, no ε → spec-consistent; **#20/#21** (draft ε removed in final 90B); #13 #34.
- **F27** Appendix G.2 Table 3 labels offset by 5 → spec erratum; **no upstream item**.
- **F28** deterministic sources score near full entropy → spec limitation; **J #223 #70 #47** (black-box estimation impossible).
- **F29** per-estimator blind spots → spec limitation; **J #70 #223**, #150 (arbitrary windows).
- **F30** LRS estimates collision entropy, exceeds min-entropy → spec-consistent; **J #163** ("W-tuple collision entropy"); no defect item.

---

## 5. Quick dedup rules (root-cause families already known)

- Bitstring branch chosen by observed alphabet (`alph_size`) instead of width — any executable (non_iid, iid) → #253.
- Width inferred from data / narrower-than-declared handling / width absent from JSON → #254 (restart variant → #195).
- Anything about degraded runs not flagged in JSON/errorLevel (short L, −1 estimators, missing counts) → #255 / #238; IID JSON hAssessed → #251; IID figure after failed IID → #252.
- No minimum-length validation before estimators (asserts, over-reads, NaN from v≤1, v=1 blocks) → #261 / #257 / #263 / #264 (+#258 for MultiMCW threshold).
- Input path I/O: unbounded hash read → #259; `-l` arithmetic/hash scope → #260; getopt `-l` → #191.
- LRS/t-tuple time or memory on repetitive/huge inputs → #214/#163/#52/#53/#96/#228.
- IID permutation-test stochasticity, early exit, per-run flips → #220/#247/#239; restart cutoff stochasticity → #212/#247.
- LLP64/32-bit/Windows numeric differences → #155/#170/#212/#219 (unsupported platform stance).
- `-t`/`-a` semantics → #127/#139/#140.
- Bit order / encoding dependence of H_bitstring → #71/#125.
- Spec-constant precision (z_α, 10-iteration x, collision/lag closed forms) → #22/#133/#132/#141.
