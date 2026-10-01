#!/bin/bash
#
# Regression for the estimator-level safety guards.
#
# The central Section 3.1.1 intake check (regression-minsize.sh) makes every
# input exercised here unreachable through ordinary use. These guards exist so
# that the estimators are still safe when called directly, which is how they
# are unit-tested and how a future caller might use them. Memory unsafety,
# division by zero and assert aborts on ordinary input are not acceptable
# merely because a higher layer usually prevents them.
#
# Covered:
#   #257  binaryMultiMMCPredictionEstimate read S[d+1] past the buffer for
#         4 <= L <= 16; it must decline instead. Checked under AddressSanitizer.
#   #263  compression_test admitted exactly d+1 six-bit blocks, leaving one
#         test block, and divided by v-1 = 0. It must require two.
#   #264  collision_test divided by v-1 = 0 with a single collision and
#         reported min entropy 1 from a NaN comparison. It must decline.
#   #261  assert() aborted the process (SIGABRT, no report) on ordinary short
#         or repeat-free inputs. Every estimator must decline instead.
#   F14   compression_test's dictionary stored a long block index in an
#         unsigned int, truncating above 2^32 blocks and silently inflating
#         the estimate to 1.0. The element type must stay 64-bit.
#
# Each input is run with EA_ALLOW_SHORT_DATASET=1 so that the intake check
# does not mask the behaviour being tested.

set -u

here=$(cd "$(dirname "$0")" && pwd)
cpp=$(cd "${here}/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-regguard.XXXXXX") || exit 2
trap 'rm -rf "${work}"' EXIT

export EA_ALLOW_SHORT_DATASET=1

fails=0
note() { printf '%-52s %s\n' "$1" "$2"; }

# An AddressSanitizer build of the tool as it stands.
asan="${work}/ea_asan"
if ! clang++ -std=c++11 -O1 -g -fsanitize=address -fno-omit-frame-pointer -w \
	-Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include \
	-I/opt/homebrew/include -I/opt/homebrew/opt/openssl@3/include \
	"${cpp}/non_iid_main.cpp" -o "${asan}" \
	-L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib \
	-lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
	-L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto >"${work}/build.log" 2>&1; then
	echo "regression-estimator-guards: AddressSanitizer build failed; see ${work}/build.log" >&2
	sed -n '1,20p' "${work}/build.log" >&2
	exit 2
fi

# ---------------------------------------------------------------- #257
# Binary inputs of 4..16 samples reached the MultiMMC initialisation loop.
for L in 4 5 8 12 16; do
	python3 -c "
import random, sys
r = random.Random(int(sys.argv[2]))
open(sys.argv[1], 'wb').write(bytes(r.randrange(2) for _ in range(int(sys.argv[2]))))
" "${work}/b${L}.bin" "${L}"

	out=$("${asan}" -q "${work}/b${L}.bin" 1 2>&1)
	if printf '%s' "${out}" | grep -q 'heap-buffer-overflow'; then
		note "#257 binary MultiMMC L=${L}:" "heap-buffer-overflow STILL PRESENT"
		fails=$((fails + 1))
	else
		note "#257 binary MultiMMC L=${L}:" "no sanitizer error"
	fi
done

# The estimator must decline rather than produce a number from a partial model.
python3 -c "
import random
r = random.Random(8)
open('${work}/b8.bin', 'wb').write(bytes(r.randrange(2) for _ in range(8)))
"
out=$("${asan}" -v "${work}/b8.bin" 1 2>&1)
if printf '%s' "${out}" | grep -q 'not enough samples to run multiMMC'; then
	note "#257 binary MultiMMC declines below D_MMC+1:" "declined"
else
	note "#257 binary MultiMMC declines below D_MMC+1:" "no decline reported"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- #263
# 1001 six-bit blocks leaves v = 1 and divided by v-1 = 0: NaN when the last
# block repeats the one before it (the estimator then reported 1.0), +inf
# otherwise (the estimate became -0 and that became the whole figure).
python3 - "${work}" <<'PY'
import random, sys
w = sys.argv[1]
r = random.Random(11)
bits = [r.randrange(2) for _ in range(6006)]           # 1001 blocks of 6 bits
a = bits[:]; a[6000:6006] = a[5994:6000]               # last block repeats -> 0/0
b = bits[:]; b[6000:6006] = [1 - x for x in b[5994:6000]]  # differs          -> x/0
open(w + "/v1_nan.bin", "wb").write(bytes(a))
open(w + "/v1_inf.bin", "wb").write(bytes(b))
open(w + "/v2.bin", "wb").write(bytes(a + a[:6]))      # 1002 blocks, v = 2
PY

