# Executed-check ledger

Full stdout/stderr and explicit exit markers are in `logs/`. Paths below use
the detached audit worktree root
`/tmp/sp80090b-audit-20261009.5WcSLl`; generated data was not added to Git.

| Area | Command/check | Result / log |
|---|---|---|
| Repository state | `git status`, branch, remotes, SHA, merge-base and left/right count after fetching origin/upstream | Baseline recorded in `BASELINE.md` |
| Instructions/evidence | Read README, BUILDING, NOTICE, audit guide/tracker, historical reports, complete 2026-10-01 re-audit summaries and required evidence | Exclusion/regression maps |
| Upstream discussions | Retrieved issue and comment JSON for relevant historical issues; inspected source and Git refs | `logs/upstream/*.json`; rate limit left newest retrieval incomplete, existing local discussion archive cross-checked |
| Release build | `make clean`; `make non_iid iid restart` | exit 0, `logs/build-supported.log` |
| Strict suite | `cpp/selftest/run-all-checks.sh` | exit 1, 15 pass/1 fail, `logs/run-all-strict.log` |
| Delta suite | `cpp/selftest/run-all-checks.sh --allow-known-platform-deltas` | exit 0, 16 pass, `logs/run-all-platform-deltas.log` |
| Wrapper mutation | Temporarily remove one supported binary in disposable worktree and run wrapper | exit 2, `logs/wrapper-missing-binary.log` |
| Fixture-count mutation | Isolated 11-pair then 10-pair corpus with always-successful controlled comparator | both exit 0, `logs/selftest-missing-fixture.log` |
| Fixture generation | `generators/valid_fixtures.py /tmp/.../fixtures` | hashes/counts in `logs/fixture-manifest.json` |
| Non-IID battery | `ea_non_iid -q -o RESULT FIXTURE WIDTH` over constant, near-constant, bias, uniform, alternating, periodic, Markov, drift, sparse, width4/8 | `logs/valid/non-iid-battery.log`, JSON under `logs/valid/` |
| Every supported width | Explicit-width non-IID runs at 1M symbols for widths 2..8 (width 1 is in the main battery) | all exit 0; `logs/valid/supported-widths.log` and `width2.json` … `width8.json` |
| Width harness attempt | First width-loop wrapper used zsh's read-only variable name `status` | stopped after width 2; preserved as `logs/valid/supported-widths-attempt1.log`; corrected wrapper above completed |
| Repeated block | same, 1M-sample repeated 4096 block | exit 0, `logs/valid/repeated-block.log` |
| Valid subset | `ea_non_iid -l 1,1000000 ... 1` on 2M source | exit 0, `logs/valid/subset-second.log` |
| Bad subset control | `-l 1000000,1000000` under block-index semantics | exit 255, retained in battery log |
| Conditioned modes | `ea_non_iid -c -t` and `-c -a` on 1M 8-bit symbols | exit 0, `logs/valid/conditioned-truncated.json`, `conditioned-all.json`, and `conditioned-all.log` |
| MCV oracle | `oracles/mcv_oracle.py` plus tool MCV extraction | constant analytic check, worked-example calculation, exact full-quantile tool match; `logs/oracle-mcv-*.json`, `logs/oracle-mcv-worked-example.log`, `logs/oracle-mcv-compare.log` |
| Release IID control | `ea_iid -q -o ... uniform-1bit.bin 1` | exit 0/pass, `logs/release-iid-valid-uniform.log` |
| ASan IID control | same with ASan/UBSan binary | exit 0/pass, `logs/asan-iid-valid-uniform.log` |
| IID dependent case | `ea_iid` on valid 1M alternating data | known #153 assertion, exit 6, `logs/iid-valid-alternating-known-252.log` |
| IID drift case | `ea_iid` on valid 1M drift data | interrupted after 10 minutes, no result, `logs/iid-valid-drift-known-252.log` |
| Restart valid control | `ea_restart -n ... 1 .8` on 1000×1000 software-uniform matrix | exit 0, `logs/restart-valid-random.log` |
| Restart IID valid control | `ea_restart -i ... 1 .8` on the same 1000×1000 matrix | successful errorLevel-0/IID report; all required tests pass; `logs/restart-valid-uniform-iid.log`, `logs/valid/restart-uniform-iid.json` |
| Restart negative control | `ea_restart -n ... 1 1` on 1000×1000 periodic matrix | sanity rejection/exit 255, `logs/restart-valid-periodic-reject.log` |
| Sanitizer build | clean build of all three with ASan/UBSan; retry adds libomp include | first config failure then exit 0, `logs/build-asan-ubsan.log` |
| ASan non-IID valid | uniform 1M case | clean/exit 0, `logs/asan-noniid-valid.log` |
| ASan restart valid | uniform 1000×1000 case | existing C-01 mismatch/exit 6, `logs/asan-known-c01.log` |
| Bounded invalid fuzz | lengths 0,1,2,3,4,16,4095,999999; non-IID/IID widths 1/8; restart | 40 expected rejections, `logs/asan-invalid-input-bounded.log` |
| Assertions disabled | Built all three with `-O2 -DNDEBUG`; ran valid non-IID/IID/restart and 10K-sample rejection controls | build/pass and three status-255 rejections; `logs/build-ndebug.log`, `ndebug-valid-controls.log`, `ndebug-short-rejection.log`, `ndebug-comparison.json` |
| Assertions-disabled IID edge | `ea_iid` on valid 1M alternating data with `-DNDEBUG` | crossed known #153 assertion point, emitted underflow, interrupted after 10m08s without JSON; `logs/ndebug-iid-alternating-known-153.log`, `logs/ndebug-iid-alternating-status.txt` |
| Static analysis | Apple clang analyzer over three supported mains | exit 0, dead stores only, `logs/clang-static-analyzer.log` |
| OpenMP | non-IID canonical JSON at thread counts 1 and 8 | byte-identical, `logs/openmp-reproducibility.log` |
| Dynamic dependencies | `otool -L`, Homebrew formula/version/license inspection | `logs/dependencies.json` |
| TruePad tests | targeted Vitest qualification, Toeplitz, extractor, seed, and pre-RNG suites | 10 files/71 tests pass, `logs/truepad-targeted-tests.log` |
| TruePad substitution | `reproducers/truepad-unattested-tools.mjs` against exact clean upstream worktree | exit 0 false qualification, `logs/truepad-unattested-tools.log` |
| TruePad positive control | real fork `ea_non_iid` on identical period-two assessment | entropy zero/exit 0, `logs/truepad-spoof-real-tool-control.log` |
| Delivered rerun-script validation | Started `rerun.sh` without TruePad; build completed and strict suite reached full conditioned IID regression | manually interrupted after ten minutes during this duplicate expensive path; no result inferred; interrupt cleanup verified |
| Final report seal | Refetched remotes; rechecked SHAs/status, all JSON, script syntax, executable bits, evidence references, whitespace, and exclusion-map completeness | all checks pass; `logs/final-verification.txt` |

An initial attempt to use LeakSanitizer was rejected by the macOS runtime as
unsupported and was not counted as a passing check. No result is inferred from
the deliberately interrupted IID drift run.
The delivered rerun script passed JSON/shell/Node syntax checks. Its component
build and strict commands are the same already completed above; the duplicate
end-to-end validation was not misreported as another suite result.
