#!/bin/bash
#
# Regression for AA-04 (audit 2026-11-07, repro/PROV-10): ea_restart records
# which row or column estimator declined, and carries the figure it awards.
#
# WHAT WAS WRONG. ea_restart runs each literal estimator on the rows and again
# on the columns of the 1000 x 1000 restart matrix and folds what comes back
# into H_r and H_c. R-2 (d892b90) stopped it folding the -1 "cannot be
# computed" sentinel in as an entropy; the declined estimate was then skipped
# SILENTLY. Its test case simply lacked h_r or h_c, so H_r or H_c was a
# minimum over fewer estimators than SP 800-90B 6.2 lists and nothing in the
# report said so -- the direction that can only raise the figure. ea_non_iid
# has said so since F05 (dfe325a, literalEstimateNotRun; 16 sites in
# non_iid_main.cpp); restart_main.cpp set no such flag at any of its 16 folds.
#
# And no field carried the awarded figure. SP 800-90B 3.1.4.2 (PDF p. 21):
# "the entropy assessment of the noise source is taken as the minimum of the
# row, the column and the initial estimates, i.e., min(Hr, Hc, HI)." Overall
# carried h_r, h_c and h_i only; the minimum was printed once, under verbose,
# so -q suppressed the one line that stated it, and a consumer reading h_i
# alone overstated (h_i >= the minimum).
#
# Measured before the fix (2026-11-07, ea_restart sha256 4d7ba82b..., x6 in
# docs/audits/2026-11-07-aggressive-audit/logs/experiments/): on the de Bruijn
# B(100,3) matrix the LRS Test case had h_c = 6.4427... and no h_r and no
# flag; Overall had h_r 6.5833..., h_c 6.3726..., h_i 0.5 and nothing else,
# while the text said "min(H_r, H_c, H_I): 0.500000".
#
# Now: the LRS Test case carries rowEstimateNotRun true, and Overall carries
# hAssessed = min(h_r, h_c, h_i). Like F05, a declined estimator is a fact
# about the run and not an error: errorLevel stays 0, asserted below.
#
# RULE 12 DECLARATION. The change touches ground four earlier repairs touched,
# and the case each was built for is exercised, here or where named:
#
#   * R-2 (d892b90) -- the `>= 0` folds in restart_main.cpp gain an else
#     branch; the guards themselves are unchanged. PAIR TEST: the R-2 section
#     of regression-restart.sh on this same input (H_r not -1, validation
#     passes), and the baseline assertion below that the run is accepted with
#     Overall.h_r present.
#   * F05 (dfe325a) -- literalEstimateNotRun/bitstringEstimateNotRun in
#     test_case_base.h and non_iid_main.cpp. Not edited; the restart flags
#     follow its rule. PAIR TEST: regression-notrun.sh is unchanged, and here
#     errorLevel must be 0 on the flagged report.
#   * NOVEL-03 (25fbb54) -- the restart report's rows/columns layout labels.
#     The new fields are named by the same two words. PAIR TEST:
#     regression-restart.sh's restart-report-label-test.
#   * C16 (a5005bd, kept by 7a0be01) -- the H_I intake and scale. hAssessed
#     is min(H_r, H_c, H_I) with H_I as C16 resolved it. PAIR TEST: H_I is
#     given as 0.5/symbol here and Overall.h_i must read 0.5.
#
# HEAVY. ea_restart accepts exactly 1,000,000 samples and nothing else, so
# this is a 1,000,000-sample run by construction: about 6 s on the development
# host (x6, 2026-11-07) plus the Python generator. It is one more such run in a
# suite whose regression-restart.sh already makes several.
#
# REGRESSION_RESTART_TOOL points this script at another build, for showing it
# FAIL against a pre-repair binary: a regression that has only ever been seen
# passing is an untested assertion.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
tool="${REGRESSION_RESTART_TOOL:-${here}/../ea_restart}"
gen="${repo}/audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regrsnr.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT HUP INT TERM

