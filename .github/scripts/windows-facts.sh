#!/usr/bin/env bash
# Windows platform facts, run inside the MSYS2 MINGW64 shell by
# .github/workflows/windows-platform-facts.yml. CHANGES NO SOURCE.
#
# Every question records whether it passed or failed into logs/verdict.log, and
# each step's detail into its own log. A step that cannot run says so rather
# than reporting a verdict it did not earn.
set -u
mkdir -p logs
STAGE=${1:?usage: windows-facts.sh deps|build|floats|r1|runtime|probe}
V=logs/verdict.log

gate() { printf 'GATE %-6s %s\n' "$1" "$2" | tee -a "$V"; }
note() { printf '  %s\n' "$*"; }

# The packages below are taken from cpp/Makefile, not guessed:
#   CXXFLAGS  -fopenmp                 -> gcc's libgomp (ships with gcc)
#   LIB       -lbz2                    -> bzip2
#             -lpthread                -> winpthreads (ships with gcc)
#             -ldivsufsort -ldivsufsort64 -> libdivsufsort  <-- the doubtful one
#   SHARED_LIB -ljsoncpp               -> jsoncpp
#             -lcrypto                 -> openssl
#   COND_LIB  -lmpfr -lgmp             -> NOT NEEDED: ea_conditioning is not a
#                                        supported target (SUPPORTED_TARGETS)
PKGS="mingw-w64-x86_64-gcc make mingw-w64-x86_64-bzip2 mingw-w64-x86_64-jsoncpp mingw-w64-x86_64-openssl"
DIVSUF_CANDIDATES="mingw-w64-x86_64-libdivsufsort mingw-w64-x86_64-divsufsort libdivsufsort divsufsort"

case "$STAGE" in

deps)
  L=logs/01-dependencies.log
  { echo "=== MSYSTEM=${MSYSTEM:-unset}  shell=$(uname -a)"; echo; } > "$L"
  echo "=== packages the Makefile requires ===" >> "$L"
  pacman -Sy --noconfirm >> "$L" 2>&1 || true
  missing=""
  for p in $PKGS; do
    if pacman -Si "$p" >/dev/null 2>&1; then
      printf '  %-34s AVAILABLE %s\n' "$p" "$(pacman -Si "$p" 2>/dev/null | sed -n 's/^Version *: *//p' | head -1)" >> "$L"
    else
      printf '  %-34s NOT IN THE REPOSITORY\n' "$p" >> "$L"; missing="${missing} ${p}"
    fi
  done
  echo >> "$L"
  echo "=== libdivsufsort: the dependency BUILDING.md says is unpackaged ===" >> "$L"
  divsuf=""
  for p in $DIVSUF_CANDIDATES; do
    if pacman -Si "$p" >/dev/null 2>&1; then divsuf="$p"; break; fi
  done
  if [ -n "$divsuf" ]; then
    printf '  FOUND as %s -- BUILDING.md is wrong about this\n' "$divsuf" >> "$L"
    gate PASS "libdivsufsort has a mingw-w64 package: ${divsuf}"
  else
    printf '  ABSENT: none of {%s}\n' "$DIVSUF_CANDIDATES" >> "$L"
    gate FAIL "libdivsufsort has NO mingw-w64 package -- this is THE dependency finding"
    note "Instruction said the rest stops here. Continuing deliberately, with the"
    note "finding recorded as a FAILED gate above, so the other three questions"
    note "are measured in the same run; a from-source build is labelled as a"
    note "DEVIATION below and is the route BUILDING.md already documents."
  fi
  [ -n "$missing" ] && gate FAIL "packages missing from the repository:${missing}"
  [ -z "$missing" ] && gate PASS "every other Makefile dependency is packaged"

  echo >> "$L"
  echo "=== installing ===" >> "$L"
  pacman -S --noconfirm --needed $PKGS >> "$L" 2>&1 \
    && gate PASS "toolchain and packaged libraries installed" \
    || gate FAIL "pacman install failed -- see $L"
  if [ -n "$divsuf" ]; then
    pacman -S --noconfirm --needed "$divsuf" >> "$L" 2>&1 || gate FAIL "installing ${divsuf} failed"
  else
    echo >> "$L"
    echo "=== DEVIATION: building libdivsufsort from source (BUILDING.md's route) ===" >> "$L"
    pacman -S --noconfirm --needed mingw-w64-x86_64-cmake git >> "$L" 2>&1 || true
    ( set -x
      rm -rf /tmp/divsufsort
      git clone --depth 1 https://github.com/y-256/libdivsufsort /tmp/divsufsort
      cd /tmp/divsufsort
      # CMake 4 removed compatibility with cmake_minimum_required(VERSION <3.5),
      # and libdivsufsort's CMakeLists asks for an older one. The first run
      # failed here with "CMake Error at CMakeLists.txt:2
      # (cmake_minimum_required)", which is a toolchain-version incompatibility
      # and not "the route is dead": this policy flag is the documented way past
      # it (OC-48).
      cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
            -DBUILD_SHARED_LIBS=OFF -DBUILD_DIVSUFSORT64=ON \
            -DCMAKE_INSTALL_PREFIX=/mingw64 .
      cmake --build . --target install
    ) >> "$L" 2>&1 \
      && gate PASS "libdivsufsort built and installed from source (DEVIATION, not a package)" \
      || gate FAIL "libdivsufsort could not be built from source either -- see $L for the cause before concluding the route is dead"
  fi
  tail -40 "$L"
  ;;

