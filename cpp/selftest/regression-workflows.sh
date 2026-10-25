#!/bin/bash
#
# F11 (OC-84): every shell block in a CI workflow is checked for syntax.
#
# WHY. .github/workflows/x86-64-platform-facts.yml carried this, in the middle
# of the step that GATES the whole job:
#
#     gate "oracle self-test" logs/07-oracle-selftest.log "oracle-selftest: PASS"
#     if true; then
#     fi
#     gate "outside-battery regression" ...
#
# An empty `if ... then ... fi` is a bash SYNTAX ERROR. Measured: bash executes
# the lines before it and then aborts at that point with exit 2. So in that
# step the five gates AFTER the empty block never ran -- outside-battery,
# script-inventory mutations, corpus mutations, restart regression, estimator
# guards -- and `exit "${fail}"` never ran either, so the step's status was
# bash's 2 rather than the accumulated verdict. The job goes red, which is why
# this was not a silent false pass; but it goes red for a reason that has
# nothing to do with what the gates found, and a reader who took "it failed" to
# mean "a gate caught something" would be wrong on both counts.
#
# It was introduced by 1502012, the commit that WIRED the oracle self-test --
# a leftover wrapper from the edit, both lines added together.
#
# THE SHELL IS RESOLVED, NOT ASSUMED. windows-platform-facts.yml declares
# `defaults: run: shell: cmd` for its whole job, so all ten of its run blocks
# are cmd and `bash -n` on them would be checking the wrong language. Each
# block's shell is resolved the way GitHub resolves it -- the step's own
# `shell:`, else the job's `defaults.run.shell`, else the workflow's, else the
# runner default, which is pwsh on a windows runner and bash elsewhere -- and
# every block is REPORTED with the shell it resolved to, so a skipped block is
# visible rather than silently dropped (F05's lesson, one directory over).
#
# Exit 2, not 0, when PyYAML is absent: a check that did not run supports no
# claim, and run-all-checks.sh counts "could not run" as its own category.
set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
. "${here}/buildstate-lib.sh" 2>/dev/null || true

# A workflow file dropped from the tree must not read as "nothing to check".
EXPECTED_WORKFLOWS=2

if ! python3 -c 'import yaml' >/dev/null 2>&1; then
    echo "regression-workflows: PyYAML is not available, so the workflows cannot be parsed." >&2
    echo "                      Refusing to report a syntax verdict this run did not reach." >&2
    exit 2
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/ea-workflows.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

# The extractor writes one file per run-block plus a manifest of
# <path>|<job>|<step>|<shell>|<substitutions>
verdict=$(EXPECTED_WORKFLOWS="${EXPECTED_WORKFLOWS}" python3 - "${repo}" "${work}" <<'EXTRACT'
import os, re, sys, yaml

repo, work = sys.argv[1], sys.argv[2]
expected = int(os.environ['EXPECTED_WORKFLOWS'])
wfdir = os.path.join(repo, '.github', 'workflows')
files = sorted(f for f in os.listdir(wfdir) if f.endswith(('.yml', '.yaml')))
if len(files) != expected:
    print("FATAL|expected %d workflow file(s), found %d: %s"
          % (expected, len(files), ", ".join(files) or "none"))
    raise SystemExit(0)

# GitHub Actions expressions are substituted before the shell ever sees them, so
# they are replaced with a plain word rather than checked or skipped. The COUNT
# is reported, so a workflow that grows expressions does not quietly change what
# this check is reading.
EXPR = re.compile(r'\$\{\{[^}]*\}\}')

man = []
nblocks = 0
for f in files:
    path = os.path.join(wfdir, f)
    try:
        doc = yaml.safe_load(open(path, encoding='utf-8').read())
    except Exception as e:
        print("FATAL|%s is not parseable YAML: %s" % (f, e))
        raise SystemExit(0)
    if not isinstance(doc, dict) or 'jobs' not in doc:
        print("FATAL|%s has no jobs: block" % f)
        raise SystemExit(0)
    wf_shell = (((doc.get('defaults') or {}).get('run') or {}).get('shell'))
    found_here = 0
    for jname, job in (doc.get('jobs') or {}).items():
        if not isinstance(job, dict):
            continue
        job_shell = (((job.get('defaults') or {}).get('run') or {}).get('shell'))
        runs_on = job.get('runs-on') or ''
        if isinstance(runs_on, list):
            runs_on = " ".join(str(x) for x in runs_on)
        runner_default = 'pwsh' if 'windows' in str(runs_on).lower() else 'bash'
        for i, step in enumerate(job.get('steps') or []):
            if not isinstance(step, dict) or 'run' not in step:
                continue
            sh = step.get('shell') or job_shell or wf_shell or runner_default
            name = str(step.get('name') or ('step %d' % (i + 1)))
            body = step['run']
            if not isinstance(body, str):
                print("FATAL|%s / %s / %s: run: is not a string" % (f, jname, name))
                raise SystemExit(0)
            nsub = len(EXPR.findall(body))
            body = EXPR.sub('GHA_EXPR', body)
            nblocks += 1
            fn = os.path.join(work, 'block%03d.sh' % nblocks)
            open(fn, 'w', encoding='utf-8').write(body)
            found_here += 1
            man.append("%s|%s|%s|%s|%d|%s" % (f, jname, name, sh, nsub, fn))
    if found_here == 0:
        print("FATAL|%s contains no run: blocks at all; a workflow this check cannot "
              "see is not a workflow it has checked" % f)
        raise SystemExit(0)

if nblocks == 0:
    print("FATAL|no run: blocks were extracted from any workflow")
    raise SystemExit(0)
open(os.path.join(work, 'manifest'), 'w', encoding='utf-8').write("\n".join(man) + "\n")
print("OK|%d block(s) from %d workflow file(s)" % (nblocks, len(files)))
EXTRACT
)
extract_rc=$?
if [ "${extract_rc}" -ne 0 ]; then
    echo "regression-workflows: the extractor did not run (exit ${extract_rc}); its silence is not a verdict." >&2
    exit 2
