#!/usr/bin/env python3
"""Step-3 resolution (fix/restart-notrun onto the step-2 result): final values
27 regression scripts / 29 checks / 90 live instruments.  Every replacement
asserts how many times it lands."""
import re
import sys

WT = sys.argv[1]
BLOCK = re.compile(r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]*\n", re.S)
failures = []


def read(p):
    with open(WT + "/" + p, encoding="utf-8") as fh:
        return fh.read()


def write(p, t):
    with open(WT + "/" + p, "w", encoding="utf-8") as fh:
        fh.write(t)


def resolve_blocks(p, t, reps):
    found = len(BLOCK.findall(t))
    if found != len(reps):
        failures.append("%s: expected %d conflict blocks, found %d" % (p, len(reps), found))
        return t
    it = iter(reps)
    return BLOCK.sub(lambda m: next(it) + "\n", t)


def edit(p, t, old, new, n=1):
    c = t.count(old)
    if c != n:
        failures.append("%s: expected %d of %r, found %d" % (p, n, old[:70], c))
        return t
    return t.replace(old, new)


MERGED = "`04c1ccc` with `c8b0bc6`, `7d647e6` and `745b396` merged"

# ---------------------------------------------------------------- run-all-checks.sh
f = "cpp/selftest/run-all-checks.sh"
t = read(f)
t = resolve_blocks(f, t, ["EXPECTED_REGRESSION_SCRIPTS=27\nEXPECTED_TOTAL_CHECKS=29"])
write(f, t)

# ---------------------------------------------------------- CLOSING-INVENTORY.md
f = "audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md"
t = read(f)
bullets = (
    "- `cpp/selftest/run-all-checks.sh` runs 27 regression scripts\n"
    "  (`./run-all-checks.sh --allow-known-platform-deltas` — expect 29 passed, 0 failed);\n"
    "- `audits/enum-instruments.sh` prints **90 live instruments** (measured\n"
    "  2026-11-08 on the merged tree, `04c1ccc` with `c8b0bc6`, `7d647e6` and\n"
    "  `745b396` merged, up three on `OC-128`'s 87 at `a5422cf`: one each for\n"
    "  `cpp/selftest/regression-stale-report.sh` (PROV-01),\n"
    "  `cpp/selftest/regression-openssl-pin.sh` (PROV-15) and\n"
    "  `cpp/selftest/regression-restart-notrun.sh` (AA-04); the count has a\n"
    "  hand-reviewed limb, `OC-126`);"
)
cmd = "./run-all-checks.sh --allow-known-platform-deltas   # expect 29 passed, 0 failed"
t = resolve_blocks(f, t, [bullets, cmd])
write(f, t)

# -------------------------------------------------------- INSTRUMENT-INVENTORY.md
f = "audits/INSTRUMENT-INVENTORY.md"
t = read(f)
row_a = ("| **LIVE** | behaviour, present tense: is it run, sourced, compiled, or a workflow **now** | "
         "**90** at %s, 2026-11-08 |" % MERGED)
row_b = ("| **LIVE** | **90** at %s, 2026-11-08 | `cpp/selftest`, `tools`, `.github`, "
         "`audits/2026-10-11-independent-audit`, `audits/2026-10-09-independent-audit`, `repairs/*/rerun.sh` "
         "— anything a sweep must cover today |" % MERGED)
t = resolve_blocks(f, t, [row_a, row_b])
old_para = ("**87 -> 89 across the 2026-11-08 merges into master (PROV-01, PROV-15).** The\n"
            "instruments are `cpp/selftest/regression-stale-report.sh`, the regression for\n"
            "the stale-report ordering defect in the three tools' `-o` claim, and\n"
            "`cpp/selftest/regression-openssl-pin.sh`, the regression for the openssl@3\n"
            "pin's include and link order. Each fix branch counted 88 alone against the\n"
            "same 87, so the branch figures do not sum: the merged tree is counted once,\n"
            "by the enumerator, after each merge.\n")
new_para = ("**87 -> 90 across the 2026-11-08 merges into master (PROV-01, PROV-15, AA-04).**\n"
            "The instruments are `cpp/selftest/regression-stale-report.sh`, the regression\n"
            "for the stale-report ordering defect in the three tools' `-o` claim;\n"
            "`cpp/selftest/regression-openssl-pin.sh`, the regression for the openssl@3\n"
            "pin's include and link order; and `cpp/selftest/regression-restart-notrun.sh`,\n"
            "the regression for a declined restart row or column estimator that was\n"
            "dropped from the report silently. Each fix branch counted 88 alone against\n"
            "the same 87, so the branch figures do not sum: the merged tree is counted\n"
            "once, by the enumerator, after each merge.\n")
t = edit(f, t, old_para, new_para)
write(f, t)

