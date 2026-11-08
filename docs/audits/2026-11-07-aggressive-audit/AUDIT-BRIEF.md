# Aggressive security and correctness audit — brief for every agent

Date: 2026-11-07. Branch: `audit/2026-11-07`. Fixes go on `fix/<topic>`, one per fix.
This file is the contract. Read it before doing anything; follow it exactly.

## Why this matters, and how everything is ranked

ShannonPad sizes one-time pads from the min-entropy this tool reports. The worst
bug is one that makes the tool report MORE entropy than the data has. Rank by:

| severity | meaning |
|---|---|
| **CRITICAL** | the tool can report more min-entropy than the data has (any path, any width) |
| **HIGH** | memory safety or undefined behaviour reachable from an input file |
| **MEDIUM** | wrong result in the conservative direction, wrong refusal, nondeterminism |
| **LOW** | everything else |

Target data profile: 1,000,000+ samples from an Infinite Noise device, 1 or 8 bits
per symbol, through `ea_non_iid` (and `ea_iid`, `ea_restart`).

## Ground rules — non-negotiable

1. **Nothing goes upstream.** No issue, PR, comment, email or workflow dispatch to
   `usnistgov` or any other SP 800-90B project. Every `gh` call carries
   `-R systemslibrarian/SP800-90B_EntropyAssessment`. Prefer not to use `gh` at all.
2. **Do not touch `master`, any tag, or history.** No rebase, no force, no tag moves,
   no commits to master. Work only on `audit/2026-11-07` and `fix/*` branches.
3. **Do not run `make` inside `cpp/`** and do not overwrite `cpp/ea_non_iid`,
   `cpp/ea_iid`, `cpp/ea_restart` — those are the production binaries the regression
   scripts read. Any instrumented build (sanitizer, AFL, debug) is built OUT OF TREE
   with an explicit `-o` into the scratch area, using the exact compile line in
   `BUILD-LINES.md` here.
4. **This machine has 16 GB RAM and runs out of memory under two heavy jobs.**
   A heavy job = a build, a run on ≥ 200,000 samples, a sanitizer run, a fuzzer.
   Analysis-phase agents run NO heavy jobs. Execution phases are serialized by the
   orchestrator; never start a second heavy job yourself. Always set
   `OMP_NUM_THREADS=2` unless the task is specifically about thread counts.
   Cap any fuzzing run at 2 hours.
5. **Short inputs**: the tools refuse < 1,000,000 samples (§3.1.1). The test escape is
   `EA_ALLOW_SHORT_DATASET=1`; the run is marked non-compliant. Use it for small
   differential and edge-case inputs. Note it in every record that used it.
6. **Follow THIS repository's rules and numbering only**: `audits/BUG-REPAIR-GUIDE.md`
   (instrument rules 1–5; rules 6–18). Never import rule numbers from any other
   project. The ones that bite most here:
   - instrument rule 2: a conclusion from ABSENCE needs a well-formed report first
     (a usage message, a crash, a timeout and a missing line are different outcomes);
   - instrument rule 4: name the binary (sha256) every measurement ran against;
   - instrument rule 5: labelled reads, never positional (`head -1`, `[0]`);
   - rule 7: a negative control is built by MUTATION of a passing artefact, and the
     baseline is asserted accepted;
   - rule 17: never pipe a tool's output into `head`/`tail` for a verdict — write a
     file, read the file; read the producer's exit status;
   - rule 18: when you branch on a classification, state what it cannot see.
