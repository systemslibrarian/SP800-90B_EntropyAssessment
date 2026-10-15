# Candidate clusters — 2026-10-11/12 independent audit

Twelve auditors worked independently, so the same defect was often reported
more than once from different directions. These clusters group the 119 raw
candidates into the 23 distinct defects they actually describe, which is the
unit the verification phase judged and the unit the report presents.

A cluster with several members is **already corroborated**: independent
auditors, working different subsystems and unaware of each other, arrived at
the same place. For those clusters the verification phase was told not to
spend its budget re-reproducing what five people had already reproduced, and
to settle prior art, upstream relation and severity instead. Clusters with one
member, or with a numeric claim that mattered, got the full three lenses.

| Cluster | Members | Highest severity claimed | Lenses applied |
|---|---:|---|---|
| `C01-multimmc-chained` | 1 | High | refute, repro, impact |
| `C02-c-mode-hassessed` | 1 | High | refute, repro, impact |
| `C03-iid-verdict-not-in-status` | 3 | High | refute, repro, impact |
| `C04-chisq-negative-df` | 2 | High | refute, repro, impact |
| `C05-restart-k-effective` | 1 | High | refute, repro, impact |
| `C06-cond-width-inference` | 1 | High | impact |
| `C07-lrs-underflow-abort` | 5 | High | refute, impact |
| `C08-harness-cannot-fail` | 14 | High | refute, impact |
| `C09-cond-no-intake-checks` | 4 | Medium | refute, impact |
| `C10-restart-stats-zero` | 3 | Medium | refute, impact |
| `C11-c01-scalar-delete` | 1 | Medium | impact |
| `C12-sha256-stack-overread` | 1 | Medium | refute, repro, impact |
| `C13-errmsg-format-string` | 5 | Low | refute |
| `C14-report-contract` | 8 | Medium | refute, impact |
| `C15-negative-zero` | 4 | Low | refute |
| `C16-permissive-parsing` | 6 | Low | refute |
| `C17-platform-divergence` | 4 | Low | refute |
| `C18-llp64-overflow` | 3 | Low | refute |
| `C19-docs-drift` | 12 | Medium | refute |
| `C20-openmp-race` | 3 | Low | refute |
| `C21-cond-misc` | 12 | Low | refute |
| `C22-predictor-numerics` | 12 | Low | refute |
| `C23-misc-reporting` | 13 | Low | refute |

## C01-multimmc-chained

**Lead candidate.** `predictors-1` — MultiMMC's chained prefix lookup suppresses subpredictions that SP 800-90B 6.3.9 step 4.b.i requires, once the depth-d dictionary fills one round before depth d+1 (F10 confirmed)

**What the verification phase was asked to settle.** F10 was UNCONFIRMED in the prior tracker; this is the first execution-confirmed report, and it claims an overestimate direction on a supported path. Verify the chained-vs-unchained spec reading of 6.3.9 step 4.b.i, the maxEntries=100000 mechanism, and both fixtures' C/r/H digit for digit.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `predictors-1` | High | `predictors` | yes | overestimate | MultiMMC's chained prefix lookup suppresses subpredictions that SP 800-90B 6.3.9 step 4.b.i requires, once the depth-d dictionary fills one round before depth d+1 (F10 confirmed) |

## C02-c-mode-hassessed

**Lead candidate.** `output-automation-contracts-1` — Under -c the JSON reports hAssessed as word_size x h' (per symbol) while the spec, the usage text and the default console line all give h' per bit, and nothing in the report identifies the mode

**What the verification phase was asked to settle.** Claims the -c JSON reports hAssessed as word_size x h' (per symbol) while console/usage/spec give per bit. An overestimate in the machine-readable field is the worst case for this fork's purpose. Check against intake-noniid-aggregation-4's weaker -c claim.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `output-automation-contracts-1` | High | `output-automation-contracts` | yes | overestimate | Under -c the JSON reports hAssessed as word_size x h' (per symbol) while the spec, the usage text and the default console line all give h' per bit, and nothing in the report identifies the mode |

## C03-iid-verdict-not-in-status

**Lead candidate.** `output-automation-contracts-2` — ea_iid exits 0 with errorLevel 0, "IID": true and an hAssessed figure when all three Section 5 batteries fail; a pipeline reading the exit status sees a successful IID assessment

**What the verification phase was asked to settle.** Three reports: ea_iid exits 0 with 'IID': true when all three Section 5 batteries fail; the JSON IID field is a compile-time constant; ea_restart -i gives errorLevel 0 and an estimate after a failed IID test. Relate to upstream #252 and to the repair branch's fail-closed commits -- does the repair close all three?

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `output-automation-contracts-2` | High | `output-automation-contracts` | yes | IID decision | ea_iid exits 0 with errorLevel 0, "IID": true and an hAssessed figure when all three Section 5 batteries fail; a pipeline reading the exit status sees a successful IID assessment |
| `restart-1` | High | `restart` | yes | overestimate | ea_restart -i awards an entropy estimate with errorLevel 0 and exit 0 after an IID test on the restart datasets has failed |
| `output-automation-contracts-3` | Medium | `output-automation-contracts` | yes | misreport | The JSON "IID" field is a compile-time constant restating which binary was invoked; ea_iid writes "IID": true for files it never read and ea_restart -i for a file it never opened |

## C04-chisq-negative-df

