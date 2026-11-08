# RUN-RECORD -- AFL++ campaign, 2026-11-07 aggressive audit

- started_utc: 2026-11-08T23:47:00Z
- fuzz_dir: `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz`
- host: arm64 26.6.2; 10 CPUs; 16 GB; load { 38.60 23.49 22.71 }
- afl: afl-fuzz++5.03c
- kern.sysv.shmmax: 4194304; AFL_MAP_SIZE for T7: 65536
- AFL runtime per binary (AFL_DUMP_MAP_SIZE probe): plain/ea_non_iid=map:2644 plain/ea_iid=map:3189 plain/ea_restart=map:4492
- ReportCrash loaded: yes (AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 set; crash handling is slower; consider: launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportCrash.plist)
- per-target cap: 8 min; targets: T3; variant override: plain
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
T3  ea_non_iid  -i -a @@ 1               w1    plain   8      16384  2000+  declared 1 bit: the binary path (no H_bitstring), plus the 'wider than...
total fuzz minutes: 8 (plus ~1 min start-up per target; -V counts fuzz time only)
```

## seeds check

```
checked 216 manifest rows against disk and generator: 0 problem(s)
```

## pre-flight (baseline accepted, instrument live, every seed run once, edge cases)

### T2 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'min(H_original, 8 X H_bitstring): 3.421437'
- instrumentation: afl-showmap tuples = 534
- seeds run once: 29 seeds: 25 assessed (exit 0), 4 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T2/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T2-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

## campaign

| T | variant | minutes | wall s | afl rc | execs | execs/s | corpus | crashes | hangs | stability | map cvg | log |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
### T3 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'H_original: 0.074168'
- instrumentation: afl-showmap tuples = 400
- seeds run once: 28 seeds: 22 assessed (exit 0), 6 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T3/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T3-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

## campaign

| T | variant | minutes | wall s | afl rc | execs | execs/s | corpus | crashes | hangs | stability | map cvg | log |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T3 | plain | 8 | 481 | 0 | 117198 | 244.14 | 273 | 0 | 0 | 100.00% | 22.47% | `logs/fuzz-T3.log` |

## what this record cannot see (rule 18)

- A seed that AFL skipped silently (empty files) is covered only by the one-shot edge run above.
- The heavy-job check is a process-name heuristic; it cannot see a heavy job it does not match.
- T6's permutation verdict is nondeterministic (seed() reads /dev/urandom; EA_TEST_RANDOM_SOURCE does not reach it).
- A crash here is under Homebrew clang 23 instrumentation; it is not a finding until triage.sh reproduces it under the Apple-clang sanitizer build or the production binary.
- Inputs are capped at -G bytes per target; a defect needing a longer input is out of reach of this campaign.

finished_utc: 2026-11-08T23:55:04Z

Next: `harness/fuzz/triage.sh /private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz` (writes logs/fuzz/TRIAGE.md).
| T2 | plain | 8 | 486 | 0 | 21465 | 44.69 | 463 | 0 | 2 | 99.64% | 31.09% | `logs/fuzz-T2.log` |

## what this record cannot see (rule 18)

- A seed that AFL skipped silently (empty files) is covered only by the one-shot edge run above.
- The heavy-job check is a process-name heuristic; it cannot see a heavy job it does not match.
- T6's permutation verdict is nondeterministic (seed() reads /dev/urandom; EA_TEST_RANDOM_SOURCE does not reach it).
- A crash here is under Homebrew clang 23 instrumentation; it is not a finding until triage.sh reproduces it under the Apple-clang sanitizer build or the production binary.
- Inputs are capped at -G bytes per target; a defect needing a longer input is out of reach of this campaign.

finished_utc: 2026-11-08T23:55:09Z

Next: `harness/fuzz/triage.sh /private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz` (writes logs/fuzz/TRIAGE.md).