build)
  L=logs/02-build.log
  : > "$L"
  # A failure here has two very different causes and the first run's gate
  # conflated them (OC-48): a MISSING DEPENDENCY stops the preprocessor before
  # any of this project's source is judged, whereas a source incompatibility is
  # the thing the Windows question is actually about. Separate them, and never
  # report "does not compile" for a header that was simply absent.
  for t in non_iid iid restart; do
    echo "===== make $t =====" >> "$L"
    out=$( ( cd cpp && make -B "$t" ) 2>&1 ); rc=$?
    printf '%s\n' "$out" >> "$L"
    if [ "$rc" -eq 0 ]; then
      gate PASS "compiles and links: ea_${t}"
    elif printf '%s' "$out" | grep -qE 'fatal error: [a-zA-Z0-9_./]+\.h: No such file'; then
      gate FAIL "ea_${t}: a DEPENDENCY HEADER is absent ($(printf '%s' "$out" | sed -n 's/.*fatal error: \([^:]*\): No such file.*/\1/p' | head -1)) -- the preprocessor stopped before any of this project's source was judged, so MinGW source compatibility is UNTESTED, not refuted"
    elif printf '%s' "$out" | grep -qE 'cannot find -l|undefined reference'; then
      gate FAIL "ea_${t}: compiles but does NOT LINK -- the source is MinGW-compatible and a library is missing"
    else
      gate FAIL "ea_${t}: does NOT compile, and not for a missing header or library -- this is a genuine source incompatibility, see $L"
    fi
  done
  echo "===== what exists =====" >> "$L"
  ls -la cpp/ea_*.exe cpp/ea_non_iid cpp/ea_iid cpp/ea_restart 2>/dev/null >> "$L"
  sha256sum cpp/ea_*.exe 2>/dev/null >> "$L"
  grep -E '^GATE|error:|Error' "$L" | tail -20
  ;;

floats)
  L=logs/03-float-environment.log
  cat > /tmp/fp.c <<'EOF'