**Lead candidate.** `memory-safety-fuzz-2` — chi_square_tests.h:569 computes nbin-k in size_t and there is no 'df < 1 -> do not apply the test' guard, so a 1M skewed dataset gets df = -58, P-value 1 and a Passed IID verdict

**What the verification phase was asked to settle.** nbin-k computed in size_t with no df<1 guard; claimed df = -58 and a Passed verdict on 1M skewed data. Determine whether a wrong Passed here can flip an IID acceptance.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `memory-safety-fuzz-2` | High | `memory-safety-fuzz` | yes | IID decision | chi_square_tests.h:569 computes nbin-k in size_t and there is no 'df < 1 -> do not apply the test' guard, so a 1M skewed dataset gets df = -58, P-value 1 and a Passed IID verdict |
| `iid-track-2` | Low | `iid-track` | yes | misreport | §5.2.1 independence test with df<=0 is reported as Passed (and prints degrees of freedom = 0 or -1) instead of 'not applied' |

## C05-restart-k-effective

**Lead candidate.** `restart-3` — ea_restart aborts with assert(k_effective <= k) whenever the observed alphabet is smaller than ceil(2^H_I), producing no report (upstream #195) — still present on master, upstream and the repair branch

**What the verification phase was asked to settle.** assert(k_effective <= k) in simulateBound aborts whenever the observed alphabet is smaller than ceil(2^H_I); claimed upstream #195 and still open. Check the current upstream issue state read-only.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `restart-3` | High | `restart` | yes | crash | ea_restart aborts with assert(k_effective <= k) whenever the observed alphabet is smaller than ceil(2^H_I), producing no report (upstream #195) — still present on master, upstream and the repair branch |

## C06-cond-width-inference

**Lead candidate.** `conditioning-transpose-2` — Width inference discards stuck-at-zero high bits of the conditioned output, overestimating h' (and h_out = h' x n_out) by up to 1.6x; no bits-per-symbol argument exists

**What the verification phase was asked to settle.** The coordinating session already re-derived this independently (audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md, OC-1): on two files of identical information content h_out is 7.1552 vs 4.5185, and 7.1552 exceeds the 7-bit ceiling of the data. Refutation and reproduction are done; you supply only impact, prior art and severity. Read OC-1 first.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `conditioning-transpose-2` | High | `conditioning-transpose` | yes | overestimate | Width inference discards stuck-at-zero high bits of the conditioned output, overestimating h' (and h_out = h' x n_out) by up to 1.6x; no bits-per-symbol argument exists |

## C07-lrs-underflow-abort

**Lead candidate.** `memory-safety-fuzz-1` — assert(p_col >= 1/k) aborts ea_iid and ea_restart -i on valid 1,000,000-sample data with an exactly balanced k-symbol alphabet (k >= 17): arm64 reproduction of R-1

