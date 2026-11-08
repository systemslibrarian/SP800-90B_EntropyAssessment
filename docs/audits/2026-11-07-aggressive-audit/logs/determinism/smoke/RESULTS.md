# Determinism and thread-count phase -- RESULTS (SMOKE: plumbing check on 20,000-sample inputs, non-compliant, <= 2 threads)

Written 2026-11-07T21:52:31-05:00 by harness/determinism/compare_runs.py from `/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke`.

## Binaries measured (instrument rule 4) and host

```
1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (153368 bytes, mtime 2026-11-07T19:28:57)
22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (193656 bytes, mtime 2026-11-07T19:28:52)
4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (230904 bytes, mtime 2026-11-07T19:29:04)
```
```
date=2026-11-07T21:52:20-0500
mode=smoke
threads=1 2
uname_a=Darwin MacBook-Air.local 25.6.0 Darwin Kernel Version 25.6.0: Fri Jul 31 19:16:20 PDT 2026; root:xnu-12377.161.14~5/RELEASE_ARM64_T8142 arm64 arm Darwin
uname_s=Darwin
uname_m=arm64
compiler=Apple clang version 21.0.0 (clang-2100.4.1.1)
hw.ncpu=10
hw.memsize=17179869184
cpu=Apple M5
sw_vers=ProductName:		macOS ProductVersion:		26.6.2 BuildVersion:		25G83 
git_head=1151b2224594acec4267c4f17deabdf53e206721
git_branch=audit/2026-11-07
git_dirty=1184 paths modified or untracked
omp_runtime=	/opt/homebrew/opt/libomp/lib/libomp.dylib
python=Python 3.14.7
```

## Summary

| tool | case | class | runs | identical pairs |
|---|---|---|---|---|
| iid | smoke-csprng-1bit-20000 | DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary | 5 | 0 |
| iid | smoke-csprng-8bit-20000 | DETERMINISTIC (RNG-independent fields) | 5 | 10 |
| non_iid | smoke-csprng-1bit-20000 | DETERMINISTIC | 3 | 3 |
| non_iid | smoke-csprng-8bit-20000 | DETERMINISTIC | 3 | 3 |

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

## iid / smoke-csprng-1bit-20000 -- DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| a-t2-r1 | a | 2 | 0 | yes | 0 | 22f1319ae347ab4e | 17917b5af1e8d08d | 0 |
| a-t2-r2 | a | 2 | 0 | yes | 1 | 22f1319ae347ab4e | 17917b5af1e8d08d | 0 |
| b-t1-r1 | b | 1 | 0 | yes | 0 | 22f1319ae347ab4e | 17917b5af1e8d08d | 0 |
| b-t2-r1 | b | 2 | 0 | yes | 0 | 22f1319ae347ab4e | 17917b5af1e8d08d | 0 |
| b-t2-r2 | b | 2 | 0 | yes | 0 | 22f1319ae347ab4e | 17917b5af1e8d08d | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| a-t2-r1 vs a-t2-r2 | DIFF | DIFF | = | = | 58 (58 / 0) |
| a-t2-r1 vs b-t1-r1 | DIFF | DIFF | = | = | 70 (70 / 0) |
| a-t2-r1 vs b-t2-r1 | DIFF | DIFF | = | = | 66 (66 / 0) |
| a-t2-r1 vs b-t2-r2 | DIFF | DIFF | = | = | 46 (46 / 0) |
| a-t2-r2 vs b-t1-r1 | DIFF | DIFF | = | = | 66 (66 / 0) |
| a-t2-r2 vs b-t2-r1 | DIFF | DIFF | = | = | 72 (72 / 0) |
| a-t2-r2 vs b-t2-r2 | DIFF | DIFF | = | = | 64 (64 / 0) |
| b-t1-r1 vs b-t2-r1 | DIFF | DIFF | = | = | 74 (74 / 0) |
| b-t1-r1 vs b-t2-r2 | DIFF | DIFF | = | = | 70 (70 / 0) |
| b-t2-r1 vs b-t2-r2 | DIFF | DIFF | = | = | 76 (76 / 0) |

