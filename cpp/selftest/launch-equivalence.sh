#!/bin/bash
#
# launch-equivalence.sh -- MEASURE that this tree and its base commit produce
# byte-identical deterministic figures on this host (launch/b63aff1-windows).
#
# The launch branch carries only the repairs the three tools need to run on
# native Windows, and the claim "nothing changes any computed figure" is not
# asserted from the diff; it is measured here, on every platform the branch is
# built for, by running the base commit's tools and this tree's tools over the
# same corpus and comparing every report and every -vv transcript.
#
# What is compared, and how:
#   * ea_non_iid: the -vv text transcript byte for byte (the selftest's own
#     artefact, every intermediate printed), and the JSON report with only
#     dateTimeStamp and commandline set aside (commandline names the binary).
#   * ea_iid and ea_restart: the JSON report, with the fields that the SAME
#     binary changes between two of its own runs set aside -- the permutation
#     tests seed from the OS, so those fields are excluded BY MEASUREMENT, the
#     way OC-53 compared before and after C18 -- and the pass/fail verdicts,
#     counts and shapes of those seeded groups still required to match.
#   * the entropy floor (audits/.../oracles/entropy_floor.py, this tree's
#     copy) run on both builds' ea_non_iid reports: identical output.
#   * exit statuses, always.
#   * the comparator is shown LIVE: a 1e-15 perturbation of one figure in a
#     copy of a report must be reported as a difference, or this script is a
#     harness fault (exit 2), never a pass.
#
# Corpus: the eleven inputs under bin/ that the selftest uses (digests checked
# against cpp/selftest/fixture-manifest.txt), plus three generated streams
# from fixed seeds whose digests are printed. Short inputs run with
# EA_ALLOW_SHORT_DATASET=1 as the selftest does.
#
# Refuses (exit 2) rather than guessing when: the tree has uncommitted changes
# under cpp/ (what would be measured is not what is committed), a build fails,
# a corpus digest mismatches, or the live check does not fire.
#
#   LAUNCH_BASE=<commit>     the base to compare against (default b63aff1)
#   LAUNCH_EQ_WORK=<dir>     keep the work directory (default: a temp dir)
#   LAUNCH_EQ_REUSE=1        reuse the builds already in LAUNCH_EQ_WORK
#   LAUNCH_EQ_INPUTS="a b"   run only the named corpus inputs (a piecewise run
#                            on a host that cannot hold the whole run; the
#                            summary line then says PARTIAL and never PASS)

set -u
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
BASE=${LAUNCH_BASE:-b63aff1}
work=${LAUNCH_EQ_WORK:-$(mktemp -d "${TMPDIR:-/tmp}/ea-eq.XXXXXX")} || exit 2
keep=${LAUNCH_EQ_WORK:-}
[ -n "${keep}" ] || trap 'rm -rf "${work}"' EXIT HUP INT TERM
mkdir -p "${work}"
fails=0; harness=0; n_cmp=0; n_same=0
say()  { printf '  %-60s %s\n' "$1" "$2"; }
ok()   { say "$1" "PASS${2:+  $2}"; }
bad()  { say "$1" "FAIL  ${2:-}"; fails=$((fails + 1)); }
hfault() { say "$1" "HARNESS FAULT  ${2:-}"; harness=$((harness + 1)); }
sha_of() { local h; h=$( (command -v shasum >/dev/null && shasum -a 256 "$1") || sha256sum "$1" ); echo "${h%% *}"; }

echo "launch-equivalence: base ${BASE}, head $(git -C "${repo}" rev-parse --short HEAD), host $(uname -s) $(uname -m), $(${CXX:-c++} --version 2>/dev/null | head -1)"

# ---------------------------------------------------------------- preconditions
if [ -n "$(git -C "${repo}" status --porcelain -- cpp/ 2>/dev/null)" ]; then
    hfault "the working tree has uncommitted changes under cpp/" "commit them; what is measured must be what is pinned"
fi
git -C "${repo}" cat-file -e "${BASE}^{commit}" 2>/dev/null || hfault "base commit ${BASE} is not in this repository" "fetch the full history"
[ "${harness}" -eq 0 ] || { echo "launch-equivalence: REFUSED (${harness} harness fault(s))"; exit 2; }

