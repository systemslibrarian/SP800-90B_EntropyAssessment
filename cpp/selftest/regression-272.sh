#!/bin/bash
#
# Regression for the selftest gaps reported upstream as issue #272.
#
# Two independent faults are covered:
#
#   A. compareresults.pl collected only per-estimator values, so a fault
#      confined to main()'s final combination left every collected value
#      unchanged and the comparison passed. Mutants 1 and 2 below are exactly
#      that kind of fault.
#
#   B. selftest discarded compareresults.pl's exit status, so it exited 0
#      even after printing "Significant difference".
#
# The mutants are the two preserved in
# audits/2026-09-30/phase2-focused/repro/issue272/. Each is applied to a
# scratch copy of cpp/; nothing in the working tree is modified.
#
# For A the test deliberately uses a sample that compares clean on this
# platform, and asserts that the mutant is caught *and* that the keys which
# caught it are the final figures. That distinguishes a real detection from
# the pre-existing cross-platform predictor deltas (upstream #155), which
# make some other samples differ on non-Linux builds regardless.

set -u

here=$(cd "$(dirname "$0")" && pwd)
cpp=$(cd "${here}/.." && pwd)
repo=$(cd "${cpp}/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-reg272.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

fails=0
note() { printf '%-28s %s\n' "$1" "$2"; }

build() { # build <srcdir>
	( cd "$1" && make non_iid >/dev/null 2>&1 ) || return 1
	[ -x "$1/ea_non_iid" ]
}

# compare <binary> <sample basename> ; prints compareresults.pl output
compare() {
	local bin=$1 base=$2
	"${bin}" -vv "${repo}/bin/${base}.bin" > "${work}/${base}.res" 2>/dev/null
	"${here}/compareresults.pl" "${work}/${base}.res" "${here}/refdata/${base}.res" 2>&1
}

# ---------------------------------------------------------------- baseline
cp -R "${cpp}" "${work}/clean" || exit 2
rm -f "${work}/clean/ea_non_iid"
build "${work}/clean" || { echo "regression-272: baseline build failed" >&2; exit 2; }

# Samples chosen because the unmutated build compares clean against refdata on
# every platform tested; each mutant moves that sample's final figure.
#   mutant 1 (drops n x H_bitstring)  -> multi-bit sample, Assessed 7.2338 -> 7.8651
#   mutant 2 (drops H_original)       -> binary sample,    Assessed 0.0286 -> 1
m1_sample=truerand_8bit
m2_sample=biased-random-bits

for s in "${m1_sample}" "${m2_sample}"; do
	if out=$(compare "${work}/clean/ea_non_iid" "${s}") && \
	   ! printf '%s' "${out}" | grep -q 'Significant difference'; then
		note "baseline ${s}:" "clean (as required)"
	else
		note "baseline ${s}:" "UNEXPECTED mismatch on the unmutated build"
		printf '%s\n' "${out}" | sed 's/^/    /'
		fails=$((fails + 1))
	fi
done

# ---------------------------------------------- A. final-combination mutants
# assert_caught <label> <sample> <compareresults output>
assert_caught() {
	local label=$1 out=$3
	if ! printf '%s' "${out}" | grep -q 'Significant difference'; then
		note "${label}:" "NOT CAUGHT — the mutant passed the comparison"
		fails=$((fails + 1))
		return
	fi
	# The mutant changes only main()'s final combination, so the keys that
	# caught it must be final figures, not estimator values.
	local keys
	keys=$(printf '%s\n' "${out}" | sed -n 's/.*Significant difference for \(.*\) (reference.*/\1/p')
	if printf '%s\n' "${keys}" | grep -qvE '^(H_original|H_bitstring|H_bitstring Per Symbol|Assessed min entropy)$'; then
		note "${label}:" "caught, but by an estimator key (not the #272 gap)"
		printf '%s\n' "${keys}" | sed 's/^/    key: /'
		fails=$((fails + 1))
		return
	fi
	note "${label}:" "caught by final figures: $(printf '%s' "${keys}" | tr '\n' ' ')"
}

cp -R "${cpp}" "${work}/m1" && rm -f "${work}/m1/ea_non_iid"
perl -0pi -e 's/\Qh_assessed = min(h_assessed, H_bitstring * data.word_size);\E/\/* regression-272 mutant 1 *\//' "${work}/m1/non_iid_main.cpp"
if ! grep -q 'regression-272 mutant 1' "${work}/m1/non_iid_main.cpp"; then
	note "mutant 1:" "SOURCE PATTERN NOT FOUND — update this script"
	fails=$((fails + 1))
elif build "${work}/m1"; then
	assert_caught "mutant 1 (drop n x Hbit)" "${m1_sample}" "$(compare "${work}/m1/ea_non_iid" "${m1_sample}")"
else
	note "mutant 1:" "build failed"; fails=$((fails + 1))
fi

cp -R "${cpp}" "${work}/m2" && rm -f "${work}/m2/ea_non_iid"
perl -0pi -e 's/\Qh_assessed = min(h_assessed, H_original);\E/\/* regression-272 mutant 2 *\//' "${work}/m2/non_iid_main.cpp"
if ! grep -q 'regression-272 mutant 2' "${work}/m2/non_iid_main.cpp"; then
	note "mutant 2:" "SOURCE PATTERN NOT FOUND — update this script"
	fails=$((fails + 1))
elif build "${work}/m2"; then
	assert_caught "mutant 2 (drop H_original)" "${m2_sample}" "$(compare "${work}/m2/ea_non_iid" "${m2_sample}")"
else
	note "mutant 2:" "build failed"; fails=$((fails + 1))
fi

# ------------------------------------------- B. exit status of selftest itself
# A mismatch in the FIRST sample alone must make selftest exit nonzero. The
# whole harness is copied so that refdata can be edited without touching the
# working tree.
cp -R "${here}" "${work}/st"
rm -f "${work}/st"/*.res
ln -sf "${work}/clean/ea_non_iid" "${work}/clean/ea_non_iid.link" 2>/dev/null
first=$(basename "$(ls "${repo}"/bin/* | head -1)" .bin)
perl -pi -e 's/^(Literal Most Common Value Estimate: p_u = ).*/${1}0.9/' "${work}/st/refdata/${first}.res"
( cd "${work}/st" && ln -sf "${work}/clean/ea_non_iid" ../ea_non_iid 2>/dev/null; true )
mkdir -p "${work}/stroot" && cp -R "${work}/st" "${work}/stroot/selftest" && cp "${work}/clean/ea_non_iid" "${work}/stroot/ea_non_iid"
mkdir -p "${work}/stbin" && cp "${repo}"/bin/*.bin "${work}/stbin/" 2>/dev/null
# selftest resolves samples as ../../bin/* and the binary as ../ea_non_iid
mkdir -p "${work}/strepo/cpp" && cp -R "${work}/stroot/selftest" "${work}/strepo/cpp/selftest" && cp "${work}/clean/ea_non_iid" "${work}/strepo/cpp/ea_non_iid" && cp -R "${repo}/bin" "${work}/strepo/bin"
out=$( cd "${work}/strepo/cpp/selftest" && ./selftest 2>&1 ); rc=$?
if [ "${rc}" -ne 0 ]; then
	note "selftest exit status:" "nonzero (${rc}) when the first sample mismatches"
else
	note "selftest exit status:" "ZERO despite a mismatch in ${first} — the #272 fault"
	fails=$((fails + 1))
fi
if printf '%s' "${out}" | grep -q "${first}"; then
	note "selftest naming:" "the failing sample is named in the summary"
else
	note "selftest naming:" "failing sample not named"
	fails=$((fails + 1))
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-272: PASS"
	exit 0
fi
echo "regression-272: FAIL (${fails} checks)"
exit 1