for f in v1_nan v1_inf; do
	out=$("${asan}" -vv "${work}/${f}.bin" 1 2>&1)
	if printf '%s' "${out}" | grep -q 'not enough samples to run compression'; then
		note "#263 compression declines at v=1 (${f}):" "declined"
	else
		note "#263 compression declines at v=1 (${f}):" "ran anyway"
		fails=$((fails + 1))
	fi
	if printf '%s' "${out}" | grep -qE 'Compression Estimate: sigma-hat = (-?nan|-?inf)'; then
		note "#263 no NaN/inf sigma-hat (${f}):" "NaN or inf still produced"
		fails=$((fails + 1))
	else
		note "#263 no NaN/inf sigma-hat (${f}):" "none"
	fi
done

# Two test blocks is the smallest usable case and must still run.
out=$("${asan}" -vv "${work}/v2.bin" 1 2>&1)
if printf '%s' "${out}" | grep -qE 'Compression Estimate: sigma-hat = [0-9]'; then
	note "#263 compression still runs at v=2:" "ran with a finite sigma-hat"
else
	note "#263 compression still runs at v=2:" "did not run"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- #264
# Five binary samples yield one collision: sigma-hat was NaN, and because NaN
# compares false against both thresholds the estimator reported min entropy 1
# without measuring anything.
printf '\x00\x01\x01\x00\x01' > "${work}/b5.bin"
out=$("${asan}" -vv "${work}/b5.bin" 1 2>&1)
if printf '%s' "${out}" | grep -q 'not enough collisions to run collision test'; then
	note "#264 collision declines at v=1:" "declined"
else
	note "#264 collision declines at v=1:" "ran anyway"
	fails=$((fails + 1))
fi
if printf '%s' "${out}" | grep -qE 'Collision Estimate: (sigma-hat = -?nan|min entropy = 1$)'; then
	note "#264 no unmeasured 1.0 from NaN:" "still produced"
	fails=$((fails + 1))
else
	note "#264 no unmeasured 1.0 from NaN:" "none"
fi

# ---------------------------------------------------------------- #261
# These inputs all aborted on an assert before the fix: no message from the
# tool, no JSON, exit 134. They must now be declined with a reason, and the
# run must still produce a report.
printf '\x00\x01' > "${work}/two.bin"                       # no repeated substring
python3 -c "open('${work}/d256.bin','wb').write(bytes(range(256)))"   # every byte once
python3 -c "open('${work}/b3.bin','wb').write(bytes([0,1,0]))"        # binary, L=3
for L in 17 18 19; do
	python3 -c "
import random, sys
r = random.Random(int(sys.argv[2]))
open(sys.argv[1],'wb').write(bytes(r.randrange(2) for _ in range(int(sys.argv[2]))))
" "${work}/b${L}.bin" "${L}"
done

check_no_abort() { # check_no_abort <file> <bits> <label>
	local out rc
	out=$("${asan}" -q "${work}/$1" "$2" 2>&1); rc=$?
	if [ "${rc}" -eq 134 ] || printf '%s' "${out}" | grep -q 'Assertion failed'; then
		note "#261 $3:" "ABORTED (exit ${rc})"
		fails=$((fails + 1))
	else
		note "#261 $3:" "no abort (exit ${rc})"
	fi
}
check_no_abort two.bin  1 "two distinct bytes, nothing repeats"
check_no_abort d256.bin 8 "256 distinct bytes, nothing repeats"
check_no_abort b3.bin   1 "binary L=3 (MultiMMC)"
check_no_abort b17.bin  1 "binary L=17 (LZ78Y)"
check_no_abort b18.bin  1 "binary L=18 (LZ78Y)"
check_no_abort b19.bin  1 "binary L=19 (LZ78Y)"

