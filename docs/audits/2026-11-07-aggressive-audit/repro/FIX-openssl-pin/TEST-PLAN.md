# FIX-openssl-pin -- test plan for the orchestrator

Finding: PROV-15 (`repro/PROV-15/`, `logs/analysis/cli-build.md` 5.2, 6.1-6.2).
Branch: `fix/openssl-pin`, created from master `04c1ccc`, in the worktree
`/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-2`.
Written 2026-11-08 WITHOUT building or running make (heavy slot busy); everything
below that needs a build is for the orchestrator to run, one heavy job at a time.

What changed: `cpp/Makefile` Darwin block -- the pinned `$(OPENSSL_PREFIX)` -I/-L now
precede the generic `$(BREW_PREFIX)` -I/-L. New `cpp/selftest/regression-openssl-pin.sh`;
inventory + counts bumped (25 scripts / 27 checks); CLOSING-INVENTORY.md and
WHAT-A-GREEN-SUITE-ESTABLISHES.md counts follow; NOTICE entry; x86-64 CI gate now
expects two named abstentions on Linux (`regression-openssl-pin regression-platform-deltas`).

All paths below: `WT=/Users/gmcas/repos/SP800-90B_EntropyAssessment/.claude/worktrees/wf_5c2ce2eb-d82-2`,
`SCR=<a scratch dir>`, `MAIN=/Users/gmcas/repos/SP800-90B_EntropyAssessment`.
Write every output to a file and read the file (rule 17); never pipe a tool into head/tail.

## 1. Build lines (from BUILD-LINES.md; `-o` into scratch; run from the worktree's `cpp/`)

Master's binary -- BUILD-LINES.md's line exactly, which IS the defective order
(generic prefix first on -I and -L). Build it from master's sources so it is master's binary:

```sh
git -C "$MAIN" worktree add "$SCR/master-src" master      # or any checkout of 04c1ccc
cd "$SCR/master-src/cpp" && clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
  -I/opt/homebrew/opt/openssl@3/include non_iid_main.cpp -o "$SCR/master-bin/ea_non_iid" \
  -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto > "$SCR/build-master.log" 2>&1; echo "rc=$?" >> "$SCR/build-master.log"
```