fi
case "${verdict}" in
    FATAL\|*)
        echo "regression-workflows: FAIL  ${verdict#FATAL|}" >&2
        exit 1 ;;
    OK\|*) : ;;
    *)
        echo "regression-workflows: the extractor printed nothing recognisable: '${verdict}'" >&2
        exit 2 ;;
esac
echo "  extracted: ${verdict#OK|}"

[ -s "${work}/manifest" ] || {
    echo "regression-workflows: the extractor reported OK but wrote no manifest." >&2; exit 2; }

fails=0; checked=0; skipped=0; subs=0; delegated=0; unchecked=0; unchecked_lines=0
while IFS='|' read -r file job step shell nsub blockfile; do
    [ -n "${file}" ] || continue
    subs=$((subs + nsub))
    case "${shell}" in
        bash|sh|bash\ *|sh\ *|/bin/bash*|/bin/sh*)
            if out=$(bash -n "${blockfile}" 2>&1); then
                printf '  %-34s %-26s %-5s OK\n' "${file}" "$(printf '%.26s' "${step}")" "${shell}"
                checked=$((checked + 1))
            else
                printf '  %-34s %-26s %-5s SYNTAX ERROR\n' "${file}" "$(printf '%.26s' "${step}")" "${shell}"
                # The line number is the one inside the extracted block, which
                # is what a reader needs to find it in the run: body.
                printf '%s\n' "${out}" | sed "s|${blockfile}|${file} / ${step} (run: block line)|" | sed 's/^/        /'
                fails=$((fails + 1))
            fi
            ;;
        *)
            # NOT A SKIP IN SILENCE, AND NOT A BLANKET ONE EITHER (OC-96).
            #
            # "not bash-checked" was true and uninformative. Measured: EIGHT of
            # the ten cmd blocks in windows-platform-facts.yml are a SINGLE
            # LINE invoking `bash .github/scripts/windows-facts.sh <subcommand>`
            # through MSYS2, and that script IS checked by bash -n below. So
            # their substance is checked; only the wrapper is not.
            #
            # The two that carry real cmd logic are reported as such, with
            # their line count, because that is the unchecked surface and a
            # number is the only honest way to describe it. cmd has no -n
            # equivalent and no parser this project can invoke -- pwsh is not
            # installed on the development host either -- so this is a
            # measurement of what is unchecked, not a check.
            nlines=$(grep -c . "${blockfile}" 2>/dev/null || echo 0)
            delegates=$(grep -c 'windows-facts\.sh' "${blockfile}" 2>/dev/null || echo 0)
            if [ "${nlines}" -le 2 ] && [ "${delegates}" -ge 1 ]; then
                printf '  %-34s %-26s %-5s delegates to a bash script (checked below)\n' \
                    "${file}" "$(printf '%.26s' "${step}")" "${shell}"
                delegated=$((delegated + 1))
            else
                printf '  %-34s %-26s %-5s UNCHECKED: %s line(s) of %s logic\n' \
                    "${file}" "$(printf '%.26s' "${step}")" "${shell}" "${nlines}" "${shell}"
                unchecked=$((unchecked + 1))
                unchecked_lines=$((unchecked_lines + nlines))
            fi
            skipped=$((skipped + 1))
            ;;
    esac
done < "${work}/manifest"

# Shell scripts the workflows invoke are bash whatever the step's shell is, so
# they are checked directly rather than through the cmd blocks that call them.
for s in "${repo}"/.github/scripts/*.sh; do
    [ -e "${s}" ] || continue
    if out=$(bash -n "${s}" 2>&1); then
        printf '  %-34s %-26s %-5s OK\n' ".github/scripts" "$(basename "${s}")" "bash"
        checked=$((checked + 1))
    else
        printf '  %-34s %-26s %-5s SYNTAX ERROR\n' ".github/scripts" "$(basename "${s}")" "bash"
        printf '%s\n' "${out}" | sed 's/^/        /'
        fails=$((fails + 1))
    fi
done

echo
printf '  %d block(s) checked with bash -n; %d not, of which %d delegate to a checked bash script\n' \
    "${checked}" "${skipped}" "${delegated}"
printf '  UNCHECKED SURFACE: %d block(s), %d line(s) of shell no syntax tool here can parse\n' \
    "${unchecked}" "${unchecked_lines}"
printf '  %d GitHub expression(s) substituted\n' "${subs}"

# SHAPE-03: an empty accumulator reads as success. Zero blocks checked means
# this script looked at nothing, whatever the exit status would otherwise say.
if [ "${checked}" -eq 0 ]; then
    echo "regression-workflows: NOTHING was checked, so this run supports no claim." >&2
    exit 2
fi
if [ "${fails}" -eq 0 ]; then
    echo "regression-workflows: PASS"
    exit 0
fi
echo "regression-workflows: FAIL (${fails} block(s) with a syntax error)"
exit 1
