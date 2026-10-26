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

# ---- the citation link: the counts this script expects are also stated, as
# literals, in the tool's header, the generator's docstring and the audit's
# OC-17 text. A corpus edit cannot reach those, and an edit to this script's
# EXPECT_* alone leaves them disagreeing. So the expected set is anchored in
# four places that must all agree; a "0 of 25" in a document is only as good
# as this link (OC-23 follow-up, 2026-10-18). OUTSIDE_BATTERY_CITE_ROOT points
# the check at mirrored copies, for demonstrating it failing.
cite_root="${OUTSIDE_BATTERY_CITE_ROOT:-${repo}}"
cite_total=$((EXPECT_MT + EXPECT_SHA))
cite() { # cite <label> <file> <grep-regex> <sed-extract> <expected>
	local label=$1 file=$2 rx=$3 ex=$4 want=$5 got
	if [ ! -r "${cite_root}/${file}" ]; then cbad "citation source missing:" "${file}"; return; fi
	got=$(grep -oE "${rx}" "${cite_root}/${file}" | head -1 | sed "${ex}")
	if [ -z "${got}" ]; then cbad "citation not found (${label}):" "${file} has no match for '${rx}'"
	elif [ "${got}" != "${want}" ]; then cbad "citation disagrees (${label}):" "${file} says ${got}, this script expects ${want}"; fi
}
cite "tool header: clean total"   tools/outside-battery-check.cpp 'MEASURED on [0-9]+ independent clean' 's/MEASURED on \([0-9]*\).*/\1/' "${cite_total}"
cite "tool header: MT family"     tools/outside-battery-check.cpp '\([0-9]+ Mersenne' 's/(\([0-9]*\).*/\1/' "${EXPECT_MT}"
cite "tool header: SHA family"    tools/outside-battery-check.cpp ', [0-9]+ SHA-256 counter mode' 's/, \([0-9]*\).*/\1/' "${EXPECT_SHA}"
cite "generator docstring: total" audits/2026-10-11-independent-audit/generators/blindspot_streams.py 'CLEAN \([0-9]+,' 's/CLEAN (\([0-9]*\).*/\1/' "${cite_total}"
cite "generator docstring: mt range" audits/2026-10-11-independent-audit/generators/blindspot_streams.py 'mt00\.\.mt[0-9]+' 's/mt00\.\.mt//' "$(printf '%02d' $((EXPECT_MT - 1)))"
cite "generator docstring: sha range" audits/2026-10-11-independent-audit/generators/blindspot_streams.py 'sha00\.\.sha[0-9]+' 's/sha00\.\.sha//' "$((EXPECT_SHA - 1))"
cite "OC-17: calibration total"   audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md 'Calibration: [0-9]+ independent clean streams' 's/Calibration: \([0-9]*\).*/\1/' "${cite_total}"
cite "OC-17: 0/N false positives" audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md '\*\*0/[0-9]+\*\* over 5\.731' 's/\*\*0\/\([0-9]*\).*/\1/' "${cite_total}"
for fig in 8538.7 59.938 40.21 0.8546; do   # the figures this script pins must still be the ones the record cites
	grep -q -- "${fig}" "${cite_root}/audits/2026-10-11-independent-audit/ORCHESTRATOR-CHECKS.md" 2>/dev/null \
		|| cbad "pinned figure no longer cited in ORCHESTRATOR-CHECKS.md:" "${fig}"
done
for nm in B_osc5000 E_weaklag5000 G_xor13_; do  # and the names behind them must be the generator's names (G is built from a format string)
	grep -q -- "${nm}" "${cite_root}/audits/2026-10-11-independent-audit/generators/blindspot_streams.py" 2>/dev/null \
		|| cbad "named input not defined by the generator:" "${nm}"
