# Sanitizer phase -- RESULTS

Generated 2026-11-08 15:50:27 -0500 by harness/sanitizers/summarize.py from `logs/sanitizers`.
Every verdict below was re-derived from the tool-output region of the log file; the `hdr` column says whether run.sh's own trailer agreed.

## Binaries measured (from BUILD-RECORD.txt)

| variant | tool | sha256 | build exit | smoke exit |
|---|---|---|---|---|
| asan_ubsan | ea_non_iid | `c6350c1d3c9434402122abc54ef242362c285bda0e50c24e957d54f377d52547` | 0 | 0 |
| asan_ubsan | ea_iid | `bebaad509b661a68a8a014007fb3818ea5da255cf8e389f436edd62035ddabcf` | 0 | 0 |
| asan_ubsan | ea_restart | `9f913fd296d6a5be11956f7e8bb77b8e03a62fdb2014ca8906a3aa0cca9dff4e` | 0 | 0 |
| tsan | ea_non_iid | `600839ad54bc5f955873a8797319c89cf8344738e0d418553a36335a1ea22b42` | 0 | 0 |
| tsan | ea_iid | `c59311b28c5a76397d56e2c67d74933494ee6e39ff099d514afadf01119bb143` | 0 | 0 |
| tsan | ea_restart | `072cb7898553adfc5f2a04dda3b8bf63cb6e1c3cc9a075c46ce4078627e54d5f` | 0 | 0 |

- `host=Darwin MacBook-Air.local 25.6.0 Darwin Kernel Version 25.6.0: Fri Jul 31 19:16:20 PDT 2026; root:xnu-12377.161.14~5/RELEASE_ARM64_T8142 arm64 arm Darwin`
- `compiler=Apple clang version 21.0.0 (clang-2100.4.1.1)`
- `libomp=libomp 23.1.2`
- `production_binary=cpp/ea_non_iid sha256_before=1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`
- `production_binary=cpp/ea_iid sha256_before=22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`
- `production_binary=cpp/ea_restart sha256_before=4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`
- `runtime_dylib=/libclang_rt.asan_osx_dynamic.dylib for=asan_ubsan/ea_non_iid sha256=missing`
- `runtime_dylib=/libclang_rt.asan_osx_dynamic.dylib for=asan_ubsan/ea_iid sha256=missing`
- `runtime_dylib=/libclang_rt.asan_osx_dynamic.dylib for=asan_ubsan/ea_restart sha256=missing`
- `runtime_dylib=/libclang_rt.tsan_osx_dynamic.dylib for=tsan/ea_non_iid sha256=missing`
- `runtime_dylib=/libclang_rt.tsan_osx_dynamic.dylib for=tsan/ea_iid sha256=missing`
- `runtime_dylib=/libclang_rt.tsan_osx_dynamic.dylib for=tsan/ea_restart sha256=missing`
- `lsan_supported=no probe_binary=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san/asan_ubsan/ea_non_iid probe_exit=1 probe_log=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san/asan_ubsan/lsan-probe.log probe_output="==32871==AddressSanitizer: detect_leaks is not supported on this platform. "`
- `production_binary=cpp/ea_non_iid sha256_after=1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f unchanged=yes`
- `production_binary=cpp/ea_iid sha256_after=22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349 unchanged=yes`
- `production_binary=cpp/ea_restart sha256_after=4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c unchanged=yes`

## Environment (ENV.txt)