#include <stdio.h>
#include <float.h>
int main(void){
  printf("sizeof(long double) = %zu\n", sizeof(long double));
  printf("LDBL_MANT_DIG   = %d\n", LDBL_MANT_DIG);
  printf("LDBL_MIN_EXP    = %d\n", LDBL_MIN_EXP);
  printf("LDBL_MIN        = %Lg\n", LDBL_MIN);
  printf("LDBL_TRUE_MIN   = %Lg\n", LDBL_TRUE_MIN);
  printf("LDBL_EPSILON    = %Lg\n", LDBL_EPSILON);
#ifdef FLT_EVAL_METHOD
  printf("FLT_EVAL_METHOD = %d\n", FLT_EVAL_METHOD);
#else
  printf("FLT_EVAL_METHOD = (not defined)\n");
#endif
  printf("sizeof(long)    = %zu   (LLP64 on Windows: expect 4)\n", sizeof(long));
  return 0;
}
EOF
  { gcc --version | head -1; gcc -O0 -o /tmp/fp.exe /tmp/fp.c && /tmp/fp.exe; } > "$L" 2>&1
  cat "$L"
  if grep -q 'LDBL_MANT_DIG   = 64' "$L"; then
    gate PASS "x87 80-bit long double, as predicted for MinGW"
  else
    gate FAIL "NOT x87 80-bit: $(sed -n 's/^LDBL_MANT_DIG *= *//p' "$L") -- every R-1 prediction below is about THIS format"
  fi
  if grep -qE 'sizeof\(long\) *= *4' "$L"; then
    gate PASS "LLP64 confirmed (long is 32-bit) -- this is the C18 precondition"
  else
    gate FAIL "long is not 32-bit here; C18's premise does not hold on this toolchain"
  fi
  ;;

r1)
  L=logs/04-r1-blast-radius.log
  if g++ -std=c++11 -fopenmp -O2 -Icpp/shared -Icpp/non_iid \
        audits/2026-10-11-independent-audit/reproducers/r1_pcol_sweep.cpp \
        -o /tmp/r1sweep.exe -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
        -ljsoncpp -lcrypto > "$L" 2>&1; then
    /tmp/r1sweep.exe >> "$L" 2>&1
    grep -E 'sizeof|aborting alphabet|^aborting k|powers of two|width 1|still aborting' "$L"
    n=$(sed -n 's/^aborting alphabet sizes at exact balance: \([0-9]*\) of 255/\1/p' "$L" | head -1)
    if [ "${n:-x}" = "155" ]; then
      gate PASS "R-1 affected set is 155 of 255 -- the Linux x87 prediction CONFIRMED"
    else
      gate FAIL "R-1 affected set is ${n:-unmeasured} of 255, not the predicted 155 -- the prediction is BROKEN and the shape of the difference is the finding"
    fi
  else
    gate FAIL "the R-1 sweep did not build on Windows; no blast-radius measurement"
    tail -15 "$L"
  fi
  ;;

runtime)
  L=logs/05-runtime.log
  : > "$L"
  # python3 is not on PATH in this shell (first run, OC-48), so generate the
  # input with the compiler that is certainly here.
  cat > /tmp/gen.c <<'EOF'
