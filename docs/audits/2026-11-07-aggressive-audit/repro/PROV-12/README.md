# PROV-12 -- Lossy UTF-8 transcoding of commandline/filename: a stray continuation byte swallows the following ASCII byte

**Provisional ID:** PROV-12 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** LOW (reporting; sha256 is the real identity and is unaffected)
**Direction:** neutral
**Component:** cpp/shared/utils.h:recreateCommandLine() :1293-1302 (argv space-joined, unquoted) and cpp/non_iid_main.cpp:275 (filename = argv[optind] verbatim), both serialised by jsoncpp 1.9.8 valueToQuotedString()/utf8ToCodepoint() (/opt/homebrew/include/json, Json::StyledWriter in non_iid_test_run.h:26).
**Spec:** n/a (report integrity).
**Prior-fix interaction (rule 12):** N-07 (c01fb43): the sha256 of the consumed bytes is the identity the report binds to, so a mangled filename does not change what was assessed. A05 (663f9ae) protects the input by path bytes before any transcoding. Inherited (jsoncpp behaviour).
**Analysis-phase source (re-checked here):** logs/analysis/output.md 2.6 and 5.7 (CONFIRMED via argv[0]; filename case NOT RUN on APFS).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED through argv[0] (bash `exec -a`): bytes 65 61 5f 80 5a 71 -> commandline token "ea_\ufffdq" (U+0065 U+0061 U+005F U+FFFD U+0071): the 'Z' is gone; bytes ff fe -> two U+FFFD. Valid JSON, exit 0, errorLevel 0. Control: 'ea_Zq' round-trips exactly.

**What this reproducer does not establish:** The filename case cannot be created on APFS (invalid UTF-8 names are refused); on ext4 the same transcoder path applies (not measured).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-12-observed.log` and `PROV-12-control.log`.

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
# PROV-12 observed.txt  2026-11-07 21:56:15 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
fixture sha256 3814404497a3b912f8d3db6bc05a99338f0986cd75fe54af2a5f1bdb0a12a583  /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin
argv[0] bytes (hex): 65615f805a71   and   65615ffffe71
$ ( exec -a <ea_ 80 5a 71> /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o out/u1.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1 )
rc[argv0-80Zq]=0 errorLevel=0
$ ( exec -a <ea_ ff fe 71> /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o out/u2.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1 )
rc[argv0-fffeq]=0 errorLevel=0
raw bytes of the commandline token in u1.json: 22636f6d6d616e646c696e6522203a202265615f5c7566666664710a
argv[0] sent  : ea_ 80 'Z' 'q'   -> commandline token 0 = 'ea_�q'  (codepoints U+0065 U+0061 U+005F U+FFFD U+0071)
argv[0] sent  : ea_ FF FE 'q'    -> commandline token 0 = 'ea_��q'  (codepoints U+0065 U+0061 U+005F U+FFFD U+FFFD U+0071)
'Z' swallowed: True ; FF FE -> two U+FFFD: True
DEFECT
RESULT: PASS -- a stray 0x80 continuation byte in argv swallows the following ASCII 'Z' in the JSON commandline (valid JSON, exit 0, no diagnostic)
```

### control.txt (verbatim)

```
# PROV-12 control.txt  2026-11-07 21:56:16 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
$ ( exec -a 'ea_Zq' /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -q -o out/c_u.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/bin/rand1_short.bin 1 )
rc=0 commandline token 0 = 'ea_Zq'
RESULT: CONTROL-OK -- valid ASCII argv[0] round-trips exactly; the lost 'Z' in run.sh is the transcoder's doing
```
