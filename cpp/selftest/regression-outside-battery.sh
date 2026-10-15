#!/bin/bash
#
# Regression for OC-15/16/17/18: pins the calibration of
# tools/outside-battery-check and the battery behaviour it exists because of.
#
# WHY OUTCOMES AND NOT CONSTANTS
#
# Pinning the threshold constants would catch an edit to the thresholds and
# nothing else. These checks pin the MEASURED OUTCOMES -- B's spectral peak at
# 8538.7x and 59.938 Hz, E at 40.21 sigma at lag 5000 -- so a change in the FFT,
# the correlation accumulator, the mean-centering, or the z normalisation fails
# here even if every constant in the file is untouched.
#
# WHAT IS PINNED
#
#   1. 0 of 25 clean streams fire. Two different generators (5 Mersenne
#      Twister, 20 SHA-256 counter mode), all seeded.
#   2. All five linearly-visible defects fire: B, C, D, E, F.
#   3. B's spectral peak: 8538.7x mean power at 59.938 Hz (at 300 kHz).
#   4. E: 40.21 sigma at lag 5000, the reference weak long-lag defect.
#   5. G_xor13_02 does NOT fire. This is OC-18, the combined blind spot: it is
#      invisible to this tool BY CONSTRUCTION, and a future version that starts
#      firing on it has changed its coverage and must be re-documented, not
#      silently accepted. A check that fires on everything pins nothing.
#   6. Compression binds 5 of 5 clean streams at 0.8546 +/- 0.0092 (full mode).
#      THE ENTIRE HEADROOM TABLE IN OC-16 RESTS ON THIS. If a future build
#      changes which estimator binds, that table is invalid and this says so
#      rather than letting it stand.
#
# The corpus is regenerated from seeds and verified against pinned SHA-256
# digests. A seed that does not reproduce is not a pin, so a digest mismatch is
# a FAILURE, not a warning.
#
# WHAT EACH CHECK ACTUALLY PINS -- measured by perturbing the tool (OC-19), not
# assumed. The division came out cleaner than expected:
#
#   B's spectral peak  pins the FFT and the power path. Caught: a structural
#                      break in the bit-reversal permutation (8538.9x vs
#                      8538.7x) and a 1e-3 relative twiddle error (8534.1x).
#   E's sigma          pins the correlation accumulator and the z
#                      normalisation. Caught: N instead of N-k (40.31 vs
#                      40.21). INSENSITIVE to every FFT perturbation tried,
#                      because r = c[k]/c[0] is a ratio and the errors cancel.
#                      So E does NOT pin the FFT; B does.
#   clean + G_xor13_02 pin the thresholds, in both directions: lowering the
#                      spectral threshold to 13.0 fires on 5 of 5 clean streams
#                      AND trips the OC-18 coverage check.
#
#   MEASURED COVERAGE LIMIT: a twiddle perturbation of 1e-5 or smaller changes
#   no pinned outcome and is NOT caught. Such an error is far below the
#   magnitude that would matter for these statistics, but it is a limit and it
#   is stated rather than left implied.
#
# MODES
#   default                    5 clean + B + E + G, FFT only.    ~2 min
#   OUTSIDE_BATTERY_FULL=1     all 25 clean, all defects, and the
#                              Compression-binding check via ea_non_iid.
#   OUTSIDE_BATTERY_TOOL=path  test a different build of the tool. Used to
#                              demonstrate these checks FAILING against
#                              deliberately perturbed builds; see OC-19.
#   OUTSIDE_BATTERY_WORK=dir   reuse a corpus directory instead of a temp dir.
#
# EXIT  0 pass   1 fail   2 could not run (missing tool/generator/python3)

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "${here}/../.." && pwd)
tool="${OUTSIDE_BATTERY_TOOL:-${repo}/tools/outside-battery-check}"
src="${repo}/tools/outside-battery-check.cpp"
gen="${repo}/audits/2026-10-11-independent-audit/generators/blindspot_streams.py"
ea="${here}/../ea_non_iid"
full="${OUTSIDE_BATTERY_FULL:-0}"

fails=0
cannot_run=0
note() { printf '%-58s %s\n' "$1" "$2"; }

work="${OUTSIDE_BATTERY_WORK:-}"
if [ -z "${work}" ]; then
	work=$(mktemp -d "${TMPDIR:-/tmp}/ea-obc.XXXXXX") || exit 2
	trap 'rm -rf "${work}"' EXIT HUP INT TERM
else
	mkdir -p "${work}" || exit 2
fi

command -v python3 >/dev/null 2>&1 || { echo "regression-outside-battery: no python3" >&2; exit 2; }
[ -r "${gen}" ] || { echo "regression-outside-battery: generator missing at ${gen}" >&2; exit 2; }

