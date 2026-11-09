#!/usr/bin/env python3
"""Apply the merge-map resolution for one merge step to the scratch worktree.

Every replacement asserts how many times it lands (instrument rule 1: a
mutation that did not land reports neither a pass nor a fail).  Conflict
blocks are replaced in order of appearance; the count of blocks per file is
asserted too.
"""
import re
import sys

WT = sys.argv[1]
STEP = int(sys.argv[2])

BLOCK = re.compile(r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]*\n", re.S)

ROW_TAIL = (
    "| `cpp/selftest`, `tools`, `.github`, `audits/2026-10-11-independent-audit`, "
    "`audits/2026-10-09-independent-audit`, `repairs/*/rerun.sh` — anything a sweep must cover today |"
)

BEHAVIOUR_ROW = (
    "| **behaviour regressions** (`regression-*.sh`) | {scripts} | that the specific defect each names does not "
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

ROW2 = (
    "| **2. every member's inputs exist before an absence is read** | **PARTLY ENFORCED, and it is the "
    "minority.** {pres} of {scripts} assert presence or carry a third outcome. | `grep -lE 'HARNESS FAULT\\|is "
    "absent or empty\\|INPUT-DID-NOT-REACH' cpp/selftest/*.sh \\| grep -c .` → {pres} |"
)

ROW3 = (
    "| **3. build state is recorded** | **ENFORCED where declared, and declared by few.** The aggregator now "
    "surfaces every declaration and prints the coverage; it is **{decl} of {checks}** — 5 of 26 measured "
    "2026-10-27 from the `build-state:` line of `./run-all-checks.sh --allow-known-platform-deltas`, which is "
    "the only place this figure exists, plus {new_members} (added 2026-11-08), each of which declares through "
    "`bs_print`; DERIVED from the measurement by {added_word}, and the next run's `build-state:` line "
    "re-measures it. It is NOT derivable by reading the tree: {src_word} scripts source `buildstate-lib.sh` "
    "and only {decl_word} of them are suite members that declare, so a static count gives {src} and is wrong "
    "(`OC-126`). The two `-DNDEBUG` arms are now distinguishable, where before they were byte-identical "
    "(`OC-66`). | the `build-state:` line in every run |"
)

STEPS = {
    2: dict(
        scripts=26, checks=28, live=89, named=23, pres=5, decl=7, src=9,
        added_word="two", src_word="nine", decl_word="seven", members_word="two members",
        new_members="`regression-stale-report.sh` and `regression-openssl-pin.sh`",
        merged="`04c1ccc` with `c8b0bc6` and `7d647e6` merged",
        ids="PROV-01, PROV-15",
        header=("the commands given. Counts re-derived 2026-11-08 when\n"
                "`regression-stale-report.sh` (PROV-01) and `regression-openssl-pin.sh`\n"
                "(PROV-15) joined the suite."),
        ci_live_tail=("  2026-11-08 on the merged tree, `04c1ccc` with `c8b0bc6` and `7d647e6`\n"
                      "  merged, up two on `OC-128`'s 87 at `a5422cf`: one each for\n"
                      "  `cpp/selftest/regression-stale-report.sh` (PROV-01) and\n"
                      "  `cpp/selftest/regression-openssl-pin.sh` (PROV-15); the count has a\n"
                      "  hand-reviewed limb, `OC-126`);"),
        inv_para=("**87 -> 89 across the 2026-11-08 merges into master (PROV-01, PROV-15).** The\n"
                  "instruments are `cpp/selftest/regression-stale-report.sh`, the regression for\n"
                  "the stale-report ordering defect in the three tools' `-o` claim, and\n"
                  "`cpp/selftest/regression-openssl-pin.sh`, the regression for the openssl@3\n"
                  "pin's include and link order. Each fix branch counted 88 alone against the\n"
                  "same 87, so the branch figures do not sum: the merged tree is counted once,\n"
                  "by the enumerator, after each merge.\n"),
        prev=dict(scripts=25, checks=27, live=88, named=22),
    ),
    3: dict(
        scripts=27, checks=29, live=90, named=24, pres=5, decl=8, src=10,
        added_word="three", src_word="ten", decl_word="eight", members_word="three members",
        new_members=("`regression-stale-report.sh`, `regression-openssl-pin.sh` and "
                     "`regression-restart-notrun.sh`"),
        merged="`04c1ccc` with `c8b0bc6`, `7d647e6` and `745b396` merged",
        ids="PROV-01, PROV-15, AA-04",
        header=("the commands given. Counts re-derived 2026-11-08 when\n"
                "`regression-stale-report.sh` (PROV-01), `regression-openssl-pin.sh`\n"
                "(PROV-15) and `regression-restart-notrun.sh` (AA-04) joined the suite."),
        ci_live_tail=("  2026-11-08 on the merged tree, `04c1ccc` with `c8b0bc6`, `7d647e6` and\n"
                      "  `745b396` merged, up three on `OC-128`'s 87 at `a5422cf`: one each for\n"
                      "  `cpp/selftest/regression-stale-report.sh` (PROV-01),\n"
                      "  `cpp/selftest/regression-openssl-pin.sh` (PROV-15) and\n"
                      "  `cpp/selftest/regression-restart-notrun.sh` (AA-04); the count has a\n"
                      "  hand-reviewed limb, `OC-126`);"),
        inv_para=("**87 -> 90 across the 2026-11-08 merges into master (PROV-01, PROV-15, AA-04).**\n"
                  "The instruments are `cpp/selftest/regression-stale-report.sh`, the regression\n"
                  "for the stale-report ordering defect in the three tools' `-o` claim;\n"
                  "`cpp/selftest/regression-openssl-pin.sh`, the regression for the openssl@3\n"
                  "pin's include and link order; and `cpp/selftest/regression-restart-notrun.sh`,\n"
                  "the regression for a declined restart row or column estimator that was\n"
                  "dropped from the report silently. Each fix branch counted 88 alone against\n"
                  "the same 87, so the branch figures do not sum: the merged tree is counted\n"
                  "once, by the enumerator, after each merge.\n"),
        prev=dict(scripts=26, checks=28, live=89, named=23),
    ),
}

P = STEPS[STEP]
PREV = P["prev"]

failures = []


def read(path):
    with open(WT + "/" + path, encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    with open(WT + "/" + path, "w", encoding="utf-8") as fh:
        fh.write(text)


def resolve_blocks(path, text, replacements):
    blocks = BLOCK.findall(text)
    if len(blocks) != len(replacements):
        failures.append("%s: expected %d conflict blocks, found %d" % (path, len(replacements), len(blocks)))
        return text
    it = iter(replacements)
    return BLOCK.sub(lambda m: next(it) + "\n", text)


def edit(path, text, old, new, n=1):
    c = text.count(old)
    if c != n:
        failures.append("%s: expected %d occurrence(s) of %r, found %d" % (path, n, old[:60], c))
        return text
    return text.replace(old, new)


# ---------------------------------------------------------------- run-all-checks.sh
f = "cpp/selftest/run-all-checks.sh"
t = read(f)
t = edit(f, t, "EXPECTED_REGRESSION_SCRIPTS=%d\n" % PREV["scripts"], "EXPECTED_REGRESSION_SCRIPTS=%d\n" % P["scripts"])
t = edit(f, t, "EXPECTED_TOTAL_CHECKS=%d\n" % PREV["checks"], "EXPECTED_TOTAL_CHECKS=%d\n" % P["checks"])
write(f, t)

# ---------------------------------------------------------- CLOSING-INVENTORY.md
f = "audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md"
t = read(f)
t = resolve_blocks(f, t, [P["ci_live_tail"]])
t = edit(f, t, "runs %d regression scripts" % PREV["scripts"], "runs %d regression scripts" % P["scripts"])
t = edit(f, t, "expect %d passed, 0 failed" % PREV["checks"], "expect %d passed, 0 failed" % P["checks"], n=2)
t = edit(f, t, "**%d live instruments**" % PREV["live"], "**%d live instruments**" % P["live"])
write(f, t)

# -------------------------------------------------------- INSTRUMENT-INVENTORY.md
f = "audits/INSTRUMENT-INVENTORY.md"
t = read(f)
row_a = ("| **LIVE** | behaviour, present tense: is it run, sourced, compiled, or a workflow **now** | "
         "**%d** at %s, 2026-11-08 |" % (P["live"], P["merged"]))
row_b = "| **LIVE** | **%d** at %s, 2026-11-08 %s" % (P["live"], P["merged"], ROW_TAIL)
t = resolve_blocks(f, t, [row_a, row_b])
if STEP == 2:
    old_para = ("**87 -> 88 at `04c1ccc` with one file staged (PROV-01, 2026-11-08).** The\n"
                "instrument is `cpp/selftest/regression-stale-report.sh`, the regression for\n"
                "the stale-report ordering defect in the three tools' `-o` claim. Counted\n"
                "while staged and before its commit existed, which is what the index rule\n"
                "above is for: the number was read from the enumerator, not predicted.\n")
else:
    old_para = STEPS[2]["inv_para"]
t = edit(f, t, old_para, P["inv_para"])
write(f, t)

# ------------------------------------------------- WHAT-A-GREEN-SUITE-ESTABLISHES.md
f = "cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md"
t = read(f)
fmt = dict(scripts=P["scripts"], checks=P["checks"], pres=P["pres"], decl=P["decl"], src=P["src"],
           new_members=P["new_members"], added_word=P["added_word"], src_word=P["src_word"],
           decl_word=P["decl_word"])
tail = ("that do not say (21 of 26 measured 2026-10-27, same source as above; the %s\n"
        "added 2026-11-08 declare, so the denominator moved and the numerator did not)." % P["members_word"])
if STEP == 2:
    t = resolve_blocks(f, t, [BEHAVIOUR_ROW.format(**fmt), ROW2.format(**fmt) + "\n" + ROW3.format(**fmt), tail])
    t = edit(f, t, STEPS[2]["header"].replace(" (PROV-01) and `regression-openssl-pin.sh`\n(PROV-15) joined the suite.",
                                              " joined the suite (PROV-01)."), P["header"])
else:
    # the step-3 block list is filled in once the step-3 conflicts are known
    blocks = [b for b in sys.argv[3:]]
    t = resolve_blocks(f, t, [eval(b) for b in blocks]) if blocks else t
    t = edit(f, t, STEPS[2]["header"], P["header"])
t = edit(f, t, "They cover 3 of %d." % PREV["scripts"], "They cover 3 of %d." % P["scripts"])
t = edit(f, t, "3 of %d scripts are covered" % PREV["scripts"], "3 of %d scripts are covered" % P["scripts"])
t = edit(f, t, "**%d named defects" % PREV["named"], "**%d named defects" % P["named"])
t = edit(f, t, "21 of %d checks" % PREV["checks"], "21 of %d checks" % P["checks"])
t = edit(f, t, "a statement about %d checks" % PREV["named"], "a statement about %d checks" % P["named"])
if STEP == 3:
    pf = dict(fmt)
    t = edit(f, t, BEHAVIOUR_ROW.format(**dict(fmt, scripts=PREV["scripts"])), BEHAVIOUR_ROW.format(**fmt))
    t = edit(f, t, ROW2.format(**dict(fmt, scripts=PREV["scripts"])), ROW2.format(**fmt))
    t = edit(f, t, ROW3.format(**dict(STEPS[2], **{})) if False else ROW3.format(
        scripts=26, checks=28, pres=5, decl=7, src=9,
        new_members=STEPS[2]["new_members"], added_word="two", src_word="nine", decl_word="seven"),
        ROW3.format(**fmt))
    t = edit(f, t, ("that do not say (21 of 26 measured 2026-10-27, same source as above; the two members\n"
                    "added 2026-11-08 declare, so the denominator moved and the numerator did not)."), tail)
write(f, t)

for path in ("cpp/selftest/run-all-checks.sh", "audits/2026-10-11-independent-audit/CLOSING-INVENTORY.md",
             "audits/INSTRUMENT-INVENTORY.md", "cpp/selftest/WHAT-A-GREEN-SUITE-ESTABLISHES.md", "NOTICE",
             "cpp/selftest/regression-script-inventory.txt"):
    if BLOCK.search(read(path)) or "<<<<<<<" in read(path) or ">>>>>>>" in read(path):
        failures.append("%s: conflict markers remain" % path)

if failures:
    print("RESOLUTION-DID-NOT-APPLY")
    for x in failures:
        print("  " + x)
    sys.exit(2)
print("resolution step %d applied: %d files" % (STEP, 4))