```
# ENV -- written by run.sh at 2026-11-08T20:49:37Z
host=Darwin MacBook-Air.local 25.6.0 Darwin Kernel Version 25.6.0: Fri Jul 31 19:16:20 PDT 2026; root:xnu-12377.161.14~5/RELEASE_ARM64_T8142 arm64 arm Darwin
stages=a force=1 san_dir=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san build_record_sha256=b8c97f62ce6c5200a5d783c8845b0c91e3b89d011a7e7b0ae17ae98ede6b4a0f
lsan_supported_per_build_record=no detect_leaks_used=0
asan_threads=2 tsan_threads=10 timeout_scale=1 ubsan_continue=1 tsan_passive_wait=1
timeout_bin=/opt/homebrew/bin/gtimeout
ASAN_OPTIONS=detect_leaks=0:abort_on_error=1:halt_on_error=1:strict_string_checks=1:detect_stack_use_after_return=1:check_initialization_order=1:strict_init_order=1
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1:report_error_type=1
UBSAN_OPTIONS_continue=print_stacktrace=1:halt_on_error=0:report_error_type=1
TSAN_OPTIONS=halt_on_error=0:second_deadlock_stack=1:history_size=3:print_suppressions=1:suppressions=/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/harness/sanitizers/tsan-libomp.supp
EA_TEST_RANDOM_SOURCE=/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/san/inputs/random-source-1MiB.bin sha256=086ffa536e219367d6d24bdb65276f387defca619590acb93674db149d190ce8 reaches=TestRunUtils.h:478 (-o temporary-file suffix only; permutation seed is /dev/urandom, utils.h:797)
suppressions_sha256=707b3bc207b2f19886100f5a6a9d42ebaee56f24bbd234ef037137bfbf00513e
gen_inputs_sha256=4a061faa33315f5ec61d76ea5f87209bb7caf154273c598cc557bedd0ac51dd8 run_sh_sha256=0022247c39c1384e243f6c228fefb7d98ecd58cbb99cb2e7bb8c4fa0328f4986
```

## Counts

| variant | logs | complete | COMPLETED* | SANITIZER (re-derived) | REFUSED | TIMEOUT | SIGNAL | UNCLASSIFIED | ALIAS | SKIPPED-INPUT | incomplete (killed) | hdr disagreements |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| asan_ubsan | 25 | 25 | 3 | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## What this table cannot see

- a sanitizer report in a format the detector regexes do not match (`==<pid>==ERROR:`, `: runtime error:`, `WARNING: ThreadSanitizer:`, `==<pid>==WARNING: <X>Sanitizer`); a crash that printed nothing is SIGNAL-n, not explained;
- a wrong NUMBER printed by a run that completed cleanly (that is the differential phase's job, not this one's);
- code paths no input reached: the sanitizers instrument the whole binary but report only on executed code; the stage list and the alias/skip columns bound what ran;
- leaks, if `detect_leaks_used=0` in ENV.txt (LeakSanitizer unsupported on this host per BUILD-RECORD);
- under UBSan `halt_on_error=1`, everything after the FIRST recoverable report on an input -- the `.ubsan-continue.log` re-run (listed below) is the only view of the rest;
- for TSan: the happens-before that libomp's uninstrumented barriers and locks establish (see the triage section); and `ea_non_iid`/`ea_restart -n` have no live parallel region, so a clean TSan result there is a control, not coverage;
- EA_ALLOW_SHORT_DATASET=1 rows are non-compliant runs by construction (brief, ground rule 5) -- the `short` column.

## asan_ubsan runs