# ---------------------------------------------------------------- two builds
build_tree() { # build_tree <label> <commit>
    local label=$1 commit=$2 d="${work}/${1}"
    mkdir -p "${d}"
    git -C "${repo}" archive "${commit}" cpp | tar -x -C "${d}" || return 1
    ( cd "${d}/cpp" && make -B non_iid iid restart ) > "${d}/build.log" 2>&1 || return 1
    [ -x "${d}/cpp/ea_non_iid" ] && [ -x "${d}/cpp/ea_iid" ] && [ -x "${d}/cpp/ea_restart" ]
}
if [ "${LAUNCH_EQ_REUSE:-0}" = 1 ] && [ -x "${work}/base/cpp/ea_restart" ] && [ -x "${work}/head/cpp/ea_restart" ]; then
    say "builds" "reused from ${work} (LAUNCH_EQ_REUSE=1)"
else
    if build_tree base "${BASE}"; then ok "built ${BASE} (base)"; else hfault "build of ${BASE} failed" "see ${work}/base/build.log"; fi
    if build_tree head HEAD;      then ok "built HEAD (this tree)"; else hfault "build of HEAD failed" "see ${work}/head/build.log"; fi
fi
[ "${harness}" -eq 0 ] || { echo "launch-equivalence: REFUSED (${harness} harness fault(s))"; exit 2; }
for t in ea_non_iid ea_iid ea_restart; do
    say "sha256 ${t}" "base $(sha_of "${work}/base/cpp/${t}" | cut -c1-16)  head $(sha_of "${work}/head/cpp/${t}" | cut -c1-16)"
done

# ---------------------------------------------------------------- the corpus
mkdir -p "${work}/corpus"
ncorp=0
while read -r kind name want; do
    [ "${kind}" = "input" ] || continue
    f="${repo}/bin/${name}"
    if [ ! -r "${f}" ]; then bad "corpus input ${name}" "missing"; continue; fi
    got=$(sha_of "${f}")
    if [ "${got}" != "${want}" ]; then hfault "corpus input ${name}" "digest ${got:0:16} != manifest ${want:0:16}"; continue; fi
    cp "${f}" "${work}/corpus/${name}"; ncorp=$((ncorp + 1))
done < "${here}/fixture-manifest.txt"
# three generated streams, fixed seeds: splitmix64 bit 0 (1-bit), splitmix64
# low byte (8-bit), and a biased 8-bit stream (two seeded splitmix draws OR'd)
cat > "${work}/gen.c" <<'GENEOF'
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static unsigned long long sm(unsigned long long *x){ *x += 0x9E3779B97F4A7C15ULL; unsigned long long z=*x;
  z=(z^(z>>30))*0xBF58476D1CE4E5B9ULL; z=(z^(z>>27))*0x94D049BB133111EBULL; return z^(z>>31); }
int main(int argc,char**argv){ if(argc<2) return 2; unsigned long long x=0x90B2026ULL, y=0x5EEDULL;
  for(long i=0;i<1000000;i++){ unsigned long long z=sm(&x);
    if(!strcmp(argv[1],"bit")) putchar((int)(z&1ULL));
    else if(!strcmp(argv[1],"byte")) putchar((int)(z&0xffULL));
    else if(!strcmp(argv[1],"biased")) putchar((int)((z|sm(&y))&0xffULL));
    else return 2; } return 0; }
GENEOF
cc -O1 -o "${work}/gen" "${work}/gen.c" 2>/dev/null || { hfault "no C compiler for the generated streams" ""; }
for g in bit byte biased; do
    "${work}/gen" "${g}" > "${work}/corpus/gen_${g}.bin" && ncorp=$((ncorp + 1))
    say "generated gen_${g}.bin" "sha256 $(sha_of "${work}/corpus/gen_${g}.bin" | cut -c1-16)"
done
say "corpus" "${ncorp} inputs"
[ "${harness}" -eq 0 ] || { echo "launch-equivalence: REFUSED (${harness} harness fault(s))"; exit 2; }

