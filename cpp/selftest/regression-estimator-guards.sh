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
