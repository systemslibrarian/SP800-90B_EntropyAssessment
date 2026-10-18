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
# The corpus is regenerated from seeds and verified against the pinned manifest
# outside-battery-corpus.txt: identities, digests and PER-FAMILY COUNTS, in
# both directions (missing and unlisted), in every mode. A seed that does not
# reproduce is not a pin, and a corpus that cannot be counted does not support
# a "0 of 25", so any of these is a FAILURE, not a warning (2026-10-18).
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
#   OUTSIDE_BATTERY_CORPUS=f   use a different manifest. Only for demonstrating
#                              the corpus checks FAILING (see OC-23).
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
#
# THE EXPECTED SET LIVES IN outside-battery-corpus.txt, NOT HERE. Until
# 2026-10-18 the stream lists were inline in this script, so deleting one
# stream from the list produced a passing run whose "0 / 25" had quietly
# become 0 / 24 -- the harness checked digests but could not count. Now:
#   * the manifest's per-FAMILY counts must equal the expectations below
#     (5 mt, 20 sha, 5 defect, 1 blindspot), checked separately so a family
#     cannot be hollowed out while a total holds;
#   * every listed stream must be regenerable from its seed and match its
#     digest (a seed that does not reproduce is not a pin);
#   * the corpus directory must contain NO stream the manifest does not list;
#   * ALL of this is checked in every mode. Fast mode only RUNS the tool on a
#     subset; the corpus behind every published figure is verified whole.
# The whole set is 31 streams. Failing any of it is exit 1, a regression, not
# exit 2: the corpus the figures rest on has changed or cannot be reproduced.
corpus="${OUTSIDE_BATTERY_CORPUS:-${here}/outside-battery-corpus.txt}"
[ -r "${corpus}" ] || { echo "regression-outside-battery: corpus manifest missing at ${corpus}" >&2; exit 2; }
EXPECT_MT=5; EXPECT_SHA=20; EXPECT_DEFECT=5; EXPECT_BLINDSPOT=1

corpus_bad=0
cbad() { note "CORPUS $1" "$2"; corpus_bad=$((corpus_bad + 1)); }
ALL_NAMES=""; MT=""; SHA=""; DEFECT_ALL=""; BLINDSPOT=""
n_mt=0; n_sha=0; n_defect=0; n_blindspot=0; lineno=0
while IFS=' ' read -r fam name sha extra || [ -n "${fam:-}" ]; do
	lineno=$((lineno + 1))
	case "${fam}" in ''|'#'*) continue ;; esac
	if [ -n "${extra:-}" ] || ! printf '%s' "${sha:-}" | grep -Eq '^[0-9a-f]{64}$' \
	   || ! printf '%s' "${name:-}" | grep -Eq '^[A-Za-z0-9_]+$'; then
		cbad "malformed manifest line ${lineno}" "${fam} ${name:-} ${sha:-}"; continue
	fi
	case " ${ALL_NAMES} " in *" ${name} "*) cbad "duplicate manifest entry" "${name}"; continue ;; esac
	case "${fam}" in
		mt) MT="${MT} ${name}"; n_mt=$((n_mt + 1)) ;;
		sha) SHA="${SHA} ${name}"; n_sha=$((n_sha + 1)) ;;
		defect) DEFECT_ALL="${DEFECT_ALL} ${name}"; n_defect=$((n_defect + 1)) ;;
		blindspot) BLINDSPOT="${BLINDSPOT} ${name}"; n_blindspot=$((n_blindspot + 1)) ;;
		*) cbad "unknown family on line ${lineno}" "${fam}"; continue ;;
	esac
	ALL_NAMES="${ALL_NAMES} ${name}"
	eval "DIGEST_${name}=${sha}"