(Alternatively skip this build: `$MAIN/cpp/ea_non_iid`, `ea_iid`, `ea_restart` -- sha256
`1ad1568c..`, `22f1319a..`, `4d7ba82b..`, built 2026-11-07 19:28 from this same line -- ARE
master's binaries and already load `libcrypto.4.dylib`. Use `REGRESSION_OPENSSL_PIN_BINDIR=$MAIN/cpp`.)

The fixed binary -- the same line with the two pairs swapped, which is what the fixed
Makefile prints. CONFIRM the order first from the fixed Makefile's own dry-run, read from a file:

```sh
( cd "$WT/cpp" && make -n non_iid ) > "$SCR/dryrun-fixed.txt" 2>&1; echo "rc=$?" >> "$SCR/dryrun-fixed.txt"
grep -n 'openssl@3/include -I/opt/homebrew/include' "$SCR/dryrun-fixed.txt"   # must hit
grep -n 'openssl@3/lib -L/opt/homebrew/lib'         "$SCR/dryrun-fixed.txt"   # must hit
cd "$WT/cpp" && clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/opt/openssl@3/include \
  -I/opt/homebrew/include non_iid_main.cpp -o "$SCR/fixed-bin/ea_non_iid" \
  -L/opt/homebrew/opt/openssl@3/lib -L/opt/homebrew/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto > "$SCR/build-fixed.log" 2>&1; echo "rc=$?" >> "$SCR/build-fixed.log"
otool -L "$SCR/fixed-bin/ea_non_iid" > "$SCR/otool-fixed.txt"     # expect .../opt/openssl@3/lib/libcrypto.3.dylib
shasum -a 256 "$SCR/fixed-bin/ea_non_iid" "$SCR/master-bin/ea_non_iid" > "$SCR/sha.txt"   # instrument rule 4
```

Build `ea_iid`/`ea_restart` the same way only if wanted; the test reports an absent binary as
"not built here; not measured" and still passes on the ones present.

## 2. Show the regression test FAILING against master, PASSING against the fix

```sh
cd "$WT/cpp/selftest"
git -C "$WT" show master:cpp/Makefile > "$SCR/Makefile.master"

# A. master's Makefile text + master's binaries  -> exit 1, FAIL (5):
#    "-I: ... generic at token 9, pinned at 10", "-L: ... generic at token 14, pinned at 15",
#    and each binary "loads /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib; the pin is /opt/homebrew/opt/openssl@3"
REGRESSION_OPENSSL_PIN_MAKEFILE="$SCR/Makefile.master" REGRESSION_OPENSSL_PIN_BINDIR="$MAIN/cpp" \
  ./regression-openssl-pin.sh > "$SCR/A-master.out" 2>&1; echo "rc=$?" >> "$SCR/A-master.out"

# B. the fixed Makefile + master's binaries -> exit 1, FAIL (3): the text half passes, the binary half catches the relink
REGRESSION_OPENSSL_PIN_BINDIR="$MAIN/cpp" \
  ./regression-openssl-pin.sh > "$SCR/B-fixedtext-masterbin.out" 2>&1; echo "rc=$?" >> "$SCR/B-fixedtext-masterbin.out"

# C. the fixed Makefile + the fixed binary -> exit 0, "regression-openssl-pin: PASS"
REGRESSION_OPENSSL_PIN_BINDIR="$SCR/fixed-bin" \
  ./regression-openssl-pin.sh > "$SCR/C-fixed.out" 2>&1; echo "rc=$?" >> "$SCR/C-fixed.out"
```

Read `$SCR/A-master.out`, `B-...out`, `C-fixed.out` and the `rc=` line in each. In every arm the
four "PAIR d240098: ... is on the line once" lines must PASS (rule 7: the baseline the earlier
repair installed is shown accepted; rule 12: the pair is exercised). The `[build-state]` lines
must say `asserts=LIVE` (the 2026-11-08 seam runs said UNKNOWN only because a `cc` shim stopped
the calibration from compiling).

## 3. What else to run

- `cd "$WT/cpp/selftest" && ./run-all-checks.sh --allow-known-platform-deltas > "$SCR/suite.out" 2>&1`
  -- expect `27 passed, 0 failed (25 regression scripts discovered)` ONLY once the binaries the
  suite reads (`$WT/cpp/ea_*`) are built from the fixed Makefile. Against binaries that load
  openssl@4 the member FAILS by design. The brief forbids overwriting `$MAIN/cpp/ea_*` during
  the audit; build in the worktree's `cpp/` or wait for the owner's rebuild.
- Read the `build-state:` line of that run. WHAT-A-GREEN-SUITE-ESTABLISHES.md now says
  `6 of 27` (5 of 26 measured 2026-10-27 plus this member, which declares via `bs_print`); if the
  measured line differs, correct the document to the measured value and date it.
- `./regression-docs.sh > "$SCR/docs.out" 2>&1` -- the derived counts (inventory 25, total 27,
  CLOSING-INVENTORY rows 9 of 9, pair sweep 12 = 12, scope denominators) were replicated by grep
  on 2026-11-08 but the script itself was not run (it runs `make -Bn`).
- `./harness-inventory-mutation-test.sh` -- expect `5 of 5`; it derives its summary from the new counts.
- `./regression-workflows.sh` -- needs PyYAML (absent on this host, exit 2 here); the 12 run:
  blocks of the edited x86-64 workflow were `bash -n`'d directly on 2026-11-08, 12 of 12 OK.
- The x86-64 CI workflow on this branch must show `N-2 passed, 0 failed, 2 could not run` and
  `could-not-run: regression-openssl-pin regression-platform-deltas`.
- Optional confirmation of PROV-15 6.3c: `-vv` on any fixture with the fixed binary; the printed
  SHA-256 must equal `shasum -a 256` of the input (the only OpenSSL-dependent output).

## Observed 2026-11-08 without a build (seam runs; `cc` shim, so nothing compiled)

| arm | dry-run text | binaries | exit | verdict |
|---|---|---|---|---|
| a | master's line (BUILD-LINES.md) | none | 1 | FAIL (2): -I and -L order; PAIR tokens 4/4 PASS |
| b | fixed line | `$MAIN/cpp` (1ad1568c.., 22f1319a.., 4d7ba82b..) | 1 | FAIL (3): each loads openssl@4 |
| c | fixed line | 2026-10-20 `ea_conditioning` (b7a55528..) as ea_non_iid | 0 | PASS: loads openssl@3 |
| d | fixed line | -- (`uname` shim -> Linux) | 2 | COULD NOT RUN, reason printed |
| e | fixed line | none | 2 | text passed, nothing measured |
| f | master's line | `$MAIN/cpp` | 1 | FAIL (5) |

Outputs: `/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/pin/*.out` (session-scoped scratch; copy if wanted).

This file was written at the worktree copy of the requested path because the fix agent's
sandbox refuses writes outside its worktree; copy it to
`/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/FIX-openssl-pin/TEST-PLAN.md`.
It is not part of the fix commit (the audit directory is not tracked).