fails=0
note() { printf '%-58s %s\n' "$1" "$2"; }
[ -x "${tool}" ] || { echo "regression-restart-notrun: ${tool} missing (run 'make restart')" >&2; exit 2; }
[ -f "${gen}" ] || { echo "regression-restart-notrun: COULD NOT RUN (no generator at ${gen})" >&2; exit 2; }
# instrument rule 5, mechanised (OC-73): every read below is by label
. "${here}/labelread-lib.sh"
# BUILD STATE AS A PRINTED PRECONDITION (instrument rule 4, OC-43).
. "${here}/buildstate-lib.sh"
bs_print "${tool}"

# ------------------------------------------------------------- the fixture
# A de Bruijn B(100,3) sequence is exactly 1,000,000 samples (a compliant
# restart matrix) in which every 3-tuple occurs once and every 2-tuple about
# 100 times, so the LRS estimate on the rows hits "v < u, cannot be computed"
# (SP 800-90B 6.3.6 step 2). The same generator and seed as regression-notrun.sh
# and the R-2 section of regression-restart.sh. The generator asserts the
# 3-tuple uniqueness itself and prints "ok <n> max symbol <m>"; both are read
# here so the fixture is shown to be what it claims before anything is
# concluded from it.
if ! python3 "${gen}" 100 11 "${work}/db100.bin" > "${work}/gen.out" 2>&1; then
	echo "regression-restart-notrun: COULD NOT RUN (generator failed: $(cat "${work}/gen.out"))" >&2
	exit 2
fi
gen_n=$(sed -n 's/^ok \([0-9][0-9]*\) max symbol 99$/\1/p' "${work}/gen.out" | lr_one "generator ok line") || exit 2
bytes=$(wc -c < "${work}/db100.bin" | tr -d ' ')
if [ "${gen_n}" = "1000000" ] && [ "${bytes}" = "1000000" ]; then
	note "fixture: de Bruijn B(100,3), 1,000,000 bytes, 100 symbols:" "yes"
else
	note "fixture: de Bruijn B(100,3), 1,000,000 bytes, 100 symbols:" "generator said ${gen_n}, file is ${bytes} bytes"
	exit 2
fi

# ------------------------------------------------------------- the run
# Rule 17: output to files, the producer's exit status read, nothing piped.
# -v (verbose 2) prints the per-estimator lines and the "min(H_r, H_c, H_I):"
# line the JSON field is checked against; -o writes the report.
"${tool}" -n -v -o "${work}/db.json" "${work}/db100.bin" 8 0.5/symbol > "${work}/db.out" 2> "${work}/db.err"
rc=$?

# ------------------------------------------------------------- precondition
# RULE 7 / INSTRUMENT RULE 2. The baseline must be a well-formed, ACCEPTED
# report before any absence in it is read as a fact: exit 0, a parseable
# report with errorLevel 0 and the sanity check passed, "Validation Test
# Passed" printed exactly once, and the row LRS estimate really declined --
# the decline line printed exactly once (rows only), the LRS Test case holding
# h_c and lacking h_r. If the fixture stopped exercising the defect, that is a
# failure here, not a pass by default.
pre=0
if [ "${rc}" -eq 0 ]; then
	note "baseline: the run is accepted (exit 0):" "yes"
else
	note "baseline: the run is accepted (exit 0):" "exit ${rc}; stderr: $(tail -3 "${work}/db.err" | tr '\n' ' ')"
	pre=$((pre + 1))
fi
if validated=$(grep -c '^Validation Test Passed' "${work}/db.out") && [ "${validated}" = "1" ]; then
	note "baseline: 'Validation Test Passed' printed once:" "yes"
else
	note "baseline: 'Validation Test Passed' printed once:" "matched ${validated:-0} line(s)"
	pre=$((pre + 1))