# ---------------------------------------------------------------- the comparator
cat > "${work}/cmp.py" <<'PYEOF'
import json, sys
# cmp.py <a.json> <b.json> [excluded.dotted.path ...]  -> prints differing paths; exit 1 if any
def walk(x, p, out):
    if isinstance(x, dict):
        for k in sorted(x): walk(x[k], p + "." + k, out)
    elif isinstance(x, list):
        out[p + ".#len"] = len(x)
        for i, v in enumerate(x): walk(v, p + "[%d]" % i, out)
    else:
        out[p] = x
a = {}; b = {}
walk(json.load(open(sys.argv[1])), "", a); walk(json.load(open(sys.argv[2])), "", b)
excl = sys.argv[3:]
def excluded(p):
    if p.endswith(".#len"): return False   # a seeded group's SIZE is not seeded: always compared
    return any(p == e or p.startswith(e + ".") or p.startswith(e + "[") for e in excl)
diff = [p for p in sorted(set(a) | set(b)) if not excluded(p) and a.get(p, "<absent>") != b.get(p, "<absent>")]
for p in diff: print("  differs: %s  %r != %r" % (p, a.get(p, "<absent>"), b.get(p, "<absent>")))
sys.exit(1 if diff else 0)
PYEOF
cat > "${work}/leaves.py" <<'PYEOF'
import json, sys
# leaves.py <a.json> <b.json> -> prints the dotted paths whose values differ (the seeded set), excluding nothing
def walk(x, p, out):
    if isinstance(x, dict):
        for k in sorted(x): walk(x[k], p + "." + k, out)
    elif isinstance(x, list):
        out[p + ".#len"] = len(x)
        for i, v in enumerate(x): walk(v, p + "[%d]" % i, out)
    else: out[p] = x
a = {}; b = {}
walk(json.load(open(sys.argv[1])), "", a); walk(json.load(open(sys.argv[2])), "", b)
for p in sorted(set(a) | set(b)):
    if a.get(p, "<absent>") != b.get(p, "<absent>"): print(p)
PYEOF
cat > "${work}/perturb.py" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1])); tc = d["testCases"][0]
k = next(k for k in ("hOriginal", "hAssessed", "h_r") if k in tc)
tc[k] = tc[k] + 1e-15 if isinstance(tc[k], float) else tc[k]
json.dump(d, open(sys.argv[2], "w"), indent=1)
print(k)
PYEOF
ALWAYS_EXCL=".dateTimeStamp .commandline"

# ---------------------------------------------------------------- the seeded set, measured
# Run ea_iid and ea_restart TWICE with the base binary on one input; the paths
# that differ are what the OS seed touches. That set, and only that set, is
# excluded below -- and it is printed, so a reader can see it is the
# permutation groups and nothing else.
seed_in="${work}/corpus/gen_bit.bin"
export EA_ALLOW_SHORT_DATASET=1
if ! ( cd "${work}" && "${work}/base/cpp/ea_iid" -i -q -o seed1.json "${seed_in}" 1 >/dev/null 2>&1 && "${work}/base/cpp/ea_iid" -i -q -o seed2.json "${seed_in}" 1 >/dev/null 2>&1 ); then
    hfault "the two base ea_iid runs for the seeded-set measurement did not both succeed" ""
fi
# reduce each differing leaf to the test-case field that holds it
# (.testCases[0].permutationTestResults[2].compression -> .testCases[0].permutationTestResults)
reduce_seeded() { grep -vE '^\.(dateTimeStamp|commandline)$' | sed -E 's/^(\.testCases\[[0-9]+\]\.[A-Za-z0-9_]+)([\.\[].*)?$/\1/' | sort -u | tr '\n' ' '; }
IID_SEEDED=$(python3 "${work}/leaves.py" "${work}/seed1.json" "${work}/seed2.json" | reduce_seeded)
if ! ( cd "${work}" && "${work}/base/cpp/ea_restart" -i -q -o rseed1.json "${seed_in}" 1 0.9 >/dev/null 2>&1 && "${work}/base/cpp/ea_restart" -i -q -o rseed2.json "${seed_in}" 1 0.9 >/dev/null 2>&1 ); then
    hfault "the two base ea_restart runs for the seeded-set measurement did not both succeed" ""