| stage | tool | input (bytes) | operands | flags | short | heavy | exit | wall s | sanitizer report | #rep | first report line | outcome | hdr | battery | log |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a | ea_iid | rand1_short.bin (10000) | <width inferred by the tool> | -vv | yes | no | 0 | 0 | no | 0 | - | COMPLETED | agrees | not-seen (0 progress lines) | `asan_ubsan/ea_iid-rand1_short.vv.log` |
| a | ea_iid | rand4_short.bin (10000) | <width inferred by the tool> | -vv | yes | no | 1 | 1 | no | 0 | - | COMPLETED-IID-BATTERY-FAILED | agrees | not-seen (0 progress lines) | `asan_ubsan/ea_iid-rand4_short.vv.log` |
| a | ea_iid | rand8_short.bin (10000) | <width inferred by the tool> | -vv | yes | no | 1 | 0 | no | 0 | - | COMPLETED-IID-BATTERY-FAILED | agrees | skipped-after-required-test-failure (0 progress lines) | `asan_ubsan/ea_iid-rand8_short.vv.log` |
| a | ea_non_iid | biased-random-bits.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 0 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-biased-random-bits.selftest-vv.log` |
| a | ea_non_iid | biased-random-bytes.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 2 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-biased-random-bytes.selftest-vv.log` |
| a | ea_non_iid | data.pi.bin (1165666) | <width inferred by the tool> | -vv | no | yes | 134 | 1 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-data.pi.selftest-vv.log` |
| a | ea_non_iid | normal.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 2 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-normal.selftest-vv.log` |
| a | ea_non_iid | rand1_short.bin (10000) | <width inferred by the tool> | -vv | yes | no | 134 | 1 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-rand1_short.selftest-vv.log` |
| a | ea_non_iid | rand4_short.bin (10000) | <width inferred by the tool> | -vv | yes | no | 134 | 0 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-rand4_short.selftest-vv.log` |
| a | ea_non_iid | rand8_short.bin (10000) | <width inferred by the tool> | -vv | yes | no | 134 | 0 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-rand8_short.selftest-vv.log` |
| a | ea_non_iid | ringOsc-nist.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 1 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-ringOsc-nist.selftest-vv.log` |
| a | ea_non_iid | truerand_1bit.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 0 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-truerand_1bit.selftest-vv.log` |
| a | ea_non_iid | truerand_4bit.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 1 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-truerand_4bit.selftest-vv.log` |
| a | ea_non_iid | truerand_8bit.bin (1000000) | <width inferred by the tool> | -vv | no | yes | 134 | 2 | yes | 1 | non_iid/lag_test.h:111:21: runtime error: implicit conversion from type 'int' of value 256 (32-bit, signed) to type 'uint8_t' (aka 'unsigned | SANITIZER | agrees |  | `asan_ubsan/ea_non_iid-truerand_8bit.selftest-vv.log` |

## UBSan continue passes (halt_on_error=0; every recoverable report on that input)

| re-run of | exit | wall s | #reports | UBSan kinds | outcome | log |
|---|---|---|---|---|---|---|
| ea_non_iid-biased-random-bits.selftest-vv.log | 0 | 0 | 3 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-biased-random-bits.selftest-vv.ubsan-continue.log` |
| ea_non_iid-biased-random-bytes.selftest-vv.log | 0 | 10 | 3 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-biased-random-bytes.selftest-vv.ubsan-continue.log` |
| ea_non_iid-data.pi.selftest-vv.log | 0 | 0 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-data.pi.selftest-vv.ubsan-continue.log` |
| ea_non_iid-normal.selftest-vv.log | 0 | 9 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-normal.selftest-vv.ubsan-continue.log` |
| ea_non_iid-rand1_short.selftest-vv.log | 0 | 0 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-rand1_short.selftest-vv.ubsan-continue.log` |
| ea_non_iid-rand4_short.selftest-vv.log | 0 | 0 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-rand4_short.selftest-vv.ubsan-continue.log` |
| ea_non_iid-rand8_short.selftest-vv.log | 0 | 0 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-rand8_short.selftest-vv.ubsan-continue.log` |
| ea_non_iid-ringOsc-nist.selftest-vv.log | 0 | 0 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-ringOsc-nist.selftest-vv.ubsan-continue.log` |
| ea_non_iid-truerand_1bit.selftest-vv.log | 0 | 1 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-truerand_1bit.selftest-vv.ubsan-continue.log` |
| ea_non_iid-truerand_4bit.selftest-vv.log | 0 | 8 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-truerand_4bit.selftest-vv.ubsan-continue.log` |
| ea_non_iid-truerand_8bit.selftest-vv.log | 0 | 10 | 2 | implicit-signed-integer-truncation | SANITIZER | `asan_ubsan/ea_non_iid-truerand_8bit.selftest-vv.ubsan-continue.log` |

## ThreadSanitizer report triage

Construct line ranges derived from the source when this file was generated (check them by eye against `cpp/`):

| file | kind | name | lines |
|---|---|---|---|
| iid/permutation_tests.h | parallel | - | 625-729 |
| iid/permutation_tests.h | for | - | 651-726 |
| iid/permutation_tests.h | critical | resultUpdate | 661-680 |
| iid/permutation_tests.h | critical | verboseOutput | 714-718 |
| iid/permutation_tests.h | atomic | - | 722-723 |
| restart_main.cpp | parallel | - | 307-319 |
| restart_main.cpp | for | - | 315-318 |

No ThreadSanitizer report in any tsan log (or the tsan stage has not run).

## Aliases (byte-identical input at the same width and flags; run once)

none