done < "${corpus}"
[ "${n_mt}" -eq "${EXPECT_MT}" ] || cbad "family mt short or long:" "${n_mt} listed, ${EXPECT_MT} required (the OC-16 baseline and Compression-binding figure rest on exactly 5)"
[ "${n_sha}" -eq "${EXPECT_SHA}" ] || cbad "family sha short or long:" "${n_sha} listed, ${EXPECT_SHA} required (the 0/25 false-positive figure needs 5 + 20)"
[ "${n_defect}" -eq "${EXPECT_DEFECT}" ] || cbad "family defect short or long:" "${n_defect} listed, ${EXPECT_DEFECT} required"
[ "${n_blindspot}" -eq "${EXPECT_BLINDSPOT}" ] || cbad "family blindspot short or long:" "${n_blindspot} listed, ${EXPECT_BLINDSPOT} required"
for must in B_osc5000 E_weaklag5000 G_xor13_02; do
	case " ${ALL_NAMES} " in *" ${must} "*) ;; *) cbad "named input missing from manifest:" "${must} (a pinned figure is measured on it)" ;; esac
done
for n in ${MT}; do [ "${n}" != "${n#mt}" ] || cbad "family mt entry not an mt stream:" "${n}"; done
for n in ${SHA}; do [ "${n}" != "${n#sha}" ] || cbad "family sha entry not a sha stream:" "${n}"; done

CLEAN_FAST="${MT# }"
CLEAN_REST="${SHA# }"
if [ "${full}" = "1" ]; then
	CLEAN="${CLEAN_FAST} ${CLEAN_REST}"
	DEFECTS="${DEFECT_ALL# }"
else
	CLEAN="${CLEAN_FAST}"
	DEFECTS="B_osc5000 E_weaklag5000"
fi
NEED="${ALL_NAMES# }"          # the WHOLE corpus is verified in every mode

digest_of() { eval "printf '%s' \"\${DIGEST_$1:-}\""; }

sha_of() {
	if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
	else sha256sum "$1" | cut -d' ' -f1; fi
}

if [ "${corpus_bad}" -eq 0 ]; then
	missing=""
	for n in ${NEED}; do
		[ -s "${work}/${n}.bin" ] || missing="${missing} ${n}"
	done
	if [ -n "${missing}" ]; then
		echo "regenerating from seeds:${missing}"
		# shellcheck disable=SC2086
		if ! python3 "${gen}" "${work}" ${missing} >"${work}/generator.log" 2>&1; then
			cbad "generator cannot produce a listed stream:" "$(tail -1 "${work}/generator.log")"
		fi
	fi
	# set inequality, the other direction: a stream present that is not listed
	for f in "${work}"/*.bin; do
		[ -e "${f}" ] || continue
		n=$(basename "${f}" .bin)
		case " ${NEED} " in *" ${n} "*) ;; *) cbad "unlisted stream present in corpus:" "${n}" ;; esac
	done
	# a seed that does not reproduce is not a pin
	for n in ${NEED}; do
		want=$(digest_of "${n}")
		if [ ! -s "${work}/${n}.bin" ]; then cbad "listed stream absent after regeneration:" "${n}"; continue; fi
		got=$(sha_of "${work}/${n}.bin")
		[ "${want}" = "${got}" ] || cbad "DIGEST MISMATCH ${n}" "want ${want:0:16}... got ${got:0:16}..."
	done
fi
if [ "${corpus_bad}" -ne 0 ]; then
	echo
	echo "regression-outside-battery: FAIL (corpus: ${corpus_bad} problem(s); nothing was measured)"
	echo "  The corpus behind every pinned figure (0/25 clean, B, E, the Compression"
	echo "  binding) is not the one the calibration was measured on, or cannot be"
	echo "  counted. Fix the manifest or the generator deliberately; do not widen."
	exit 1
fi
note "corpus pinned, reproduced and counted:" "${n_mt} mt + ${n_sha} sha clean, ${n_defect} defect, ${n_blindspot} blindspot = $(echo ${NEED} | wc -w | tr -d ' ') streams"

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