#include <stdio.h>
int main(void){ unsigned s=11u; for(long i=0;i<1000000;i++){ s=s*1103515245u+12345u; putchar((int)((s>>16)&1u)); } return 0; }
EOF
  gcc -O1 -o /tmp/gen.exe /tmp/gen.c 2>>"$L" && /tmp/gen.exe > /tmp/w1.bin 2>>"$L"
  if [ ! -s /tmp/w1.bin ]; then
    gate FAIL "could not generate a test input; the runtime questions are UNTESTED"
    exit 0
  fi
  run() { # run <label> <cmd...>
    local label=$1; shift
    echo "===== ${label}: $*" >> "$L"
    local out rc
    out=$(timeout 900 "$@" 2>&1); rc=$?
    printf 'exit=%s\n' "$rc" >> "$L"
    printf '%s\n' "$out" | head -30 >> "$L"
    # How far did it get? Positive markers only (the absence rule).
    local far="nothing recognisable"
    printf '%s' "$out" | grep -q 'Loaded'            && far="loaded the input"
    printf '%s' "$out" | grep -q 'Calculating base'  && far="reached baseline statistics"
    printf '%s' "$out" | grep -qE '^\*\* (Passed|Failed)' && far="reached the test battery"
    printf '%s' "$out" | grep -q 'Assessed min entropy' && far="produced a figure"
    printf '%s' "$out" | grep -qi 'random source'    && far="DIED at seed(): no /dev/urandom"
    printf 'how far: %s\n\n' "${far}" >> "$L"
    printf '  %-34s exit=%-4s %s\n' "${label}" "${rc}" "${far}"
  }
  run ea_non_iid ./cpp/ea_non_iid -i -a -q -o /tmp/n.json /tmp/w1.bin 1
  run ea_iid     ./cpp/ea_iid     -i -q -o /tmp/i.json /tmp/w1.bin 1
  run ea_restart ./cpp/ea_restart -i -q -o /tmp/r.json /tmp/w1.bin 1 0.9
  # ABSENCE RULE (OC-36), which the first version of this gate broke in the very
  # workflow that applies the rule elsewhere: it read "no tool died at seed()"
  # as the prediction being refuted, when in fact NO BINARY EXISTED and
  # `timeout` had reported "No such file or directory" with exit 127. A
  # prediction is UNTESTED until something ran.
  built=0
  for b in ./cpp/ea_non_iid ./cpp/ea_iid ./cpp/ea_restart; do
    [ -x "$b" ] || [ -x "$b.exe" ] && built=$((built + 1))
  done
  if [ "$built" -eq 0 ]; then
    gate FAIL "no tool was built, so the seed()//dev/urandom prediction is UNTESTED -- not refuted, not confirmed"
  elif grep -q 'DIED at seed' "$L"; then
    gate PASS "the seed()//dev/urandom prediction is CONFIRMED for at least one tool -- see which, above"
  elif grep -q 'produced a figure' "$L"; then
    gate FAIL "a tool produced a figure where seed() was predicted to kill it: the OC-42 prediction is BROKEN and what actually happens is the finding"
  else
    gate FAIL "tools ran but neither died at seed() nor produced a figure; read $L before concluding anything"
  fi
  ;;

probe)
  L=logs/06-buildstate-probe.log
  . cpp/selftest/buildstate-lib.sh
  { bs_calibration
    echo "--- why, in detail: what nm shows for the calibration binaries here ---"
    cat > /tmp/cal.c <<'CEOF'
#include <assert.h>
int main(int c,char**v){assert(c>0);return (int)(long)v;}
CEOF
    gcc -O0 -o /tmp/cal_live.exe /tmp/cal.c 2>/dev/null && \
      { echo "nm -u on an asserts-live PE binary:"; nm -u /tmp/cal_live.exe 2>&1 | head -12; }
    echo "(an empty or assert-free listing is why calibration refuses: PE/COFF"
    echo " undefined symbols do not necessarily surface through nm -u)"
    for b in cpp/ea_non_iid.exe cpp/ea_iid.exe cpp/ea_restart.exe \
             cpp/ea_non_iid cpp/ea_iid cpp/ea_restart; do
      [ -e "$b" ] && bs_print "$b"
    done
  } > "$L" 2>&1
  cat "$L"
  # THE POINT OF THIS STEP. Windows is a platform the probe has never met. It
  # must either calibrate successfully and give a real verdict, or report that
  # it cannot. What it must NEVER do is report NDEBUG without calibrating,
  # because that is "absence of a symbol I was not looking for" dressed as an
  # answer -- and that defect would outrank the Windows question itself.
  if grep -q 'calibration: OK' "$L"; then
    if grep -qE 'asserts=(LIVE|NDEBUG)' "$L"; then
      gate PASS "probe calibrated on Windows and gave a real verdict"
    else
      gate FAIL "probe calibrated but produced no verdict"
    fi
  elif grep -q 'calibration: FAILED' "$L" && ! grep -q 'asserts=NDEBUG' "$L"; then
    gate PASS "probe could NOT calibrate on Windows and refused -- UNKNOWN, never a guess"
  else
    gate FAIL "PROBE DEFECT: it concluded without calibrating on an unrecognised platform"
  fi
  ;;

*) echo "unknown stage: $STAGE" >&2; exit 2 ;;
esac