fi
RS_SEEDED=$(python3 "${work}/leaves.py" "${work}/rseed1.json" "${work}/rseed2.json" | reduce_seeded)
say "ea_iid fields the OS seed changes (measured)" "${IID_SEEDED:-NONE}"
say "ea_restart fields the OS seed changes (measured)" "${RS_SEEDED:-NONE}"
case " ${IID_SEEDED} " in *permutationTestResults*) ;; *) hfault "the seeded-field measurement did not find the permutation groups for ea_iid" "${IID_SEEDED:-nothing differed}" ;; esac
case " ${RS_SEEDED} " in *permutationTestResults*) ;; *) hfault "the seeded-field measurement did not find the permutation groups for ea_restart" "${RS_SEEDED:-nothing differed}" ;; esac
for p in ${IID_SEEDED} ${RS_SEEDED}; do
    case "${p}" in *permutationTestResults*) ;; *) bad "the OS seed changed a field outside the permutation groups" "${p}" ;; esac
done
# the groups' pass/fail verdicts and shapes are NOT excluded: the comparator keeps
# .passedIidPermutationTests, .ranIidPermutationTests and the groups' #len
[ "${harness}" -eq 0 ] || { echo "launch-equivalence: REFUSED (${harness} harness fault(s))"; exit 2; }

# ---------------------------------------------------------------- the live check
if ! python3 "${work}/perturb.py" "${work}/seed1.json" "${work}/seed1p.json" > "${work}/perturbed-field.txt" 2>&1; then
    hfault "the perturbation could not be made" "$(head -1 "${work}/perturbed-field.txt")"
fi
pfield=$(cat "${work}/perturbed-field.txt")
python3 "${work}/cmp.py" "${work}/seed1.json" "${work}/seed1p.json" ${ALWAYS_EXCL} ${IID_SEEDED} > "${work}/live.txt" 2>&1
liverc=$?
# exit 1 AND the perturbed field named: an exception in the comparator (exit
# 2, a traceback) must not pass for a reported difference
if [ "${liverc}" -eq 1 ] && grep -q "differs: .testCases\[0\].${pfield} " "${work}/live.txt"; then
    ok "comparator live" "a 1e-15 perturbation of ${pfield} is reported"
else
    hfault "the comparator is NOT live" "exit ${liverc}; a 1e-15 perturbation of ${pfield} was not reported by name: $(head -1 "${work}/live.txt")"
fi
[ "${harness}" -eq 0 ] || { echo "launch-equivalence: REFUSED (${harness} harness fault(s))"; exit 2; }