fi
# One labelled pass over the report. Every case is found by testCaseDesc and
# a label that matches anything but exactly one case is a failure of the
# read, not a value (instrument rule 5). Facts come out one per line as
# name=value, '<absent>' for a key that is not there.
if ! python3 - "${work}/db.json" > "${work}/facts.txt" 2> "${work}/facts.err" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
cases = d.get("testCases") or []
def one(label):
    hits = [c for c in cases if c.get("testCaseDesc") == label]
    if len(hits) != 1:
        sys.stderr.write("LABELLED READ FAILED: testCaseDesc %r matched %d case(s), expected exactly 1\n" % (label, len(hits)))
        sys.exit(1)
    return hits[0]
def emit(name, v):
    print("%s=%s" % (name, "<absent>" if v is None else json.dumps(v)))
emit("errorLevel", d.get("errorLevel"))
emit("passedRestartSanityCheck", d.get("passedRestartSanityCheck"))
emit("cases", len(cases))
lrs = one("LRS Test")
ov = one("Overall")
for k in ("h_r", "h_c", "rowEstimateNotRun", "columnEstimateNotRun"):
    emit("lrs." + k, lrs.get(k))
for k in ("h_r", "h_c", "h_i", "hAssessed"):
    emit("overall." + k, ov.get(k))
# the minimum as a consumer would take it from the three fields, and how far
# the awarded field is from it
if all(k in ov for k in ("h_r", "h_c", "h_i")):
    m = min(ov["h_r"], ov["h_c"], ov["h_i"])
    emit("overall.min_h_r_h_c_h_i", m)
    emit("overall.hAssessed_minus_min", abs(ov["hAssessed"] - m) if "hAssessed" in ov else None)
else:
    emit("overall.min_h_r_h_c_h_i", None)
    emit("overall.hAssessed_minus_min", None)
# a flag on a case whose estimate ran would be a false positive; list any
spurious = sorted(c.get("testCaseDesc", "?") for c in cases
                  if c is not lrs and (c.get("rowEstimateNotRun") or c.get("columnEstimateNotRun")))
print("spuriousFlags=%s" % (";".join(spurious) if spurious else "none"))
PY
then
	note "baseline: the report parses and its labels resolve:" "no -- $(tr '\n' ' ' < "${work}/facts.err")"
	pre=$((pre + 1))
fi
fact() { sed -n "s/^$1=//p" "${work}/facts.txt" | lr_one "$1"; }
if [ "${pre}" -eq 0 ]; then
	errlevel=$(fact errorLevel) || exit 1
	sanity=$(fact passedRestartSanityCheck) || exit 1
	if [ "${errlevel}" = "0" ] && [ "${sanity}" = "true" ]; then
		note "baseline: errorLevel 0 and the sanity check passed:" "yes"
	else
		note "baseline: errorLevel 0 and the sanity check passed:" "errorLevel ${errlevel}, passedRestartSanityCheck ${sanity}"
		pre=$((pre + 1))
	fi
	ov_hr=$(fact overall.h_r) || exit 1
	ov_hi=$(fact overall.h_i) || exit 1
	if [ "${ov_hr}" != "<absent>" ] && [ "${ov_hi}" = "0.5" ]; then
		note "baseline: Overall carries h_r (R-2 holds) and h_i = 0.5 (C16 scale):" "h_r ${ov_hr}"
	else
		note "baseline: Overall carries h_r (R-2 holds) and h_i = 0.5 (C16 scale):" "h_r ${ov_hr}, h_i ${ov_hi}"
		pre=$((pre + 1))
	fi
	if declined=$(grep -c "^LRS Estimate: v<u. Can't Run LRS Test\.$" "${work}/db.out") && [ "${declined}" = "1" ]; then
		note "baseline: the LRS estimate declined exactly once (one of rows/cols):" "yes"
	else
		note "baseline: the LRS estimate declined exactly once (one of rows/cols):" "matched ${declined:-0} line(s); this input no longer exercises the defect"
		pre=$((pre + 1))
	fi
	lrs_hr=$(fact lrs.h_r) || exit 1
	lrs_hc=$(fact lrs.h_c) || exit 1
	if [ "${lrs_hr}" = "<absent>" ] && [ "${lrs_hc}" != "<absent>" ]; then
		note "baseline: it was the ROW estimate (LRS Test has h_c, lacks h_r):" "h_c ${lrs_hc}"
	else
		note "baseline: it was the ROW estimate (LRS Test has h_c, lacks h_r):" "h_r ${lrs_hr}, h_c ${lrs_hc}"
		pre=$((pre + 1))
	fi
