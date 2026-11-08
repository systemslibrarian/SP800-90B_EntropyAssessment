# Determinism and thread-count phase -- RESULTS

Written 2026-11-08T17:04:24-05:00 by harness/determinism/compare_runs.py from `/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism`.

## Binaries measured (instrument rule 4) and host

```
1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (153368 bytes, mtime 2026-11-07T19:28:57)
22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (193656 bytes, mtime 2026-11-07T19:28:52)
4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (230904 bytes, mtime 2026-11-07T19:29:04)
```
```
date=2026-11-08T16:59:06-0500
mode=full
threads=1 2 10
uname_a=Darwin MacBook-Air.local 25.6.0 Darwin Kernel Version 25.6.0: Fri Jul 31 19:16:20 PDT 2026; root:xnu-12377.161.14~5/RELEASE_ARM64_T8142 arm64 arm Darwin
uname_s=Darwin
uname_m=arm64
compiler=Apple clang version 21.0.0 (clang-2100.4.1.1)
hw.ncpu=10
hw.memsize=17179869184
cpu=Apple M5
sw_vers=ProductName:		macOS ProductVersion:		26.6.2 BuildVersion:		25G83 
git_head=855e47eb66c8ade055707de41aac8b4ddc2b20c6
git_branch=audit/2026-11-07
git_dirty=13 paths modified or untracked
omp_runtime=	/opt/homebrew/opt/libomp/lib/libomp.dylib
python=Python 3.14.7
```

## Summary

| tool | case | class | runs | identical pairs |
|---|---|---|---|---|
| iid | truerand_1bit | DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary | 6 | 0 |
| iid | truerand_8bit | DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary | 6 | 0 |
| non_iid | biased-random-bits | DETERMINISTIC | 4 | 6 |
| non_iid | biased-random-bytes | DETERMINISTIC | 4 | 6 |
| non_iid | csprng-1bit-1000000 | DETERMINISTIC | 4 | 6 |
| non_iid | csprng-8bit-1000000 | DETERMINISTIC | 4 | 6 |
| non_iid | data.pi | DETERMINISTIC | 4 | 6 |
| non_iid | normal | DETERMINISTIC | 4 | 6 |
| non_iid | period255-8bit-1000000 | DETERMINISTIC | 4 | 6 |
| non_iid | rand1_short | INCOMPLETE | 4 | 0 |
| non_iid | rand4_short | INCOMPLETE | 4 | 0 |
| non_iid | rand8_short | INCOMPLETE | 4 | 0 |
| non_iid | ringOsc-nist | DETERMINISTIC | 4 | 6 |
| non_iid | truerand_1bit | DETERMINISTIC | 4 | 6 |
| non_iid | truerand_4bit | DETERMINISTIC | 4 | 6 |
| non_iid | truerand_8bit | DETERMINISTIC | 4 | 6 |
| non_iid | two9010-8bit-1000000 | DETERMINISTIC | 4 | 6 |
| restart | restart-csprng-1bit-1000x1000 | DETERMINISTIC | 4 | 6 |
| restart | restart-csprng-8bit-1000x1000 | DETERMINISTIC | 4 | 6 |

## Threading in the three tools, from the source (the measurement below tests this)

