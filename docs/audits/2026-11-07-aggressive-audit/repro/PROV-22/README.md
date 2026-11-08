# PROV-22 -- xoshiro_jump(k) is not k canonical jumps for k >= 2 (accumulators never re-zeroed): threads 2+ start at a J-linear image of the seed

**Provisional ID:** PROV-22 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (code-vs-comment; each thread's shuffle is still uniform; overlap probability ~threads x 2^44 / 2^256)
**Direction:** neutral
**Component:** cpp/shared/utils.h:xoshiro_jump() :765-789 (s0..s3 declared once, outside `for j < jump_count`); caller cpp/iid/permutation_tests.h:649 `xoshiro_jump(omp_get_thread_num(), ...)`. Only OMP_NUM_THREADS >= 3 is affected.
**Spec:** n/a (SP 800-90B 5.1 names no randomness source). The code's own comment (utils.h:762-764, permutation_tests.h:648) promises 'omp_get_thread_num() * 2^128 calls'.
**Prior-fix interaction (rule 12):** None; upstream-inherited. OC-53's bit-identity exclusion of permutationTestResults rests on the field varying run to run, which it does regardless.
**Analysis-phase source (re-checked here):** logs/analysis/iid-permutation.md 2.1 'Per-thread streams' (CONFIRMED by model, analysis-iid-perm-rng-model.log) and section 5.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED AT MODEL LEVEL ONLY: model.py (a transcription of utils.h:765-789 beside the canonical Blackman/Vigna jump) shows k = 0, 1 agree, k = 2, 3, 4 disagree, and k = 2 equals S1 xor S2 exactly as the un-reset accumulators predict. No binary observable depends on the offset, and an instrumented build is not allowed this phase.

**What this reproducer does not establish:** Not a measurement of the production binary; the statistical harmlessness is an argument from xoshiro256's single-cycle structure. The upgrade/retire measurement is iid-permutation.md edge case 8 (thread-count independence of the C0/C1/C2 distribution).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-22-observed.log` and `PROV-22-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-22 observed.txt  2026-11-07 21:56:24 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
source sha256 a5462f85e296d8fcd908e0f7f56f445aa0905724d840ea69082cdbc97ffdc60e  cpp/shared/utils.h ; xoshiro_jump at lines 765-
  | void xoshiro_jump(unsigned int jump_count, uint64_t *xoshiro256starstarState) {
  | 	static const uint64_t JUMP[] = { 0x180ec6d33cfd0aba, 0xd5a61266f0c9392c, 0xa9582618e03fc9aa, 0x39abdc4529b1661c };
  | 	uint64_t s0 = 0;
  | 	uint64_t s1 = 0;
  | 	uint64_t s2 = 0;
  | 	uint64_t s3 = 0;
  | 
  | 	for(unsigned int j=0; j < jump_count; j++) {
  | 		for(unsigned int i = 0; i < sizeof JUMP / sizeof *JUMP; i++)
  | 			for(unsigned int b = 0; b < 64; b++) {
  | 				if (JUMP[i] & ((uint64_t)1) << b) {
  | 					s0 ^= xoshiro256starstarState[0];
  | 					s1 ^= xoshiro256starstarState[1];
  | 					s2 ^= xoshiro256starstarState[2];
  | 					s3 ^= xoshiro256starstarState[3];
  | 				}
  | 				xoshiro256starstar(xoshiro256starstarState);	
  | 			}
  | 			
  | 		xoshiro256starstarState[0] = s0;
  | 		xoshiro256starstarState[1] = s1;
  | 		xoshiro256starstarState[2] = s2;
  | 		xoshiro256starstarState[3] = s3;
  | 	}
  | }
caller: permutation_tests.h:649
  model: k=0 (thread 0): code==canonical? True ; code state nonzero? True
  model: k=1 (thread 1): code==canonical? True ; code state nonzero? True
  model: k=2 (thread 2): code==canonical? False ; code state nonzero? True
  model: k=3 (thread 3): code==canonical? False ; code state nonzero? True
  model: k=4 (thread 4): code==canonical? False ; code state nonzero? True
  model: k=2 equals S1 xor S2 (the un-reset accumulator prediction)? True
model exit (0 = every k agrees with canonical): 1
RESULT: PASS -- k >= 2 diverges from k canonical jumps and k = 2 equals S1 xor S2 exactly as the un-reset accumulators predict (model-level reproduction)
```

### control.txt (verbatim)

```
# PROV-22 control.txt  2026-11-07 21:56:24 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
  model: k=0 (thread 0): code==canonical? True ; code state nonzero? True
  model: k=1 (thread 1): code==canonical? True ; code state nonzero? True
RESULT: CONTROL-OK -- k = 0 and k = 1 equal the canonical jump; only threads >= 2 are affected
```