**a-t2-r1 vs a-t2-r2 -- RNG-dependent differences (58; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r1__vs__a-t2-r2.diff.txt`

| field | a-t2-r1 | a-t2-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `25` | `33` |
| `C-table[compression].C0` | `13` | `16` |
| `C-table[compression].C1` | `0` | `1` |
| `C-table[compression].C2` | `6` | `5` |
| `C-table[covariance(1)].C0` | `7` | `9` |
| `C-table[covariance(16)].C2` | `212` | `293` |
| `C-table[covariance(2)].C0` | `18` | `8` |
| `C-table[covariance(32)].C0` | `6` | `5` |
| `C-table[covariance(32)].C1` | `0` | `1` |
| `C-table[covariance(32)].C2` | `57` | `126` |
| `C-table[covariance(8)].C0` | `14` | `6` |
| `C-table[excursion].C0` | `12` | `10` |
| `C-table[lenDirectionalRuns].C2` | `60` | `79` |
| `C-table[lenRunsMedian].C0` | `8` | `2` |
| `C-table[lenRunsMedian].C1` | `3` | `4` |
| `C-table[maxCollision].C0` | `10` | `15` |
| `C-table[numDirectionalRuns].C0` | `33` | `19` |
| `C-table[numDirectionalRuns].C1` | `1` | `0` |
| `C-table[numDirectionalRuns].C2` | `5` | `6` |
| `C-table[numIncreasesDecreases].C0` | `30` | `28` |
| `C-table[numRunsMedian].C2` | `9` | `6` |
| `C-table[periodicity(1)].C0` | `29` | `68` |
| `C-table[periodicity(1)].C1` | `1` | `0` |
| `C-table[periodicity(1)].C2` | `5` | `6` |
| `C-table[periodicity(16)].C2` | `56` | `33` |
| `C-table[periodicity(32)].C0` | `12` | `17` |
| `C-table[periodicity(32)].C1` | `0` | `1` |
| `C-table[periodicity(32)].C2` | `6` | `5` |
| `C-table[periodicity(8)].C0` | `6` | `11` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `25.0` | `33.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `13.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `7.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `18.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `14.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `12.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `8.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `10.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `33.0` | `19.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `30.0` | `28.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `29.0` | `68.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `12.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `3.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.numDirectionalRuns` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `212.0` | `293.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `57.0` | `126.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `60.0` | `79.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.numRunsMedian` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity1` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `56.0` | `33.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity32` | `6.0` | `5.0` |

**a-t2-r1 vs b-t1-r1 -- RNG-dependent differences (70; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r1__vs__b-t1-r1.diff.txt`

| field | a-t2-r1 | b-t1-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `25` | `15` |
| `C-table[compression].C0` | `13` | `5` |
| `C-table[compression].C1` | `0` | `1` |
| `C-table[compression].C2` | `6` | `5` |
| `C-table[covariance(1)].C0` | `7` | `12` |
| `C-table[covariance(16)].C2` | `212` | `225` |
| `C-table[covariance(2)].C0` | `18` | `28` |
| `C-table[covariance(32)].C2` | `57` | `130` |
| `C-table[covariance(8)].C0` | `14` | `23` |
| `C-table[excursion].C0` | `12` | `6` |
| `C-table[excursion].C2` | `6` | `7` |
| `C-table[lenDirectionalRuns].C0` | `1` | `2` |
| `C-table[lenDirectionalRuns].C1` | `5` | `4` |
| `C-table[lenDirectionalRuns].C2` | `60` | `81` |
| `C-table[lenRunsMedian].C0` | `8` | `5` |
| `C-table[maxCollision].C0` | `10` | `8` |
| `C-table[maxCollision].C1` | `0` | `1` |
| `C-table[maxCollision].C2` | `6` | `5` |
| `C-table[numDirectionalRuns].C0` | `33` | `17` |
| `C-table[numDirectionalRuns].C1` | `1` | `0` |
| `C-table[numDirectionalRuns].C2` | `5` | `6` |
| `C-table[numIncreasesDecreases].C0` | `30` | `13` |
| `C-table[numIncreasesDecreases].C1` | `0` | `1` |
| `C-table[numIncreasesDecreases].C2` | `6` | `5` |
| `C-table[periodicity(1)].C0` | `29` | `30` |
| `C-table[periodicity(1)].C1` | `1` | `2` |
| `C-table[periodicity(1)].C2` | `5` | `4` |
| `C-table[periodicity(16)].C0` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `56` | `23` |
| `C-table[periodicity(2)].C0` | `15` | `13` |
| `C-table[periodicity(32)].C0` | `12` | `22` |
| `C-table[periodicity(32)].C1` | `0` | `1` |
| `C-table[periodicity(32)].C2` | `6` | `5` |
| `C-table[periodicity(8)].C0` | `6` | `12` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `25.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `13.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `7.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `18.0` | `28.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `14.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `12.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `8.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `10.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `33.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `30.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `29.0` | `30.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `15.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `12.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numDirectionalRuns` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.numIncreasesDecreases` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `5.0` |
| ... 10 more | | |

**a-t2-r1 vs b-t2-r1 -- RNG-dependent differences (66; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r1__vs__b-t2-r1.diff.txt`

| field | a-t2-r1 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `25` | `21` |
| `C-table[compression].C0` | `13` | `4` |
| `C-table[compression].C1` | `0` | `2` |
| `C-table[compression].C2` | `6` | `4` |
| `C-table[covariance(1)].C0` | `7` | `10` |
| `C-table[covariance(16)].C2` | `212` | `303` |
| `C-table[covariance(2)].C0` | `18` | `10` |
| `C-table[covariance(32)].C2` | `57` | `77` |
| `C-table[covariance(8)].C0` | `14` | `15` |
| `C-table[excursion].C0` | `12` | `11` |
| `C-table[lenDirectionalRuns].C0` | `1` | `4` |
| `C-table[lenDirectionalRuns].C1` | `5` | `2` |
| `C-table[lenDirectionalRuns].C2` | `60` | `125` |
| `C-table[lenRunsMedian].C0` | `8` | `5` |
| `C-table[lenRunsMedian].C1` | `3` | `2` |
| `C-table[lenRunsMedian].C2` | `3` | `4` |
| `C-table[maxCollision].C0` | `10` | `9` |
| `C-table[maxCollision].C1` | `0` | `1` |
| `C-table[maxCollision].C2` | `6` | `5` |
| `C-table[numDirectionalRuns].C0` | `33` | `25` |
| `C-table[numIncreasesDecreases].C0` | `30` | `18` |
| `C-table[numIncreasesDecreases].C1` | `0` | `2` |
| `C-table[numIncreasesDecreases].C2` | `6` | `4` |
| `C-table[numRunsMedian].C0` | `6` | `7` |
| `C-table[numRunsMedian].C2` | `9` | `6` |
| `C-table[periodicity(1)].C0` | `29` | `53` |
| `C-table[periodicity(1)].C1` | `1` | `0` |
| `C-table[periodicity(1)].C2` | `5` | `6` |
| `C-table[periodicity(16)].C2` | `56` | `36` |
| `C-table[periodicity(2)].C0` | `15` | `44` |
| `C-table[periodicity(32)].C0` | `12` | `10` |
| `C-table[periodicity(8)].C0` | `6` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `25.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `13.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `7.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `18.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `14.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `12.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `1.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `8.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `10.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `33.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `30.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `29.0` | `53.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `15.0` | `44.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `12.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `5.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numIncreasesDecreases` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity8` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `212.0` | `303.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `57.0` | `77.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `60.0` | `125.0` |
| ... 6 more | | |

**a-t2-r1 vs b-t2-r2 -- RNG-dependent differences (46; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r1__vs__b-t2-r2.diff.txt`

| field | a-t2-r1 | b-t2-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `25` | `12` |
| `C-table[compression].C0` | `13` | `16` |
| `C-table[covariance(1)].C0` | `7` | `6` |
| `C-table[covariance(16)].C0` | `6` | `4` |
| `C-table[covariance(16)].C1` | `0` | `2` |
| `C-table[covariance(16)].C2` | `212` | `206` |
| `C-table[covariance(8)].C0` | `14` | `6` |
| `C-table[covariance(8)].C2` | `6` | `7` |
| `C-table[excursion].C0` | `12` | `15` |
| `C-table[lenDirectionalRuns].C0` | `1` | `2` |
| `C-table[lenDirectionalRuns].C1` | `5` | `4` |
| `C-table[lenDirectionalRuns].C2` | `60` | `117` |
| `C-table[lenRunsMedian].C0` | `8` | `3` |
| `C-table[lenRunsMedian].C2` | `3` | `7` |
| `C-table[numDirectionalRuns].C0` | `33` | `23` |
| `C-table[numDirectionalRuns].C1` | `1` | `0` |
| `C-table[numDirectionalRuns].C2` | `5` | `6` |
| `C-table[numIncreasesDecreases].C0` | `30` | `11` |
| `C-table[periodicity(1)].C0` | `29` | `41` |
| `C-table[periodicity(16)].C2` | `56` | `31` |
| `C-table[periodicity(2)].C0` | `15` | `17` |
| `C-table[periodicity(32)].C0` | `12` | `9` |
| `C-table[periodicity(8)].C0` | `6` | `7` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `25.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `13.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `7.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `14.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `12.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `8.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `33.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `30.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `29.0` | `41.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `15.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `12.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance16` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.numDirectionalRuns` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `212.0` | `206.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `60.0` | `117.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `3.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C2.numDirectionalRuns` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.periodicity16` | `56.0` | `31.0` |

**a-t2-r2 vs b-t1-r1 -- RNG-dependent differences (66; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r2__vs__b-t1-r1.diff.txt`

| field | a-t2-r2 | b-t1-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `33` | `15` |
| `C-table[compression].C0` | `16` | `5` |
| `C-table[covariance(1)].C0` | `9` | `12` |
| `C-table[covariance(16)].C2` | `293` | `225` |
| `C-table[covariance(2)].C0` | `8` | `28` |
| `C-table[covariance(32)].C0` | `5` | `6` |
| `C-table[covariance(32)].C1` | `1` | `0` |
| `C-table[covariance(32)].C2` | `126` | `130` |
| `C-table[covariance(8)].C0` | `6` | `23` |
| `C-table[excursion].C0` | `10` | `6` |
| `C-table[excursion].C2` | `6` | `7` |
| `C-table[lenDirectionalRuns].C0` | `1` | `2` |
| `C-table[lenDirectionalRuns].C1` | `5` | `4` |
| `C-table[lenDirectionalRuns].C2` | `79` | `81` |
| `C-table[lenRunsMedian].C0` | `2` | `5` |
| `C-table[lenRunsMedian].C1` | `4` | `3` |
| `C-table[maxCollision].C0` | `15` | `8` |
| `C-table[maxCollision].C1` | `0` | `1` |
| `C-table[maxCollision].C2` | `6` | `5` |
| `C-table[numDirectionalRuns].C0` | `19` | `17` |
| `C-table[numIncreasesDecreases].C0` | `28` | `13` |
| `C-table[numIncreasesDecreases].C1` | `0` | `1` |
| `C-table[numIncreasesDecreases].C2` | `6` | `5` |
| `C-table[numRunsMedian].C2` | `6` | `9` |
| `C-table[periodicity(1)].C0` | `68` | `30` |
| `C-table[periodicity(1)].C1` | `0` | `2` |
| `C-table[periodicity(1)].C2` | `6` | `4` |
| `C-table[periodicity(16)].C0` | `6` | `5` |
| `C-table[periodicity(16)].C1` | `0` | `1` |
| `C-table[periodicity(16)].C2` | `33` | `23` |
| `C-table[periodicity(2)].C0` | `15` | `13` |
| `C-table[periodicity(32)].C0` | `17` | `22` |
| `C-table[periodicity(8)].C0` | `11` | `12` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `33.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `16.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `9.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `8.0` | `28.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `6.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `10.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `2.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `15.0` | `8.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `19.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `28.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `68.0` | `30.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `6.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `15.0` | `13.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `17.0` | `22.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `11.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numIncreasesDecreases` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `293.0` | `225.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `126.0` | `130.0` |
| `json.testCases[].permutationTestResults[input].C2.excursion` | `6.0` | `7.0` |
| ... 6 more | | |

**a-t2-r2 vs b-t2-r1 -- RNG-dependent differences (72; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r2__vs__b-t2-r1.diff.txt`

| field | a-t2-r2 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `33` | `21` |
| `C-table[compression].C0` | `16` | `4` |
| `C-table[compression].C1` | `1` | `2` |
| `C-table[compression].C2` | `5` | `4` |
| `C-table[covariance(1)].C0` | `9` | `10` |
| `C-table[covariance(16)].C2` | `293` | `303` |
| `C-table[covariance(2)].C0` | `8` | `10` |
| `C-table[covariance(32)].C0` | `5` | `6` |
| `C-table[covariance(32)].C1` | `1` | `0` |
| `C-table[covariance(32)].C2` | `126` | `77` |
| `C-table[covariance(8)].C0` | `6` | `15` |
| `C-table[excursion].C0` | `10` | `11` |
| `C-table[lenDirectionalRuns].C0` | `1` | `4` |
| `C-table[lenDirectionalRuns].C1` | `5` | `2` |
| `C-table[lenDirectionalRuns].C2` | `79` | `125` |
| `C-table[lenRunsMedian].C0` | `2` | `5` |
| `C-table[lenRunsMedian].C1` | `4` | `2` |
| `C-table[lenRunsMedian].C2` | `3` | `4` |
| `C-table[maxCollision].C0` | `15` | `9` |
| `C-table[maxCollision].C1` | `0` | `1` |
| `C-table[maxCollision].C2` | `6` | `5` |
| `C-table[numDirectionalRuns].C0` | `19` | `25` |
| `C-table[numDirectionalRuns].C1` | `0` | `1` |
| `C-table[numDirectionalRuns].C2` | `6` | `5` |
| `C-table[numIncreasesDecreases].C0` | `28` | `18` |
| `C-table[numIncreasesDecreases].C1` | `0` | `2` |
| `C-table[numIncreasesDecreases].C2` | `6` | `4` |
| `C-table[numRunsMedian].C0` | `6` | `7` |
| `C-table[periodicity(1)].C0` | `68` | `53` |
| `C-table[periodicity(16)].C2` | `33` | `36` |
| `C-table[periodicity(2)].C0` | `15` | `44` |
| `C-table[periodicity(32)].C0` | `17` | `10` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `5` | `6` |
| `C-table[periodicity(8)].C0` | `11` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `33.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `16.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `9.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `8.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `6.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `10.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `1.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `2.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `15.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `19.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `28.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `68.0` | `53.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `15.0` | `44.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `17.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `11.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `5.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numDirectionalRuns` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numIncreasesDecreases` | `0.0` | `2.0` |
| ... 12 more | | |

**a-t2-r2 vs b-t2-r2 -- RNG-dependent differences (64; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/a-t2-r2__vs__b-t2-r2.diff.txt`

| field | a-t2-r2 | b-t2-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `33` | `12` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `5` | `6` |
| `C-table[covariance(1)].C0` | `9` | `6` |
| `C-table[covariance(16)].C0` | `6` | `4` |
| `C-table[covariance(16)].C1` | `0` | `2` |
| `C-table[covariance(16)].C2` | `293` | `206` |
| `C-table[covariance(2)].C0` | `8` | `18` |
| `C-table[covariance(32)].C0` | `5` | `6` |
| `C-table[covariance(32)].C1` | `1` | `0` |
| `C-table[covariance(32)].C2` | `126` | `57` |
| `C-table[covariance(8)].C2` | `6` | `7` |
| `C-table[excursion].C0` | `10` | `15` |
| `C-table[lenDirectionalRuns].C0` | `1` | `2` |
| `C-table[lenDirectionalRuns].C1` | `5` | `4` |
| `C-table[lenDirectionalRuns].C2` | `79` | `117` |
| `C-table[lenRunsMedian].C0` | `2` | `3` |
| `C-table[lenRunsMedian].C1` | `4` | `3` |
| `C-table[lenRunsMedian].C2` | `3` | `7` |
| `C-table[maxCollision].C0` | `15` | `10` |
| `C-table[numDirectionalRuns].C0` | `19` | `23` |
| `C-table[numIncreasesDecreases].C0` | `28` | `11` |
| `C-table[numRunsMedian].C2` | `6` | `9` |
| `C-table[periodicity(1)].C0` | `68` | `41` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C2` | `33` | `31` |
| `C-table[periodicity(2)].C0` | `15` | `17` |
| `C-table[periodicity(32)].C0` | `17` | `9` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `5` | `6` |
| `C-table[periodicity(8)].C0` | `11` | `7` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `33.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `9.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `8.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance32` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `10.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `15.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `19.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `28.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `68.0` | `41.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `15.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `17.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `11.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance16` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `4.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `293.0` | `206.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance32` | `126.0` | `57.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance8` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C2.lenDirectionalRuns` | `79.0` | `117.0` |
| `json.testCases[].permutationTestResults[input].C2.lenRunsMedian` | `3.0` | `7.0` |
| ... 4 more | | |

**b-t1-r1 vs b-t2-r1 -- RNG-dependent differences (74; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/b-t1-r1__vs__b-t2-r1.diff.txt`

| field | b-t1-r1 | b-t2-r1 |
|---|---|---|
| `C-table[avgCollision].C0` | `15` | `21` |
| `C-table[compression].C0` | `5` | `4` |
| `C-table[compression].C1` | `1` | `2` |
| `C-table[compression].C2` | `5` | `4` |
| `C-table[covariance(1)].C0` | `12` | `10` |
| `C-table[covariance(16)].C2` | `225` | `303` |
| `C-table[covariance(2)].C0` | `28` | `10` |
| `C-table[covariance(32)].C2` | `130` | `77` |
| `C-table[covariance(8)].C0` | `23` | `15` |
| `C-table[excursion].C0` | `6` | `11` |
| `C-table[excursion].C2` | `7` | `6` |
| `C-table[lenDirectionalRuns].C0` | `2` | `4` |
| `C-table[lenDirectionalRuns].C1` | `4` | `2` |
| `C-table[lenDirectionalRuns].C2` | `81` | `125` |
| `C-table[lenRunsMedian].C1` | `3` | `2` |
| `C-table[lenRunsMedian].C2` | `3` | `4` |
| `C-table[maxCollision].C0` | `8` | `9` |
| `C-table[numDirectionalRuns].C0` | `17` | `25` |
| `C-table[numDirectionalRuns].C1` | `0` | `1` |
| `C-table[numDirectionalRuns].C2` | `6` | `5` |
| `C-table[numIncreasesDecreases].C0` | `13` | `18` |
| `C-table[numIncreasesDecreases].C1` | `1` | `2` |
| `C-table[numIncreasesDecreases].C2` | `5` | `4` |
| `C-table[numRunsMedian].C0` | `6` | `7` |
| `C-table[numRunsMedian].C2` | `9` | `6` |
| `C-table[periodicity(1)].C0` | `30` | `53` |
| `C-table[periodicity(1)].C1` | `2` | `0` |
| `C-table[periodicity(1)].C2` | `4` | `6` |
| `C-table[periodicity(16)].C0` | `5` | `6` |
| `C-table[periodicity(16)].C1` | `1` | `0` |
| `C-table[periodicity(16)].C2` | `23` | `36` |
| `C-table[periodicity(2)].C0` | `13` | `44` |
| `C-table[periodicity(32)].C0` | `22` | `10` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `5` | `6` |
| `C-table[periodicity(8)].C0` | `12` | `5` |
| `C-table[periodicity(8)].C1` | `0` | `1` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `15.0` | `21.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `12.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `28.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `23.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `6.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `2.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `17.0` | `25.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `13.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `6.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `30.0` | `53.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `13.0` | `44.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `22.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `12.0` | `5.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `3.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.numDirectionalRuns` | `0.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.numIncreasesDecreases` | `1.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `2.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `1.0` | `0.0` |
| ... 14 more | | |

**b-t1-r1 vs b-t2-r2 -- RNG-dependent differences (70; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/b-t1-r1__vs__b-t2-r2.diff.txt`

| field | b-t1-r1 | b-t2-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `15` | `12` |
| `C-table[compression].C0` | `5` | `16` |
| `C-table[compression].C1` | `1` | `0` |
| `C-table[compression].C2` | `5` | `6` |
| `C-table[covariance(1)].C0` | `12` | `6` |
| `C-table[covariance(16)].C0` | `6` | `4` |
| `C-table[covariance(16)].C1` | `0` | `2` |
| `C-table[covariance(16)].C2` | `225` | `206` |
| `C-table[covariance(2)].C0` | `28` | `18` |
| `C-table[covariance(32)].C2` | `130` | `57` |
| `C-table[covariance(8)].C0` | `23` | `6` |
| `C-table[covariance(8)].C2` | `6` | `7` |
| `C-table[excursion].C0` | `6` | `15` |
| `C-table[excursion].C2` | `7` | `6` |
| `C-table[lenDirectionalRuns].C2` | `81` | `117` |
| `C-table[lenRunsMedian].C0` | `5` | `3` |
| `C-table[lenRunsMedian].C2` | `3` | `7` |
| `C-table[maxCollision].C0` | `8` | `10` |
| `C-table[maxCollision].C1` | `1` | `0` |
| `C-table[maxCollision].C2` | `5` | `6` |
| `C-table[numDirectionalRuns].C0` | `17` | `23` |
| `C-table[numIncreasesDecreases].C0` | `13` | `11` |
| `C-table[numIncreasesDecreases].C1` | `1` | `0` |
| `C-table[numIncreasesDecreases].C2` | `5` | `6` |
| `C-table[periodicity(1)].C0` | `30` | `41` |
| `C-table[periodicity(1)].C1` | `2` | `1` |
| `C-table[periodicity(1)].C2` | `4` | `5` |
| `C-table[periodicity(16)].C0` | `5` | `6` |
| `C-table[periodicity(16)].C1` | `1` | `0` |
| `C-table[periodicity(16)].C2` | `23` | `31` |
| `C-table[periodicity(2)].C0` | `13` | `17` |
| `C-table[periodicity(32)].C0` | `22` | `9` |
| `C-table[periodicity(32)].C1` | `1` | `0` |
| `C-table[periodicity(32)].C2` | `5` | `6` |
| `C-table[periodicity(8)].C0` | `12` | `7` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `15.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `5.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `12.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `28.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `23.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `6.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `5.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `8.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `17.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `13.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `30.0` | `41.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity16` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `13.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `22.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `12.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance16` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.numIncreasesDecreases` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity1` | `2.0` | `1.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity16` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.periodicity32` | `1.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C2.compression` | `5.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C2.covariance16` | `225.0` | `206.0` |
| ... 10 more | | |

**b-t2-r1 vs b-t2-r2 -- RNG-dependent differences (76; expected under a live seed):** full list in `iid/smoke-csprng-1bit-20000/b-t2-r1__vs__b-t2-r2.diff.txt`

| field | b-t2-r1 | b-t2-r2 |
|---|---|---|
| `C-table[avgCollision].C0` | `21` | `12` |
| `C-table[compression].C0` | `4` | `16` |
| `C-table[compression].C1` | `2` | `0` |
| `C-table[compression].C2` | `4` | `6` |
| `C-table[covariance(1)].C0` | `10` | `6` |
| `C-table[covariance(16)].C0` | `6` | `4` |
| `C-table[covariance(16)].C1` | `0` | `2` |
| `C-table[covariance(16)].C2` | `303` | `206` |
| `C-table[covariance(2)].C0` | `10` | `18` |
| `C-table[covariance(32)].C2` | `77` | `57` |
| `C-table[covariance(8)].C0` | `15` | `6` |
| `C-table[covariance(8)].C2` | `6` | `7` |
| `C-table[excursion].C0` | `11` | `15` |
| `C-table[lenDirectionalRuns].C0` | `4` | `2` |
| `C-table[lenDirectionalRuns].C1` | `2` | `4` |
| `C-table[lenDirectionalRuns].C2` | `125` | `117` |
| `C-table[lenRunsMedian].C0` | `5` | `3` |
| `C-table[lenRunsMedian].C1` | `2` | `3` |
| `C-table[lenRunsMedian].C2` | `4` | `7` |
| `C-table[maxCollision].C0` | `9` | `10` |
| `C-table[maxCollision].C1` | `1` | `0` |
| `C-table[maxCollision].C2` | `5` | `6` |
| `C-table[numDirectionalRuns].C0` | `25` | `23` |
| `C-table[numDirectionalRuns].C1` | `1` | `0` |
| `C-table[numDirectionalRuns].C2` | `5` | `6` |
| `C-table[numIncreasesDecreases].C0` | `18` | `11` |
| `C-table[numIncreasesDecreases].C1` | `2` | `0` |
| `C-table[numIncreasesDecreases].C2` | `4` | `6` |
| `C-table[numRunsMedian].C0` | `7` | `6` |
| `C-table[numRunsMedian].C2` | `6` | `9` |
| `C-table[periodicity(1)].C0` | `53` | `41` |
| `C-table[periodicity(1)].C1` | `0` | `1` |
| `C-table[periodicity(1)].C2` | `6` | `5` |
| `C-table[periodicity(16)].C2` | `36` | `31` |
| `C-table[periodicity(2)].C0` | `44` | `17` |
| `C-table[periodicity(32)].C0` | `10` | `9` |
| `C-table[periodicity(8)].C0` | `5` | `7` |
| `C-table[periodicity(8)].C1` | `1` | `0` |
| `json.testCases[].permutationTestResults[input].C0.avgCollision` | `21.0` | `12.0` |
| `json.testCases[].permutationTestResults[input].C0.compression` | `4.0` | `16.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance1` | `10.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance16` | `6.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance2` | `10.0` | `18.0` |
| `json.testCases[].permutationTestResults[input].C0.covariance8` | `15.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.excursion` | `11.0` | `15.0` |
| `json.testCases[].permutationTestResults[input].C0.lenDirectionalRuns` | `4.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C0.lenRunsMedian` | `5.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C0.maxCollision` | `9.0` | `10.0` |
| `json.testCases[].permutationTestResults[input].C0.numDirectionalRuns` | `25.0` | `23.0` |
| `json.testCases[].permutationTestResults[input].C0.numIncreasesDecreases` | `18.0` | `11.0` |
| `json.testCases[].permutationTestResults[input].C0.numRunsMedian` | `7.0` | `6.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity1` | `53.0` | `41.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity2` | `44.0` | `17.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity32` | `10.0` | `9.0` |
| `json.testCases[].permutationTestResults[input].C0.periodicity8` | `5.0` | `7.0` |
| `json.testCases[].permutationTestResults[input].C1.compression` | `2.0` | `0.0` |
| `json.testCases[].permutationTestResults[input].C1.covariance16` | `0.0` | `2.0` |
| `json.testCases[].permutationTestResults[input].C1.lenDirectionalRuns` | `2.0` | `4.0` |
| `json.testCases[].permutationTestResults[input].C1.lenRunsMedian` | `2.0` | `3.0` |
| `json.testCases[].permutationTestResults[input].C1.maxCollision` | `1.0` | `0.0` |
| ... 16 more | | |

**Verdict and seed-source table (arm a = default `/dev/urandom`, arm b = `EA_TEST_RANDOM_SOURCE` set):**

| run | arm | threads | random source env | rc | chi-square | LRS | permutation | JSON IID | errorLevel | Assessed min entropy | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-t2-r1 | a | 2 | /dev/urandom (default) | 0 | Passed | Passed | Passed | True | 0 | 0.95986026937287861 | 0 |
| a-t2-r2 | a | 2 | /dev/urandom (default) | 0 | Passed | Passed | Passed | True | 0 | 0.95986026937287861 | 1 |
| b-t1-r1 | b | 1 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.95986026937287861 | 0 |
| b-t2-r1 | b | 2 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.95986026937287861 | 0 |
| b-t2-r2 | b | 2 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke/inputs/fixed-random-source-1MiB.bin | 0 | Passed | Passed | Passed | True | 0 | 0.95986026937287861 | 0 |

Counters C0/C1/C2 per statistic and run (`-` = not printed; a row identical across every run under a live seed would be surprising):

| statistic | a-t2-r1 | a-t2-r2 | b-t1-r1 | b-t2-r1 | b-t2-r2 | identical across runs |
|---|---|---|---|---|---|---|
| avgCollision | 25/0/6 | 33/0/6 | 15/0/6 | 21/0/6 | 12/0/6 | no |
| compression | 13/0/6 | 16/1/5 | 5/1/5 | 4/2/4 | 16/0/6 | no |
| covariance(1) | 7/0/6 | 9/0/6 | 12/0/6 | 10/0/6 | 6/0/6 | no |
| covariance(16) | 6/0/212 | 6/0/293 | 6/0/225 | 6/0/303 | 4/2/206 | no |
| covariance(2) | 18/0/6 | 8/0/6 | 28/0/6 | 10/0/6 | 18/0/6 | no |
| covariance(32) | 6/0/57 | 5/1/126 | 6/0/130 | 6/0/77 | 6/0/57 | no |
| covariance(8) | 14/0/6 | 6/0/6 | 23/0/6 | 15/0/6 | 6/0/7 | no |
| excursion | 12/0/6 | 10/0/6 | 6/0/7 | 11/0/6 | 15/0/6 | no |
| lenDirectionalRuns | 1/5/60 | 1/5/79 | 2/4/81 | 4/2/125 | 2/4/117 | no |
| lenRunsMedian | 8/3/3 | 2/4/3 | 5/3/3 | 5/2/4 | 3/3/7 | no |
| maxCollision | 10/0/6 | 15/0/6 | 8/1/5 | 9/1/5 | 10/0/6 | no |
| numDirectionalRuns | 33/1/5 | 19/0/6 | 17/0/6 | 25/1/5 | 23/0/6 | no |
| numIncreasesDecreases | 30/0/6 | 28/0/6 | 13/1/5 | 18/2/4 | 11/0/6 | no |
| numRunsMedian | 6/0/9 | 6/0/6 | 6/0/9 | 7/0/6 | 6/0/9 | no |
| periodicity(1) | 29/1/5 | 68/0/6 | 30/2/4 | 53/0/6 | 41/1/5 | no |
| periodicity(16) | 6/0/56 | 6/0/33 | 5/1/23 | 6/0/36 | 6/0/31 | no |
| periodicity(2) | 15/0/6 | 15/0/6 | 13/0/6 | 44/0/6 | 17/0/6 | no |
| periodicity(32) | 12/0/6 | 17/1/5 | 22/1/5 | 10/0/6 | 9/0/6 | no |
| periodicity(8) | 6/0/6 | 11/0/6 | 12/0/6 | 5/1/6 | 7/0/6 | no |

Arm (b) under `EA_TEST_RANDOM_SOURCE`: two runs at the same thread count agree on the JSON? threads=2: DIFFER (2 runs). Prediction from the source was DIFFER (the variable does not reach `seed()`); if they AGREE, the source reading above is wrong and must be re-read.

Reading: every RNG-independent field is identical in all pairs; only the permutation counters/verdict path varies, which the live seed explains. NOT a finding.

## iid / smoke-csprng-8bit-20000 -- DETERMINISTIC (RNG-independent fields)

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| a-t2-r1 | a | 2 | 1 | yes | 0 | 22f1319ae347ab4e | 8e5441d8de225b55 | 0 |
| a-t2-r2 | a | 2 | 1 | yes | 0 | 22f1319ae347ab4e | 8e5441d8de225b55 | 0 |
| b-t1-r1 | b | 1 | 1 | yes | 0 | 22f1319ae347ab4e | 8e5441d8de225b55 | 0 |
| b-t2-r1 | b | 2 | 1 | yes | 0 | 22f1319ae347ab4e | 8e5441d8de225b55 | 0 |
| b-t2-r2 | b | 2 | 1 | yes | 0 | 22f1319ae347ab4e | 8e5441d8de225b55 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| a-t2-r1 vs a-t2-r2 | = | = | = | = | 0 (0 / 0) |
| a-t2-r1 vs b-t1-r1 | = | = | = | = | 0 (0 / 0) |
| a-t2-r1 vs b-t2-r1 | = | = | = | = | 0 (0 / 0) |
| a-t2-r1 vs b-t2-r2 | = | = | = | = | 0 (0 / 0) |
| a-t2-r2 vs b-t1-r1 | = | = | = | = | 0 (0 / 0) |
| a-t2-r2 vs b-t2-r1 | = | = | = | = | 0 (0 / 0) |
| a-t2-r2 vs b-t2-r2 | = | = | = | = | 0 (0 / 0) |
| b-t1-r1 vs b-t2-r1 | = | = | = | = | 0 (0 / 0) |
| b-t1-r1 vs b-t2-r2 | = | = | = | = | 0 (0 / 0) |
| b-t2-r1 vs b-t2-r2 | = | = | = | = | 0 (0 / 0) |

**Verdict and seed-source table (arm a = default `/dev/urandom`, arm b = `EA_TEST_RANDOM_SOURCE` set):**

| run | arm | threads | random source env | rc | chi-square | LRS | permutation | JSON IID | errorLevel | Assessed min entropy | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-t2-r1 | a | 2 | /dev/urandom (default) | 1 | Failed | Passed | <absent> | False | 2 | <absent> | 0 |
| a-t2-r2 | a | 2 | /dev/urandom (default) | 1 | Failed | Passed | <absent> | False | 2 | <absent> | 0 |
| b-t1-r1 | b | 1 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke/inputs/fixed-random-source-1MiB.bin | 1 | Failed | Passed | <absent> | False | 2 | <absent> | 0 |
| b-t2-r1 | b | 2 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke/inputs/fixed-random-source-1MiB.bin | 1 | Failed | Passed | <absent> | False | 2 | <absent> | 0 |
| b-t2-r2 | b | 2 | /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/smoke/inputs/fixed-random-source-1MiB.bin | 1 | Failed | Passed | <absent> | False | 2 | <absent> | 0 |

Counters C0/C1/C2 per statistic and run (`-` = not printed; a row identical across every run under a live seed would be surprising):

| statistic | a-t2-r1 | a-t2-r2 | b-t1-r1 | b-t2-r1 | b-t2-r2 | identical across runs |
|---|---|---|---|---|---|---|
| avgCollision | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| compression | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| covariance(1) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| covariance(16) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| covariance(2) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| covariance(32) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| covariance(8) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| excursion | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| lenDirectionalRuns | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| lenRunsMedian | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| maxCollision | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| numDirectionalRuns | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| numIncreasesDecreases | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| numRunsMedian | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| periodicity(1) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| periodicity(16) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| periodicity(2) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| periodicity(32) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |
| periodicity(8) | -/-/- | -/-/- | -/-/- | -/-/- | -/-/- | yes |

Arm (b) under `EA_TEST_RANDOM_SOURCE`: the permutation battery did NOT run in every arm-b run (skipped after a deterministic chi-square/LRS refusal), so these runs say nothing about the seed; their agreement (threads=2: AGREE (2 runs)) is the deterministic path's.

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / smoke-csprng-1bit-20000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 0 | 1ad1568c083b2774 | 17917b5af1e8d08d | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | 17917b5af1e8d08d | 0 |
| t2-r2 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | 17917b5af1e8d08d | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t2-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t2-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

## non_iid / smoke-csprng-8bit-20000 -- DETERMINISTIC

| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |
|---|---|---|---|---|---|---|---|---|
| t1-r1 | - | 1 | 0 | yes | 1 | 1ad1568c083b2774 | 8e5441d8de225b55 | 0 |
| t2-r1 | - | 2 | 0 | yes | 0 | 1ad1568c083b2774 | 8e5441d8de225b55 | 0 |
| t2-r2 | - | 2 | 0 | yes | 1 | 1ad1568c083b2774 | 8e5441d8de225b55 | 0 |

| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |
|---|---|---|---|---|---|
| t1-r1 vs t2-r1 | = | = | = | = | 0 (0 / 0) |
| t1-r1 vs t2-r2 | = | = | = | = | 0 (0 / 0) |
| t2-r1 vs t2-r2 | = | = | = | = | 0 (0 / 0) |

Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.