# Build the tool if it is absent. Its source is tracked; the binary is not.
if [ ! -x "${tool}" ]; then
	if [ -r "${src}" ]; then
		c++ -std=c++11 -O2 -o "${tool}" "${src}" 2>/dev/null || {
			echo "regression-outside-battery: could not build ${src}" >&2; exit 2; }
	else
		echo "regression-outside-battery: ${src} missing" >&2; exit 2
	fi
fi

# ---------------------------------------------------------------- the corpus
CLEAN_FAST="mt00 mt01 mt02 mt03 mt04"
CLEAN_REST="sha00 sha01 sha02 sha03 sha04 sha05 sha06 sha07 sha08 sha09 sha10 sha11 sha12 sha13 sha14 sha15 sha16 sha17 sha18 sha19"
if [ "${full}" = "1" ]; then
	CLEAN="${CLEAN_FAST} ${CLEAN_REST}"
	DEFECTS="B_osc5000 C_osc500 D_lag5000 E_weaklag5000 F_xor30"
else
	CLEAN="${CLEAN_FAST}"
	DEFECTS="B_osc5000 E_weaklag5000"
fi
NEED="${CLEAN} ${DEFECTS} G_xor13_02"

digest_of() {
	case "$1" in
	mt00) echo ba0af622c60742c366e2f628dc9a4012cfd162df7505c62109bb2680f77142e1;;
	mt01) echo 9026925bb4b48e4830253bf0acc8255d225fccde9d82f3c4747a965d38626b16;;
	mt02) echo 7a915424cf36663fae24fa8210fb51fbf670ac4efd91bca30954cf6bfeb29fed;;
	mt03) echo f5b1cff45fe6546aad64b9350243b841847a64ee777a079867f72f9f9cca6f36;;
	mt04) echo 6d98bdb30e3d3d8b5e9565f608ff727cd2d14c9ec3096d23f0ea96383b6a7b3e;;
	sha00) echo 5c94a42fc7643f10c278bfc4b6605efb67139f4607d652d9a939809a1e124023;;
	sha01) echo 2a9a5f99df9c766e840531ededd72d55f744d0d2d03f475088ff0aeaa2afb09e;;
	sha02) echo b41dcf87d02d6f1e3feab0646fd3d7f31a80cbd81d62f10e932c86c9c582d36d;;
	sha03) echo 3119d39caff77bf64a43fa151ca242f784700cd5163f768ca8faf5fdfca84b1b;;
	sha04) echo 253bc56535fa1427f582f034d2a72816501b70be9a05db4060749526e479e351;;
	sha05) echo b355047c07fd88bc6bfa5341b2344aee398084b859702c159d5e585cbcb9ed50;;
	sha06) echo 5291a94c5dddfaf3e66fca4398849bd304b53f683117ba7a43ed55b717b48fcf;;
	sha07) echo 2e4185d3f141cf4cba92b0425dc621ac59c37a971e07dbbfc93e35da01398b3f;;
	sha08) echo f99f3dafe2a0d43285ba8503bb6a223cd6b93a67372f6a81dd90073097da03d2;;
	sha09) echo a12b163a7ed7cddc2a259b4c00bb47a4804971fa679f6ae3610fc93d2821e80a;;
	sha10) echo fba681a4d4bbe3003ffc84a52be23ce56ca9019fc49fe8bc94ae278cc0922412;;
	sha11) echo 44da0ce86bad8f95594b3640d296cc21d7dd40f8bf47f3795ad79ec55e55c732;;
	sha12) echo 1c7f7d438b6a5377a7758ce9e4ff617c37d5a7cb10f2737224e489c66910cbda;;
	sha13) echo 9865dcbf2d547a17b66dde77e2d835960b0581dd58ebb1690baf9d691a7c4ed6;;
	sha14) echo 6c5025b16082700bb5e95b2fb56e71d1a17eddd5a6d79f9e6b0528c1f3ef97fb;;
	sha15) echo 3c00b742844e9cd242d285e4ffb56d3ca64c276aac94270bc854294374ed3348;;
	sha16) echo 5fd291695d25580e597cda409c8aa38690285ddcf07d99b6b3e2232eec5fe94c;;
	sha17) echo 68b759d81e9798ccb13175cbac46cfbdea254fc0373f0b2e8708341318b5e683;;
	sha18) echo 4370510489db9ea42dd4e41b0ae343ec1beae4279d305648e8c823bae94365ee;;
	sha19) echo afa5d96eb6d42c8376f1e9807eb81e154e5ce41ba6e1ea92b1d06df2bc9247f8;;
	B_osc5000) echo 98b279d1c9826527b038d7b8b420382c2907932cdcee9ae5f811e1bd34706715;;
	C_osc500) echo 5927c604939d0921438f6a497aa892a50f9e0ccb6ea8b9a99636262260a92513;;
	D_lag5000) echo 0efbc90cacc8a5b299602340f9d293317413ffe9e6dbbc6b9a0f4b2fd439ffac;;
	E_weaklag5000) echo 50104af027186907b1ececfd3d9efb314816b078da0820eb2a4dcc95a6e2e452;;
	F_xor30) echo 8cb55830b5fd6dff9c4c2a2a33fefa50391f74812ab1c8852f8d8e866e881309;;
	G_xor13_02) echo 99cca6b4efdfcfeaf2446f87ad404a3b08580cab2c54885d991bd784d75b9a48;;
	*) echo "";;
	esac
}