# ------------------------------------------------- WHAT-A-GREEN-SUITE-ESTABLISHES.md
f = "cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md"
t = read(f)
behaviour = (
    "| **behaviour regressions** (`regression-*.sh`) | 27 | that the specific defect each names does not "
    "reproduce, on the inputs each generates | anything about inputs it does not generate, or defects it does "
    "not name. Several assert only that a tool did not abort. One member, `regression-workflows.sh`, is not "
    "about the tool at all: it `bash -n`s the shell blocks in the CI workflow definitions, and says nothing "
    "about whether those workflows' gates are *correct* — only that bash can parse them (`OC-84`). Another, "
    "`regression-option-order.sh`, guards a deliberate BEHAVIOUR CHANGE rather than a defect: `OC-104` makes "
    "all three tools refuse an option placed after the file operand, because glibc permutes such a line and "
    "BSD does not, so one command line named two different operations on two supported platforms. A third, "
    "`regression-constants.sh`, asserts that **no mutated constant survives** in the floor oracle or the "
    "pinned manifests — it runs **last** and compares values rather than searching for markers, because a "
    "mutation that removed its own marker would pass a marker search (`OC-121`). A fourth, "
    "`regression-openssl-pin.sh`, is about the BUILD rather than the tool: it reads the Makefile's `make -n` "
    "plan and the built binaries' `otool -L` load commands to assert the openssl@3 pin is searched before the "
    "generic Homebrew prefix (PROV-15), and off macOS it abstains with exit 2 rather than passing. |"
)
integrity = (
    "| **inventory and corpus integrity** (`verify-fixture-inventory.sh`, `regression-selftest-inventory.sh`, "
    "`regression-outside-battery.sh`) | 3 | that the fixture and corpus sets match their manifests, both "
    "directions | that a manifest is right. `verify-fixture-inventory.sh` **prints its manifest's digest and "
    "does not verify it** (`OC-76`, Tier A). |"
)
mutation = (
    "| **mutation harnesses** | 3 | that the guards they mutate **can fail**, with each mutation shown to land "
    "and a baseline shown accepted | that any *other* member can fail. They cover 3 of 27. |"
)
row1 = (
    "| **1. every member can fail** | **BELIEVED, and known false five times.** 3 of 27 scripts are covered by "
    "a mutation harness; the rest rest on having been *observed* to fail once, at the time they were written, "
    "recorded in the commit if at all. | `ls cpp/selftest/*mutation-test.sh cpp/selftest/regression-deadguard.sh "
    "\\| wc -l` → 3 |"
)
row2 = (
    "| **2. every member's inputs exist before an absence is read** | **PARTLY ENFORCED, and it is the "
    "minority.** 5 of 27 assert presence or carry a third outcome. | `grep -lE 'HARNESS FAULT\\|is absent or "
    "empty\\|INPUT-DID-NOT-REACH' cpp/selftest/*.sh \\| grep -c .` → 5 |"
)
row3 = (
    "| **3. build state is recorded** | **ENFORCED where declared, and declared by few.** The aggregator now "
    "surfaces every declaration and prints the coverage; it is **8 of 29** — 5 of 26 measured 2026-10-27 from "
    "the `build-state:` line of `./run-all-checks.sh --allow-known-platform-deltas`, which is the only place "
    "this figure exists, plus `regression-stale-report.sh`, `regression-openssl-pin.sh` and "
    "`regression-restart-notrun.sh` (added 2026-11-08), each of which declares through `bs_print`; DERIVED "
    "from the measurement by three, and the next run's `build-state:` line re-measures it. It is NOT "
    "derivable by reading the tree: ten scripts source `buildstate-lib.sh` and only eight of them are suite "
    "members that declare, so a static count gives 10 and is wrong (`OC-126`). The two `-DNDEBUG` arms are "
    "now distinguishable, where before they were byte-identical (`OC-66`). | the `build-state:` line in every "
    "run |"
)
tail = (
    "at all, or that the binary measured was the one intended in the 21 of 29 checks\n"
    "that do not say (21 of 26 measured 2026-10-27, same source as above; the three members\n"
    "added 2026-11-08 declare, so the denominator moved and the numerator did not)."
)
t = resolve_blocks(f, t, [behaviour + "\n" + integrity + "\n" + mutation, row1 + "\n" + row2 + "\n" + row3, tail])
t = edit(f, t,
         "the commands given. Counts re-derived 2026-11-08 when\n"
         "`regression-stale-report.sh` (PROV-01) and `regression-openssl-pin.sh`\n"
         "(PROV-15) joined the suite.",
         "the commands given. Counts re-derived 2026-11-08 when\n"
         "`regression-stale-report.sh` (PROV-01), `regression-openssl-pin.sh`\n"
         "(PROV-15) and `regression-restart-notrun.sh` (AA-04) joined the suite.")
t = edit(f, t, "**23 named defects", "**24 named defects")
t = edit(f, t, "a statement about 23 checks", "a statement about 24 checks")
write(f, t)

for p in ("cpp/selftest/run-all-checks.sh", "audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md",
          "audits/INSTRUMENT-INVENTORY.md", "cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md", "NOTICE",
          "cpp/selftest/regression-script-inventory.txt", ".github/workflows/x86-64-platform-facts.yml"):
    s = read(p)
    if "<<<<<<< " in s or ">>>>>>> " in s:
        failures.append("%s: conflict markers remain" % p)

if failures:
    print("RESOLUTION-DID-NOT-APPLY")
    for x in failures:
        print("  " + x)
    sys.exit(2)
print("resolution step 3 applied")
