# RUN-RECORD -- AFL++ campaign, 2026-11-07 aggressive audit

- started_utc: 2026-11-08T23:38:03Z
- fuzz_dir: `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/fuzz`
- host: arm64 26.6.2; 10 CPUs; 16 GB; load { 5.27 13.86 20.77 }
- afl: afl-fuzz++5.03c
- kern.sysv.shmmax: 4194304; AFL_MAP_SIZE for T7: 65536
- AFL runtime per binary (AFL_DUMP_MAP_SIZE probe): plain/ea_non_iid=map:2644 plain/ea_iid=map:3189 plain/ea_restart=map:4492
- ReportCrash loaded: yes (AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 set; crash handling is slower; consider: launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportCrash.plist)
- per-target cap: 8 min; targets: T1 T2 T3 T4 T5 T6 T7 T8; variant override: plain
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
T1  ea_non_iid  -i -a @@                 w8    plain   8      16384  2000+  initial estimate, width INFERRED from the data (utils.h:458-470): the ...
T2  ea_non_iid  -i -a @@ 8               w8    plain   8      16384  2000+  declared 8 bits: no refusal possible on width, every byte value legal;...
T3  ea_non_iid  -i -a @@ 1               w1    plain   8      16384  2000+  declared 1 bit: the binary path (no H_bitstring), plus the 'wider than...
T4  ea_non_iid  -c -a @@ 8               w8    plain   8      16384  2000+  conditioned (-c) view: bitstring estimators only, h' path (non_iid_mai...
T5  ea_non_iid  -l 1,17 -i @@            w8    plain   8      16384  2000+  subset arithmetic (utils.h:363-405): offset 17, files <= 17 bytes refu...
T6  ea_iid      -i -a @@ 4               w4    plain   8      4096   5000+  IID battery at declared 4 bits: chi-square, LRS, 10,000-permutation te...
T7  argv_driver @@                       argv  plain   8      1024   5000+  argv fuzzer: one token per line, optional first line N|I|R picks the t...
T8  ea_restart  -n @@ 8 0.5/symbol       w8    plain   8      16384  2000+  ea_restart's SEPARATE intake copy read_file (utils.h:549-735) and the ...
total fuzz minutes: 64 (plus ~1 min start-up per target; -V counts fuzz time only)
```

## seeds check

```
checked 216 manifest rows against disk and generator: 0 problem(s)
```

## pre-flight (baseline accepted, instrument live, every seed run once, edge cases)

### T1 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'min(H_original, 8 X H_bitstring): 3.421437'
- instrumentation: afl-showmap tuples = 526
- seeds run once: 29 seeds: 25 assessed (exit 0), 4 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T1/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T1-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

### T2 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'min(H_original, 8 X H_bitstring): 3.421437'
- instrumentation: afl-showmap tuples = 535
- seeds run once: 29 seeds: 25 assessed (exit 0), 4 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T2/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T2-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

### T3 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'H_original: 0.074168'
- instrumentation: afl-showmap tuples = 400
- seeds run once: 28 seeds: 22 assessed (exit 0), 6 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T3/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T3-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

### T4 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'h': 0.432425'
- instrumentation: afl-showmap tuples = 402
- seeds run once: 29 seeds: 25 assessed (exit 0), 4 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T4/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T4-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

### T5 (ea_non_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'min(H_original, 8 X H_bitstring): 1.919436'
- instrumentation: afl-showmap tuples = 490
- seeds run once: 29 seeds: 14 assessed (exit 0), 15 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T5/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T5-seeds.log`
- edge: empty.bin rc=255 (expected 255); refused as past-end (utils.h:385; the expected refusal under -l, which runs before the empty check)
- pre-flight: OK

### T6 (ea_iid, plain)

- baseline (`rnd-00064.bin`): rc=0 (expected 0); last stdout line: 'min(H_original, 4 X H_bitstring): 2.246999'
- instrumentation: afl-showmap tuples = 547
- seeds run once: 29 seeds: 7 assessed (exit 0), 5 refused (exit 255), 10 exited by SIGNAL (input + stderr + stdout copied to `out/T6/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T6-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

### T7 (argv_driver, plain)

- baseline (`basic-i-a-8.txt`): rc=0 (expected 0); last stdout line: 'H_original: 0.719564'; driver print-mode matched; slash-token negative control: REJECTED two or more slashes in token (path-shaped): /etc/passwd
- instrumentation: afl-showmap tuples = 404
- seeds run once: 66 seeds: 20 assessed (exit 0), 46 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T7/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T7-seeds.log`
- edge: n/a
- pre-flight: OK

### T8 (ea_restart, plain)

- baseline (`rnd-00064.bin`): rc=255 (expected 255); last stdout line: ''
- instrumentation: afl-showmap tuples = 119
- seeds run once: 29 seeds: 0 assessed (exit 0), 29 refused (exit 255), 0 exited by SIGNAL (input + stderr + stdout copied to `out/T8/seed-crashes/`; triage.sh re-runs them), 0 hit the 30 s cap; per-seed status in `logs/fuzz-preflight-T8-seeds.log`
- edge: empty.bin rc=255 (expected 255); the 'is empty' refusal line is present
- pre-flight: OK

## campaign

NOT RUN: --preflight-only. Targets that would have been skipped: none.

finished_utc: 2026-11-08T23:38:10Z