**What the verification phase was asked to settle.** FIVE independent finders hit the same assert(p_col >= 1/k) / p_colPower underflow abort, on arm64 AND on an x86-64 GCC build under emulation, in ea_iid and in ea_restart -i. Reproduction is therefore already corroborated; do NOT spend the budget re-running it. Resolve instead: the prior tracker recorded R-1 as 'not reproducible on arm64' -- say why that was wrong; the relation to upstream #153; whether the repair branch's #153 fail-closed commit actually prevents the abort or only reports it; and the exact platform dependence of the abort window (117 vs 155 of 255 alphabet sizes).

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `build-portability-harness-docs-1` | High | `build-portability-harness-docs` | yes | crash | LRS underflow abort window depends on `long double` width: arm64/MSVC aborts on valid 1M inputs an x86-64 GCC build assesses, and the fork's portability analysis never mentions it |
| `linux-x86-docker-1` | High | `linux-x86-docker` | yes | crash | R-1 confirmed on 80-bit long double: ea_iid aborts (SIGABRT, no JSON) on a compliant perfectly balanced dataset, for 155 of 255 alphabet sizes |
| `memory-safety-fuzz-1` | High | `memory-safety-fuzz` | yes | crash | assert(p_col >= 1/k) aborts ea_iid and ea_restart -i on valid 1,000,000-sample data with an exactly balanced k-symbol alphabet (k >= 17): arm64 reproduction of R-1 |
| `restart-2` | High | `restart` | yes | crash | ea_restart -i aborts with SIGABRT and no report at all on a valid 1,000,000-sample dataset that has already passed the sanity check (LRS p_colPower underflow assert, upstream #153) — reproduced on arm64 |
| `estimators-ttuple-lrs-1` | Medium | `estimators-ttuple-lrs` | yes | crash | R-1 reproduces on arm64: len_LRS_test assert(p_col >= 1/k) aborts ea_iid and ea_restart on exactly balanced valid 1,000,000-sample inputs for 117 of 255 alphabet sizes (incl. k=25 at L=10^6) |

## C08-harness-cannot-fail

**Lead candidate.** `regression-quality-reconciliation-1` — The N-07 regression cannot fail: every assertion sits in a statement-position python heredoc, so the script prints PASS and exits 0 after an AssertionError

**What the verification phase was asked to settle.** Fourteen reports that the fork's OWN test discipline does not detect what it claims: a python-heredoc N-07 assertion that cannot fail, a C-01 sanitizer control that passes unrepaired and is never run by any suite, --allow-known-platform-deltas excusing failures by filename rather than magnitude, compareresults.pl exiting 0 on an empty reference, regressions that silently drop their only 1M check, and an inventory that covers only regression-*.sh. This is the cluster that decides how much the fork's green suite is worth, and it bears directly on whether the repair branch should be merged. Run the scripts yourself to confirm the 'cannot fail' claims; that is cheap. Then give one consolidated impact judgement.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `regression-quality-reconciliation-1` | High | `regression-quality-reconciliation` | no | misreport | The N-07 regression cannot fail: every assertion sits in a statement-position python heredoc, so the script prints PASS and exits 0 after an AssertionError |
| `regression-quality-reconciliation-2` | High | `regression-quality-reconciliation` | no | misreport | The C-01 regression passes against the unrepaired code in two configurations, and no suite ever runs it |
| `build-portability-harness-docs-2` | Medium | `build-portability-harness-docs` | yes | misreport | `--allow-known-platform-deltas`, the documented macOS invocation, excuses selftest failures by filename and never by magnitude |
| `build-portability-harness-docs-3` | Medium | `build-portability-harness-docs` | yes | misreport | `compareresults.pl` exits 0 when the reference file is empty or truncated, and `generate-refdata` can produce exactly that file unnoticed |
| `build-portability-harness-docs-4` | Medium | `build-portability-harness-docs` | yes | misreport | The repair branch's #153 regression forces a fixed repeat length, so 7 of its 8 inputs never reach the underflow on the documented reference platform |
| `regression-quality-reconciliation-3` | Medium | `regression-quality-reconciliation` | no | misreport | The IND-02 inventory covers only regression-*.sh, so three harness programs are outside the discipline it created — including the one that is never run |
| `regression-quality-reconciliation-4` | Medium | `regression-quality-reconciliation` | no | misreport | Two master regressions silently drop their only 1,000,000-sample check and still print PASS when a generator in the frozen audits archive is absent |
| `build-portability-harness-docs-10` | Low | `build-portability-harness-docs` | yes | misreport | `regression-docs.sh` cannot pass on the reference platform, and has seven further silent-skip or scope gaps |
| `build-portability-harness-docs-12` | Low | `build-portability-harness-docs` | yes | misreport | `selftest` reports the wrong exit code for a failed tool run (always 0) on master |
| `build-portability-harness-docs-13` | Low | `build-portability-harness-docs` | no | misreport | Two repair-branch harness tools, including the C-01 sanitizer control, are never run by the suite and appear in no document |
| `linux-x86-docker-4` | Low | `linux-x86-docker` | yes | misreport | selftest compares one of the two final figures against nothing: compareresults.pl tolerates extra data items and no refdata file contains H_bitstring Per Symbol |
| `regression-quality-reconciliation-5` | Low | `regression-quality-reconciliation` | yes | misreport | F19's sha256-scope assertion is satisfied by both of the fork's two incompatible scope policies, because it tests a subset that is the whole file |
| `regression-quality-reconciliation-6` | Low | `regression-quality-reconciliation` | yes | underestimate | The repaired MultiMMC binary-path check agrees with the tool on both sides of the F09 repair, so it does not discriminate the defect it was added for |
| `regression-quality-reconciliation-9` | Low | `regression-quality-reconciliation` | no | misreport | Part of the N-08 production change, and all of ea_conditioning, are exercised by no regression |

## C09-cond-no-intake-checks

**Lead candidate.** `conditioning-transpose-1` — ea_conditioning -n -i on constant (all-zero) data: assert abort with no JSON; with NDEBUG a heap over-read in markov_test; -c iid silently reports h' = -0

**What the verification phase was asked to settle.** Four reports that ea_conditioning -i applies none of the intake discipline the fork added to the other tools: no 1,000,000-sample rule, no single-symbol or width check, and word_size 0 on all-zero input leading to malloc(0) and an out-of-bounds read in markov_test. Corroborated; resolve severity and whether the fork's own 1M policy was meant to cover this program.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `conditioning-transpose-1` | Medium | `conditioning-transpose` | no | crash | ea_conditioning -n -i on constant (all-zero) data: assert abort with no JSON; with NDEBUG a heap over-read in markov_test; -c iid silently reports h' = -0 |
| `conditioning-transpose-4` | Medium | `conditioning-transpose` | no | misreport | No minimum-sample, single-symbol or width check on the -i conditioned dataset: a 125,000-byte file is assessed with errorLevel 0 and no nonCompliantShortDataset flag |
| `memory-safety-fuzz-4` | Medium | `memory-safety-fuzz` | yes | overestimate | ea_conditioning never applies the 1,000,000-sample intake rule, so it assesses a 100-byte file and reports errorLevel 0 with no non-compliance flag |
| `memory-safety-fuzz-5` | Medium | `memory-safety-fuzz` | yes | crash | ea_conditioning's width inference yields word_size 0 for all-zero input, so every bitstring estimator is handed a malloc(0) buffer: markov_test reads data[-1] under -DNDEBUG, most_common aborts otherwise |

## C10-restart-stats-zero

**Lead candidate.** `restart-5` — ea_restart -i reports mean and median as 0.0 for every dataset in its JSON report

**What the verification phase was asked to settle.** ea_restart -i publishes mean 0.0 and median 0.0 as the Section 5.1 baseline statistics while the computed values are 0.500831 and 0.5, and the -i JSON omits the MCV test case. Relate to N-10 and to the repair branch's report-stats commit.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `output-automation-contracts-7` | Medium | `output-automation-contracts` | yes | misreport | ea_restart -i publishes mean 0.0 and median 0.0 as the Section 5.1 baseline statistics; the computed values are 0.500831 and 0.5 |
| `restart-5` | Medium | `restart` | yes | misreport | ea_restart -i reports mean and median as 0.0 for every dataset in its JSON report |
| `restart-10` | Info | `restart` | yes | misreport | The -i JSON omits the per-estimator Most Common Value test case: tc631Iid is built, its h_c is never assigned, and it is never pushed |

## C11-c01-scalar-delete

**Lead candidate.** `restart-4` — ea_restart deallocates an array allocation with scalar delete (C-01), aborting the run under ASan before any assessment output

**What the verification phase was asked to settle.** C-01 is a known open defect on master, repaired on the repair branch. Confirm only its current status on both targets and its disposition; no new reproduction needed.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `restart-4` | Medium | `restart` | yes | crash | ea_restart deallocates an array allocation with scalar delete (C-01), aborting the run under ASan before any assessment output |

## C12-sha256-stack-overread

**Lead candidate.** `memory-safety-fuzz-3` — ea_conditioning ignores sha256_file()'s status and writes an uninitialised 65-byte stack buffer into the JSON provenance record (stack over-read)

**What the verification phase was asked to settle.** Claims ea_conditioning ignores sha256_file()'s status and writes an uninitialised 65-byte stack buffer into the JSON provenance record. A genuine stack over-read reaching output deserves full verification; check it under the sanitizer build.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `memory-safety-fuzz-3` | Medium | `memory-safety-fuzz` | yes | misreport | ea_conditioning ignores sha256_file()'s status and writes an uninitialised 65-byte stack buffer into the JSON provenance record (stack over-read) |

## C13-errmsg-format-string

**Lead candidate.** `memory-safety-fuzz-9` — Comma-operator errorMsg assignments in read_file/read_file_subset store the format string, so the JSON errorMessage reads "Error: '%s' is empty"

**What the verification phase was asked to settle.** Five finders report the same comma-operator bug writing a literal format string ("%s", "Error: '%s' is empty") into the JSON errorMessage. Corroborated across tools; confirm the site list and that no site actually formats, then stop.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `intake-noniid-aggregation-1` | Low | `intake-noniid-aggregation` | no | misreport | Comma-operator errorMsg assignment writes the literal format string "%s" into the JSON errorMessage |
| `linux-x86-docker-3` | Low | `linux-x86-docker` | no | misreport | JSON errorMessage carries the literal conversion specifier "%s" and a raw newline instead of the file name (comma-operator assignment) |
| `memory-safety-fuzz-9` | Low | `memory-safety-fuzz` | yes | misreport | Comma-operator errorMsg assignments in read_file/read_file_subset store the format string, so the JSON errorMessage reads "Error: '%s' is empty" |
| `output-automation-contracts-9` | Low | `output-automation-contracts` | yes | misreport | errorMessage is built with the comma operator at four sites, so the JSON carries the literal template "Error: '%s' is empty\n" with the filename lost and a newline embedded |
| `restart-7` | Low | `restart` | yes | misreport | The empty-input JSON errorMessage is the literal format string "Error: '%s' is empty\n" (comma-operator assignment) |

## C14-report-contract

**Lead candidate.** `output-automation-contracts-5` — No exit status or JSON field distinguishes a statistical rejection from invalid input or an internal error; every failure is 255 with errorLevel -1 and testCases null

**What the verification phase was asked to settle.** The machine interface as a whole: no exit status or JSON field separates statistical rejection from invalid input or internal error; stale -o files survive error paths; -q suppresses exactly the verdict lines; three file problems collapse to one message; the write is not atomic; --version anywhere in argv short-circuits. Judge these together as one consumer-contract finding, since that is how they will be repaired.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `output-automation-contracts-4` | Medium | `output-automation-contracts` | yes | misreport | Error paths that never reach writeJsonReport leave the previous run's report file in place, so a pipeline that checks the exit status and then reads -o gets stale results |
| `output-automation-contracts-5` | Medium | `output-automation-contracts` | yes | misreport | No exit status or JSON field distinguishes a statistical rejection from invalid input or an internal error; every failure is 255 with errorLevel -1 and testCases null |
| `output-automation-contracts-6` | Medium | `output-automation-contracts` | yes | misreport | ea_restart -q suppresses exactly the sanity-check and validation-failure lines, and ea_restart reports omit bitsPerSymbol, the final min(H_r,H_c,H_I) and every sanity-check input |
| `output-automation-contracts-12` | Low | `output-automation-contracts` | yes | misreport | Three distinct file problems collapse to one errorMessage, and those reports carry neither filename nor sha256, so the JSON does not say which file failed or why |
| `output-automation-contracts-13` | Low | `output-automation-contracts` | no | misreport | The report write is not atomic: a signal during the write leaves a truncated, syntactically invalid JSON at the operator's path and exits 153, a status no document mentions |
| `restart-8` | Low | `restart` | yes | misreport | On the -i validation-failure path the JSON report discards every IID test result it just computed (testCases is null) |
| `restart-9` | Low | `restart` | yes | misreport | Quiet mode suppresses the pass/fail verdict but still prints the H_I line, so -q without -o yields no diagnosis at all |
| `output-automation-contracts-16` | Info | `output-automation-contracts` | no | misreport | --version anywhere in argv, including as the filename, exits 0 before getopt and before any assessment, writing no report even with -o |

## C15-negative-zero

**Lead candidate.** `estimators-mcv-collision-markov-compression-1` — Zero min-entropy is reported as "-0" in text and -0.0 in JSON (negative zero propagates through the min() folds into hOriginal/hAssessed)

**What the verification phase was asked to settle.** Four finders report -0 / -0.0 reaching stdout and JSON from -log2(1.0). Confirm the sites and that it is cosmetic (comparisons and min() behave as 0).

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `estimators-mcv-collision-markov-compression-1` | Low | `estimators-mcv-collision-markov-compression` | yes | misreport (numerically equal to zero; comparisons and min() behave as 0) | Zero min-entropy is reported as "-0" in text and -0.0 in JSON (negative zero propagates through the min() folds into hOriginal/hAssessed) |
| `conditioning-transpose-14` | Info | `conditioning-transpose` | no | none | Constant conditioned data yields h' = -0 and JSON 'h_p': -0.0 / 'h_out': -0.0 (negative zero from -log2(1.0)); value correct |
| `estimators-ttuple-lrs-3` | Info | `estimators-ttuple-lrs` | yes | misreport | t-tuple/LRS report '-0' (negative zero) in text and JSON when p_u clips to 1 |
| `predictors-8` | Info | `predictors` | yes | misreport | A zero min-entropy is reported as negative zero in stdout and in the JSON report ("hAssessed": -0.0) |

## C16-permissive-parsing

**Lead candidate.** `intake-noniid-aggregation-2` — N-08 new vector: atoi int truncation turns an out-of-range bits_per_symbol into a valid width and a full assessment runs at that width

**What the verification phase was asked to settle.** N-08 family plus new vectors: atoi truncation producing a valid width, strtoul base 0 reading '010' as octal, strtod accepting hex floats for H_I, and -s accepting ULONG_MAX-1 into new uint16_t[] with no bound or exception handler. Confirm which are reachable and which need hostile input.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `conditioning-transpose-8` | Low | `conditioning-transpose` | no | crash | N-11 recheck: n_in or n_out >= 1073741823 (and UINT_MAX) pass the parser then abort on the MPFR emax assert; accepted sizes are computationally unbounded |
| `conditioning-transpose-9` | Low | `conditioning-transpose` | no | misreport | Permissive integer parsing: ea_conditioning n_in '010' is read as octal 8 (strtoul base 0); ea_transpose -l '1abc'/'0x1' accepted on master (repair fixes transpose only) |
| `intake-noniid-aggregation-2` | Low | `intake-noniid-aggregation` | no | underestimate | N-08 new vector: atoi int truncation turns an out-of-range bits_per_symbol into a valid width and a full assessment runs at that width |
| `memory-safety-fuzz-11` | Low | `memory-safety-fuzz` | no | crash | ea_restart accepts any -s up to ULONG_MAX-1 and passes it straight to new uint16_t[], giving an uncaught std::bad_alloc |
| `restart-13` | Low | `restart` | no | crash | H_I is still parsed with strtod, so hex-float literals and leading whitespace are accepted on master and on the repair branch; '0x1p3' reaches the #195 abort |
| `restart-6` | Low | `restart` | no | crash | -s accepts any value up to ULONG_MAX-1 and allocates 2 bytes per round with no bound and no exception handling: SIGKILL with no message at -s 1e11, uncaught std::bad_alloc at the top of the range |

## C17-platform-divergence

**Lead candidate.** `linux-x86-docker-2` — Platform divergence (#155) is caused by the width of long double inside prediction_estimate_function, and the predictor min-entropy delta exceeds the fork's own 1e-10 comparison epsilon

**What the verification phase was asked to settle.** Mechanisms behind upstream #155: long double width inside prediction_estimate_function, the com_exp sawtooth, FMA in the excursion statistic, and -march=native with -ffp-contract=fast in the default Linux build. Confirm the mechanisms and that the effects are last-digit.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `linux-x86-docker-2` | Low | `linux-x86-docker` | yes | misreport | Platform divergence (#155) is caused by the width of long double inside prediction_estimate_function, and the predictor min-entropy delta exceeds the fork's own 1e-10 comparison epsilon |
| `estimators-mcv-collision-markov-compression-3` | Info | `estimators-mcv-collision-markov-compression` | yes | either direction, <= 2e-14 bit on all tested data | com_exp(p) is a sawtooth in double because Bterm = 1.0L - z quantises small z (long double is 64-bit on arm64), making the compression bisection non-monotone |
| `iid-track-1` | Info | `iid-track` | yes | none | Excursion statistic computed with fused multiply-add; last bits platform-dependent |
| `linux-x86-docker-5` | Info | `linux-x86-docker` | yes | misreport | The default Linux build carries -march=native with -ffp-contract=fast, tying the binary and potentially its floating-point results to the build host's CPU |

## C18-llp64-overflow

**Lead candidate.** `predictors-10` — Every estimator counter is `long`, which is 32-bit on LLP64; the bitstring length blen = len*word_size is computed in that type

**What the verification phase was asked to settle.** Windows/LLP64-only integer width claims (long is 32-bit): blen = len*word_size, n_choose_2 in long int, unsigned-int lengths in compression(). Source-only on this host; decide whether each is real on LLP64 and whether the fork claims Windows support.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `estimators-ttuple-lrs-5` | Low | `estimators-ttuple-lrs` | yes | IID decision | n_choose_2 computes N=C(L-W+1,2) in `long int`, which overflows for L >= 65,537 on LLP64 targets (Windows) and would corrupt the 5.2.5 decision |
| `iid-track-5` | Info | `iid-track` | no | IID decision | compression(): unsigned-int lengths overflow at ~1.07e9 8-bit symbols and bzip2 errors silently become statistic 0 |
| `predictors-10` | Info | `predictors` | no | crash | Every estimator counter is `long`, which is 32-bit on LLP64; the bitstring length blen = len*word_size is computed in that type |

## C19-docs-drift

**Lead candidate.** `build-portability-harness-docs-9` — "all eight regression scripts pass" in a document that explains why hand-maintained counts drift; 14 exist on master

**What the verification phase was asked to settle.** Documentation and packaging drift: hand-maintained file counts that are wrong, an untracked file documented as the archive index, the only Linux artefact cloning upstream instead of the fork, a sanitizer command that cannot work on the verified platform, README option lists missing -q/-o/-s/--version, ARCH detection special-casing only Darwin/arm64, and an unchanged 1.1.8 version string across three different JSON schemas. Verify the factual claims (counts, file existence, command failure) by running them.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `build-portability-harness-docs-5` | Medium | `build-portability-harness-docs` | no | misreport | `audits/README.md` claims 585 tracked files and 118 tracked subdirectories against an actual 739 and 126, and nothing checks the numbers |
| `build-portability-harness-docs-6` | Medium | `build-portability-harness-docs` | no | misreport | `audits/2026-10-01-re-audit/inventory.json` is documented as the archive's machine-readable index but is untracked, hidden by the blanket `*.json` ignore |
| `build-portability-harness-docs-7` | Medium | `build-portability-harness-docs` | yes | misreport | The only Linux artefact in the repository clones upstream, and BUILDING's re-pin procedure names it as the way to build "the same fork" on the reference platform |
| `output-automation-contracts-8` | Medium | `output-automation-contracts` | yes | misreport | Schema drift under an unchanged toolVersion: upstream, master and the repair branch all report "1.1.8" while emitting three different JSON schemas, and nothing identifies the fork or build |
| `build-portability-harness-docs-11` | Low | `build-portability-harness-docs` | yes | misreport | README option lists omit -q, -o and --version for every tool and -s for ea_restart; ea_conditioning's -c is documented nowhere |
| `build-portability-harness-docs-14` | Low | `build-portability-harness-docs` | no | misreport | The BUG-REPAIR-GUIDE's sanitizer build command cannot work on the only verified platform |
| `build-portability-harness-docs-15` | Low | `build-portability-harness-docs` | no | none | ARCH host detection special-cases only Darwin/arm64, so every other arm64 host gets the x86-only -march=native |
| `build-portability-harness-docs-17` | Low | `build-portability-harness-docs` | yes | misreport | Version string 1.1.8 is identical to upstream although behaviour deliberately differs, and one production change is missing from NOTICE's "each change is listed" list |
| `build-portability-harness-docs-8` | Low | `build-portability-harness-docs` | no | misreport | BUILDING.md says "Three predictor values" differ where its own table, NOTICE and a full regeneration all say eight |
| `build-portability-harness-docs-9` | Low | `build-portability-harness-docs` | no | misreport | "all eight regression scripts pass" in a document that explains why hand-maintained counts drift; 14 exist on master |
| `output-automation-contracts-14` | Low | `output-automation-contracts` | yes | misreport | Documentation does not describe the machine interface: README omits -o, -q and -s; ea_restart's own usage never mentions -o; the -s floor is undocumented and silent; no document records the JSON schema or any exit status |
| `build-portability-harness-docs-16` | Info | `build-portability-harness-docs` | no | none | Dependency and advisory record: no reachable vulnerability in any linked library; OpenSSL is one patch release behind |

## C20-openmp-race

**Lead candidate.** `memory-safety-fuzz-10` — Data race on test_status[] and on completed in the ea_iid permutation OpenMP region (formally UB, benign in effect)

**What the verification phase was asked to settle.** Formal data races on test_status[] and the completed counter in the ea_iid permutation region. Decide whether they are benign by monotonicity and whether any reported verdict can change.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `memory-safety-fuzz-10` | Low | `memory-safety-fuzz` | yes | none | Data race on test_status[] and on completed in the ea_iid permutation OpenMP region (formally UB, benign in effect) |
| `iid-track-3` | Info | `iid-track` | yes | misreport | 'completed' progress counter updated both inside omp critical and via omp atomic outside it (unsynchronised pair) |
| `iid-track-4` | Info | `iid-track` | yes | none | test_status[] read outside the critical region while written inside (formal data race, benign by monotonicity) |

## C21-cond-misc

**Lead candidate.** `conditioning-transpose-5` — N-05 recheck: JSON binds the -i file's name and SHA-256 to an h' that did not come from it (CLI h' given, or vetted mode)

**What the verification phase was asked to settle.** The rest of ea_conditioning and ea_transpose: fesetround(FE_TOWARDZERO) left in effect during the h' battery, provenance bound to a file that did not produce h', sha256 failure ignored, hard-coded IID false, BSD getopt rejecting the documented option order, unchecked ofstream writes, declined estimators' -1 folded into h' giving h_out = -256, periodicity/covariance unsigned wrap, and an assert that can never fire. Confirm each briefly; flag any that is more than Low.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `conditioning-transpose-10` | Low | `conditioning-transpose` | no | misreport | Documented option order '<n_in> <n_out> <nw> <h_in> [-o file]' fails on macOS: BSD getopt stops at the first positional, so a trailing -o makes the run 'Incorrect usage' with no JSON |
| `conditioning-transpose-3` | Low | `conditioning-transpose` | yes | both (observed overestimate at the 1e-12 level) | fesetround(FE_TOWARDZERO) stays in effect during the h' estimator battery, so ea_conditioning's h' differs from ea_non_iid on identical data (observed up to +9.6e-13, direction not uniform) |
| `conditioning-transpose-5` | Low | `conditioning-transpose` | no | misreport | N-05 recheck: JSON binds the -i file's name and SHA-256 to an h' that did not come from it (CLI h' given, or vetted mode) |
| `conditioning-transpose-6` | Low | `conditioning-transpose` | no | misreport | N-06 recheck (conditioning instance): sha256_file failure ignored; JSON 'sha256' is the h' argv text for a nonexistent file with errorLevel 0, rc 0 |
| `memory-safety-fuzz-6` | Low | `memory-safety-fuzz` | no | crash | periodicity()/covariance() iterate to an unsigned n-p that wraps when n < p; covariance has no guard at all, so the over-read happens even in an assert-enabled build |
| `memory-safety-fuzz-7` | Low | `memory-safety-fuzz` | no | misreport | ea_conditioning folds declined estimators' -1 sentinel into h', reporting h' = -1 and h_out = -256 with errorLevel 0 |
| `memory-safety-fuzz-8` | Low | `memory-safety-fuzz` | yes | misreport | ea_conditioning writes its JSON report through unchecked raw ofstreams and exits 0 when nothing was written |
| `conditioning-transpose-11` | Info | `conditioning-transpose` | no | misreport | N-09 instances recheck: ea_conditioning -o to an unwritable path exits 0 with no file; ea_transpose fclose unchecked (not exercisable on macOS) |
| `conditioning-transpose-12` | Info | `conditioning-transpose` | no | none | ea_transpose usage text says the result is saved in '<file>.column' but the program writes to the explicit <outfile> argument |
| `conditioning-transpose-13` | Info | `conditioning-transpose` | no | misreport | ea_conditioning -n -i read failure with -o exits 255 without writing any JSON, unlike the h_in<=0 / h'<=0 paths which write an error JSON |
| `conditioning-transpose-7` | Info | `conditioning-transpose` | no | misreport | N-10 recheck: conditioning JSON hard-codes 'IID': false even with -c iid, has no vetted/non-vetted field, and reports the clamped nw rather than the CLI nw |
| `memory-safety-fuzz-12` | Info | `memory-safety-fuzz` | yes | none | conditioning_main.cpp:603 assert(mpfr_get_emin() < -maxval) can never fail: maxval is unsigned int, so the unary minus wraps |

## C22-predictor-numerics

**Lead candidate.** `predictors-5` — calc_p_local's 4-ULP stopping test can never be met because its objective is step-quantised, so P_local is located only to ~1e-11 relative at supported N (worst non-conservative min-entropy error +1.6e-11 bit)

**What the verification phase was asked to settle.** Estimator numerics that are claimed negligible or conservative: P_local bisection quantisation, the x recurrence iterated to convergence rather than 10 steps, P_global' dividing by N-1 at N==1, ZALPHA vs the printed 2.576, Markov complements, collision/compression step-8 direction, the spec errata's own arithmetic error, and -vvv printing nothing. Check that each stated bound and direction is right; the risk here is a 'negligible' that is not.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `predictors-5` | Low | `predictors` | yes | overestimate | calc_p_local's 4-ULP stopping test can never be met because its objective is step-quantised, so P_local is located only to ~1e-11 relative at supported N (worst non-conservative min-entropy error +1.6e-11 bit) |
| `estimators-mcv-collision-markov-compression-2` | Info | `estimators-mcv-collision-markov-compression` | yes | none (conservative: it under-reports relative to the literal text) | Collision and compression return 0 where the literal text of step 8 would return 1 ("if the search does not yield a solution, min-entropy = 1") |
| `estimators-mcv-collision-markov-compression-4` | Info | `estimators-mcv-collision-markov-compression` | yes | either direction, <= 3e-13 bit in H (measured Markov H deltas: 1.1 ULP uniform, 44 ULP = 7.6e-17 biased-p01) | Markov complements (P1 = 1-P0, P01 = 1-P00, P11 = 1-P10) are computed by subtraction rather than as count ratios, losing relative precision for small complements |
| `estimators-mcv-collision-markov-compression-5` | Info | `estimators-mcv-collision-markov-compression` | no | none for the tool (the code follows the formula) | SP 800-90B errata item 2 (2025-05-29) for the §6.3.1 worked example is itself inconsistent with the step-2 formula; a validator trusting it would wrongly judge the tool off by 1.1% |
| `estimators-ttuple-lrs-2` | Info | `estimators-ttuple-lrs` | yes | overestimate | ZALPHA_L long double literal is one ulp below the correctly rounded z_0.995 (negligible effect) |
| `estimators-ttuple-lrs-4` | Info | `estimators-ttuple-lrs` | yes | misreport | ea_non_iid -vvv (verbose=4) prints no per-estimator detail because lrs_test.h (and other estimators) gate on verbose == 2 / == 3 exactly |
| `predictors-2` | Info | `predictors` | yes | underestimate | F09 (MultiMMC run reset on a Null prediction) is still repaired on master, and the new fixtures show the pre-repair error is ~0.3 bit |
| `predictors-3` | Info | `predictors` | yes | none | prediction_estimate_function is evaluated at p > r/(r+1) in a compliant 1M run, where it returns a numerically meaningless value (or NaN in isolation); the decision is nevertheless correct |
| `predictors-4` | Info | `predictors` | yes | underestimate | calc_p_local always terminates by bracket collapse, and a failed or imprecise search can only lower the reported entropy (F25 not reproducible) |
| `predictors-6` | Info | `predictors` | yes | overestimate | ZALPHA is the exact 0.995 quantile (2.5758293035489008) where the spec text prints 2.576, which raises every prediction estimate by ~1e-7 bit at N=1e6 |
| `predictors-7` | Info | `predictors` | yes | none | The x recurrence is iterated to convergence (<=66 steps) rather than the spec's fixed 10 iterations |
| `predictors-9` | Info | `predictors` | no | underestimate | P_global' divides by (N-1), which is zero when N == 1 (generic LZ78Y at len==18); the result clamps to 1 and reports 0 bits |

## C23-misc-reporting

**Lead candidate.** `intake-noniid-aggregation-4` — F23 sub-claims confirmed: JSON MCV intermediates are literal-only (bitstring values overwritten) and -c hAssessed is n×h' while text prints h' per bit

**What the verification phase was asked to settle.** Remaining reporting and coverage observations, including F23's mcvEstimate overwriting, a warning recorded but never emitted, a latent wrong stride that is correct only because r==c, the simulated restart cutoff sitting at or above the exact binomial cutoff, ea_restart accepting a width wider than the data, and two repair-branch behaviours. Confirm or rule out each.

**Members**

| Candidate | Severity | Reported by | Supported path | Direction | Claim |
|---|---|---|---|---|---|
| `intake-noniid-aggregation-3` | Low | `intake-noniid-aggregation` | no | misreport | read_file_subset: bsymbols allocation failure returns false without setting errorLevel, so the JSON reports errorLevel 0 while the process exits 255 |
| `intake-noniid-aggregation-4` | Low | `intake-noniid-aggregation` | yes | misreport | F23 sub-claims confirmed: JSON MCV intermediates are literal-only (bitstring values overwritten) and -c hAssessed is n×h' while text prints h' per bit |
| `output-automation-contracts-10` | Low | `output-automation-contracts` | yes | misreport | The "Symbols appear to be narrower than described" warning is recorded in errorMsg but never emitted, because GetBaseJson prints errorMessage only when errorLevel is nonzero |
| `output-automation-contracts-11` | Low | `output-automation-contracts` | yes | misreport | One mcvEstimate* triple per test case: under -i the bitstring pass's Most Common Value intermediates are overwritten by the literal pass, and the field that would disambiguate them is inverted and disabled |
| `regression-quality-reconciliation-7` | Low | `regression-quality-reconciliation` | yes | misreport | ea_restart accepts a declared symbol width wider than the data and its report records no width at all, and no regression covers it |
| `iid-track-6` | Info | `iid-track` | yes | misreport | seed() failure message says 'Reverting to a deterministic seed.' but the process exits |
| `iid-track-7` | Info | `iid-track` | yes | none | Repair branch: permutation battery skipped after a deterministic rejection, and a legitimate negative IID verdict is signalled through errorLevel=2 |
| `intake-noniid-aggregation-5` | Info | `intake-noniid-aggregation` | no | misreport | Repair branch: a nonexistent input path produces no reason on the terminal (only in the JSON) |
| `intake-noniid-aggregation-6` | Info | `intake-noniid-aggregation` | yes | none | Report self-description gaps: -t truncation not in any JSON data field, MSB-first bitstring order undocumented, -vvv prints less than -vv, testCases null on failure |
| `output-automation-contracts-15` | Info | `output-automation-contracts` | yes | misreport | The JSON calls the permutation-test counter index "iteration" where the console correctly labels the same three numbers C[i][0..2]; ea_iid's single test case has an empty testCaseDesc; retMinEntropy is never emitted |
| `regression-quality-reconciliation-8` | Info | `regression-quality-reconciliation` | no | none | Evidentiary limits of three regressions: two IID-decision repairs are tested only below the 1,000,000-sample minimum, N-09's write-fails-midway half is skipped on this platform, and F14's proxy has no clean-build control |
| `restart-11` | Info | `restart` | yes | none | Latent wrong stride in the row and column index arithmetic (rdata[i*r + j], cdata[j*c + i]) — correct only because r == c == 1000 |
| `restart-12` | Info | `restart` | yes | overestimate | The §3.1.4.3 cutoff is obtained by simulation and sits at or above the exact binomial cutoff, so it accepts data the literal rule rejects, and it varies from run to run |

