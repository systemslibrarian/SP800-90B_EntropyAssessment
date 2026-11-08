# PROV-02 -- -c mode: JSON hAssessed = word_size x h' while stdout h' is per bit; no unit or mode field (F23 sub-claim)

**Provisional ID:** PROV-02 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** MEDIUM (consumer-dependent overstatement by a factor of bitsPerSymbol, up to 8x, if hAssessed from a -c report is read as the standard's per-bit h'; the tool's own arithmetic is internally consistent; outside the target profile, which is -i)
**Direction:** overstates if misread (x8 on byte-packed conditioned output); neutral in the code
**Component:** cpp/non_iid_main.cpp:main() :632-637 (`h_assessed = min(word_size, H_bitstring * word_size)` under !initial_entropy), :651 (`printf("\nh': %f\n", H_bitstring)`), :666-679 (tcOverall.h_assessed, data_word_size). Same in cpp/iid_main.cpp:455-463.
**Spec:** SP 800-90B 3.1.5.2 (PDF p. 25): "Let the obtained entropy estimate per bit be h'. The output of the conditioning component (nout) shall be treated as a binary string, for purposes of the entropy estimation. ... h_out = min(Output_Entropy(n_in, n_out, nw, h_in), 0.999 n_out, h' x n_out)." The multiplication by n_out belongs to h_out and uses the conditioner's output width, not the file's packing width.
**Prior-fix interaction (rule 12):** Tracker F23 (UNCONFIRMED there; confirmed by this run). NOVEL-02/N-10 (9f64f62, 094189c) moved ea_iid's h_assessed out of the verbosity branch and deliberately preserved this combination ("ea_non_iid already records only what it computed"). N-02 (134d377) built the -c bitstring view the figure comes from. Upstream-inherited (identical at upstream/master 491-512).
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.2 and 4.1; aggregation.md 2.5 and headline 3; mcv.md S-1 (probe 4); cli-build.md 2.1 and 9.1.
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: text h' = 0.732612 per bit; JSON Overall.hAssessed = 5.860893744485249 = 8 x hBitstring (0.7326117180606562) bit-for-bit; no key in the document names a unit or the mode (bitsPerSymbol/bitsPerSymbolInferred are the only width-related keys).

**What this reproducer does not establish:** ShannonPad's reader was not inspected; whether any consumer reads a -c report per bit is unknown. The documented sizing path is -i, where hAssessed is per sample and the text agrees with it.

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-02-observed.log` and `PROV-02-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-02 observed.txt  2026-11-07 21:56:06 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin (10,000 samples, 8-bit)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -c -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-02/out/c8.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[c8_default]=0  stdout=c8.out stderr=c8.err
stdout line:            h': 0.732612        (printf "\nh': %f\n", H_bitstring -- per bit)
JSON Overall.hAssessed   = 5.860893744485249
JSON Overall.hBitstring  = 0.7326117180606562
JSON Overall.dataWordSize= 8.0
JSON Overall.hOriginal   = <absent>
JSON keys naming a unit/mode/h-prime anywhere in the document: bitsPerSymbol,bitsPerSymbolInferred
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -c -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-02/out/c8v.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand8_short.bin 8
rc[c8_vvv]=0  stdout=c8v.out stderr=c8v.err
  -vvv text: H_bitstring = 0.73261171806065617
  -vvv text: H_bitstring Per Symbol = 5.8608937444852494
  -vvv text: Assessed min entropy: 5.8608937444852494
  -vvv text has an h' line: 0 (0 expected -- only the 'Assessed' label exists at this level)
ratio hAssessed/hBitstring = 8 ; hAssessed == dataWordSize*hBitstring: True ; hAssessed equals the text h': False
DEFECT
RESULT: PASS -- stdout h' is per bit; JSON hAssessed = dataWordSize x h' (x8 here) under the same key name as the -i per-sample figure; no unit or mode field in the report
```

### control.txt (verbatim)

```
# PROV-02 control.txt  2026-11-07 21:56:07 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 3814404497a3b912f8d3db6bc05a99338f0986cd75fe54af2a5f1bdb0a12a583  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin (10,000 samples, 1-bit)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -c -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-02/out/c1.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1
rc[c1_default]=0  stdout=c1.out stderr=c1.err
stdout h': 0.611716 ; JSON hAssessed=0.6117162047939451 hBitstring=0.6117162047939451 dataWordSize=1.0
RESULT: CONTROL-OK -- at word_size 1 the text h' and JSON hAssessed agree to the printed precision; the x8 gap in run.sh is the packing width
```