sha_of() {
	if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
	else sha256sum "$1" | cut -d' ' -f1; fi
}

missing=""
for n in ${NEED}; do
	[ -s "${work}/${n}.bin" ] || missing="${missing} ${n}"
done
if [ -n "${missing}" ]; then
	echo "regenerating from seeds:${missing}"
	# shellcheck disable=SC2086
	python3 "${gen}" "${work}" ${missing} >/dev/null 2>&1 || {
		echo "regression-outside-battery: generator failed" >&2; exit 2; }
fi

# A seed that does not reproduce is not a pin.
bad_digest=0
for n in ${NEED}; do
	want=$(digest_of "${n}")
	got=$(sha_of "${work}/${n}.bin")
	if [ "${want}" != "${got}" ]; then
		note "DIGEST MISMATCH ${n}" "want ${want%%????????????????????????????????????????????????}… got ${got:0:16}…"
		bad_digest=$((bad_digest + 1))
	fi
done
if [ "${bad_digest}" -ne 0 ]; then
	echo
	echo "regression-outside-battery: FAIL (corpus not reproducible: ${bad_digest} digest mismatch(es))"
	echo "  The generator no longer produces the bytes the calibration was measured on,"
	echo "  so every pinned outcome below would be measured against a different corpus."
	exit 1
fi
note "corpus reproduced from seeds (${bad_digest} mismatches)" "$(echo ${NEED} | wc -w | tr -d ' ') streams"

# ------------------------------------------------------- 1. clean must be silent
fp=0
for n in ${CLEAN}; do
	"${tool}" --quiet "${work}/${n}.bin" >/dev/null 2>&1
	[ $? -eq 0 ] || { fp=$((fp + 1)); note "FALSE POSITIVE on clean stream" "${n}"; }
done
if [ "${fp}" -eq 0 ]; then
	note "clean streams silent:" "0 / $(echo ${CLEAN} | wc -w | tr -d ' ') fired"
else
	note "clean streams silent:" "${fp} FIRED -- false-positive rate regressed"
	fails=$((fails + 1))
fi

# ------------------------------------------------------- 2. defects must fire
miss=0
for n in ${DEFECTS}; do
	"${tool}" --quiet "${work}/${n}.bin" >/dev/null 2>&1
	[ $? -eq 1 ] || { miss=$((miss + 1)); note "MISSED defect" "${n}"; }
done
if [ "${miss}" -eq 0 ]; then
	note "defects detected:" "$(echo ${DEFECTS} | wc -w | tr -d ' ') / $(echo ${DEFECTS} | wc -w | tr -d ' ')"
else
	note "defects detected:" "${miss} MISSED -- sensitivity regressed"
	fails=$((fails + 1))
fi

# ------------------------------- 3. B's spectral peak: magnitude AND frequency
bout=$("${tool}" --rate 300000 "${work}/B_osc5000.bin" 2>&1)
bmag=$(printf '%s' "${bout}" | sed -n 's/^spectrum.*top line \([0-9.]*\)x.*/\1/p')
bhz=$(printf '%s' "${bout}"  | sed -n 's/^spectrum.*(= \([0-9.]*\) Hz).*/\1/p')
if [ "${bmag}" = "8538.7" ] && [ "${bhz}" = "59.938" ]; then
	note "B spectral peak pinned:" "${bmag}x at ${bhz} Hz"
else
	note "B spectral peak pinned:" "got ${bmag:-?}x at ${bhz:-?} Hz, want 8538.7x at 59.938 Hz"
	echo "    -> the FFT, the mean-centering, or the power normalisation changed."
	fails=$((fails + 1))
fi