- `ea_non_iid`: NO `#pragma omp` anywhere in `non_iid_main.cpp`, `non_iid/*.h`, `shared/*.h` (`grep -rn 'pragma omp'`; the only `omp` token is `#include <omp.h>` in `shared/utils.h:19`). `libdivsufsort` does not link libomp (`otool -L`). `OMP_NUM_THREADS` should therefore have NO effect; any thread-dependent difference here is itself a finding (something outside the tool's own code -- runtime memory layout reaching an uninitialised read -- and belongs in the sanitizer phase).
- `ea_iid`: ONE parallel region, `iid/permutation_tests.h:625-729` (`omp parallel` / `omp for` over the 10,000 permutations, `omp critical(resultUpdate)` for the counters). Each thread copies the `/dev/urandom` seed and calls `xoshiro_jump(omp_get_thread_num(), ...)` (`:649`). The seed is read by `shared/utils.h:seed()` from the LITERAL path `/dev/urandom` (`:797`); `EA_TEST_RANDOM_SOURCE` reaches only `TestRunUtils.h:129` (`g_randomSourcePath`) and is used only for the report temp-file suffix (`:478`). PREDICTION: arm (b) varies exactly like arm (a).
- `ea_restart`: the only `#pragma omp` is in `simulateBound()` (`restart_main.cpp:307-316`), which is called only under `#ifdef EA_RESTART_WITHOUT_C23_FIX` (`:745`); the production compile line (BUILD-LINES.md) defines nothing, so under `-n` NO parallel region executes and `OMP_NUM_THREADS` should have no effect. Under `-i` it is threaded through `permutation_tests()` (`:1127`, `:1134`) -- not run here (heavy, and seeded like `ea_iid`).
- `xoshiro_jump(k)` for k >= 2: re-derived independently in `harness/determinism/xoshiro_model.py` (closed form `J (I+J)^(k-1) S0`; log `xoshiro-model.log`). Consequence for this phase: with the seed live every run differs; with a fixed seed the permutation SET would still depend on the thread count (static `omp for` partition, one stream per thread), so counters changing with the thread count would be expected and only a VERDICT change would not be.

## How to read the classes

| class | pattern in the pair table | what it indicates |
|---|---|---|
| DETERMINISTIC | every pair identical on json/stdout/stderr/rc | no race, no reduction-order effect, no RNG in the path (within n = 2 repeats per thread count) |
| THREAD-DEPENDENT | repeats at one thread count identical; 1 vs 2 differ | parallel reduction order (FP associativity) or per-thread partition -- deterministic in the thread count |
| 10-ONLY | 1 vs 2 identical, 1 vs 10 or 2 vs 10 differ | scheduling/contention-sensitive; NOT long double width, FMA or libm (those cannot depend on the thread count) |
| NONDETERMINISTIC | repeats at the same thread count differ | data race or non-thread-safe call (any tool, any non-RNG field); for `ea_iid` RNG-dependent fields it is the live seed, by design |
| INCOMPLETE | a run is malformed (rc, missing final line, placeholder JSON) | not a determinism result (instrument rule 2) |

Platform classes (long double width, FMA contraction, libm) present as IDENTICAL at every thread count on this host and different from Linux by the same amount every time; see `compare-linux.md`.

## iid / truerand_1bit -- DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| a-t10-r1 | a | 10 | 0 | yes | 16 | 22f1319ae347ab4e | f9ea8832af4c4205 | 0 |
| a-t10-r2 | a | 10 | 0 | yes | 13 | 22f1319ae347ab4e | f9ea8832af4c4205 | 0 |
| b-t1-r1 | b | 1 | 0 | yes | 20 | 22f1319ae347ab4e | f9ea8832af4c4205 | 0 |
| b-t2-r1 | b | 2 | 0 | yes | 18 | 22f1319ae347ab4e | f9ea8832af4c4205 | 0 |
| b-t10-r1 | b | 10 | 0 | yes | 11 | 22f1319ae347ab4e | f9ea8832af4c4205 | 0 |
| b-t10-r2 | b | 10 | 0 | yes | 15 | 22f1319ae347ab4e | f9ea8832af4c4205 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| a-t10-r1 vs a-t10-r2 | DIFF | DIFF | = | = | 44 (44 / 0) |
| a-t10-r1 vs b-t1-r1 | DIFF | DIFF | = | = | 50 (50 / 0) |
| a-t10-r1 vs b-t2-r1 | DIFF | DIFF | = | = | 50 (50 / 0) |
| a-t10-r1 vs b-t10-r1 | DIFF | DIFF | = | = | 60 (60 / 0) |
| a-t10-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 56 (56 / 0) |
| a-t10-r2 vs b-t1-r1 | DIFF | DIFF | = | = | 38 (38 / 0) |
| a-t10-r2 vs b-t2-r1 | DIFF | DIFF | = | = | 44 (44 / 0) |
| a-t10-r2 vs b-t10-r1 | DIFF | DIFF | = | = | 58 (58 / 0) |
| a-t10-r2 vs b-t10-r2 | DIFF | DIFF | = | = | 56 (56 / 0) |
| b-t1-r1 vs b-t2-r1 | DIFF | DIFF | = | = | 42 (42 / 0) |
| b-t1-r1 vs b-t10-r1 | DIFF | DIFF | = | = | 52 (52 / 0) |
| b-t1-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 62 (62 / 0) |
| b-t2-r1 vs b-t10-r1 | DIFF | DIFF | = | = | 46 (46 / 0) |
| b-t2-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 60 (60 / 0) |
| b-t10-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 62 (62 / 0) |

**a-t10-r1 vs a-t10-r2 -- RNG-dependent differences (44; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r1__vs__a-t10-r2.diff.txt`

| field | a-t10-r1 | a-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C2` | `20` | `46` |
| `C-table[compression].C0` | `116` | `64` |
| `C-table[covariance(1)].C2` | `22` | `18` |
| `C-table[covariance(16)].C0` | `88` | `55` |
| `C-table[covariance(2)].C0` | `11` | `6` |
| `C-table[covariance(32)].C2` | `614` | `915` |
| `C-table[covariance(8)].C0` | `8` | `6` |
| `C-table[excursion].C0` | `8` | `7` |
| `C-table[lenDirectionalRuns].C0` | `0` | `2` |
| `C-table[lenDirectionalRuns].C1` | `6` | `4` |
| `C-table[lenDirectionalRuns].C2` | `10` | `2` |
| `C-table[lenRunsMedian].C0` | `17` | `9` |
| `C-table[maxCollision].C0` | `9` | `12` |
| `C-table[numDirectionalRuns].C2` | `19` | `22` |
| `C-table[numIncreasesDecreases].C2` | `20` | `26` |
| `C-table[numRunsMedian].C0` | `6` | `14` |
| `C-table[periodicity(1)].C0` | `11` | `9` |
| `C-table[periodicity(16)].C2` | `14` | `16` |
| `C-table[periodicity(2)].C0` | `6` | `11` |
| `C-table[periodicity(2)].C2` | `9` | `6` |
| `C-table[periodicity(32)].C2` | `750` | `703` |
| `C-table[periodicity(8)].C2` | `11` | `6` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `116.0` | `64.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `88.0` | `55.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `17.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `9.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `11.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `20.0` | `46.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `22.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `614.0` | `915.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `10.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `19.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `20.0` | `26.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `14.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `750.0` | `703.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `11.0` | `6.0` |

**a-t10-r1 vs b-t1-r1 -- RNG-dependent differences (50; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r1__vs__b-t1-r1.diff.txt`

| field | a-t10-r1 | b-t1-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `20` | `21` |
| `C-table[compression].C0` | `116` | `57` |
| `C-table[covariance(1)].C2` | `22` | `6` |
| `C-table[covariance(16)].C0` | `88` | `89` |
| `C-table[covariance(2)].C0` | `11` | `15` |
| `C-table[covariance(32)].C2` | `614` | `476` |
| `C-table[covariance(8)].C0` | `8` | `6` |
| `C-table[lenDirectionalRuns].C0` | `0` | `2` |
| `C-table[lenDirectionalRuns].C1` | `6` | `4` |
| `C-table[lenDirectionalRuns].C2` | `10` | `4` |
| `C-table[lenRunsMedian].C0` | `17` | `11` |
| `C-table[lenRunsMedian].C1` | `4` | `2` |
| `C-table[lenRunsMedian].C2` | `2` | `4` |
| `C-table[maxCollision].C0` | `9` | `12` |
| `C-table[maxCollision].C1` | `3` | `2` |
| `C-table[maxCollision].C2` | `3` | `4` |
| `C-table[numDirectionalRuns].C2` | `19` | `14` |
| `C-table[numIncreasesDecreases].C2` | `20` | `22` |
| `C-table[numRunsMedian].C0` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `11` | `16` |
| `C-table[periodicity(16)].C2` | `14` | `21` |
| `C-table[periodicity(2)].C0` | `6` | `11` |
| `C-table[periodicity(2)].C2` | `9` | `6` |
| `C-table[periodicity(32)].C2` | `750` | `674` |
| `C-table[periodicity(8)].C2` | `11` | `6` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `116.0` | `57.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `88.0` | `89.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `11.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `17.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `9.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `11.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `20.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `22.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `614.0` | `476.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `10.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `2.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `19.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `20.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `14.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `750.0` | `674.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `11.0` | `6.0` |

**a-t10-r1 vs b-t2-r1 -- RNG-dependent differences (50; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r1__vs__b-t2-r1.diff.txt`

| field | a-t10-r1 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `20` | `25` |
| `C-table[compression].C0` | `116` | `39` |
| `C-table[covariance(1)].C2` | `22` | `12` |
| `C-table[covariance(16)].C0` | `88` | `51` |
| `C-table[covariance(2)].C0` | `11` | `12` |
| `C-table[covariance(32)].C2` | `614` | `806` |
| `C-table[covariance(8)].C0` | `8` | `6` |
| `C-table[excursion].C0` | `8` | `7` |
| `C-table[lenDirectionalRuns].C0` | `0` | `3` |
| `C-table[lenDirectionalRuns].C1` | `6` | `3` |
| `C-table[lenDirectionalRuns].C2` | `10` | `3` |
| `C-table[lenRunsMedian].C0` | `17` | `11` |
| `C-table[lenRunsMedian].C1` | `4` | `3` |
| `C-table[lenRunsMedian].C2` | `2` | `3` |
| `C-table[maxCollision].C0` | `9` | `14` |
| `C-table[maxCollision].C1` | `3` | `2` |
| `C-table[maxCollision].C2` | `3` | `4` |
| `C-table[numDirectionalRuns].C2` | `19` | `22` |
| `C-table[numIncreasesDecreases].C2` | `20` | `10` |
| `C-table[numRunsMedian].C0` | `6` | `15` |
| `C-table[periodicity(1)].C0` | `11` | `20` |
| `C-table[periodicity(16)].C2` | `14` | `6` |
| `C-table[periodicity(2)].C2` | `9` | `11` |
| `C-table[periodicity(32)].C2` | `750` | `1632` |
| `C-table[periodicity(8)].C2` | `11` | `6` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `116.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `88.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `11.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `0.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `17.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `9.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `11.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `6.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `20.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `22.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `614.0` | `806.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `10.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `19.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `20.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `14.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `9.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `750.0` | `1632.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `11.0` | `6.0` |

**a-t10-r1 vs b-t10-r1 -- RNG-dependent differences (60; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r1__vs__b-t10-r1.diff.txt`

| field | a-t10-r1 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `20` | `17` |
| `C-table[compression].C0` | `116` | `51` |
| `C-table[compression].C1` | `0` | `1` |
| `C-table[compression].C2` | `6` | `5` |
| `C-table[covariance(1)].C2` | `22` | `6` |
| `C-table[covariance(16)].C0` | `88` | `66` |
| `C-table[covariance(2)].C0` | `11` | `14` |
| `C-table[covariance(32)].C2` | `614` | `544` |
| `C-table[covariance(8)].C0` | `8` | `6` |
| `C-table[excursion].C0` | `8` | `7` |
| `C-table[lenDirectionalRuns].C0` | `0` | `8` |
| `C-table[lenDirectionalRuns].C1` | `6` | `3` |
| `C-table[lenDirectionalRuns].C2` | `10` | `3` |
| `C-table[lenRunsMedian].C0` | `17` | `7` |
| `C-table[lenRunsMedian].C1` | `4` | `3` |
| `C-table[lenRunsMedian].C2` | `2` | `3` |
| `C-table[maxCollision].C0` | `9` | `7` |
| `C-table[maxCollision].C1` | `3` | `2` |
| `C-table[maxCollision].C2` | `3` | `4` |
| `C-table[numDirectionalRuns].C2` | `19` | `32` |
| `C-table[numIncreasesDecreases].C0` | `6` | `9` |
| `C-table[numIncreasesDecreases].C2` | `20` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `11` | `16` |
| `C-table[periodicity(16)].C0` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `14` | `22` |
| `C-table[periodicity(2)].C2` | `9` | `6` |
| `C-table[periodicity(32)].C2` | `750` | `514` |
| `C-table[periodicity(8)].C2` | `11` | `7` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `116.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `88.0` | `66.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `11.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `0.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `17.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `9.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `11.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `6.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `20.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `22.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `614.0` | `544.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `10.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `19.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `20.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `14.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `750.0` | `514.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `11.0` | `7.0` |

**a-t10-r1 vs b-t10-r2 -- RNG-dependent differences (56; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r1__vs__b-t10-r2.diff.txt`

| field | a-t10-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C2` | `20` | `12` |
| `C-table[compression].C0` | `116` | `35` |
| `C-table[covariance(1)].C2` | `22` | `13` |
| `C-table[covariance(16)].C0` | `88` | `59` |
| `C-table[covariance(32)].C0` | `6` | `5` |
| `C-table[covariance(32)].C1` | `0` | `1` |
| `C-table[covariance(32)].C2` | `614` | `1083` |
| `C-table[covariance(8)].C0` | `8` | `6` |
| `C-table[covariance(8)].C2` | `6` | `8` |
| `C-table[excursion].C0` | `8` | `10` |
| `C-table[lenDirectionalRuns].C0` | `0` | `3` |
| `C-table[lenDirectionalRuns].C1` | `6` | `5` |
| `C-table[lenDirectionalRuns].C2` | `10` | `1` |
| `C-table[lenRunsMedian].C0` | `17` | `5` |
| `C-table[maxCollision].C0` | `9` | `11` |
| `C-table[maxCollision].C1` | `3` | `1` |
| `C-table[maxCollision].C2` | `3` | `5` |
| `C-table[numDirectionalRuns].C2` | `19` | `8` |
| `C-table[numIncreasesDecreases].C2` | `20` | `26` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `11` | `8` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `14` | `5` |
| `C-table[periodicity(2)].C2` | `9` | `6` |
| `C-table[periodicity(32)].C2` | `750` | `1429` |
| `C-table[periodicity(8)].C2` | `11` | `25` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `116.0` | `35.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `88.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `0.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `17.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `9.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `20.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `22.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `614.0` | `1083.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `10.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `19.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `20.0` | `26.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `14.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `750.0` | `1429.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `11.0` | `25.0` |

**a-t10-r2 vs b-t1-r1 -- RNG-dependent differences (38; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r2__vs__b-t1-r1.diff.txt`

| field | a-t10-r2 | b-t1-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `46` | `21` |
| `C-table[compression].C0` | `64` | `57` |
| `C-table[covariance(1)].C2` | `18` | `6` |
| `C-table[covariance(16)].C0` | `55` | `89` |
| `C-table[covariance(2)].C0` | `6` | `15` |
| `C-table[covariance(32)].C2` | `915` | `476` |
| `C-table[excursion].C0` | `7` | `8` |
| `C-table[lenDirectionalRuns].C2` | `2` | `4` |
| `C-table[lenRunsMedian].C0` | `9` | `11` |
| `C-table[lenRunsMedian].C1` | `4` | `2` |
| `C-table[lenRunsMedian].C2` | `2` | `4` |
| `C-table[maxCollision].C1` | `3` | `2` |
| `C-table[maxCollision].C2` | `3` | `4` |
| `C-table[numDirectionalRuns].C2` | `22` | `14` |
| `C-table[numIncreasesDecreases].C2` | `26` | `22` |
| `C-table[numRunsMedian].C0` | `14` | `8` |
| `C-table[periodicity(1)].C0` | `9` | `16` |
| `C-table[periodicity(16)].C2` | `16` | `21` |
| `C-table[periodicity(32)].C2` | `703` | `674` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `64.0` | `57.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `55.0` | `89.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `6.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `7.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `9.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `14.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `9.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `46.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `18.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `915.0` | `476.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `2.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `2.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `22.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `26.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `16.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `703.0` | `674.0` |

**a-t10-r2 vs b-t2-r1 -- RNG-dependent differences (44; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r2__vs__b-t2-r1.diff.txt`

| field | a-t10-r2 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `46` | `25` |
| `C-table[compression].C0` | `64` | `39` |
| `C-table[covariance(1)].C2` | `18` | `12` |
| `C-table[covariance(16)].C0` | `55` | `51` |
| `C-table[covariance(2)].C0` | `6` | `12` |
| `C-table[covariance(32)].C2` | `915` | `806` |
| `C-table[lenDirectionalRuns].C0` | `2` | `3` |
| `C-table[lenDirectionalRuns].C1` | `4` | `3` |
| `C-table[lenDirectionalRuns].C2` | `2` | `3` |
| `C-table[lenRunsMedian].C0` | `9` | `11` |
| `C-table[lenRunsMedian].C1` | `4` | `3` |
| `C-table[lenRunsMedian].C2` | `2` | `3` |
| `C-table[maxCollision].C0` | `12` | `14` |
| `C-table[maxCollision].C1` | `3` | `2` |
| `C-table[maxCollision].C2` | `3` | `4` |
| `C-table[numIncreasesDecreases].C2` | `26` | `10` |
| `C-table[numRunsMedian].C0` | `14` | `15` |
| `C-table[periodicity(1)].C0` | `9` | `20` |
| `C-table[periodicity(16)].C2` | `16` | `6` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(2)].C2` | `6` | `11` |
| `C-table[periodicity(32)].C2` | `703` | `1632` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `64.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `55.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `9.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `12.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `14.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `9.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `46.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `18.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `915.0` | `806.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `26.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `16.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `703.0` | `1632.0` |

**a-t10-r2 vs b-t10-r1 -- RNG-dependent differences (58; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r2__vs__b-t10-r1.diff.txt`

| field | a-t10-r2 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `46` | `17` |
| `C-table[compression].C0` | `64` | `51` |
| `C-table[compression].C1` | `0` | `1` |
| `C-table[compression].C2` | `6` | `5` |
| `C-table[covariance(1)].C2` | `18` | `6` |
| `C-table[covariance(16)].C0` | `55` | `66` |
| `C-table[covariance(2)].C0` | `6` | `14` |
| `C-table[covariance(32)].C2` | `915` | `544` |
| `C-table[lenDirectionalRuns].C0` | `2` | `8` |
| `C-table[lenDirectionalRuns].C1` | `4` | `3` |
| `C-table[lenDirectionalRuns].C2` | `2` | `3` |
| `C-table[lenRunsMedian].C0` | `9` | `7` |
| `C-table[lenRunsMedian].C1` | `4` | `3` |
| `C-table[lenRunsMedian].C2` | `2` | `3` |
| `C-table[maxCollision].C0` | `12` | `7` |
| `C-table[maxCollision].C1` | `3` | `2` |
| `C-table[maxCollision].C2` | `3` | `4` |
| `C-table[numDirectionalRuns].C2` | `22` | `32` |
| `C-table[numIncreasesDecreases].C0` | `6` | `9` |
| `C-table[numIncreasesDecreases].C2` | `26` | `6` |
| `C-table[numRunsMedian].C0` | `14` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `9` | `16` |
| `C-table[periodicity(16)].C0` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `16` | `22` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `703` | `514` |
| `C-table[periodicity(8)].C2` | `6` | `7` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `64.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `55.0` | `66.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `6.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `9.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `12.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `14.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `9.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `46.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `18.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `915.0` | `544.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `22.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `26.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `16.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `703.0` | `514.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `6.0` | `7.0` |

**a-t10-r2 vs b-t10-r2 -- RNG-dependent differences (56; expected under a live seed):** full list in `iid/truerand_1bit/a-t10-r2__vs__b-t10-r2.diff.txt`

| field | a-t10-r2 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C2` | `46` | `12` |
| `C-table[compression].C0` | `64` | `35` |
| `C-table[covariance(1)].C2` | `18` | `13` |
| `C-table[covariance(16)].C0` | `55` | `59` |
| `C-table[covariance(2)].C0` | `6` | `11` |
| `C-table[covariance(32)].C0` | `6` | `5` |
| `C-table[covariance(32)].C1` | `0` | `1` |
| `C-table[covariance(32)].C2` | `915` | `1083` |
| `C-table[covariance(8)].C2` | `6` | `8` |
| `C-table[excursion].C0` | `7` | `10` |
| `C-table[lenDirectionalRuns].C0` | `2` | `3` |
| `C-table[lenDirectionalRuns].C1` | `4` | `5` |
| `C-table[lenDirectionalRuns].C2` | `2` | `1` |
| `C-table[lenRunsMedian].C0` | `9` | `5` |
| `C-table[maxCollision].C0` | `12` | `11` |
| `C-table[maxCollision].C1` | `3` | `1` |
| `C-table[maxCollision].C2` | `3` | `5` |
| `C-table[numDirectionalRuns].C2` | `22` | `8` |
| `C-table[numRunsMedian].C0` | `14` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `9` | `8` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `16` | `5` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `703` | `1429` |
| `C-table[periodicity(8)].C2` | `6` | `25` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `64.0` | `35.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `55.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `7.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `9.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `12.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `14.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `9.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `46.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `18.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `915.0` | `1083.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `22.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `16.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `703.0` | `1429.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `6.0` | `25.0` |

**b-t1-r1 vs b-t2-r1 -- RNG-dependent differences (42; expected under a live seed):** full list in `iid/truerand_1bit/b-t1-r1__vs__b-t2-r1.diff.txt`

| field | b-t1-r1 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `21` | `25` |
| `C-table[compression].C0` | `57` | `39` |
| `C-table[covariance(1)].C2` | `6` | `12` |
| `C-table[covariance(16)].C0` | `89` | `51` |
| `C-table[covariance(2)].C0` | `15` | `12` |
| `C-table[covariance(32)].C2` | `476` | `806` |
| `C-table[excursion].C0` | `8` | `7` |
| `C-table[lenDirectionalRuns].C0` | `2` | `3` |
| `C-table[lenDirectionalRuns].C1` | `4` | `3` |
| `C-table[lenDirectionalRuns].C2` | `4` | `3` |
| `C-table[lenRunsMedian].C1` | `2` | `3` |
| `C-table[lenRunsMedian].C2` | `4` | `3` |
| `C-table[maxCollision].C0` | `12` | `14` |
| `C-table[numDirectionalRuns].C2` | `14` | `22` |
| `C-table[numIncreasesDecreases].C2` | `22` | `10` |
| `C-table[numRunsMedian].C0` | `8` | `15` |
| `C-table[periodicity(1)].C0` | `16` | `20` |
| `C-table[periodicity(16)].C2` | `21` | `6` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(2)].C2` | `6` | `11` |
| `C-table[periodicity(32)].C2` | `674` | `1632` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `57.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `89.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `15.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `12.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `8.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `16.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `21.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `476.0` | `806.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `14.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `22.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `21.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `674.0` | `1632.0` |

**b-t1-r1 vs b-t10-r1 -- RNG-dependent differences (52; expected under a live seed):** full list in `iid/truerand_1bit/b-t1-r1__vs__b-t10-r1.diff.txt`

| field | b-t1-r1 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `21` | `17` |
| `C-table[compression].C0` | `57` | `51` |
| `C-table[compression].C1` | `0` | `1` |
| `C-table[compression].C2` | `6` | `5` |
| `C-table[covariance(16)].C0` | `89` | `66` |
| `C-table[covariance(2)].C0` | `15` | `14` |
| `C-table[covariance(32)].C2` | `476` | `544` |
| `C-table[excursion].C0` | `8` | `7` |
| `C-table[lenDirectionalRuns].C0` | `2` | `8` |
| `C-table[lenDirectionalRuns].C1` | `4` | `3` |
| `C-table[lenDirectionalRuns].C2` | `4` | `3` |
| `C-table[lenRunsMedian].C0` | `11` | `7` |
| `C-table[lenRunsMedian].C1` | `2` | `3` |
| `C-table[lenRunsMedian].C2` | `4` | `3` |
| `C-table[maxCollision].C0` | `12` | `7` |
| `C-table[numDirectionalRuns].C2` | `14` | `32` |
| `C-table[numIncreasesDecreases].C0` | `6` | `9` |
| `C-table[numIncreasesDecreases].C2` | `22` | `6` |
| `C-table[numRunsMedian].C0` | `8` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(16)].C0` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `21` | `22` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `674` | `514` |
| `C-table[periodicity(8)].C2` | `6` | `7` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `57.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `89.0` | `66.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `15.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `11.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `12.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `21.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `476.0` | `544.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `14.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `22.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `21.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `674.0` | `514.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `6.0` | `7.0` |

**b-t1-r1 vs b-t10-r2 -- RNG-dependent differences (62; expected under a live seed):** full list in `iid/truerand_1bit/b-t1-r1__vs__b-t10-r2.diff.txt`

| field | b-t1-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C2` | `21` | `12` |
| `C-table[compression].C0` | `57` | `35` |
| `C-table[covariance(1)].C2` | `6` | `13` |
| `C-table[covariance(16)].C0` | `89` | `59` |
| `C-table[covariance(2)].C0` | `15` | `11` |
| `C-table[covariance(32)].C0` | `6` | `5` |
| `C-table[covariance(32)].C1` | `0` | `1` |
| `C-table[covariance(32)].C2` | `476` | `1083` |
| `C-table[covariance(8)].C2` | `6` | `8` |
| `C-table[excursion].C0` | `8` | `10` |
| `C-table[lenDirectionalRuns].C0` | `2` | `3` |
| `C-table[lenDirectionalRuns].C1` | `4` | `5` |
| `C-table[lenDirectionalRuns].C2` | `4` | `1` |
| `C-table[lenRunsMedian].C0` | `11` | `5` |
| `C-table[lenRunsMedian].C1` | `2` | `4` |
| `C-table[lenRunsMedian].C2` | `4` | `2` |
| `C-table[maxCollision].C0` | `12` | `11` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `14` | `8` |
| `C-table[numIncreasesDecreases].C2` | `22` | `26` |
| `C-table[numRunsMedian].C0` | `8` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `16` | `8` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `21` | `5` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `674` | `1429` |
| `C-table[periodicity(8)].C2` | `6` | `25` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `57.0` | `35.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `89.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `15.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `11.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `12.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `16.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `2.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `21.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `6.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `476.0` | `1083.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `4.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `14.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `22.0` | `26.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `21.0` | `5.0` |
| ... 2 more | | |

**b-t2-r1 vs b-t10-r1 -- RNG-dependent differences (46; expected under a live seed):** full list in `iid/truerand_1bit/b-t2-r1__vs__b-t10-r1.diff.txt`

| field | b-t2-r1 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C2` | `25` | `17` |
| `C-table[compression].C0` | `39` | `51` |
| `C-table[compression].C1` | `0` | `1` |
| `C-table[compression].C2` | `6` | `5` |
| `C-table[covariance(1)].C2` | `12` | `6` |
| `C-table[covariance(16)].C0` | `51` | `66` |
| `C-table[covariance(2)].C0` | `12` | `14` |
| `C-table[covariance(32)].C2` | `806` | `544` |
| `C-table[lenDirectionalRuns].C0` | `3` | `8` |
| `C-table[lenRunsMedian].C0` | `11` | `7` |
| `C-table[maxCollision].C0` | `14` | `7` |
| `C-table[numDirectionalRuns].C2` | `22` | `32` |
| `C-table[numIncreasesDecreases].C0` | `6` | `9` |
| `C-table[numIncreasesDecreases].C2` | `10` | `6` |
| `C-table[numRunsMedian].C0` | `15` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `20` | `16` |
| `C-table[periodicity(16)].C0` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `6` | `22` |
| `C-table[periodicity(2)].C2` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `1632` | `514` |
| `C-table[periodicity(8)].C2` | `6` | `7` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `39.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `51.0` | `66.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `12.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `3.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `11.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `14.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `15.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `20.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `25.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `12.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `806.0` | `544.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `22.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `10.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `6.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1632.0` | `514.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `6.0` | `7.0` |

**b-t2-r1 vs b-t10-r2 -- RNG-dependent differences (60; expected under a live seed):** full list in `iid/truerand_1bit/b-t2-r1__vs__b-t10-r2.diff.txt`

| field | b-t2-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C2` | `25` | `12` |
| `C-table[compression].C0` | `39` | `35` |
| `C-table[covariance(1)].C2` | `12` | `13` |
| `C-table[covariance(16)].C0` | `51` | `59` |
| `C-table[covariance(2)].C0` | `12` | `11` |
| `C-table[covariance(32)].C0` | `6` | `5` |
| `C-table[covariance(32)].C1` | `0` | `1` |
| `C-table[covariance(32)].C2` | `806` | `1083` |
| `C-table[covariance(8)].C2` | `6` | `8` |
| `C-table[excursion].C0` | `7` | `10` |
| `C-table[lenDirectionalRuns].C1` | `3` | `5` |
| `C-table[lenDirectionalRuns].C2` | `3` | `1` |
| `C-table[lenRunsMedian].C0` | `11` | `5` |
| `C-table[lenRunsMedian].C1` | `3` | `4` |
| `C-table[lenRunsMedian].C2` | `3` | `2` |
| `C-table[maxCollision].C0` | `14` | `11` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `22` | `8` |
| `C-table[numIncreasesDecreases].C2` | `10` | `26` |
| `C-table[numRunsMedian].C0` | `15` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `8` |
| `C-table[periodicity(1)].C0` | `20` | `8` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `6` | `5` |
| `C-table[periodicity(2)].C2` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `1632` | `1429` |
| `C-table[periodicity(8)].C2` | `6` | `25` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `39.0` | `35.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `51.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `12.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `7.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `11.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `14.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `15.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `20.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `3.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `25.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `12.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `806.0` | `1083.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `3.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `22.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `10.0` | `26.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1632.0` | `1429.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `6.0` | `25.0` |

**b-t10-r1 vs b-t10-r2 -- RNG-dependent differences (62; expected under a live seed):** full list in `iid/truerand_1bit/b-t10-r1__vs__b-t10-r2.diff.txt`

| field | b-t10-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C2` | `17` | `12` |
| `C-table[compression].C0` | `51` | `35` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `5` | `6` |
| `C-table[covariance(1)].C2` | `6` | `13` |
| `C-table[covariance(16)].C0` | `66` | `59` |
| `C-table[covariance(2)].C0` | `14` | `11` |
| `C-table[covariance(32)].C0` | `6` | `5` |
| `C-table[covariance(32)].C1` | `0` | `1` |
| `C-table[covariance(32)].C2` | `544` | `1083` |
| `C-table[covariance(8)].C2` | `6` | `8` |
| `C-table[excursion].C0` | `7` | `10` |
| `C-table[lenDirectionalRuns].C0` | `8` | `3` |
| `C-table[lenDirectionalRuns].C1` | `3` | `5` |
| `C-table[lenDirectionalRuns].C2` | `3` | `1` |
| `C-table[lenRunsMedian].C0` | `7` | `5` |
| `C-table[lenRunsMedian].C1` | `3` | `4` |
| `C-table[lenRunsMedian].C2` | `3` | `2` |
| `C-table[maxCollision].C0` | `7` | `11` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `32` | `8` |
| `C-table[numIncreasesDecreases].C0` | `9` | `6` |
| `C-table[numIncreasesDecreases].C2` | `6` | `26` |
| `C-table[periodicity(1)].C0` | `16` | `8` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C0` | `5` | `6` |
| `C-table[periodicity(16)].C2` | `22` | `5` |
| `C-table[periodicity(32)].C2` | `514` | `1429` |
| `C-table[periodicity(8)].C2` | `7` | `25` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `51.0` | `35.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `66.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `14.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `7.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `8.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `7.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `7.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `16.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `3.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.avgCollision` | `17.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `6.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `544.0` | `1083.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `3.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `32.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `6.0` | `26.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `22.0` | `5.0` |
| ... 2 more | | |

**Verdict and seed-source table (arm a = default `/dev/urandom`, arm b = `EA_TEST_RANDOM_SOURCE` set):**

| run | arm | threads | random source env | rc | chi-square | LRS | permutation | JSON IID | errorLevel | Assessed min entropy | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-t10-r1 | a | 10 | /dev/urandom (default) | 0 | Passed | Passed | Passed | True | 0 | 0.99504301513122573 | 16 |
| a-t10-r2 | a | 10 | /dev/urandom (default) | 0 | Passed | Passed | Passed | True | 0 | 0.99504301513122573 | 13 |
| b-t1-r1 | b | 1 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.99504301513122573 | 20 |
| b-t2-r1 | b | 2 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.99504301513122573 | 18 |
| b-t10-r1 | b | 10 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.99504301513122573 | 11 |
| b-t10-r2 | b | 10 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.99504301513122573 | 15 |

Counters C0/C1/C2 per statistic and run (`-` = not printed; a row identical across every run under a live seed would be surprising):

| statistic | a-t10-r1 | a-t10-r2 | b-t1-r1 | b-t2-r1 | b-t10-r1 | b-t10-r2 | identical across runs |
|---|---|---|---|---|---|---|---|
| avgCollision | 6/0/20 | 6/0/46 | 6/0/21 | 6/0/25 | 6/0/17 | 6/0/12 | no |
| compression | 116/0/6 | 64/0/6 | 57/0/6 | 39/0/6 | 51/1/5 | 35/0/6 | no |
| covariance(1) | 6/0/22 | 6/0/18 | 6/0/6 | 6/0/12 | 6/0/6 | 6/0/13 | no |
| covariance(16) | 88/0/6 | 55/0/6 | 89/0/6 | 51/0/6 | 66/0/6 | 59/0/6 | no |
| covariance(2) | 11/0/6 | 6/0/6 | 15/0/6 | 12/0/6 | 14/0/6 | 11/0/6 | no |
| covariance(32) | 6/0/614 | 6/0/915 | 6/0/476 | 6/0/806 | 6/0/544 | 5/1/1083 | no |
| covariance(8) | 8/0/6 | 6/0/6 | 6/0/6 | 6/0/6 | 6/0/6 | 6/0/8 | no |
| excursion | 8/0/6 | 7/0/6 | 8/0/6 | 7/0/6 | 7/0/6 | 10/0/6 | no |
| lenDirectionalRuns | 0/6/10 | 2/4/2 | 2/4/4 | 3/3/3 | 8/3/3 | 3/5/1 | no |
| lenRunsMedian | 17/4/2 | 9/4/2 | 11/2/4 | 11/3/3 | 7/3/3 | 5/4/2 | no |
| maxCollision | 9/3/3 | 12/3/3 | 12/2/4 | 14/2/4 | 7/2/4 | 11/1/5 | no |
| numDirectionalRuns | 6/0/19 | 6/0/22 | 6/0/14 | 6/0/22 | 6/0/32 | 6/0/8 | no |
| numIncreasesDecreases | 6/0/20 | 6/0/26 | 6/0/22 | 6/0/10 | 9/0/6 | 6/0/26 | no |
| numRunsMedian | 6/0/6 | 14/0/6 | 8/0/6 | 15/0/6 | 6/0/8 | 6/0/8 | no |
| periodicity(1) | 11/0/6 | 9/0/6 | 16/0/6 | 20/0/6 | 16/0/6 | 8/1/5 | no |
| periodicity(16) | 6/0/14 | 6/0/16 | 6/0/21 | 6/0/6 | 5/1/22 | 6/1/5 | no |
| periodicity(2) | 6/0/9 | 11/0/6 | 11/0/6 | 6/0/11 | 6/0/6 | 6/0/6 | no |
| periodicity(32) | 6/0/750 | 6/0/703 | 6/0/674 | 6/0/1632 | 6/0/514 | 6/0/1429 | no |
| periodicity(8) | 6/0/11 | 6/0/6 | 6/0/6 | 6/0/6 | 6/0/7 | 6/0/25 | no |

Arm (b) under `EA_TEST_RANDOM_SOURCE`: two runs at the same thread count agree on the JSON? threads=10: DIFFER (2 runs). Prediction from the source was DIFFER (the variable does not reach `seed()`); if they AGREE, the source reading above is wrong and must be re-read.

Reading: every RNG-independent field is identical in all pairs; only the permutation counters/verdict path varies, which the live seed explains. NOT a finding.

## iid / truerand_8bit -- DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| a-t10-r1 | a | 10 | 0 | yes | 13 | 22f1319ae347ab4e | c7e56911d2657fa9 | 0 |
| a-t10-r2 | a | 10 | 0 | yes | 4 | 22f1319ae347ab4e | c7e56911d2657fa9 | 0 |
| b-t1-r1 | b | 1 | 0 | yes | 18 | 22f1319ae347ab4e | c7e56911d2657fa9 | 0 |
| b-t2-r1 | b | 2 | 0 | yes | 9 | 22f1319ae347ab4e | c7e56911d2657fa9 | 0 |
| b-t10-r1 | b | 10 | 0 | yes | 6 | 22f1319ae347ab4e | c7e56911d2657fa9 | 0 |
| b-t10-r2 | b | 10 | 0 | yes | 8 | 22f1319ae347ab4e | c7e56911d2657fa9 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| a-t10-r1 vs a-t10-r2 | DIFF | DIFF | = | = | 52 (52 / 0) |
| a-t10-r1 vs b-t1-r1 | DIFF | DIFF | = | = | 44 (44 / 0) |
| a-t10-r1 vs b-t2-r1 | DIFF | DIFF | = | = | 48 (48 / 0) |
| a-t10-r1 vs b-t10-r1 | DIFF | DIFF | = | = | 56 (56 / 0) |
| a-t10-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 42 (42 / 0) |
| a-t10-r2 vs b-t1-r1 | DIFF | DIFF | = | = | 54 (54 / 0) |
| a-t10-r2 vs b-t2-r1 | DIFF | DIFF | = | = | 52 (52 / 0) |
| a-t10-r2 vs b-t10-r1 | DIFF | DIFF | = | = | 52 (52 / 0) |
| a-t10-r2 vs b-t10-r2 | DIFF | DIFF | = | = | 48 (48 / 0) |
| b-t1-r1 vs b-t2-r1 | DIFF | DIFF | = | = | 50 (50 / 0) |
| b-t1-r1 vs b-t10-r1 | DIFF | DIFF | = | = | 56 (56 / 0) |
| b-t1-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 44 (44 / 0) |
| b-t2-r1 vs b-t10-r1 | DIFF | DIFF | = | = | 48 (48 / 0) |
| b-t2-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 52 (52 / 0) |
| b-t10-r1 vs b-t10-r2 | DIFF | DIFF | = | = | 54 (54 / 0) |

**a-t10-r1 vs a-t10-r2 -- RNG-dependent differences (52; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r1__vs__a-t10-r2.diff.txt`

| field | a-t10-r1 | a-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `46` | `24` |
| `C-table[compression].C0` | `5` | `6` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `38` | `10` |
| `C-table[covariance(1)].C2` | `15` | `11` |
| `C-table[covariance(16)].C2` | `6` | `24` |
| `C-table[covariance(2)].C2` | `55` | `76` |
| `C-table[covariance(8)].C0` | `8` | `6` |
| `C-table[covariance(8)].C2` | `6` | `8` |
| `C-table[lenDirectionalRuns].C0` | `3` | `4` |
| `C-table[lenRunsMedian].C0` | `23` | `21` |
| `C-table[lenRunsMedian].C1` | `6` | `5` |
| `C-table[lenRunsMedian].C2` | `0` | `1` |
| `C-table[maxCollision].C0` | `8` | `7` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `78` | `21` |
| `C-table[numIncreasesDecreases].C0` | `6` | `8` |
| `C-table[numRunsMedian].C0` | `6` | `11` |
| `C-table[periodicity(1)].C2` | `44` | `21` |
| `C-table[periodicity(16)].C0` | `8` | `17` |
| `C-table[periodicity(2)].C0` | `11` | `14` |
| `C-table[periodicity(32)].C0` | `6` | `5` |
| `C-table[periodicity(32)].C1` | `0` | `1` |
| `C-table[periodicity(32)].C2` | `1305` | `302` |
| `C-table[periodicity(8)].C2` | `30` | `50` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `46.0` | `24.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `23.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `8.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `14.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `38.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `15.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `6.0` | `24.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `55.0` | `76.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `78.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `44.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1305.0` | `302.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `30.0` | `50.0` |

**a-t10-r1 vs b-t1-r1 -- RNG-dependent differences (44; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r1__vs__b-t1-r1.diff.txt`

| field | a-t10-r1 | b-t1-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `46` | `30` |
| `C-table[compression].C0` | `5` | `6` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `38` | `39` |
| `C-table[covariance(1)].C2` | `15` | `11` |
| `C-table[covariance(16)].C0` | `6` | `9` |
| `C-table[covariance(2)].C2` | `55` | `43` |
| `C-table[covariance(32)].C2` | `6` | `10` |
| `C-table[covariance(8)].C0` | `8` | `18` |
| `C-table[excursion].C2` | `11` | `13` |
| `C-table[lenDirectionalRuns].C0` | `3` | `6` |
| `C-table[lenRunsMedian].C0` | `23` | `34` |
| `C-table[maxCollision].C0` | `8` | `11` |
| `C-table[numDirectionalRuns].C2` | `78` | `70` |
| `C-table[numIncreasesDecreases].C0` | `6` | `7` |
| `C-table[numRunsMedian].C0` | `6` | `5` |
| `C-table[numRunsMedian].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `44` | `30` |
| `C-table[periodicity(16)].C0` | `8` | `12` |
| `C-table[periodicity(2)].C0` | `11` | `7` |
| `C-table[periodicity(32)].C2` | `1305` | `1413` |
| `C-table[periodicity(8)].C2` | `30` | `40` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `46.0` | `30.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `3.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `23.0` | `34.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `8.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.numRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `38.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `15.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `55.0` | `43.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `78.0` | `70.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `44.0` | `30.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1305.0` | `1413.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `30.0` | `40.0` |

**a-t10-r1 vs b-t2-r1 -- RNG-dependent differences (48; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r1__vs__b-t2-r1.diff.txt`

| field | a-t10-r1 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `46` | `61` |
| `C-table[compression].C0` | `5` | `6` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `38` | `29` |
| `C-table[covariance(1)].C2` | `15` | `13` |
| `C-table[covariance(16)].C2` | `6` | `9` |
| `C-table[covariance(2)].C2` | `55` | `104` |
| `C-table[covariance(32)].C2` | `6` | `9` |
| `C-table[excursion].C2` | `11` | `10` |
| `C-table[lenDirectionalRuns].C0` | `3` | `2` |
| `C-table[lenRunsMedian].C0` | `23` | `28` |
| `C-table[lenRunsMedian].C1` | `6` | `5` |
| `C-table[lenRunsMedian].C2` | `0` | `1` |
| `C-table[maxCollision].C0` | `8` | `11` |
| `C-table[numDirectionalRuns].C2` | `78` | `118` |
| `C-table[numIncreasesDecreases].C2` | `6` | `8` |
| `C-table[numRunsMedian].C0` | `6` | `11` |
| `C-table[periodicity(1)].C2` | `44` | `32` |
| `C-table[periodicity(16)].C0` | `8` | `20` |
| `C-table[periodicity(2)].C0` | `11` | `6` |
| `C-table[periodicity(32)].C2` | `1305` | `427` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `C-table[periodicity(8)].C2` | `30` | `31` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `46.0` | `61.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `23.0` | `28.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `8.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `38.0` | `29.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `15.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `55.0` | `104.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `78.0` | `118.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `44.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1305.0` | `427.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `30.0` | `31.0` |

**a-t10-r1 vs b-t10-r1 -- RNG-dependent differences (56; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r1__vs__b-t10-r1.diff.txt`

| field | a-t10-r1 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `46` | `39` |
| `C-table[compression].C0` | `5` | `6` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `38` | `19` |
| `C-table[covariance(1)].C2` | `15` | `11` |
| `C-table[covariance(16)].C2` | `6` | `18` |
| `C-table[covariance(2)].C2` | `55` | `46` |
| `C-table[covariance(32)].C2` | `6` | `8` |
| `C-table[covariance(8)].C0` | `8` | `11` |
| `C-table[excursion].C0` | `6` | `8` |
| `C-table[excursion].C2` | `11` | `6` |
| `C-table[lenDirectionalRuns].C0` | `3` | `5` |
| `C-table[lenRunsMedian].C0` | `23` | `21` |
| `C-table[lenRunsMedian].C1` | `6` | `5` |
| `C-table[lenRunsMedian].C2` | `0` | `1` |
| `C-table[maxCollision].C0` | `8` | `22` |
| `C-table[maxCollision].C1` | `2` | `3` |
| `C-table[maxCollision].C2` | `4` | `3` |
| `C-table[numDirectionalRuns].C2` | `78` | `59` |
| `C-table[numIncreasesDecreases].C0` | `6` | `17` |
| `C-table[periodicity(1)].C2` | `44` | `16` |
| `C-table[periodicity(16)].C0` | `8` | `6` |
| `C-table[periodicity(16)].C2` | `6` | `12` |
| `C-table[periodicity(2)].C0` | `11` | `23` |
| `C-table[periodicity(32)].C2` | `1305` | `371` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `C-table[periodicity(8)].C2` | `30` | `70` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `46.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `3.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `23.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `38.0` | `19.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `15.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `6.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `55.0` | `46.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `78.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `44.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1305.0` | `371.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `30.0` | `70.0` |

**a-t10-r1 vs b-t10-r2 -- RNG-dependent differences (42; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r1__vs__b-t10-r2.diff.txt`

| field | a-t10-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `46` | `37` |
| `C-table[compression].C0` | `5` | `6` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `38` | `32` |
| `C-table[covariance(1)].C2` | `15` | `8` |
| `C-table[covariance(16)].C0` | `6` | `7` |
| `C-table[covariance(2)].C2` | `55` | `91` |
| `C-table[covariance(32)].C2` | `6` | `18` |
| `C-table[excursion].C2` | `11` | `8` |
| `C-table[lenDirectionalRuns].C0` | `3` | `1` |
| `C-table[lenRunsMedian].C0` | `23` | `25` |
| `C-table[maxCollision].C0` | `8` | `10` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `78` | `67` |
| `C-table[numIncreasesDecreases].C0` | `6` | `8` |
| `C-table[periodicity(1)].C2` | `44` | `51` |
| `C-table[periodicity(16)].C0` | `8` | `9` |
| `C-table[periodicity(2)].C0` | `11` | `20` |
| `C-table[periodicity(32)].C2` | `1305` | `511` |
| `C-table[periodicity(8)].C2` | `30` | `43` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `46.0` | `37.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `3.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `23.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `8.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `11.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `38.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `15.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `55.0` | `91.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `78.0` | `67.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `44.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1305.0` | `511.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `30.0` | `43.0` |

**a-t10-r2 vs b-t1-r1 -- RNG-dependent differences (54; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r2__vs__b-t1-r1.diff.txt`

| field | a-t10-r2 | b-t1-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `24` | `30` |
| `C-table[compression].C2` | `10` | `39` |
| `C-table[covariance(16)].C0` | `6` | `9` |
| `C-table[covariance(16)].C2` | `24` | `6` |
| `C-table[covariance(2)].C2` | `76` | `43` |
| `C-table[covariance(32)].C2` | `6` | `10` |
| `C-table[covariance(8)].C0` | `6` | `18` |
| `C-table[covariance(8)].C2` | `8` | `6` |
| `C-table[excursion].C2` | `11` | `13` |
| `C-table[lenDirectionalRuns].C0` | `4` | `6` |
| `C-table[lenRunsMedian].C0` | `21` | `34` |
| `C-table[lenRunsMedian].C1` | `5` | `6` |
| `C-table[lenRunsMedian].C2` | `1` | `0` |
| `C-table[maxCollision].C0` | `7` | `11` |
| `C-table[maxCollision].C1` | `1` | `2` |
| `C-table[maxCollision].C2` | `5` | `4` |
| `C-table[numDirectionalRuns].C2` | `21` | `70` |
| `C-table[numIncreasesDecreases].C0` | `8` | `7` |
| `C-table[numRunsMedian].C0` | `11` | `5` |
| `C-table[numRunsMedian].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `21` | `30` |
| `C-table[periodicity(16)].C0` | `17` | `12` |
| `C-table[periodicity(2)].C0` | `14` | `7` |
| `C-table[periodicity(32)].C0` | `5` | `6` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `302` | `1413` |
| `C-table[periodicity(8)].C2` | `50` | `40` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `24.0` | `30.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `6.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `4.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `21.0` | `34.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `7.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `8.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `11.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `17.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `14.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.numRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `10.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `24.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `76.0` | `43.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `21.0` | `70.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `21.0` | `30.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `302.0` | `1413.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `50.0` | `40.0` |

**a-t10-r2 vs b-t2-r1 -- RNG-dependent differences (52; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r2__vs__b-t2-r1.diff.txt`

| field | a-t10-r2 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `24` | `61` |
| `C-table[compression].C2` | `10` | `29` |
| `C-table[covariance(1)].C2` | `11` | `13` |
| `C-table[covariance(16)].C2` | `24` | `9` |
| `C-table[covariance(2)].C2` | `76` | `104` |
| `C-table[covariance(32)].C2` | `6` | `9` |
| `C-table[covariance(8)].C0` | `6` | `8` |
| `C-table[covariance(8)].C2` | `8` | `6` |
| `C-table[excursion].C2` | `11` | `10` |
| `C-table[lenDirectionalRuns].C0` | `4` | `2` |
| `C-table[lenRunsMedian].C0` | `21` | `28` |
| `C-table[maxCollision].C0` | `7` | `11` |
| `C-table[maxCollision].C1` | `1` | `2` |
| `C-table[maxCollision].C2` | `5` | `4` |
| `C-table[numDirectionalRuns].C2` | `21` | `118` |
| `C-table[numIncreasesDecreases].C0` | `8` | `6` |
| `C-table[numIncreasesDecreases].C2` | `6` | `8` |
| `C-table[periodicity(1)].C2` | `21` | `32` |
| `C-table[periodicity(16)].C0` | `17` | `20` |
| `C-table[periodicity(2)].C0` | `14` | `6` |
| `C-table[periodicity(32)].C0` | `5` | `6` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `302` | `427` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `C-table[periodicity(8)].C2` | `50` | `31` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `24.0` | `61.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `21.0` | `28.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `7.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `17.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `14.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `10.0` | `29.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `11.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `24.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `76.0` | `104.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `21.0` | `118.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `21.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `302.0` | `427.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `50.0` | `31.0` |

**a-t10-r2 vs b-t10-r1 -- RNG-dependent differences (52; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r2__vs__b-t10-r1.diff.txt`

| field | a-t10-r2 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `24` | `39` |
| `C-table[compression].C2` | `10` | `19` |
| `C-table[covariance(16)].C2` | `24` | `18` |
| `C-table[covariance(2)].C2` | `76` | `46` |
| `C-table[covariance(32)].C2` | `6` | `8` |
| `C-table[covariance(8)].C0` | `6` | `11` |
| `C-table[covariance(8)].C2` | `8` | `6` |
| `C-table[excursion].C0` | `6` | `8` |
| `C-table[excursion].C2` | `11` | `6` |
| `C-table[lenDirectionalRuns].C0` | `4` | `5` |
| `C-table[maxCollision].C0` | `7` | `22` |
| `C-table[maxCollision].C1` | `1` | `3` |
| `C-table[maxCollision].C2` | `5` | `3` |
| `C-table[numDirectionalRuns].C2` | `21` | `59` |
| `C-table[numIncreasesDecreases].C0` | `8` | `17` |
| `C-table[numRunsMedian].C0` | `11` | `6` |
| `C-table[periodicity(1)].C2` | `21` | `16` |
| `C-table[periodicity(16)].C0` | `17` | `6` |
| `C-table[periodicity(16)].C2` | `6` | `12` |
| `C-table[periodicity(2)].C0` | `14` | `23` |
| `C-table[periodicity(32)].C0` | `5` | `6` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `302` | `371` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `C-table[periodicity(8)].C2` | `50` | `70` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `24.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `7.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `8.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `17.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `14.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `1.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `10.0` | `19.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `24.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `76.0` | `46.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `5.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `21.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `21.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `302.0` | `371.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `50.0` | `70.0` |

**a-t10-r2 vs b-t10-r2 -- RNG-dependent differences (48; expected under a live seed):** full list in `iid/truerand_8bit/a-t10-r2__vs__b-t10-r2.diff.txt`

| field | a-t10-r2 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `24` | `37` |
| `C-table[compression].C2` | `10` | `32` |
| `C-table[covariance(1)].C2` | `11` | `8` |
| `C-table[covariance(16)].C0` | `6` | `7` |
| `C-table[covariance(16)].C2` | `24` | `6` |
| `C-table[covariance(2)].C2` | `76` | `91` |
| `C-table[covariance(32)].C2` | `6` | `18` |
| `C-table[covariance(8)].C0` | `6` | `8` |
| `C-table[covariance(8)].C2` | `8` | `6` |
| `C-table[excursion].C2` | `11` | `8` |
| `C-table[lenDirectionalRuns].C0` | `4` | `1` |
| `C-table[lenRunsMedian].C0` | `21` | `25` |
| `C-table[lenRunsMedian].C1` | `5` | `6` |
| `C-table[lenRunsMedian].C2` | `1` | `0` |
| `C-table[maxCollision].C0` | `7` | `10` |
| `C-table[numDirectionalRuns].C2` | `21` | `67` |
| `C-table[numRunsMedian].C0` | `11` | `6` |
| `C-table[periodicity(1)].C2` | `21` | `51` |
| `C-table[periodicity(16)].C0` | `17` | `9` |
| `C-table[periodicity(2)].C0` | `14` | `20` |
| `C-table[periodicity(32)].C0` | `5` | `6` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `302` | `511` |
| `C-table[periodicity(8)].C2` | `50` | `43` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `24.0` | `37.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `4.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `21.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `7.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `17.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `14.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `10.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `24.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `76.0` | `91.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `6.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `21.0` | `67.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `21.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `302.0` | `511.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `50.0` | `43.0` |

**b-t1-r1 vs b-t2-r1 -- RNG-dependent differences (50; expected under a live seed):** full list in `iid/truerand_8bit/b-t1-r1__vs__b-t2-r1.diff.txt`

| field | b-t1-r1 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `30` | `61` |
| `C-table[compression].C2` | `39` | `29` |
| `C-table[covariance(1)].C2` | `11` | `13` |
| `C-table[covariance(16)].C0` | `9` | `6` |
| `C-table[covariance(16)].C2` | `6` | `9` |
| `C-table[covariance(2)].C2` | `43` | `104` |
| `C-table[covariance(32)].C2` | `10` | `9` |
| `C-table[covariance(8)].C0` | `18` | `8` |
| `C-table[excursion].C2` | `13` | `10` |
| `C-table[lenDirectionalRuns].C0` | `6` | `2` |
| `C-table[lenRunsMedian].C0` | `34` | `28` |
| `C-table[lenRunsMedian].C1` | `6` | `5` |
| `C-table[lenRunsMedian].C2` | `0` | `1` |
| `C-table[numDirectionalRuns].C2` | `70` | `118` |
| `C-table[numIncreasesDecreases].C0` | `7` | `6` |
| `C-table[numIncreasesDecreases].C2` | `6` | `8` |
| `C-table[numRunsMedian].C0` | `5` | `11` |
| `C-table[numRunsMedian].C1` | `1` | `0` |
| `C-table[periodicity(1)].C2` | `30` | `32` |
| `C-table[periodicity(16)].C0` | `12` | `20` |
| `C-table[periodicity(2)].C0` | `7` | `6` |
| `C-table[periodicity(32)].C2` | `1413` | `427` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `C-table[periodicity(8)].C2` | `40` | `31` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `30.0` | `61.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `18.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `6.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `34.0` | `28.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `7.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `5.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `12.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `7.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.numRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `39.0` | `29.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `11.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `43.0` | `104.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `10.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `13.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `70.0` | `118.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `30.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1413.0` | `427.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `40.0` | `31.0` |

**b-t1-r1 vs b-t10-r1 -- RNG-dependent differences (56; expected under a live seed):** full list in `iid/truerand_8bit/b-t1-r1__vs__b-t10-r1.diff.txt`

| field | b-t1-r1 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `30` | `39` |
| `C-table[compression].C2` | `39` | `19` |
| `C-table[covariance(16)].C0` | `9` | `6` |
| `C-table[covariance(16)].C2` | `6` | `18` |
| `C-table[covariance(2)].C2` | `43` | `46` |
| `C-table[covariance(32)].C2` | `10` | `8` |
| `C-table[covariance(8)].C0` | `18` | `11` |
| `C-table[excursion].C0` | `6` | `8` |
| `C-table[excursion].C2` | `13` | `6` |
| `C-table[lenDirectionalRuns].C0` | `6` | `5` |
| `C-table[lenRunsMedian].C0` | `34` | `21` |
| `C-table[lenRunsMedian].C1` | `6` | `5` |
| `C-table[lenRunsMedian].C2` | `0` | `1` |
| `C-table[maxCollision].C0` | `11` | `22` |
| `C-table[maxCollision].C1` | `2` | `3` |
| `C-table[maxCollision].C2` | `4` | `3` |
| `C-table[numDirectionalRuns].C2` | `70` | `59` |
| `C-table[numIncreasesDecreases].C0` | `7` | `17` |
| `C-table[numRunsMedian].C0` | `5` | `6` |
| `C-table[numRunsMedian].C1` | `1` | `0` |
| `C-table[periodicity(1)].C2` | `30` | `16` |
| `C-table[periodicity(16)].C0` | `12` | `6` |
| `C-table[periodicity(16)].C2` | `6` | `12` |
| `C-table[periodicity(2)].C0` | `7` | `23` |
| `C-table[periodicity(32)].C2` | `1413` | `371` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `C-table[periodicity(8)].C2` | `40` | `70` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `30.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `18.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `34.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `11.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `7.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `12.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `7.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.numRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `39.0` | `19.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `6.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `43.0` | `46.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `10.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `13.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `70.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `30.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1413.0` | `371.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `40.0` | `70.0` |

**b-t1-r1 vs b-t10-r2 -- RNG-dependent differences (44; expected under a live seed):** full list in `iid/truerand_8bit/b-t1-r1__vs__b-t10-r2.diff.txt`

| field | b-t1-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `30` | `37` |
| `C-table[compression].C2` | `39` | `32` |
| `C-table[covariance(1)].C2` | `11` | `8` |
| `C-table[covariance(16)].C0` | `9` | `7` |
| `C-table[covariance(2)].C2` | `43` | `91` |
| `C-table[covariance(32)].C2` | `10` | `18` |
| `C-table[covariance(8)].C0` | `18` | `8` |
| `C-table[excursion].C2` | `13` | `8` |
| `C-table[lenDirectionalRuns].C0` | `6` | `1` |
| `C-table[lenRunsMedian].C0` | `34` | `25` |
| `C-table[maxCollision].C0` | `11` | `10` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `70` | `67` |
| `C-table[numIncreasesDecreases].C0` | `7` | `8` |
| `C-table[numRunsMedian].C0` | `5` | `6` |
| `C-table[numRunsMedian].C1` | `1` | `0` |
| `C-table[periodicity(1)].C2` | `30` | `51` |
| `C-table[periodicity(16)].C0` | `12` | `9` |
| `C-table[periodicity(2)].C0` | `7` | `20` |
| `C-table[periodicity(32)].C2` | `1413` | `511` |
| `C-table[periodicity(8)].C2` | `40` | `43` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `30.0` | `37.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `9.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `18.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `6.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `34.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `11.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `7.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `12.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `7.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `39.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `43.0` | `91.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `10.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `13.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `70.0` | `67.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `30.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `1413.0` | `511.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `40.0` | `43.0` |

**b-t2-r1 vs b-t10-r1 -- RNG-dependent differences (48; expected under a live seed):** full list in `iid/truerand_8bit/b-t2-r1__vs__b-t10-r1.diff.txt`

| field | b-t2-r1 | b-t10-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `61` | `39` |
| `C-table[compression].C2` | `29` | `19` |
| `C-table[covariance(1)].C2` | `13` | `11` |
| `C-table[covariance(16)].C2` | `9` | `18` |
| `C-table[covariance(2)].C2` | `104` | `46` |
| `C-table[covariance(32)].C2` | `9` | `8` |
| `C-table[covariance(8)].C0` | `8` | `11` |
| `C-table[excursion].C0` | `6` | `8` |
| `C-table[excursion].C2` | `10` | `6` |
| `C-table[lenDirectionalRuns].C0` | `2` | `5` |
| `C-table[lenRunsMedian].C0` | `28` | `21` |
| `C-table[maxCollision].C0` | `11` | `22` |
| `C-table[maxCollision].C1` | `2` | `3` |
| `C-table[maxCollision].C2` | `4` | `3` |
| `C-table[numDirectionalRuns].C2` | `118` | `59` |
| `C-table[numIncreasesDecreases].C0` | `6` | `17` |
| `C-table[numIncreasesDecreases].C2` | `8` | `6` |
| `C-table[numRunsMedian].C0` | `11` | `6` |
| `C-table[periodicity(1)].C2` | `32` | `16` |
| `C-table[periodicity(16)].C0` | `20` | `6` |
| `C-table[periodicity(16)].C2` | `6` | `12` |
| `C-table[periodicity(2)].C0` | `6` | `23` |
| `C-table[periodicity(32)].C2` | `427` | `371` |
| `C-table[periodicity(8)].C2` | `31` | `70` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `61.0` | `39.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `8.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `28.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `11.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `20.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `6.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `29.0` | `19.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `13.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `9.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `104.0` | `46.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `9.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `10.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `118.0` | `59.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `32.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `427.0` | `371.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `31.0` | `70.0` |

**b-t2-r1 vs b-t10-r2 -- RNG-dependent differences (52; expected under a live seed):** full list in `iid/truerand_8bit/b-t2-r1__vs__b-t10-r2.diff.txt`

| field | b-t2-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `61` | `37` |
| `C-table[compression].C2` | `29` | `32` |
| `C-table[covariance(1)].C2` | `13` | `8` |
| `C-table[covariance(16)].C0` | `6` | `7` |
| `C-table[covariance(16)].C2` | `9` | `6` |
| `C-table[covariance(2)].C2` | `104` | `91` |
| `C-table[covariance(32)].C2` | `9` | `18` |
| `C-table[excursion].C2` | `10` | `8` |
| `C-table[lenDirectionalRuns].C0` | `2` | `1` |
| `C-table[lenRunsMedian].C0` | `28` | `25` |
| `C-table[lenRunsMedian].C1` | `5` | `6` |
| `C-table[lenRunsMedian].C2` | `1` | `0` |
| `C-table[maxCollision].C0` | `11` | `10` |
| `C-table[maxCollision].C1` | `2` | `1` |
| `C-table[maxCollision].C2` | `4` | `5` |
| `C-table[numDirectionalRuns].C2` | `118` | `67` |
| `C-table[numIncreasesDecreases].C0` | `6` | `8` |
| `C-table[numIncreasesDecreases].C2` | `8` | `6` |
| `C-table[numRunsMedian].C0` | `11` | `6` |
| `C-table[periodicity(1)].C2` | `32` | `51` |
| `C-table[periodicity(16)].C0` | `20` | `9` |
| `C-table[periodicity(2)].C0` | `6` | `20` |
| `C-table[periodicity(32)].C2` | `427` | `511` |
| `C-table[periodicity(8)].C0` | `5` | `6` |
| `C-table[periodicity(8)].C1` | `1` | `0` |
| `C-table[periodicity(8)].C2` | `31` | `43` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `61.0` | `37.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `28.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `11.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `11.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `20.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `6.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `29.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `13.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `104.0` | `91.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `9.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `10.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `4.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `118.0` | `67.0` |
| `json.testCases[].permutationTestResults[input].C2.numIncreasesDecreases` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `32.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `427.0` | `511.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `31.0` | `43.0` |

**b-t10-r1 vs b-t10-r2 -- RNG-dependent differences (54; expected under a live seed):** full list in `iid/truerand_8bit/b-t10-r1__vs__b-t10-r2.diff.txt`

| field | b-t10-r1 | b-t10-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `39` | `37` |
| `C-table[compression].C2` | `19` | `32` |
| `C-table[covariance(1)].C2` | `11` | `8` |
| `C-table[covariance(16)].C0` | `6` | `7` |
| `C-table[covariance(16)].C2` | `18` | `6` |
| `C-table[covariance(2)].C2` | `46` | `91` |
| `C-table[covariance(32)].C2` | `8` | `18` |
| `C-table[covariance(8)].C0` | `11` | `8` |
| `C-table[excursion].C0` | `8` | `6` |
| `C-table[excursion].C2` | `6` | `8` |
| `C-table[lenDirectionalRuns].C0` | `5` | `1` |
| `C-table[lenRunsMedian].C0` | `21` | `25` |
| `C-table[lenRunsMedian].C1` | `5` | `6` |
| `C-table[lenRunsMedian].C2` | `1` | `0` |
| `C-table[maxCollision].C0` | `22` | `10` |
| `C-table[maxCollision].C1` | `3` | `1` |
| `C-table[maxCollision].C2` | `3` | `5` |
| `C-table[numDirectionalRuns].C2` | `59` | `67` |
| `C-table[numIncreasesDecreases].C0` | `17` | `8` |
| `C-table[periodicity(1)].C2` | `16` | `51` |
| `C-table[periodicity(16)].C0` | `6` | `9` |
| `C-table[periodicity(16)].C2` | `12` | `6` |
| `C-table[periodicity(2)].C0` | `23` | `20` |
| `C-table[periodicity(32)].C2` | `371` | `511` |
| `C-table[periodicity(8)].C0` | `5` | `6` |
| `C-table[periodicity(8)].C1` | `1` | `0` |
| `C-table[periodicity(8)].C2` | `70` | `43` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `39.0` | `37.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `8.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `5.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `21.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `22.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `17.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `23.0` | `20.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `3.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `19.0` | `32.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance1` | `11.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `18.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance2` | `46.0` | `91.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `8.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `6.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.maxCollision` | `3.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `59.0` | `67.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `16.0` | `51.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `12.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `371.0` | `511.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity8` | `70.0` | `43.0` |

**Verdict and seed-source table (arm a = default `/dev/urandom`, arm b = `EA_TEST_RANDOM_SOURCE` set):**

| run | arm | threads | random source env | rc | chi-square | LRS | permutation | JSON IID | errorLevel | Assessed min entropy | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-t10-r1 | a | 10 | /dev/urandom (default) | 0 | Passed | Passed | Passed | True | 0 | 7.8651180028995897 | 13 |
| a-t10-r2 | a | 10 | /dev/urandom (default) | 0 | Passed | Passed | Passed | True | 0 | 7.8651180028995897 | 4 |
| b-t1-r1 | b | 1 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 7.8651180028995897 | 18 |
| b-t2-r1 | b | 2 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 7.8651180028995897 | 9 |
| b-t10-r1 | b | 10 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 7.8651180028995897 | 6 |
| b-t10-r2 | b | 10 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 7.8651180028995897 | 8 |

Counters C0/C1/C2 per statistic and run (`-` = not printed; a row identical across every run under a live seed would be surprising):

| statistic | a-t10-r1 | a-t10-r2 | b-t1-r1 | b-t2-r1 | b-t10-r1 | b-t10-r2 | identical across runs |
|---|---|---|---|---|---|---|---|
| avgCollision | 46/0/6 | 24/0/6 | 30/0/6 | 61/0/6 | 39/0/6 | 37/0/6 | no |
| compression | 5/1/38 | 6/0/10 | 6/0/39 | 6/0/29 | 6/0/19 | 6/0/32 | no |
| covariance(1) | 6/0/15 | 6/0/11 | 6/0/11 | 6/0/13 | 6/0/11 | 6/0/8 | no |
| covariance(16) | 6/0/6 | 6/0/24 | 9/0/6 | 6/0/9 | 6/0/18 | 7/0/6 | no |
| covariance(2) | 6/0/55 | 6/0/76 | 6/0/43 | 6/0/104 | 6/0/46 | 6/0/91 | no |
| covariance(32) | 6/0/6 | 6/0/6 | 6/0/10 | 6/0/9 | 6/0/8 | 6/0/18 | no |
| covariance(8) | 8/0/6 | 6/0/8 | 18/0/6 | 8/0/6 | 11/0/6 | 8/0/6 | no |
| excursion | 6/0/11 | 6/0/11 | 6/0/13 | 6/0/10 | 8/0/6 | 6/0/8 | no |
| lenDirectionalRuns | 3/6/0 | 4/6/0 | 6/6/0 | 2/6/0 | 5/6/0 | 1/6/0 | no |
| lenRunsMedian | 23/6/0 | 21/5/1 | 34/6/0 | 28/5/1 | 21/5/1 | 25/6/0 | no |
| maxCollision | 8/2/4 | 7/1/5 | 11/2/4 | 11/2/4 | 22/3/3 | 10/1/5 | no |
| numDirectionalRuns | 6/0/78 | 6/0/21 | 6/0/70 | 6/0/118 | 6/0/59 | 6/0/67 | no |
| numIncreasesDecreases | 6/0/6 | 8/0/6 | 7/0/6 | 6/0/8 | 17/0/6 | 8/0/6 | no |
| numRunsMedian | 6/0/6 | 11/0/6 | 5/1/6 | 11/0/6 | 6/0/6 | 6/0/6 | no |
| periodicity(1) | 6/0/44 | 6/0/21 | 6/0/30 | 6/0/32 | 6/0/16 | 6/0/51 | no |
| periodicity(16) | 8/0/6 | 17/0/6 | 12/0/6 | 20/0/6 | 6/0/12 | 9/0/6 | no |
| periodicity(2) | 11/0/6 | 14/0/6 | 7/0/6 | 6/0/6 | 23/0/6 | 20/0/6 | no |
| periodicity(32) | 6/0/1305 | 5/1/302 | 6/0/1413 | 6/0/427 | 6/0/371 | 6/0/511 | no |
| periodicity(8) | 6/0/30 | 6/0/50 | 6/0/40 | 5/1/31 | 5/1/70 | 6/0/43 | no |

Arm (b) under `EA_TEST_RANDOM_SOURCE`: two runs at the same thread count agree on the JSON? threads=10: DIFFER (2 runs). Prediction from the source was DIFFER (the variable does not reach `seed()`); if they AGREE, the source reading above is wrong and must be re-read.

Reading: every RNG-independent field is identical in all pairs; only the permutation counters/verdict path varies, which the live seed explains. NOT a finding.

## non_iid / biased-random-bits -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 1 | 1ad1568c083b2774 | 481cdac6e2d65d45 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | 481cdac6e2d65d45 | 0 |
| t10-r1 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | 481cdac6e2d65d45 | 0 |
| t10-r2 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | 481cdac6e2d65d45 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / biased-random-bytes -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 6 | 1ad1568c083b2774 | 146bd7497d8e2d61 | 0 |
| t2-r1 | - | 2 | 0 | yes | 5 | 1ad1568c083b2774 | 146bd7497d8e2d61 | 0 |
| t10-r1 | - | 10 | 0 | yes | 6 | 1ad1568c083b2774 | 146bd7497d8e2d61 | 0 |
| t10-r2 | - | 10 | 0 | yes | 6 | 1ad1568c083b2774 | 146bd7497d8e2d61 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / csprng-1bit-1000000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 0 | 1ad1568c083b2774 | f5a2bbe8db53c7c8 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | f5a2bbe8db53c7c8 | 0 |
| t10-r1 | - | 10 | 0 | yes | 1 | 1ad1568c083b2774 | f5a2bbe8db53c7c8 | 0 |
| t10-r2 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | f5a2bbe8db53c7c8 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / csprng-8bit-1000000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 5 | 1ad1568c083b2774 | c98c420474bd9a41 | 0 |
| t2-r1 | - | 2 | 0 | yes | 5 | 1ad1568c083b2774 | c98c420474bd9a41 | 0 |
| t10-r1 | - | 10 | 0 | yes | 5 | 1ad1568c083b2774 | c98c420474bd9a41 | 0 |
| t10-r2 | - | 10 | 0 | yes | 5 | 1ad1568c083b2774 | c98c420474bd9a41 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / data.pi -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 0 | 1ad1568c083b2774 | d9a7de4e1f170f36 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | d9a7de4e1f170f36 | 0 |
| t10-r1 | - | 10 | 0 | yes | 1 | 1ad1568c083b2774 | d9a7de4e1f170f36 | 0 |
| t10-r2 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | d9a7de4e1f170f36 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / normal -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 5 | 1ad1568c083b2774 | a70ce92a71b9b0c6 | 0 |
| t2-r1 | - | 2 | 0 | yes | 5 | 1ad1568c083b2774 | a70ce92a71b9b0c6 | 0 |
| t10-r1 | - | 10 | 0 | yes | 5 | 1ad1568c083b2774 | a70ce92a71b9b0c6 | 0 |
| t10-r2 | - | 10 | 0 | yes | 4 | 1ad1568c083b2774 | a70ce92a71b9b0c6 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / period255-8bit-1000000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 3 | 1ad1568c083b2774 | c596f5438f65a471 | 0 |
| t2-r1 | - | 2 | 0 | yes | 2 | 1ad1568c083b2774 | c596f5438f65a471 | 0 |
| t10-r1 | - | 10 | 0 | yes | 3 | 1ad1568c083b2774 | c596f5438f65a471 | 0 |
| t10-r2 | - | 10 | 0 | yes | 3 | 1ad1568c083b2774 | c596f5438f65a471 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / rand1_short -- INCOMPLETE

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 3814404497a3b912 | 0 |
| t2-r1 | - | 2 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 3814404497a3b912 | 0 |
| t10-r1 | - | 10 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 3814404497a3b912 | 0 |
| t10-r2 | - | 10 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 3814404497a3b912 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t1-r1 vs t10-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t1-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |
| t2-r1 vs t10-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t2-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |
| t10-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |

Reading: at least one run is malformed -- see the well-formed column; nothing about determinism follows from this case until it is re-run.

## non_iid / rand4_short -- INCOMPLETE

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | a9e2169cb1accc78 | 0 |
| t2-r1 | - | 2 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | a9e2169cb1accc78 | 0 |
| t10-r1 | - | 10 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | a9e2169cb1accc78 | 0 |
| t10-r2 | - | 10 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | a9e2169cb1accc78 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t1-r1 vs t10-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t1-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |
| t2-r1 vs t10-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t2-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |
| t10-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |

Reading: at least one run is malformed -- see the well-formed column; nothing about determinism follows from this case until it is re-run.

## non_iid / rand8_short -- INCOMPLETE

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 17d2eaf9544cd6ae | 0 |
| t2-r1 | - | 2 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 17d2eaf9544cd6ae | 0 |
| t10-r1 | - | 10 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 17d2eaf9544cd6ae | 0 |
| t10-r2 | - | 10 | 255 | NO: rc 255 (expected 0); final marker 'Assessed min entropy:' absent from stdout; errorLevel -1 (expected 0) | 0 | 1ad1568c083b2774 | 17d2eaf9544cd6ae | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t1-r1 vs t10-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t1-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |
| t2-r1 vs t10-r1 | - | - | - | - | NOT A RESULT: a run is malformed |
| t2-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |
| t10-r1 vs t10-r2 | - | - | - | - | NOT A RESULT: a run is malformed |

Reading: at least one run is malformed -- see the well-formed column; nothing about determinism follows from this case until it is re-run.

## non_iid / ringOsc-nist -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 1 | 1ad1568c083b2774 | 7d37dc3795e9b292 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | 7d37dc3795e9b292 | 0 |
| t10-r1 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | 7d37dc3795e9b292 | 0 |
| t10-r2 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | 7d37dc3795e9b292 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / truerand_1bit -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 1 | 1ad1568c083b2774 | f9ea8832af4c4205 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | f9ea8832af4c4205 | 0 |
| t10-r1 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | f9ea8832af4c4205 | 0 |
| t10-r2 | - | 10 | 0 | yes | 1 | 1ad1568c083b2774 | f9ea8832af4c4205 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / truerand_4bit -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 4 | 1ad1568c083b2774 | 489bc841bb364ba8 | 0 |
| t2-r1 | - | 2 | 0 | yes | 4 | 1ad1568c083b2774 | 489bc841bb364ba8 | 0 |
| t10-r1 | - | 10 | 0 | yes | 4 | 1ad1568c083b2774 | 489bc841bb364ba8 | 0 |
| t10-r2 | - | 10 | 0 | yes | 5 | 1ad1568c083b2774 | 489bc841bb364ba8 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / truerand_8bit -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 5 | 1ad1568c083b2774 | c7e56911d2657fa9 | 0 |
| t2-r1 | - | 2 | 0 | yes | 6 | 1ad1568c083b2774 | c7e56911d2657fa9 | 0 |
| t10-r1 | - | 10 | 0 | yes | 5 | 1ad1568c083b2774 | c7e56911d2657fa9 | 0 |
| t10-r2 | - | 10 | 0 | yes | 5 | 1ad1568c083b2774 | c7e56911d2657fa9 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / two9010-8bit-1000000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 0 | 1ad1568c083b2774 | d6f58132e5804e02 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | d6f58132e5804e02 | 0 |
| t10-r1 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | d6f58132e5804e02 | 0 |
| t10-r2 | - | 10 | 0 | yes | 0 | 1ad1568c083b2774 | d6f58132e5804e02 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## restart / restart-csprng-1bit-1000x1000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 0 | 4d7ba82b43ce03d0 | e9936cbf43ea7d4c | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 4d7ba82b43ce03d0 | e9936cbf43ea7d4c | 0 |
| t10-r1 | - | 10 | 0 | yes | 1 | 4d7ba82b43ce03d0 | e9936cbf43ea7d4c | 0 |
| t10-r2 | - | 10 | 0 | yes | 1 | 4d7ba82b43ce03d0 | e9936cbf43ea7d4c | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## restart / restart-csprng-8bit-1000x1000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 15 | 4d7ba82b43ce03d0 | 47311ae5a2277489 | 0 |
| t2-r1 | - | 2 | 0 | yes | 8 | 4d7ba82b43ce03d0 | 47311ae5a2277489 | 0 |
| t10-r1 | - | 10 | 0 | yes | 8 | 4d7ba82b43ce03d0 | 47311ae5a2277489 | 0 |
| t10-r2 | - | 10 | 0 | yes | 10 | 4d7ba82b43ce03d0 | 47311ae5a2277489 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r1 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |
| t10-r1 vs t10-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