# ---------------------------------------------------------------- the runs
run_both() { # run_both <label> <outname> <tool> <args...>; sets RC (agreed exit status) or returns 1 after a FAIL
    # No command substitution around this: a FAIL printed inside $(...) would
    # be captured into the variable instead of shown, and its count lost in
    # the subshell -- which is exactly what happened to the first version.
    local label=$1 out=$2 tool=$3; shift 3
    local rc_b rc_h
    ( cd "${work}/out-base" && "${work}/base/cpp/${tool}" "$@" > "${out}.txt" 2>&1 ); rc_b=$?
    ( cd "${work}/out-head" && "${work}/head/cpp/${tool}" "$@" > "${out}.txt" 2>&1 ); rc_h=$?
    if [ "${rc_b}" -ne "${rc_h}" ]; then
        # THE BASELINE-AGAINST-ITSELF CONTROL (OC-53). ea_iid and ea_restart's
        # exit status carries the permutation verdict, which the OS seed can
        # flip on a marginal input. Before calling a difference a difference,
        # run the BASE binary again on the same input: if it disagrees with
        # itself, the status is seeded on this input and is noted, not failed.
        case "${tool}" in
            ea_iid|ea_restart)
                local rc_b2
                ( cd "${work}/out-base2" && "${work}/base/cpp/${tool}" "$@" > "${out}.txt" 2>&1 ); rc_b2=$?
                if [ "${rc_b2}" -ne "${rc_b}" ]; then
                    say "${label}: exit status seeded on this input" "base ${rc_b} then ${rc_b2}, head ${rc_h} -- the verdict flips run to run"
                    RC="${rc_b}/${rc_b2}/${rc_h}"; return 0
                fi ;;
        esac
        bad "${label}: exit status" "base ${rc_b} head ${rc_h}"; return 1
    fi
    RC=${rc_b}
}
# compare_seeded <label> <base.json> <head.json> <base2-rerun: tool args...>
# The report comparison with the measured seeded fields excluded; if a
# difference remains, the base binary is run again and the difference is
# accepted only if the base differs from ITSELF in exactly those fields.
compare_seeded() {
    local label=$1 bj=$2 hj=$3 out=$4 tool=$5 seeded=$6; shift 6
    if python3 "${work}/cmp.py" "${bj}" "${hj}" ${ALWAYS_EXCL} ${seeded} > "${work}/${out}.diff" 2>&1; then
        n_same=$((n_same + 1)); ok "${label} identical outside the seeded groups" "(rc ${RC})"; return 0
    fi
    ( cd "${work}/out-base2" && "${work}/base/cpp/${tool}" "$@" > "${out}.rerun.txt" 2>&1 )
    local bj2="${work}/out-base2/$(basename "${bj}")"
    if [ -s "${bj2}" ]; then
        local dh db2 extra
        dh=$(python3 "${work}/leaves.py" "${bj}" "${hj}" | reduce_seeded)
        db2=$(python3 "${work}/leaves.py" "${bj}" "${bj2}" | reduce_seeded)
        extra=""
        for p in ${dh}; do case " ${db2} " in *" ${p} "*) ;; *) extra="${extra} ${p}" ;; esac; done
        if [ -z "${extra}" ]; then
            n_same=$((n_same + 1)); ok "${label} identical outside what the seed changes ON THIS INPUT" "base differs from itself in:${dh:+ ${dh}}"; return 0
        fi
        bad "${label} DIFFERS beyond the seed" "${extra} (base-vs-head: ${dh}; base-vs-base: ${db2:-none})"; return 1
    fi
    bad "${label} DIFFERS" "$(head -2 "${work}/${out}.diff" | tr '\n' ' ')"; return 1
}
mkdir -p "${work}/out-base" "${work}/out-head" "${work}/out-base2"
for f in "${work}"/corpus/*.bin; do
    name=$(basename "${f}" .bin)
    if [ -n "${LAUNCH_EQ_INPUTS:-}" ]; then
        case " ${LAUNCH_EQ_INPUTS} " in *" ${name} "*) ;; *) continue ;; esac
    fi
    nbytes=$(wc -c < "${f}" | tr -d ' ')
    # ---- ea_non_iid, -vv text (the selftest's artefact), byte for byte
    run_both "${name}: ea_non_iid -vv" "${name}.nonIID.vv" ea_non_iid -vv "${f}" || continue; rc=${RC}
    n_cmp=$((n_cmp + 1))
    if cmp -s "${work}/out-base/${name}.nonIID.vv.txt" "${work}/out-head/${name}.nonIID.vv.txt"; then
        n_same=$((n_same + 1)); ok "${name}: ea_non_iid -vv transcript identical" "(rc ${rc}, $(wc -l < "${work}/out-base/${name}.nonIID.vv.txt" | tr -d ' ') lines)"
    else
        bad "${name}: ea_non_iid -vv transcript DIFFERS" "$(diff "${work}/out-base/${name}.nonIID.vv.txt" "${work}/out-head/${name}.nonIID.vv.txt" | head -3 | tr '\n' ' ')"
    fi
    # ---- ea_non_iid JSON (-i -a), and the floor on it
    run_both "${name}: ea_non_iid json" "${name}.nonIID.json.run" ea_non_iid -i -a -q -o "${name}.nonIID.json" "${f}" || continue; rc=${RC}
    n_cmp=$((n_cmp + 1))
    if [ -s "${work}/out-base/${name}.nonIID.json" ] && python3 "${work}/cmp.py" "${work}/out-base/${name}.nonIID.json" "${work}/out-head/${name}.nonIID.json" ${ALWAYS_EXCL} > "${work}/${name}.nonIID.diff" 2>&1; then
        n_same=$((n_same + 1)); ok "${name}: ea_non_iid report identical" "(rc ${rc})"
        fb=$(python3 "${repo}/audits/2026-10-11-independent-audit/oracles/entropy_floor.py" "${work}/out-base/${name}.nonIID.json" 2>&1 | grep -vE 'dateTimeStamp|\.json' )
        fh=$(python3 "${repo}/audits/2026-10-11-independent-audit/oracles/entropy_floor.py" "${work}/out-head/${name}.nonIID.json" 2>&1 | grep -vE 'dateTimeStamp|\.json' )
        if ! printf '%s' "${fb}" | grep -qE 'MEASURED FLOOR|EVALUATED MARGIN|FLOOR'; then
            # the oracle refused (a short, non-compliant input): two identical
            # refusals are not a floor comparison and are not counted as one;
            # two DIFFERENT refusals are a difference
            if [ "${fb}" = "${fh}" ]; then say "${name}: entropy floor" "the oracle refused identically on both reports -- no floor to compare: $(printf '%s' "${fb}" | head -1 | cut -c1-70)"
            else bad "${name}: entropy floor: the oracle's refusal DIFFERS between the builds" ""; fi
        else
            n_cmp=$((n_cmp + 1))
            if [ "${fb}" = "${fh}" ]; then n_same=$((n_same + 1)); ok "${name}: entropy floor identical" "$(printf '%s' "${fb}" | grep -E 'FLOOR|MARGIN|floor' | head -1 | cut -c1-60)"
            else bad "${name}: entropy floor DIFFERS" ""; fi
        fi
    elif [ ! -s "${work}/out-base/${name}.nonIID.json" ]; then
        say "${name}: ea_non_iid report" "neither build wrote a report (rc ${rc}); exit status agreed"
    else
        bad "${name}: ea_non_iid report DIFFERS" "$(head -2 "${work}/${name}.nonIID.diff" | tr '\n' ' ')"
    fi
    # ---- ea_iid JSON, seeded fields excluded by measurement
    run_both "${name}: ea_iid" "${name}.iid.run" ea_iid -i -q -o "${name}.iid.json" "${f}" || continue; rc=${RC}
    n_cmp=$((n_cmp + 1))
    if [ -s "${work}/out-base/${name}.iid.json" ]; then
        compare_seeded "${name}: ea_iid report" "${work}/out-base/${name}.iid.json" "${work}/out-head/${name}.iid.json" "${name}.iid" ea_iid "${IID_SEEDED}" -i -q -o "${name}.iid.json" "${f}"
    else
        say "${name}: ea_iid report" "neither build wrote a report (rc ${rc}); exit status agreed"
    fi
    # ---- ea_restart JSON, only where the input is a 1000x1000 matrix (1,000,000 samples)
    if [ "${nbytes}" -eq 1000000 ]; then
        run_both "${name}: ea_restart" "${name}.rs.run" ea_restart -i -q -o "${name}.rs.json" "${f}" 0.9 || continue; rc=${RC}
        n_cmp=$((n_cmp + 1))
        if [ -s "${work}/out-base/${name}.rs.json" ]; then
            compare_seeded "${name}: ea_restart report" "${work}/out-base/${name}.rs.json" "${work}/out-head/${name}.rs.json" "${name}.rs" ea_restart "${RS_SEEDED}" -i -q -o "${name}.rs.json" "${f}" 0.9
        else
            say "${name}: ea_restart report" "neither build wrote a report (rc ${rc}); exit status agreed"
        fi
    fi
done

echo
echo "launch-equivalence: ${n_same} of ${n_cmp} comparisons identical; base ${BASE}, head $(git -C "${repo}" rev-parse --short HEAD); seeded fields excluded: ${IID_SEEDED}${RS_SEEDED}"
if [ "${harness}" -ne 0 ]; then echo "launch-equivalence: REFUSED (${harness} harness fault(s))"; exit 2; fi
if [ -n "${LAUNCH_EQ_INPUTS:-}" ]; then
    echo "launch-equivalence: PARTIAL (${LAUNCH_EQ_INPUTS}); ${fails} difference(s) -- a PASS needs the whole corpus in one run"
    [ "${fails}" -eq 0 ] && exit 0; exit 1
fi
if [ "${fails}" -eq 0 ] && [ "${n_cmp}" -ge 20 ]; then echo "launch-equivalence: PASS"; exit 0; fi
[ "${n_cmp}" -ge 20 ] || echo "launch-equivalence: too few comparisons ran (${n_cmp})"
echo "launch-equivalence: FAIL (${fails})"; exit 1