7. **The authority is the published standard, not memory.** The text of NIST SP
   800-90B (January 2018) is at `reference/sp800-90b.pages.txt` with
   `===== PDF PAGE N =====` markers. It was extracted from the PDF downloaded from
   nvlpubs.nist.gov on 2026-11-07, sha256
   `9b0dd77131ade3617a91cd8457fa09e0dc354c273bb2220a6afeaca16e5defe7` (identical to
   `audits/2026-09-30/reference/NIST.SP.800-90B.pdf`). Cite as
   `SP 800-90B §6.3.4 step 7 (PDF p. 54)`. Quote the spec text you rely on.
   Section → PDF page: 3.1.1 p17 · 3.1.2 p19 · 3.1.3 p20 · 3.1.4 p20–22 · 3.1.5
   p22–25 · 5.1 p37–43 · 5.2 p43–47 · 6.1/6.2 p48 · 6.3.1 p49 · 6.3.2 p50 · 6.3.3
   p51 · 6.3.4 p53 · 6.3.5 p55 · 6.3.6 p56 · 6.3.7 p57 · 6.3.8 p59 · 6.3.9 p60 ·
   6.3.10 p63 · 6.4 p66.
8. **Known, documented divergences from the standard are NOT bugs** unless the code
   departs from the documented decision. Read `FORK-DIVERGENCE-AND-TRUST.md`
   sections A, B and D before reporting: `C23` (restart sanity check decides on the
   exact multinomial, not step 5's printed formula), `C22c` (exact 0.995 quantile,
   not 2.576), `D-1`…`D-6`, the ≥ 1,000,000 intake, the fail-closed IID battery, the
   option-order refusal (`OC-104`). Report such a case as DOCUMENTED DIVERGENCE with
   the citation, in the limitations section.
9. **Don't report anything you haven't reproduced.** Label a suspicion as a
   suspicion. A suspicion is welcome; a suspicion dressed as a finding is not.
10. **Keep the numbers honest** (guide ground rule 7): record measured outputs, not
    expected ones. If a reproduction does not show the failure, say so and stop.

## What every finding must carry

```
ID: AA-NN                      (AA = this audit; sequential)
Title:
Severity: CRITICAL | HIGH | MEDIUM | LOW
Direction: overstates | understates | neutral | crash | nondeterministic
Component: file:function (lines)
Spec: SP 800-90B §x.y.z, PDF p. N — quoted text
Code: quoted lines
Reproducer: corpus/<file> + exact command (with env vars); binary sha256
Observed:   (verbatim, from a file you wrote, not a pipe)
Expected:   (from the spec / the reference implementation, with the arithmetic)
Negative control: the same command on a minimally different input / build that does
                  NOT trigger it, showing the reproducer is what triggers it
Platform: Darwin arm64, Apple clang 21 (this host) — and anything else measured
Prior-fix interaction: which NOTICE/tracker repair, if any, this touches (rule 12)
```

## Where things go (all under `docs/audits/2026-11-07-aggressive-audit/`)

- `FINDINGS.md` — the deliverable (orchestrator writes it)
- `reference/` — spec text, label captures, the independent Python reference
  implementation (`reference/py90b/`)
- `harness/` — differential driver, corpus generator, sanitizer/fuzz scripts
- `corpus/` — generated inputs (keep each ≤ 1 MB; generate larger ones on demand
  from a script with a fixed seed and record the sha256)
- `repro/` — one directory per finding: input, command, observed, expected
- `logs/` — raw logs, named `<phase>-<what>.log`; `logs/analysis/<component>.md`
  for the understanding phase

## Independence of the reference implementation

The Python reference (`reference/py90b/`) is written FROM THE SPEC TEXT ONLY.
Reference writers must not open any file under `cpp/`. The only thing they take from
the C++ is the NAMES of the intermediate quantities printed in verbose mode
(`reference/cpp-verbose-labels-*.txt`), so the differential driver can match them.
Every reference module exposes:

```python
def estimate(symbols, bits_per_symbol):   # symbols: sequence of ints in [0, 2^bps)
    """returns a dict: {'min_entropy': float, ...named intermediates...}"""
```

and a `__main__` that reads a raw byte file (one symbol per byte, low `bps` bits)
and prints that dict as JSON. Each module ships `tests/test_<name>.py` that checks the
spec's own worked example(s) for that estimator, where the spec gives one.
