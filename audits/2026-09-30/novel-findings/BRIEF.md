# Shared brief — adversarial NOVEL-findings audit of usnistgov/SP800-90B_EntropyAssessment

Paths (SCR = /tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad):
- Upstream master source, commit 87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289, extracted twice:
  - SCR/audit/rel/cpp   — release build, upstream Makefile flags (g++ 13.3, -O2 -ffloat-store -march=native -fopenmp). Binaries: ea_iid ea_non_iid ea_restart ea_conditioning ea_transpose. Selftest passes (max delta 1e-13).
  - SCR/audit/asan/cpp  — same source built -O1 -g -fsanitize=address,undefined,float-divide-by-zero,float-cast-overflow. Run with ASAN_OPTIONS=detect_leaks=0. Selftest clean under sanitizers.
  - Sample data: SCR/audit/rel/bin/*.bin (NIST's own samples).
- You may copy either tree into SCR/audit/work/<your-area>/ to instrument, add -DNDEBUG, change flags, write harnesses, etc. Put ALL generated files under SCR/audit/work/<your-area>/.
- Complete upstream issue/PR database (all 270 issues+PRs, open and closed, bodies, all conversation comments, inline PR review comments): SCR/gh/all.md. Each item starts with a line `######## #N [ISSUE|PR open|closed] title`. grep it for dedup — search by function name, file name, symptom words, estimator name.
- Prior local audit of ea_non_iid (not upstream, but already known to the user): /workspaces/SP800-90B_EntropyAssessment/AUDIT-2026-09-30.md (rows F01–F30). Read it.
- SP 800-90B (Jan 2018) is the standard. If you need the text and it isn't in the repo, work from your knowledge of the standard and say so; cite section numbers.

HARD RULES
- Never modify /workspaces/SP800-90B_EntropyAssessment (the git repo). Read-only there.
- No GitHub writes of any kind: no issues, PRs, comments. Do not run `gh` at all; use SCR/gh/all.md.
- Machine has 2 cores; keep individual runs bounded (use `timeout`), do not run more than 2 heavy processes at once. Prefer small/medium inputs unless a ≥1,000,000-sample case is needed to show certification relevance (then do it, but time-box).

KNOWN — never report these as new (semantic dedup: same root cause = duplicate, even with a different length, executable, platform, downstream symptom or stronger reproducer):
#253 two-valued multi-bit data takes binary path, n×H_bitstring omitted (PR #256). #254 inferred bits_per_symbol narrows width / not in JSON. #255 sub-minimum sample counts & skipped estimators (-1) invisible in JSON/errorLevel (related #238). #257 binary MultiMMC heap over-read 4<=L<=16 (PR #268, dup PR #269). #258 literal MultiMCW skipped for L<4096 (dup #265). #259 sha256_file unbounded read / hang on /dev/zero, FIFO (dup #266). #260 -l index*samples overflow, samples=0, short final block, whole-file hash for subset (dup #267). #261 assert aborts on tiny / repeat-free inputs, LZ78Y/MultiMMC length checks (dup #262). #263 compression v=1 divide by zero (PR #270). #264 collision v<=1 NaN. Closed #214/#163/#52 LRS quadratic time. Closed #22 z_alpha rounding. Plus EVERYTHING else in SP 800-90B issue history in all.md, and rows F01–F30 in AUDIT-2026-09-30.md (if you confirm one of the UNVERIFIED F-rows, report it under "Prior local audit row now verified", not as novel).

WHAT COUNTS
- Primary question: can this code produce a result, status, report or failure that does not faithfully represent SP 800-90B? Priority: entropy TOO HIGH, or IID wrongly accepted / restart test wrongly passed (the dangerous directions), then UB/memory safety, then provenance/report integrity, then robustness, then reporting.
- Before accepting any candidate: reproduce twice from the clean build, minimize input, identify file:function:line, explain the path, cite the spec section, determine direction and quantify, re-grep all.md with function names + symptom words, check whether an open fix PR (#256 #268 #270) already fixes it, decide whether it shares a root cause with a known item. Fails any step -> not confirmed.
- Distinguish: reproducible with a conforming ≥1,000,000-sample dataset vs only short inputs. Distinguish EXPECTED EXPENSIVE ALGORITHM vs avoidable input-triggered resource defect (give timings).
- Spec-literal behaviour that is a weakness of the standard itself is NOT a code defect; list it under "no-finding / spec limitation".
- Purely theoretical portability complaints do not count unless you demonstrate concrete wrong behaviour or clearly invalid C/C++.
- Zero confirmed findings is an acceptable result. Be as adversarial toward your own candidates as toward the code.

REPORT: write SCR/audit/reports/<your-area>.md with sections:
1. Scope actually covered (files/functions read, spec sections compared) + a conformance table | Section | Algorithm/Test | Step | Code location | Matches? | Notes |
2. Tests actually run (boundary matrices, input structures, sanitizer runs, differential/metamorphic checks, thread-count checks) — with commands and outcomes, compactly.
3. CONFIRMED NOVEL findings, each in this form:
   ### <AREA>-NN — title
   Category (A entropy correctness / B memory-UB / C assessment integrity / D robustness / E reporting), Confidence (HIGH/MEDIUM/LOW), Affected executable, Source file:function:line, SP 800-90B section, Valid ≥1,000,000-sample case? yes/no, DIRECTION: TOO HIGH / TOO LOW / none / unknown (quantified).
   Root cause. Minimal reproduction (exact deterministic commands, generator scripts inline). Actual (exact output, run twice). Expected (and why, per spec). Impact (no exaggeration). Deduplication proof (the grep terms you used on all.md and what they hit; why no existing item covers this root cause). Suggested fix direction. Regression test.
4. Suspected findings needing more work (separate).
5. EXCLUDED AS ALREADY KNOWN — every rediscovery mapped to its issue/PR/F-row.
6. No-finding areas (what was attacked and held).
Your final message back should be a short summary (≤25 lines): counts, titles of confirmed novel findings with category/confidence/direction, and the report path.
