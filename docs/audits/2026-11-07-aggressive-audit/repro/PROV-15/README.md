# PROV-15 -- OpenSSL pin defeated by include/link order: production binaries link libcrypto.4 from openssl@4, not the pinned openssl@3

**Provisional ID:** PROV-15 (AA-NN to be assigned by the orchestrator)
**Severity (provisional, brief's scale):** MEDIUM (nondeterministic build input: the same Makefile on the same host produced a different dependency on a different day; the pin and BUILDING.md are false for the binaries in cpp/)
**Direction:** nondeterministic (build input); no estimator figure moves (OpenSSL is used only for the SHA-256 of the assessed bytes)
**Component:** cpp/Makefile:70-72 (`INC += -I$(BREW_PREFIX)/include -I$(OPENSSL_PREFIX)/include`, `LDFLAGS += -L$(BREW_PREFIX)/lib -L$(OPENSSL_PREFIX)/lib`: the generic prefix precedes the pinned one on both); BUILDING.md:55 pin table and :61 build line.
**Spec:** n/a (build determinism).
**Prior-fix interaction (rule 12):** OC-121 (b53ff5d) last touched the Makefile; BUILDING.md's dependency table is the pin; pin-check.sh / buildstate-lib.sh (instrument rule 4, build state) do not record `otool -L`. Explains the ea_non_iid sha256 change b61cf8c7.. -> 1ad1568c.. with no source change (cli-build.md 6.2 candidate 1, CERTAIN).
**Analysis-phase source (re-checked here):** logs/analysis/cli-build.md 5.2, 6.1-6.2 and 9.4 (MEASURED: otool -L, Homebrew receipts, symlink mtimes).
**Platform:** Darwin 25.6.0 arm64, Apple clang 21 (this host); production binaries built 2026-11-07 19:28-19:29 from branch audit/2026-11-07 (HEAD 1151b22 at run time). Nothing else measured.

## Status

REPRODUCED: otool -L on ea_non_iid, ea_iid, ea_restart -> /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib (3 of 3 not the pinned prefix); /opt/homebrew/include/openssl and /opt/homebrew/lib/libcrypto.dylib -> Cellar/openssl@4/4.1.0 (symlinks dated Nov 7 19:28; receipt 19:28; binaries 19:28-19:29). Control: cpp/ea_conditioning (2026-10-20, same Makefile) -> /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib; the pinned lib exists at /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib.

**What this reproducer does not establish:** Whether the openssl@4 relink changed any REPORTED value (the sha256 field) is not measured here; regression-input-identity.sh / regression-subset.sh compare it to shasum and are the check (cli-build.md 6.3c). An out-of-tree rebuild with the pinned -I/-L first is the confirming experiment and is a build (not this phase).

## Files

- `run.sh` -- the reproducer: builds the tiny input if needed, runs the production binary with the exact command and env, writes `observed.txt` and its outputs under `out/`, prints `RESULT: PASS` when the defect IS present (exit 0), `FAIL` (exit 1) otherwise, `NOT-RUN` (exit 3) when it is heavy/excluded and the gate variable is unset.
- `control.sh` -- the negative control (rule 7: a minimal mutation of the same command/input that does NOT show the defect); writes `control.txt`; prints `RESULT: CONTROL-OK` (exit 0) when the control behaves as the design says.
- `expected.txt` -- what correct behaviour would print, with the arithmetic or the quoted spec text.
- `../_lib.sh` -- shared helpers (binary sha256 recording, labelled JSON reads, env `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2`).
- Copies of the two records are also written to `../../logs/repro/PROV-15-observed.log` and `PROV-15-control.log`.

## Measured 2026-11-07 (one run each; instrument rule 4)

| script | exit code | meaning |
|---|---|---|
| `run.sh` | 0 | 0 = PASS (defect present) |
| `control.sh` | 0 | 0 = CONTROL-OK (defect absent in the control) |

Binaries (sha256):
- `b7a55528a8270672a89bd26265feb529293718a83d2a19a350cd035289d83460 (built 2026-10-20, STALE against cpp/shared/TestRunUtils.h; not run)`  ea_conditioning
- `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`  ea_iid
- `1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f`  ea_non_iid
- `4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c`  ea_restart

Every tool run used `EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2` and is NOT a compliant SP 800-90B assessment (brief ground rule 5); the inputs are <= 20,000 samples unless the script is marked HEAVY.

### observed.txt (verbatim)

```
# PROV-15 observed.txt  2026-11-07 21:56:18 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
binary sha256 22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_iid  (mtime 2026-11-07 19:28:52)
binary sha256 4d7ba82b43ce03d02a83c5eb08712e5be7c80154515c9ee9d8da1fbdb468419c  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_restart  (mtime 2026-11-07 19:29:04)
pinned prefix (brew --prefix openssl@3): /opt/homebrew/opt/openssl@3 ; pinned lib present: /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib
Makefile order:
  Makefile:70:OPENSSL_PREFIX ?= $(shell brew --prefix openssl@3 2>/dev/null || echo $(BREW_PREFIX)/opt/openssl@3)
  Makefile:71:INC += -I$(BREW_PREFIX)/include -I$(OPENSSL_PREFIX)/include
  Makefile:72:LDFLAGS += -L$(BREW_PREFIX)/lib -L$(OPENSSL_PREFIX)/lib
BUILDING.md pin:
  BUILDING.md:55:| openssl@3      | 3.6.4   | SHA-256 of the input file             |
generic prefix symlinks:
  lrwxr-xr-x 1 gmcas admin 41 Nov  7 19:28 /opt/homebrew/include/openssl -> ../Cellar/openssl@4/4.1.0/include/openssl
  lrwxr-xr-x 1 gmcas admin 45 Nov  7 19:28 /opt/homebrew/lib/libcrypto.dylib -> ../Cellar/openssl@4/4.1.0/lib/libcrypto.dylib
openssl@4 install receipt: Nov 7 19:28 /opt/homebrew/Cellar/openssl@4/4.1.0/INSTALL_RECEIPT.json
  ea_non_iid -> /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib  (NOT the pinned prefix)
  ea_iid -> /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib  (NOT the pinned prefix)
  ea_restart -> /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib  (NOT the pinned prefix)
production binaries not linked against the pinned openssl@3: 3 of 3
RESULT: PASS -- all three production binaries link /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib: the generic prefix precedes the pinned one on -I and -L, so the pin cannot pin
```

### control.txt (verbatim)

```
# PROV-15 control.txt  2026-11-07 21:56:18 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 b7a55528a8270672a89bd26265feb529293718a83d2a19a350cd035289d83460  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_conditioning  (mtime 2026-10-20 21:06:00)
ea_conditioning -> /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib
openssl@4 Cellar mtime: 2026-11-07 19:28:41 ; ea_conditioning mtime: 2026-10-20 21:06:00
RESULT: CONTROL-OK -- the October build from the same Makefile links the pinned openssl@3; the 2026-11-07 builds link openssl@4 because the generic prefix moved under them
```
