# Phase-2 audit progress (paused 2026-09-30)

Baseline: upstream 87c104d exported via git archive to scratchpad/up (no worktree; another agent shares the checkout).
Build: g++ 13.3.0, Ubuntu 24.04 x86_64 glibc 2.39, stock Makefile (-O2 -fopenmp -march=native). Selftest PASS (max delta 1.0e-13).
Issue/PR dump: scratchpad/dump/{issues,prs}.json, digest.txt, full.txt (188 issues, 82 PRs; all read).
Spec text: scratchpad/spec.txt. Test data: scratchpad/w/.

## Candidates so far
1. NOVEL (A, HIGH): §5.2.3 binary chi-square independence: m=1 -> code sets T=0,df=0 -> p=1 PASS; spec says "If m is 1, the test fails".
   chi_square_tests.h:485-489. Repro: w/iid_p002.bin (Bernoulli 0.002045, L=1e6, seed 20260930). ea_iid passes all (2 runs).
   IID-track H=0.0027851 vs non-IID H=0.0020159 (+38%, TOO HIGH). Also affects ea_restart -i row/col.
2. NOVEL (E, HIGH): ea_restart -i JSON errorLevel 0 on read/width failure (exit 255). restart_main.cpp:324 sets testRunNonIid instead of testRunIid.
   Regression from merge 4d68e477 (2024-03-28, PR #230 merge). Repro: ea_restart -i -o x.json r8.bin 4 3.2.
3. NOVEL (E/B, HIGH-repro, low sev): sha256_file return ignored in all mains -> JSON "sha256" = uninitialized stack bytes when file can't be opened (seen 'ȂcρV').
4. NOVEL (D, low): ea_restart H_I=nan passes both range checks -> counts[(int)NaN] OOB stack write -> SIGSEGV (exit 139). atof: "abc"->0, "7abc"->7 accepted.
5. EXCLUDED (#246 still reachable after PR #248): len_LRS_test assert p_col>=1/k aborts for perfectly balanced k in {3,6,7,12} (k=5,10 ok). Files w/bal_k*.bin.
6. Minor: errorMsg literal "%s" (comma operator) in read_file*; conditioning -i file hashed/recorded even when h' given on cmdline (not yet tested).

## Known/excluded noted: restart sanity-check simulation vs binomial (#56/#95/#209), #195 k assert, #251 hAssessed, #252 IID gating, #153 LDBL_MIN assert, alph_size==2 gate (#253 family).

## Remaining
Mission A: IID restart w/ failing IID tests; LRS -1 unguarded in restart (conservative); OMP stability.
Mission B: conditioning edge cases/JSON echo; all-zero -i file (word_size 0 -> assert).
Mission C: chi-square oracles; OMP 1/2/4/8.
Missions D-J not started (oracles E, JSON F, portability G, resources H, CLI I, shared J). ASan/UBSan build. Final re-fetch of issues before report.

## RESUMED — parallel audit audits/2026-09-30-novel-findings-audit.md (commit 0e685f6) is now part of the exclusion set
My #1=N-01, #2=R-3, #3=N-06, #4=N-04, #5=R-1, #6=N-05. All already found. Remaining focus: D (selftest/refdata/compareresults), E (own oracles), H (resources), J (shared state/JSON writer), leftovers of F/I not in N-05..N-10.