# ------------------------- 4. E's autocorrelation: sigma AND the lag it lands on
eout=$("${tool}" "${work}/E_weaklag5000.bin" 2>&1)
esig=$(printf '%s' "${eout}" | sed -n 's/^largest |z| *\([0-9.]*\) sigma at lag.*/\1/p')
elag=$(printf '%s' "${eout}" | sed -n 's/^largest |z|.*at lag \([0-9]*\).*/\1/p')
if [ "${esig}" = "40.21" ] && [ "${elag}" = "5000" ]; then
	note "E autocorrelation pinned:" "${esig} sigma at lag ${elag}"
else
	note "E autocorrelation pinned:" "got ${esig:-?} sigma at lag ${elag:-?}, want 40.21 at 5000"
	echo "    -> the correlation accumulator or the z normalisation changed."
	fails=$((fails + 1))
fi

# --------------------- 5. the combined blind spot must stay outside this tool
"${tool}" --quiet "${work}/G_xor13_02.bin" >/dev/null 2>&1
if [ $? -eq 0 ]; then
	note "OC-18 blind spot still outside this tool:" "silent, as documented"
else
	note "OC-18 blind spot still outside this tool:" "FIRED -- coverage changed"
	echo "    -> G_xor13_02 has zero linear correlation by construction. If this tool"
	echo "       now detects it, its coverage has genuinely grown: re-document OC-18"
	echo "       and XR-06 rather than accepting this silently."
	fails=$((fails + 1))
fi

# ------------------------------- 6. Compression must still be the binding estimator
if [ "${full}" = "1" ]; then
	if [ ! -x "${ea}" ]; then
		note "Compression binds 5/5 clean streams:" "COULD NOT RUN (no ea_non_iid; run 'make non_iid')"
		cannot_run=$((cannot_run + 1))
	else
		bindfail=0
		vals=""
		for n in ${CLEAN_FAST}; do
			OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}" "${ea}" -v "${work}/${n}.bin" 1 > "${work}/${n}.ea" 2>&1
			read -r binder value <<-EOF
			$(python3 - "${work}/${n}.ea" <<-'PY'
			import re, sys
			pat = re.compile(r'^\s+(.*?)\s+(?:Test\s+)?Estimate\s*=\s*([0-9.]+)\s*/')
			d = {}
			for line in open(sys.argv[1]):
			    m = pat.match(line)
			    if m:
			        d[m.group(1).strip()] = float(m.group(2))
			if not d:
			    print("NONE 0"); raise SystemExit
			k = min(d, key=d.get)
			print("%s %.6f" % ("Compression" if "Compression" in k else k.replace(" ", "_"), d[k]))
			PY
			)
			EOF
			vals="${vals} ${value}"
			if [ "${binder}" != "Compression" ]; then
				note "binding estimator on ${n}" "${binder} (expected Compression)"
				bindfail=$((bindfail + 1))
			else
				# 0.8546 +/- 0.0092 -> accept 3 sd, i.e. [0.8270, 0.8822]
				inrange=$(python3 -c "print(1 if 0.8270 <= ${value} <= 0.8822 else 0)")
				[ "${inrange}" = "1" ] || {
					note "Compression out of band on ${n}" "${value} not in [0.8270, 0.8822]"
					bindfail=$((bindfail + 1)); }
			fi
		done
		if [ "${bindfail}" -eq 0 ]; then
			note "Compression binds 5/5 at 0.8546 +/- 0.0092:" "${vals# }"
		else
			note "Compression binds 5/5 at 0.8546 +/- 0.0092:" "${bindfail} deviation(s)"
			echo "    -> OC-16's ENTIRE HEADROOM TABLE assumes Compression is the binding"
			echo "       estimator on near-uniform data. It is now invalid and must be"
			echo "       re-measured before any headroom claim is repeated."
			fails=$((fails + 1))
		fi
	fi
else
	note "Compression binds 5/5 clean streams:" "SKIPPED (set OUTSIDE_BATTERY_FULL=1)"
fi

echo
if [ "${full}" != "1" ]; then
	echo "regression-outside-battery: fast mode -- $(echo ${CLEAN} | wc -w | tr -d ' ') clean, $(echo ${DEFECTS} | wc -w | tr -d ' ') defects."
	echo "                            OUTSIDE_BATTERY_FULL=1 runs all 25 clean, all 5 defects,"
	echo "                            and the Compression-binding check."
fi
if [ "${cannot_run}" -ne 0 ]; then
	echo "regression-outside-battery: COULD NOT RUN (${cannot_run} case(s); ${fails} of the cases that ran failed)"
	exit 2
fi
if [ "${fails}" -eq 0 ]; then
	echo "regression-outside-battery: PASS"
	exit 0
fi
echo "regression-outside-battery: FAIL (${fails} checks)"
exit 1
