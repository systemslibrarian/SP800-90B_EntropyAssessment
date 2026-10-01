# Known #242 — confirmed source defect; sanitizer defaults differ

Do not assign a new ASTRA identifier. This allocation/deallocation mismatch was explicitly recorded in the prior repository audit: novel-findings/REPORT.md known-item list, and agent-reports/restart.md sanitizer qualifications and excluded-known-items table. Their existing reports were read, not rewritten.

## Source

Historical `34fb906196f8d47da774c88928eff0d8ec08d618`, unchanged at recorded current `328ec20c146e43b4eed86424847a106539c70a5a`:

- cpp/restart_main.cpp, simulateBound: line 124 allocates `new uint16_t[simulation_rounds]`.
- Line 161 frees the array with scalar `delete results`.
- The complete function was read. Normal valid input reaches it through main at line 479.

## Fresh observed sanitizer behavior

Build: native macOS arm64, Apple clang 21, `-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`, normal Homebrew OpenMP/includes/libraries. Two threads. No source changes to the function or full CLI. Linux GCC ASan is locally blocked by cgroup OOM before even a trivial main (probe 027); that does not refute a native Linux result.

| Probe | Scope/settings | Observed result |
|---|---|---|
| 072 | Direct unchanged function, 64 diagnostic rounds; ASAN/LSAN/UBSAN options unset | exits 0; no mismatch report |
| 073 | Identical direct call; only `ASAN_OPTIONS=alloc_dealloc_mismatch=1` | aborts SIGABRT (runner -6), exact new[]/delete mismatch, allocation/deallocation lines 124/161 |
| 074 | **Full original CLI, default 5,000,000 rounds**, public truerand_8bit, H_I=3.2; sanitizer options unset | exit 0, full validation passes, no ASan/UBSan diagnostics, 29.209 s |
| 075 | Same full CLI/default rounds and fixture; only mismatch check explicitly enabled | aborts SIGABRT at simulateBound:161, 13.291 s; ASan identifies full 10,000,000-byte allocation from line 124 |

Thus default macOS sanitizer execution does not diagnose this known mismatch, while explicitly enabling the check does, including on the unchanged full valid-input CLI path. The direct 64-round test is only a bounded function-memory check, **not** a replacement for the full simulation or an entropy assessment; the separate full 5,000,000-round probes remove any ambiguity about CLI reachability. No mismatch suppression or reduced CLI simulation was used to obtain a successful result.

## Meaning of historical qualified runs

The prior audit explicitly used `alloc_dealloc_mismatch=0` for later cleanup/assessment paths, and its reduced-round diagnostic copy is disclosed in agent-reports/restart.md. The interrupted review brief additionally says leak checking was unavailable/disabled. Such runs can support only absence of the **enabled** diagnostics on the **executed** later paths. They do not test the suppressed mismatch, establish leak freedom, validate unexecuted paths, or make the whole program unqualified sanitizer-clean. The current native default clean-output run likewise is not proof that the mismatch is repaired.

Evidence: logs/070–075, restart_allocation_harness.cpp, restart_asan_build.py, hash-results/native-restart-default-asan.json, source hashes in hash-evidence-analysis.json, prior immutable repository audit files. No timeout in this known-issue batch. Current status: known defect remains, with platform-specific default detector behavior explicitly recorded.