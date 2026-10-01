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
