# 2026-09-30 audits of NIST SP 800-90B EntropyAssessment

This directory preserves independent audit findings against **NIST's SP 800-90B entropy assessment tool**, [`usnistgov/SP800-90B_EntropyAssessment`](https://github.com/usnistgov/SP800-90B_EntropyAssessment). The audits were run on **2026-09-30**.

- **Not official NIST conclusions.** Nothing here represents NIST's view. Check upstream status before treating any finding as confirmed, fixed, or rejected by the maintainers.
- **AI-assisted, then reproduced.** AI-assisted analysis (multiple Claude agents) was used. Every finding listed as confirmed or verified was independently reproduced from the preserved commands and generators: the N/R and NOVEL series on clean builds of the upstream baseline, and the verified F rows on the fork build whose `ea_non_iid` sources are byte-identical to it. Items the reports mark UNVERIFIED, THEORETICAL or spec-level are recorded as such.

## Baseline

| Item | Value |
|---|---|
| Upstream baseline audited | `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289` (upstream `master` on 2026-09-30: tag v1.1.8 plus the later merges of PRs #237, #248 and #250) |
| First-wave audit (F-series) | fork commit `f06166f`; every file on the `ea_non_iid` include path is byte-identical to `87c104d` (see [`AUDIT.md`](AUDIT.md)) |
| Standard | NIST SP 800-90B, *Recommendation for the Entropy Sources Used for Random Bit Generation*, January 2018, doi:[10.6028/NIST.SP.800-90B](https://doi.org/10.6028/NIST.SP.800-90B). The copy used during the audits (84 pages) is kept at [`reference/NIST.SP.800-90B.pdf`](reference/NIST.SP.800-90B.pdf), SHA-256 `9b0dd77131ade3617a91cd8457fa09e0dc354c273bb2220a6afeaca16e5defe7`. |
| Build used | Linux x86_64, g++ 13.3.0, upstream Makefile (`-std=c++11 -fopenmp -O2 -ffloat-store -march=native`); sanitizer builds with `-fsanitize=address,undefined` |

## What is here

| Path | Contents |
|---|---|
| [`AUDIT.md`](AUDIT.md) | First-wave adversarial audit of `ea_non_iid` (F01–F30) with round-2 verification status. Historical, unchanged; moved from the repository root. |
| [`FINDINGS-TRACKER.md`](FINDINGS-TRACKER.md) | The canonical defect work queue: the AI Repair Queue, then every confirmed finding with its operational state, reproduction, evidence, upstream issue/PR/status, fork status and next action. Unconfirmed and spec-level items are listed separately. The procedure is [`../BUG-REPAIR-GUIDE.md`](../BUG-REPAIR-GUIDE.md) |
| [`novel-findings/`](novel-findings/) | Whole-codebase novel-findings audit (N/R series). `REPORT.md` is byte-identical to fork commit `0e685f6`. Also: the coordinator's verification outputs (`repro/verify/`), the seven per-area auditor reports (`agent-reports/`), generators, reference/oracle code, harness sources and logs. `MANIFEST.md` lists every file with its original path and SHA-256. |
| [`phase2-focused/`](phase2-focused/) | Phase-2 focused audit (NOVEL series). `REPORT.md` is byte-identical to fork commit `3087ff4`. Also: the PDF-derived estimator oracles (`oracle/`), the exact #272 reproduction (`repro/issue272/`), dataset generators and evidence logs. `MANIFEST.md` lists every file. |
| [`reference/`](reference/) | The reference material used during the audits, each byte-identical to the copy added in fork commit `8082231` (branch `audits/2026-09-30-novel-findings`), where it had been placed at the repository root. [`NIST.SP.800-90B.pdf`](reference/NIST.SP.800-90B.pdf) is the standard (SHA-256 above). [`full_source.txt`](reference/full_source.txt) is a concatenated listing of the 26 `cpp/` source files, each identical to upstream `87c104d` (SHA-256 `50f2c1412dd983ee6fc8ad1f0d0b8baa1cf3bd25aec35f882e3e9b1acfc5cefb`). |

Layout changes (2026-09-30 cleanup):
- The first-wave report was moved from the repository root (`AUDIT-2026-09-30.md`) to [`AUDIT.md`](AUDIT.md), unchanged.
- The phase-2 report's original path `audits/2026-09-30-phase2-focused-audit.md` (commit `3087ff4`) was consolidated into [`phase2-focused/REPORT.md`](phase2-focused/REPORT.md), which is byte-identical.
- The novel-findings report's original path, `audits/2026-09-30-novel-findings-audit.md`, exists only on fork branch `audits/2026-09-30-novel-findings`.

## Filed upstream vs audit-only

- **Filed and open upstream:**
  - #253 (F01, PR #256)
  - #254 (F02)
  - #255 (F03/F05)
  - #257 (F16, PR #268)
  - #258 (F04)
  - #259 (F18)
  - #260 (F19)
  - #261 (F15)
  - #263 (F11, PR #270)
  - #264 (F12)
  - #271 (N-02)
  - #272 (NOVEL-01)
- **Residuals of closed upstream items, not reported upstream:** R-1 (#246), R-2 (#178), R-3 (#183).
- **Audit-only:** N-01, N-03–N-11, NOVEL-02, NOVEL-03, and the unfiled F rows. The tracker has details.

## Reproducing

1. **Build the baseline:**
   ```sh
   git clone https://github.com/usnistgov/SP800-90B_EntropyAssessment.git
   cd SP800-90B_EntropyAssessment
   git checkout 87c104d
   cd cpp && make
   ```
2. **Regenerate inputs.** Generated test datasets (`.bin`) are intentionally not committed: deterministic generators recreate them.
   - Each finding section of `novel-findings/REPORT.md` has inline Python generators; more are in `novel-findings/generators/`. For example, `f09gen.py 3 300 f09b.bin` reproduces F09's input byte-for-byte.
   - For the phase-2 datasets, run `phase2-focused/generators/gen_w.py`, `gen_mission_e.py` and `gen_mission_h.py`. All 34 datasets were verified byte-identical to the originals.
3. **Run the documented commands.** Use the report sections, `novel-findings/repro/verify/LOG.md` (the coordinator's log) and `phase2-focused/repro/issue272/repro.sh` (the #272 reproduction; it clones upstream and applies both mutants itself).
4. **Estimator oracles.** `phase2-focused/oracle/oracle.py` implements MCV, Markov, t-Tuple, LRS, Lag and LZ78Y from the SP 800-90B text. `oracle_worked_examples.py` checks it against the spec's worked examples. `cmp.py` diffs it against `ea_non_iid -vv`; set its `S=` path first.

Absolute `/tmp/...` paths inside preserved logs and scripts refer to the original audit session workspaces. They were deliberately left unedited so the evidence is unaltered. The `Original path` column of each `MANIFEST.md` gives every file's location relative to that workspace (`SCRATCH/…`), which is enough to restore the original layout.

## Deliberately not committed

- binaries and build trees, dependency and cache directories;
- generated `.bin`/`.col` datasets (regenerable);
- duplicated copies of upstream source trees (the single concatenated listing `reference/full_source.txt` is kept as audit reference material);
- raw issue/PR dumps and API responses (re-fetchable);
- packaging archives and checksum files;
- conversation transcripts.
