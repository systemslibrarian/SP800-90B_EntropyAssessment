# RUN-RECORD -- AFL++ campaign, 2026-11-07 aggressive audit

- started_utc: 2026-11-09T00:04:10Z
- fuzz_dir: `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz`
- host: arm64 26.6.2; 10 CPUs; 16 GB; load { 70.48 47.40 38.69 }
- afl: afl-fuzz++5.03c
- kern.sysv.shmmax: 4194304; AFL_MAP_SIZE for T7: 65536
- AFL runtime per binary (AFL_DUMP_MAP_SIZE probe): plain/ea_non_iid=map:2644 plain/ea_iid=map:3189 plain/ea_restart=map:4492
- ReportCrash loaded: yes (AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 set; crash handling is slower; consider: launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportCrash.plist)
- per-target cap: 8 min; targets: T8; variant override: plain
- EA_ALLOW_SHORT_DATASET=1 and OMP_NUM_THREADS=2 on EVERY execution: nothing here is a compliant assessment.
- seeds manifest: `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz/seeds/MANIFEST.txt` sha256 d37e726b148b6f61208b9d5d1d914d63b65a5628d34e2842ee7072c45070a16e

## binaries (instrument rule 4)

| role | path | sha256 |
|---|---|---|
| fuzz plain | `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz/bin/plain/ea_non_iid` | `e47978fb678cd059e145b1dee607489c2e0b15ff2bef64c09f1272e372121944` |
| fuzz plain | `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz/bin/plain/ea_iid` | `088a58d0b3820fffcd0e35b2cc884e05d0656762906d93eb1f592c583a7cba69` |
| fuzz plain | `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz/bin/plain/ea_restart` | `75f4af0f410399ca9352b616308798f5e7829dfc20e1f49fdcb7b7ec0ad4cdf0` |
| production (NOT fuzzed; for contrast) | `cpp/ea_non_iid` | `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f` |
| production (NOT fuzzed; for contrast) | `cpp/ea_iid` | `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349` |
| production (NOT fuzzed; for contrast) | `cpp/ea_restart` | `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c` |
| driver | `/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/harness/fuzz/argv_driver.sh` | `8e5cd3b796ee8675e19236d3f904762ac70be95b77e967262a67ffbae3f8ab07` |

## plan

```
T   tool        args                     seeds var     min    -G     -t     note
T8  ea_restart  -n @@ 8 0.5/symbol       w8    plain   8      16384  2000+  ea_restart's SEPARATE intake copy read_file (utils.h:549-735) and the ...
total fuzz minutes: 8 (plus ~1 min start-up per target; -V counts fuzz time only)
```

## seeds check

```
## seeds check

```
checked 216 manifest rows against disk and generator: 0 problem(s)
```

checked 216 manifest rows against disk and generator: 0 problem(s)
```

## seeds check

```
## pre-flight (baseline accepted, instrument live, every seed run once, edge cases)

## pre-flight (baseline accepted, instrument live, every seed run once, edge cases)

checked 216 manifest rows against disk and generator: 0 problem(s)
```

## pre-flight (baseline accepted, instrument live, every seed run once, edge cases)

### T8 (ea_restart, plain)

- baseline (`rnd-00064.bin`): rc=255 (expected 255); last stdout line: ''
- instrumentation: afl-showmap tuples = 120
- seeds run once: 29 seeds: 0 assessed (exit 0), 29 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T8/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T8-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

## campaign