# A repeat-free dataset must say so and still report.
out=$("${asan}" -vv "${work}/d256.bin" 8 2>&1)
if printf '%s' "${out}" | grep -q 'no repeated substrings' && \
   printf '%s' "${out}" | grep -q '^Assessed min entropy:'; then
	note "#261 repeat-free data declines and reports:" "both present"
else
	note "#261 repeat-free data declines and reports:" "missing decline or figure"
	fails=$((fails + 1))
fi

# ---------------------------------------------------------------- F14
# The end-to-end case needs more than 25.8 Gbit of input and hundreds of GB of
# memory, so it cannot be run here. What is tested instead is that the
# compile-time guard protecting the element type is real: narrowing the type
# back must fail the build.
narrow="${work}/narrow"
cp -R "${cpp}" "${narrow}" && rm -f "${narrow}/ea_non_iid"
perl -pi -e 's/^\tint64_t dict\[alph_size\];$/\tunsigned int dict[alph_size];/' "${narrow}/non_iid/compression_test.h"
if grep -q 'unsigned int dict\[alph_size\];' "${narrow}/non_iid/compression_test.h"; then
	if ( cd "${narrow}" && make non_iid >/dev/null 2>&1 ); then
		note "F14 narrowing the dictionary fails the build:" "it BUILT — the guard is not protecting"
		fails=$((fails + 1))
	else
		note "F14 narrowing the dictionary fails the build:" "build refused, as intended"
	fi
else
	note "F14 guard check:" "SOURCE PATTERN NOT FOUND — update this script"
	fails=$((fails + 1))
fi

# And the estimate on real data must be unchanged by the widening.
#
# Compared against NIST's own reference output with the tolerance the project
# uses elsewhere (1e-9 relative; see pin-check.sh for the justification), not
# against a literal. A literal here was this platform's value, so the check
# passed on macOS/clang (0.15932269772157773) and raised a false alarm on
# Linux/GCC, whose value is the one in refdata (0.15932269772157898). A
# regression that fails on the platform the project targets is worse than no
# regression: it reads as a defect that is not there.
#
# OBSERVED FAILING (2026-10-01), both directions. Against a build with G()
# inflated by 1% -- mutation confirmed by source SHA-256 changing
# bca454df0a2ab733 -> e4e97979c597f2d4 and by the binary differing from the
# clean build -- the figure becomes 0.15635841219554089 and this check prints:
#
#     F14 compression estimate unchanged: got '0.15635841219554089', reference '0.15932269772157898'
#     regression-estimator-guards: FAIL (1 checks)
#
# And in the direction the old check got wrong: a CORRECT Linux build produces
# 0.15932269772157898, which the old literal rejected as a failure. The new
# comparison accepts it at 7.8e-15 relative, well inside the 1e-9 tolerance,
# while still rejecting the 1% mutant.
want=$(sed -n 's/^Literal Compression Estimate: min entropy = //p' "${here}/refdata/ringOsc-nist.res" | head -1)
got=$("${asan}" -vv "${cpp}/../bin/ringOsc-nist.bin" 2>/dev/null | sed -n 's/^Literal Compression Estimate: min entropy = //p' | head -1)
if [ -z "${want}" ] || [ -z "${got}" ]; then
	note "F14 compression estimate unchanged:" "could not read want='${want}' got='${got}'"
	fails=$((fails + 1))
elif python3 -c "
import sys
w, g = float(sys.argv[1]), float(sys.argv[2])
m = max(abs(w), abs(g), 1e-300)
sys.exit(0 if abs(w - g) / m < 1e-9 else 1)" "${want}" "${got}"; then
	note "F14 compression estimate unchanged:" "${got} (reference ${want})"
else
	note "F14 compression estimate unchanged:" "got '${got}', reference '${want}'"
	fails=$((fails + 1))
fi

# A compliant dataset must remain sanitizer-clean.
out=$("${asan}" -q "${cpp}/../bin/ringOsc-nist.bin" 2>&1)
if printf '%s' "${out}" | grep -q 'AddressSanitizer'; then
	note "compliant dataset under AddressSanitizer:" "sanitizer error reported"
	fails=$((fails + 1))
else
	note "compliant dataset under AddressSanitizer:" "clean"
fi

echo
if [ "${fails}" -eq 0 ]; then
	echo "regression-estimator-guards: PASS"
	exit 0
fi
echo "regression-estimator-guards: FAIL (${fails} checks)"
exit 1