fi
if [ "${pre}" -ne 0 ]; then
	echo
	echo "regression-restart-notrun: PRECONDITION FAILED (${pre} baseline check(s)); the checks below would be unattributable and were not read"
	exit 1
fi

# ------------------------------------------------------------- the checks
# 1. The declined row estimate is recorded on its case.
flag_r=$(fact lrs.rowEstimateNotRun) || exit 1
if [ "${flag_r}" = "true" ]; then
	note "LRS Test carries rowEstimateNotRun true:" "yes"
else
	note "LRS Test carries rowEstimateNotRun true:" "${flag_r} (the decline is silent)"
	fails=$((fails + 1))
fi
# 2. The column estimate ran, so no column flag: a flag on a computed estimate
#    would make the field useless.
flag_c=$(fact lrs.columnEstimateNotRun) || exit 1
if [ "${flag_c}" = "<absent>" ]; then
	note "LRS Test carries no columnEstimateNotRun (that estimate ran):" "yes"
else
	note "LRS Test carries no columnEstimateNotRun (that estimate ran):" "${flag_c}"
	fails=$((fails + 1))
fi
# 3. No other case is flagged: every other estimator produced both values.
spurious=$(fact spuriousFlags) || exit 1
if [ "${spurious}" = "none" ]; then
	note "no other case carries a row or column flag:" "none"
else
	note "no other case carries a row or column flag:" "${spurious}"
	fails=$((fails + 1))
fi
# 4. Overall carries the awarded figure, equal to min(h_r, h_c, h_i). All four
#    are the same doubles through the same printer, so the difference is 0;
#    the tolerance covers only the printer's rounding.
hass=$(fact overall.hAssessed) || exit 1
hmin=$(fact overall.min_h_r_h_c_h_i) || exit 1
hdiff=$(fact overall.hAssessed_minus_min) || exit 1
if [ "${hass}" != "<absent>" ] && python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) <= 1e-12 else 1)' "${hdiff}"; then
	note "Overall carries hAssessed = min(h_r, h_c, h_i):" "${hass} (min ${hmin})"
else
	note "Overall carries hAssessed = min(h_r, h_c, h_i):" "hAssessed ${hass}, min ${hmin}, difference ${hdiff}"
	fails=$((fails + 1))
fi
# 5. And it is the quantity the tool already printed, read by its label; %f
#    carries six decimals, so the tolerance is half a unit in the sixth.
hass_txt=$(sed -n 's/^min(H_r, H_c, H_I): //p' "${work}/db.out" | lr_one "min(H_r, H_c, H_I) line") || exit 1
if [ "${hass}" != "<absent>" ] && python3 -c 'import sys; sys.exit(0 if abs(float(sys.argv[1]) - float(sys.argv[2])) <= 5e-7 else 1)' "${hass}" "${hass_txt}"; then
	note "hAssessed agrees with the printed min(H_r, H_c, H_I):" "text ${hass_txt}"
else
	note "hAssessed agrees with the printed min(H_r, H_c, H_I):" "json ${hass}, text ${hass_txt}"
	fails=$((fails + 1))
fi
# 6. A declined estimator is not an error (F05's distinction, kept).
if [ "${errlevel}" = "0" ]; then
	note "a declined estimator is not an error:" "errorLevel 0"
else
	note "a declined estimator is not an error:" "errorLevel ${errlevel}"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-restart-notrun: PASS"
	exit 0
fi
echo "regression-restart-notrun: FAIL (${fails} checks)"
exit 1