| T | variant | minutes | wall s | afl rc | execs | execs/s | corpus | crashes | hangs | stability | map cvg | log |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
### T6 (ea_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'min(H_original, 4 X H_bitstring): 2.246999'
- instrumentation: afl-showmap tuples = 543
- seeds run once: 29 seeds: 7 assessed (exit 0), 5 refused (exit 255), 10 exited by SIGNAL (input + stderr + stdout copied to `out/T6/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T6-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

## campaign

| T | variant | minutes | wall s | afl rc | execs | execs/s | corpus | crashes | hangs | stability | map cvg | log |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
### T7 (argv_driver, plain)

- baseline (`basic-i-a-8.txt`): rc=0 (expected 0); last stdout line: 'H_original: 0.719564'; driver print-mode matched; slash-token negative control: REJECTED two or more slashes in token (path-shaped): /etc/passwd
- instrumentation: afl-showmap tuples = 404
- seeds run once: 66 seeds: 20 assessed (exit 0), 46 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T7/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T7-seeds.log`
- edge: n/a
- pre-flight: OK

## campaign

| T | variant | minutes | wall s | afl rc | execs | execs/s | corpus | crashes | hangs | stability | map cvg | log |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T8 | plain | 8 | 492 | 0 | 98076 | 204.32 | 39 | 0 | 0 | 100.00% | 3.05% | `logs/fuzz-T8.log` |

## what this record cannot see (rule 18)

- A seed that AFL skipped silently (empty files) is covered only by the one-shot edge run above.
- The heavy-job check is a process-name heuristic; it cannot see a heavy job it does not match.
- T6's permutation verdict is nondeterministic (seed() reads /dev/urandom; EA_TEST_RANDOM_SOURCE does not reach it).
- A crash here is under Homebrew clang 23 instrumentation; it is not a finding until triage.sh reproduces it under the Apple-clang sanitizer build or the production binary.
- Inputs are capped at -G bytes per target; a defect needing a longer input is out of reach of this campaign.

finished_utc: 2026-11-09T00:12:34Z

Next: `harness/fuzz/triage.sh /private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz` (writes logs/fuzz/TRIAGE.md).
| T6 | plain | 8 | 507 | 0 | 30036 | 62.57 | 210 | 20 | 6 | 72.49% | 23.14% | `logs/fuzz-T6.log` |

## what this record cannot see (rule 18)

- A seed that AFL skipped silently (empty files) is covered only by the one-shot edge run above.
- The heavy-job check is a process-name heuristic; it cannot see a heavy job it does not match.
- T6's permutation verdict is nondeterministic (seed() reads /dev/urandom; EA_TEST_RANDOM_SOURCE does not reach it).
- A crash here is under Homebrew clang 23 instrumentation; it is not a finding until triage.sh reproduces it under the Apple-clang sanitizer build or the production binary.
- Inputs are capped at -G bytes per target; a defect needing a longer input is out of reach of this campaign.

finished_utc: 2026-11-09T00:12:55Z

Next: `harness/fuzz/triage.sh /private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz` (writes logs/fuzz/TRIAGE.md).
| T7 | plain | 8 | 504 | 0 | 27291 | 56.85 | 476 | 6 | 0 | 85.16% | 3.02% | `logs/fuzz-T7.log` |

## T7 fixture integrity

- **FIXTURES CHANGED during T7** -- a vector wrote to an input path. A05 bypass candidate. Diff:
```
1,2c1,2
< f8548a9c84ff53e7e17f6dec7d65e0b1c81aa50b9fdde95b86fb10357214825b  bits-2000.bin
< a32de947d07898c779f0e7f6719ae8bf48512a2d53c52c3140dfe6f355334f75  bytes-2000.bin
---
> 577a145f388ec0186419f5948cc61deb0dbec2eba686efad2d9e68fb6dc7adde  bits-2000.bin
> a428d09821500f35c33f07b081fdac24364ff62d45b1adb86f0a6431bdf3ba4f  bytes-2000.bin
```

## what this record cannot see (rule 18)

- A seed that AFL skipped silently (empty files) is covered only by the one-shot edge run above.
- The heavy-job check is a process-name heuristic; it cannot see a heavy job it does not match.
- T6's permutation verdict is nondeterministic (seed() reads /dev/urandom; EA_TEST_RANDOM_SOURCE does not reach it).
- A crash here is under Homebrew clang 23 instrumentation; it is not a finding until triage.sh reproduces it under the Apple-clang sanitizer build or the production binary.
- Inputs are capped at -G bytes per target; a defect needing a longer input is out of reach of this campaign.

finished_utc: 2026-11-09T00:13:18Z

Next: `harness/fuzz/triage.sh /private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz` (writes logs/fuzz/TRIAGE.md).