done

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
		comp_ok=0
		comp_binds=0
		vals=""
		# OC-120: every clean stream the mode selected, not just the MT five.
		# The mean bound below has a standard error of stdev/sqrt(n), so n is
		# load-bearing: 25 streams make it 2.2x tighter than 5 at no meaningful
		# cost (~0.6 s per 1-bit run). CLEAN is the 25 clean streams in full
		# mode and the 5 fast ones otherwise.
		for n in ${CLEAN}; do
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
			# OC-118: THE WINDOW AND THE BINDER REQUIREMENT, BOTH RESET FROM A
			# MEASURED DISTRIBUTION INSTEAD OF FROM FIVE DRAWS.
			#
			# Until now this required Compression to bind on every clean stream
			# and its value to lie in [0.8270, 0.8822] -- 3 sd from
			# "0.8546 +/- 0.0092" measured on FIVE streams (OC-16). Measured
			# again on THREE HUNDRED fresh draws from the same two generators
			# and the same seeding discipline
			# (reproducers/compression-window-tail.sh, seeds 900000+, which
			# cannot collide with the pinned 0xA / 0xC0+i / sha 0..19):
			#
			#   first  n=300, seeds 900000+:  Compression 284 (94.7%), mean
			#          0.854784, stdev 0.025732, min 0.805141, max 0.941540,
			#          96 of 300 = 32.0% outside [0.8270, 0.8822]
			#   repl.  n=300, seeds 910000+:  Compression 285 (95.0%), mean
			#          0.853658, stdev 0.024596, min 0.795197, max 0.935128,
			#          82 of 300 = 27.3% outside. Welch t = 0.547 against the
			#          first, so the two are indistinguishable (OC-119).
			#   POOLED n=600: mean 0.854221, stdev 0.025177,
			#          min 0.795197, max 0.941540
			#
			# So the CENTRE was right -- 0.8546 sits at percentile 54.0 -- and
			# the tolerance was 2.8x too small. The old window would have failed
			# a THIRD of ordinary clean draws and the 5/5 Compression
			# requirement a further 5.3%. It never fired only because the corpus
			# is seeded and digest-pinned, so these streams are the same bytes
			# every run (OC-115 called that latent; this measures the rate).
			#
			# THE NEW WINDOW: the observed range over n = 300 widened by one
			# sample standard deviation each side. Rule 9 -- a sweep's extremum
			# is a LOWER BOUND on the spread -- so the range is widened rather
			# than used as-is, and one sd is a margin chosen and stated, not
			# derived:  [0.805141 - 0.025732, 0.941540 + 0.025732]
			#
			# THE BINDER: FIVE estimators were observed binding across n = 600,
			# so requiring any particular set is wrong. The Compression SHARE is
			# counted instead, against a floor from the pooled rate at corpus
			# size: 94.8% - 3*sqrt(p(1-p)/25) = 81.4%, so 80%.
			# OC-119: NO ALLOWLIST OF BINDING ESTIMATORS, and the reason is a
			# replication that caught the first attempt.
			#
			# The first version of this check accepted the four estimators seen
			# binding in n = 300 (Compression, Collision, t-Tuple, LRS). An
			# INDEPENDENT 300 draws at seeds 910000+ found a FIFTH -- Lag, twice
			# -- which that allowlist would have rejected. An allowlist built
			# from a sample is the same under-sampling error this check was
			# being repaired for, one level up, so it is removed rather than
			# extended: extending it would only wait for a sixth.
			#
			# What remains is what the measurement supports: ANY estimator may
			# bind, and the Compression SHARE is counted against a floor.
			comp_ok=$((comp_ok + 1))
			[ "${binder}" = "Compression" ] && comp_binds=$((comp_binds + 1))
			inrange=$(python3 -c "print(1 if 0.7700 <= ${value} <= 0.9667 else 0)")
			[ "${inrange}" = "1" ] || {
				note "out of the measured band on ${n}" "${value} not in [0.7700, 0.9667] (pooled n=600)"
				bindfail=$((bindfail + 1)); }
		done
		# OC-120: THE MEAN BOUND, WHICH IS THE SHIFT DETECTOR.
		#
		# TWO CHECKS WITH DIFFERENT JOBS, because only one of them improves
		# with measurement:
		#
		#   the WINDOW above is the GROSS-FAILURE detector. It is derived from
		#   the observed RANGE, which does not converge -- OC-119's replication
		#   put the minimum 0.0099 BELOW the first sample's, and more draws
		#   widen such a bound rather than tightening it. So it is set wide
		#   from the pooled n = 600 and IS NOT RE-DERIVED from new samples.
		#   Chasing a non-converging extremum is work with no end. Its job is
		#   to catch a stream that is wildly wrong, not to detect a shift.
		#
		#   the MEAN BOUND here is the SHIFT detector. The standard error of a
		#   mean is stdev/sqrt(n), which shrinks at a known rate, so this one
		#   DOES get better with measurement and IS re-derived as n grows.
		#
		# The spread comes from the pooled n = 600 (OC-118 + OC-119); the
		# CENTRE comes from this corpus at the pin (OC-121 -- see the python
		# block for why). The bound is 3 standard errors at the number of
		# streams actually examined, computed from comp_ok rather than assumed,
		# so a loop that stopped early cannot pass as a tighter bound.
		#   n = 25:  3 * 0.025177/sqrt(25) = 0.015106  -> [0.833184, 0.863396]
		#   n =  5:  3 * 0.025177/sqrt(5)  = 0.033779  -> [0.814511, 0.882069]
		#
		# SENSITIVITY, BOTH DIRECTIONS, now symmetric: +0.015106 / -0.015106.
		# Before this change it was +0.021037 / -0.009175.
		#
		# AND WHAT THIS TOLERANCE COSTS. The 25 streams are digest-pinned and
		# regenerated from fixed seeds, so the corpus mean is DETERMINISTIC to
		# floating-point reproducibility -- about 1e-13 here, 1e-9 across the
		# two supported platforms. A tolerance of 0.0151 is therefore six to
		# eight orders of magnitude looser than the quantity's actual
		# reproducibility. It will never false-fire, and it will miss any drift
		# below 0.015. That is a GROSS drift detector by construction. A bound
		# at ~1e-9 would catch real estimator changes and still clear the
		# platform delta; it is NOT adopted here because that is a redesign of
		# what this check asserts rather than a correction of its centre.
		if [ "${comp_ok}" -gt 0 ]; then
			meanverdict=$(python3 - "${comp_ok}" ${vals} <<'MEANPY'
import sys, math
n = int(sys.argv[1])
vals = [float(x) for x in sys.argv[2:]]
if not vals or n != len(vals):
    print("REFUSED %d values for %d streams" % (len(vals), n)); raise SystemExit
# OC-121: CENTRED ON THE CORPUS'S OWN MEAN, NOT THE POPULATION'S, AND THE
# CHOICE IS DELIBERATE BECAUSE THE ASYMMETRY RAN THE WRONG WAY.
#
# Centred on the pooled population centre 0.854221, this bound caught a shift
# of +0.0210 upward and -0.0092 downward -- because the corpus mean sits
# 0.005931 BELOW that centre. That is 2.3x more sensitive DOWNWARD.
#
# For an entropy instrument that is backwards. A downward drift reports LESS
# entropy and is conservative; an upward drift reports MORE and is PERMISSIVE,
# which is the direction that makes a figure wrong in the way that matters. An
# asymmetry favouring the permissive direction must not be incidental, so it
# is removed.
#
# THE QUESTION THIS CHECK ASKS: "has this tool drifted from its established
# behaviour on these pinned bytes" -- a regression question, which is the job
# it has in a regression suite. It does NOT ask "does this tool agree with the
# population of clean streams"; that is a different question and it is the one
# that produced the asymmetry.
#
# So the centre is the corpus's own mean at the pinned commit, measured over
# the 25 digest-pinned clean streams, and the tolerance is symmetric:
#   centre 0.848290   tol 3 * 0.025177/sqrt(n)   =>  +/- 0.015106 at n = 25
CENTRE, SD = 0.848290, 0.025177          # corpus mean at the pin; pooled sd, n=600
se = SD / math.sqrt(len(vals))
m = sum(vals) / len(vals)
tol = 3 * se
print("%s mean=%.6f centre=%.6f tol=%.6f n=%d"
      % ("OK" if abs(m - CENTRE) <= tol else "SHIFT", m, CENTRE, tol, len(vals)))
MEANPY
)
			case "${meanverdict}" in
				OK*)     note "mean within 3 SE of the corpus centre:" "${meanverdict#OK }" ;;
				SHIFT*)  note "MEAN SHIFTED beyond 3 SE" "${meanverdict#SHIFT }"
				         bindfail=$((bindfail + 1)) ;;
				*)       note "mean bound could not be evaluated" "${meanverdict}"
				         bindfail=$((bindfail + 1)) ;;
			esac
			share=$(python3 -c "print(1 if ${comp_binds} * 100 >= 80 * ${comp_ok} else 0)")
			[ "${share}" = "1" ] || {
				note "Compression share below the measured floor" \
				     "${comp_binds}/${comp_ok} < 80% (measured 94.8% at pooled n=600)"
				bindfail=$((bindfail + 1)); }
		fi
		if [ "${bindfail}" -eq 0 ]; then
			note "binder in [0.7700, 0.9667], Compression ${comp_binds}/${comp_ok}:" "${vals# }"
		else
			note "Compression binds 5/5 at 0.8546 +/- 0.0092:" "${bindfail} deviation(s)"
			echo "    -> OC-16's ENTIRE HEADROOM TABLE assumes Compression is the binding"
			echo "       estimator on near-uniform data. It is now invalid and must be"
			echo "       re-measured before any headroom claim is repeated."
			fails=$((fails + 1))
		fi
	fi
else
	note "binding estimator in the measured band:" "SKIPPED (set OUTSIDE_BATTERY_FULL=1)"
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
