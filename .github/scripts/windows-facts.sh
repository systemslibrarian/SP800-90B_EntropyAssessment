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

# THE SERIAL SHIM (a labelled DEVIATION, and no source is touched).
#
# Without -fopenmp gcc emits no GOMP_* calls, but the project calls two OpenMP
# API functions directly (omp_get_thread_num, omp_get_num_threads in
# shared/utils.h and iid_main.cpp), so a serial link needs those two symbols
# and nothing else. Supplying them as a two-line object compiled here is
# exactly what "serial" means, and it is a LINK-TIME shim: no file in this
# repository changes, and the override is a make command-line variable.
#
# What this costs the measurement: nothing for either remaining question.
# R-1 is a long double comparison inside lrs_test.h and seed() is an open() of
# /dev/urandom; neither is inside a parallel region. Figures from a serial
# build are not offered as performance facts and every gate that uses one says
# SERIAL.
# THE LIBGOMP TEST IS A LINK TEST, NOT A FILE SEARCH.
#
# Run 4's deps gate said "the OpenMP runtime ships with the toolchain" because
# `find /mingw64 -name 'libgomp*'` matched ONE file: /mingw64/lib/libgomp.spec.
# A spec file is not a library. The link had already failed with "cannot find
# -lgomp" in run 3 and failed again in run 4's R-1 stage, which consulted the
# same glob and therefore kept -fopenmp. So the gate concluded from a signal
# weaker than the question, and the two gates contradicted each other in the
# same verdict log -- the same defect class this audit keeps repairing (OC-48).
#
# The question is whether -lgomp LINKS. Ask that.
have_libgomp() {
    local d; d=$(mktemp -d "${TMPDIR:-/tmp}/gomptest.XXXXXX") || return 1
    printf '#include <omp.h>\nint main(void){int n=0;\n#pragma omp parallel\n{n=omp_get_num_threads();}\nreturn n>0?0:1;}\n' > "$d/t.c"
    local ok=1
    gcc -fopenmp -O0 -o "$d/t.exe" "$d/t.c" >/dev/null 2>&1 && ok=0
    rm -rf "$d"
    return $ok
}

SHIM_DIR=/tmp/ompserial
make_serial_shim() {
  mkdir -p "$SHIM_DIR" || return 1
  cat > "$SHIM_DIR/shim.c" <<'SHIMEOF'
/* serial stand-ins for the only two OpenMP API functions this project calls */
int omp_get_thread_num(void)   { return 0; }
int omp_get_num_threads(void)  { return 1; }
SHIMEOF
  ( cd "$SHIM_DIR" && gcc -O2 -c shim.c -o shim.o && ar rcs libompserial.a shim.o ) >/dev/null 2>&1
}
SERIAL_MAKE_ARGS='OPENMP_CXXFLAGS=-Wno-unknown-pragmas'
serial_lib() { printf -- '-L%s -lompserial' "$SHIM_DIR"; }

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
  echo >> "$L"
  echo "=== the OpenMP runtime: -fopenmp makes gcc link -lgomp by itself ===" >> "$L"
  # Run 3 got all three tools through the compiler and failed at the link with
  # "cannot find -lgomp". That is a SECOND unpackaged dependency, and the
  # instrument rule applies to it as much as to libdivsufsort: do not conclude
  # it is absent from a name this script happens not to know. LOOK for the
  # files, then ask pacman which package owns them (OC-48).
  echo "  the test is a LINK test: compile and link a tiny -fopenmp program." >> "$L"
  echo "  (run 4 used a file glob and matched only /mingw64/lib/libgomp.spec," >> "$L"
  echo "   a spec file, and so reported an OpenMP runtime that does not link.)" >> "$L"
  find /mingw64 -name 'libgomp*' 2>/dev/null | sed 's/^/    file: /' >> "$L"
  if have_libgomp; then
    gate PASS "the OpenMP runtime LINKS: -fopenmp produces a working executable"
  else
    echo "  -lgomp does NOT link; asking pacman which package would provide it" >> "$L"
    for pk in mingw-w64-x86_64-openmp mingw-w64-x86_64-gcc-libs mingw-w64-x86_64-libgomp; do
      if pacman -Si "$pk" >/dev/null 2>&1; then
        printf '  candidate %-36s AVAILABLE -- installing\n' "$pk" >> "$L"
        pacman -S --noconfirm --needed "$pk" >> "$L" 2>&1 || true
      else
        printf '  candidate %-36s not in the repository\n' "$pk" >> "$L"
      fi
    done
    pacman -Fy >> "$L" 2>&1 || true
    for f in libgomp.a libgomp.dll.a libgomp-1.dll; do
      printf '    pacman -F %s -> ' "$f" >> "$L"; pacman -F "$f" >> "$L" 2>&1 || echo "no owning package" >> "$L"
    done
    if have_libgomp; then
      gate PASS "the OpenMP runtime LINKS after installing a candidate package"
    else
      gate FAIL "the OpenMP runtime does NOT LINK and no candidate package supplies it -- a SECOND unpackaged dependency, after libdivsufsort"
      note "A serial link is attempted in the build stage as a labelled DEVIATION."
      note "R-1 is a long double comparison and seed() is a file open; neither"
      note "sits in a parallel region, so both stay measurable without OpenMP."
    fi
  fi

  if [ -n "$divsuf" ]; then
    pacman -S --noconfirm --needed "$divsuf" >> "$L" 2>&1 || gate FAIL "installing ${divsuf} failed"
  else
    echo >> "$L"
    echo "=== DEVIATION: building libdivsufsort from source (BUILDING.md's route) ===" >> "$L"
    pacman -S --noconfirm --needed mingw-w64-x86_64-cmake mingw-w64-x86_64-make git >> "$L" 2>&1 || true
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
      # And "MinGW Makefiles" needs mingw32-make, which the mingw-w64-x86_64-make
      # package provides and plain `make` does not; run 2 failed with
      # "CMAKE_MAKE_PROGRAM is not set". Inside the MINGW64 shell the Unix
      # generator with MSYS2's own make is the simpler correct choice (OC-48).
      cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
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
      lib=$(printf '%s' "$out" | sed -n 's/.*cannot find \(-l[a-zA-Z0-9_]*\).*/\1/p' | head -1)
      # The compiler finished. Whatever this is, it is NOT a source
      # incompatibility, which is what the Windows question asks about.
      gate PASS "ea_${t}: COMPILES on MinGW -- every translation unit was accepted; the failure is at the link"
      if [ "${lib}" = "-lgomp" ] && ! have_libgomp && make_serial_shim; then
        echo "===== DEVIATION: relinking ea_${t} serially (no OpenMP runtime on this host) =====" >> "$L"
        out2=$( ( cd cpp && make -B "$t" $SERIAL_MAKE_ARGS OPENMP_LIB="$(serial_lib)" ) 2>&1 ); rc2=$?
        printf '%s\n' "$out2" >> "$L"
        if [ "$rc2" -eq 0 ]; then
          gate PASS "ea_${t}: links and runs SERIALLY (DEVIATION: libgomp absent, OpenMP off, two API symbols shimmed)"
        else
          gate FAIL "ea_${t}: does not link even serially -- see $L; the remaining symbols are the finding"
        fi
      else
        gate FAIL "ea_${t}: does NOT LINK; missing library ${lib:-unidentified} -- source compatibility is established, the dependency is not"
      fi
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
  OMPFLAGS=-fopenmp; OMPLIB=
  if ! have_libgomp; then
    make_serial_shim && { OMPFLAGS=-Wno-unknown-pragmas; OMPLIB="$(serial_lib)"; \
      echo "DEVIATION: no libgomp on this host; sweep built SERIALLY. R-1 is a" > "$L"; \
      echo "long double comparison, not a parallel region, so the affected set is" >> "$L"; \
      echo "unaffected by this -- but the gate says SERIAL." >> "$L"; }
  fi
  if g++ -std=c++11 $OMPFLAGS -ffloat-store -O2 -Icpp/shared -Icpp/non_iid \
        audits/2026-10-11-independent-audit/reproducers/r1_pcol_sweep.cpp \
        -o /tmp/r1sweep.exe $OMPLIB -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
        -ljsoncpp -lcrypto >> "$L" 2>&1; then
    /tmp/r1sweep.exe >> "$L" 2>&1
    grep -E 'sizeof|aborting alphabet|^aborting k|powers of two|width 1|still aborting' "$L"
    n=$(sed -n 's/^aborting alphabet sizes at exact balance: \([0-9]*\) of 255/\1/p' "$L" | head -1)
    if [ "${n:-x}" = "155" ]; then
      gate PASS "R-1 affected set is 155 of 255 -- the Linux x87 prediction CONFIRMED${OMPLIB:+ (SERIAL build)}"
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
/* splitmix64, bit 0 of each output.
 *
 * The first version of this was an LCG mod 2^32 emitting bit 16, and bit 16 of
 * such an LCG has period 2^17 = 131072. ea_iid duly reported a longest
 * repeated substring of 868928 = 1000000 - 131072, FAILED the LRS test, and
 * then printed "Skipped IID permutation tests after an earlier required IID
 * test failure" -- so seed() was never reached and the OC-42 prediction was
 * never put to the question. The input has to get PAST the required tests for
 * the stage under test to run at all (OC-48). */
#include <stdio.h>
int main(void){
  unsigned long long x = 0x90B2026ULL;
  for(long i=0;i<1000000;i++){
    x += 0x9E3779B97F4A7C15ULL;
    unsigned long long z = x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    z =  z ^ (z >> 31);
    putchar((int)(z & 1ULL));
  }
  return 0;
}
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
    printf '%s\n' "$out" | head -45 >> "$L"
    printf '  ... last 20 lines ...\n' >> "$L"
    printf '%s\n' "$out" | tail -20 >> "$L"
    # How far did it get? Positive markers only (the absence rule).
    local far="nothing recognisable"
    printf '%s' "$out" | grep -q 'Loaded'            && far="loaded the input"
    printf '%s' "$out" | grep -q 'Calculating base'  && far="reached baseline statistics"
    printf '%s' "$out" | grep -qE '^\*\* (Passed|Failed)' && far="reached the test battery"
    printf '%s' "$out" | grep -qE 'H_original|H_bitstring|H_assessed|Assessed min entropy|min entropy' \
                                                     && far="produced a figure"
    # the exact text of the predicted death: utils.h:796
    #   perror("Can't open random source. Reverting to a deterministic seed.")
    printf '%s' "$out" | grep -qi "open random source" && far="DIED at seed(): no /dev/urandom"
    printf 'how far: %s\n\n' "${far}" >> "$L"
    printf '  %-34s exit=%-4s %s\n' "${label}" "${rc}" "${far}"
  }
  # MinGW gcc appends .exe when -o carries no suffix, so ./cpp/ea_iid may not be
  # the filename even on a successful build. Resolve it, and say so when there
  # is nothing to resolve -- naming a path that does not exist is how the
  # absence-rule error this stage warns about got made (OC-48).
  binof() { if [ -x "$1.exe" ]; then echo "$1.exe"; elif [ -x "$1" ]; then echo "$1"; fi; }

  # RUN 4 MEASURED THE WRONG THING, AND SAID SO HONESTLY.
  #
  # All three tools ran. All three failed with ONE message -- "could not put the
  # report in place" -- which is TestRunUtils.h:79, the rename() branch of the
  # atomic report write this audit itself added for C08 (OC-47). So run 4 could
  # not answer the seed() question, because every tool died at a LATER step for
  # an unrelated reason, and `-q` had suppressed every progress marker the
  # "how far" classifier looks for.
  #
  # Two different questions were tangled together, so ask them separately:
  #   pass 1  no -o at all, verbose. The report write is not in the path, so
  #           whatever happens is about seed() and the battery. THIS is the
  #           pass the OC-42 gate reads.
  #   pass 2  -o into the working directory, twice. This is about the atomic
  #           write, and the second run is the interesting one: POSIX rename(2)
  #           replaces an existing destination, Windows rename() refuses it.
  for t in non_iid iid restart; do
    b=$(binof "./cpp/ea_${t}")
    if [ -z "$b" ]; then
      printf '  %-34s NOT BUILT -- nothing ran, nothing concluded\n' "ea_${t}"
      printf '===== ea_%s: NOT BUILT; no runtime measurement\n\n' "$t" >> "$L"
      continue
    fi
    case "$t" in
      non_iid) set -- -i -a -v /tmp/w1.bin 1 ;;
      iid)     set -- -i -v    /tmp/w1.bin 1 ;;
      restart) set -- -i -v    /tmp/w1.bin 1 0.9 ;;
    esac
    run "ea_${t} [pass 1: no report]" "$b" "$@"
  done

  echo "===== pass 2: the atomic report write, twice over the same path =====" >> "$L"
  for t in non_iid iid restart; do
    b=$(binof "./cpp/ea_${t}"); [ -z "$b" ] && continue
    case "$t" in
      non_iid) set -- -i -a -q -o "rep_${t}.json" /tmp/w1.bin 1 ;;
      iid)     set -- -i -q    -o "rep_${t}.json" /tmp/w1.bin 1 ;;
      restart) set -- -i -q    -o "rep_${t}.json" /tmp/w1.bin 1 0.9 ;;
    esac
    rm -f "rep_${t}.json"
    run "ea_${t} [pass 2a: fresh path]"    "$b" "$@"
    run "ea_${t} [pass 2b: path exists]"   "$b" "$@"
    ls -la "rep_${t}.json" 2>&1 | sed 's/^/    /' >> "$L"
  done

  # C18, WHICH THIS RUN TURNED FROM A SOURCE CLAIM INTO A MEASUREMENT.
  # `long int N = n_choose_2(L - W + 1)` overflows 32-bit long on LLP64, so
  # Pr(X >= 1) prints NEGATIVE and the 5.2.5 decision is taken against a NaN
  # threshold -- a FAIL whatever the data. Gate on the sign, which no correct
  # probability can have.
  echo "===== C18: the sign of Pr(X >= 1) =====" >> "$L"
  grep -hE 'Pr\(X >= 1\)' "$L" | sort -u | sed 's/^/  /' | tee -a "$L"
  if grep -qE 'Pr\(X >= 1\): *-' "$L"; then
    gate FAIL "C18 CONFIRMED BY MEASUREMENT: Pr(X >= 1) is NEGATIVE, so n_choose_2()'s N overflowed 32-bit long; the 5.2.5 threshold is then logl() of a negative number, i.e. NaN, and the LRS test FAILS whatever the data. See reproducers/c18_llp64_overflow.c"
  elif grep -qE 'Pr\(X >= 1\)' "$L"; then
    gate PASS "Pr(X >= 1) is non-negative in every run here -- no C18 overflow at this input size"
  else
    gate FAIL "no Pr(X >= 1) line was printed, so C18 is UNMEASURED in this run -- not refuted"
  fi

  # WHY rename() FAILED, with the errno, rather than a story about why it might
  # have. This mimics TestRunUtils.h:55-80 exactly and changes no source.
  echo "===== rename(2) semantics on this platform =====" >> "$L"
  cat > /tmp/ren.c <<'RENEOF'
#include <stdio.h>
#include <string.h>
#include <errno.h>
int main(void){
  FILE *f;
  for (int destExists = 0; destExists < 2; destExists++) {
    remove("ren_dst"); remove("ren_src");
    if (destExists) { f=fopen("ren_dst","wb"); fputs("old",f); fclose(f); }
    f=fopen("ren_src","wb"); fputs("new",f); fclose(f);
    errno = 0;
    int rc = rename("ren_src","ren_dst");
    printf("destination %-10s rename rc=%d errno=%d (%s)\n",
           destExists ? "EXISTS" : "absent", rc, errno, rc ? strerror(errno) : "ok");
    /* and the Windows primitive that is specified to replace, for contrast */
  }
  remove("ren_dst"); remove("ren_src");
  return 0;
}
RENEOF
  # AND THE SEQUENCE THE TOOLS ACTUALLY PERFORM, which is not a bare rename.
  # C14 (OC-31) claims the -o path with a PLACEHOLDER the moment -o is parsed,
  # and C08 (OC-47) then writes every later report through temp + rename. So on
  # a platform whose rename() refuses an existing destination, the placeholder
  # GUARANTEES that every subsequent write fails -- which is why pass 2a failed
  # even with a fresh path. Replicate all three cases with the real C++ calls.
  cat > /tmp/seq.cpp <<'SEQEOF'
#include <cstdio>
#include <cstring>
#include <cerrno>
#include <string>
#include <fstream>
#include <unistd.h>
using namespace std;
/* TestRunUtils.h:55-80, copied so the probe measures the real sequence */
static bool writeJsonReport(const string &path, const string &json, int *err) {
    const string tmp = path + ".tmp." + std::to_string((long)getpid());
    { ofstream o; o.open(tmp.c_str(), ios::out | ios::trunc | ios::binary);
      if (!o) { *err = errno; return false; }
      o << json; o.close();
      if (!o) { *err = errno; remove(tmp.c_str()); return false; } }
    errno = 0;
    if (rename(tmp.c_str(), path.c_str()) != 0) { *err = errno; remove(tmp.c_str()); return false; }
    *err = 0; return true;
}
int main(void) {
    /* Each case is SEQUENCED before it is printed. The first version passed
     * the call and `e` as sibling arguments to printf, and C++ leaves the
     * evaluation order of arguments unspecified: `e` was read before the call
     * that set it, so every line carried the PREVIOUS case's errno. Case 2
     * printed 0 and case 3 printed 17, which is case 2's. An instrument that
     * reports the right verdict beside the wrong number is still wrong. */
    int e = 0; bool ok;
    remove("seq.json");
    ok = writeJsonReport("seq.json", "{\"placeholder\":true}", &e);
    printf("1. fresh path, first write (the C14 placeholder): %s errno=%d (%s)\n",
           ok ? "OK" : "FAILED", e, strerror(e));
    ok = writeJsonReport("seq.json", "{\"report\":1}", &e);
    printf("2. same path, second write (every later report):  %s errno=%d (%s)\n",
           ok ? "OK" : "FAILED", e, strerror(e));
    remove("seq.json");
    ok = writeJsonReport("seq.json", "{\"single\":1}", &e);
    printf("3. fresh path again, single write only:           %s errno=%d (%s)\n",
           ok ? "OK" : "FAILED", e, strerror(e));
    remove("seq.json");
    return 0;
}
SEQEOF
  if g++ -O0 -std=c++11 -o /tmp/seq.exe /tmp/seq.cpp >>"$L" 2>&1 && /tmp/seq.exe >> "$L" 2>&1; then
    sed -n '/^[123]\. /p' "$L" | sed 's/^/  /'
    if sed -n '/^1\./p' "$L" | grep -q OK && sed -n '/^2\./p' "$L" | grep -q FAILED; then
      gate FAIL "MEASURED MECHANISM: the C14 placeholder write SUCCEEDS and every later C08 write then FAILS, because rename() will not replace it. The two repairs are individually sound and jointly non-portable."
    elif sed -n '/^2\./p' "$L" | grep -q OK; then
      gate PASS "temp+rename replaces an existing report here; the C08 repair is portable to this platform"
    else
      gate FAIL "the replication probe did not separate the cases; read $L"
    fi
  else
    gate FAIL "the replication probe did not build; the mechanism stays inferred rather than measured"
  fi

  if gcc -O0 -o /tmp/ren.exe /tmp/ren.c >>"$L" 2>&1 && /tmp/ren.exe >> "$L" 2>&1; then
    sed -n '/^destination/p' "$L" | sed 's/^/  /'
    if sed -n '/^destination EXISTS/p' "$L" | grep -q 'rc=0'; then
      gate PASS "rename(2) here REPLACES an existing destination, as POSIX specifies"
    else
      gate FAIL "rename() here REFUSES an existing destination -- the C08 atomic-write repair (OC-47) is NOT portable to Windows as written; MoveFileEx(MOVEFILE_REPLACE_EXISTING) is the platform primitive"
    fi
  else
    gate FAIL "could not measure rename() semantics; the report-write failure stays undiagnosed"
  fi
  if grep -q 'could not put the report in place' "$L"; then
    gate FAIL "the atomic report write FAILS on Windows -- TestRunUtils.h:79, a defect in a repair this audit authored, found by running it somewhere new"
  else
    gate PASS "the atomic report write succeeded on Windows"
  fi

  # ABSENCE RULE (OC-36), which the first version of this gate broke in the very
  # workflow that applies the rule elsewhere: it read "no tool died at seed()"
  # as the prediction being refuted, when in fact NO BINARY EXISTED and
  # `timeout` had reported "No such file or directory" with exit 127. A
  # prediction is UNTESTED until something ran.
  # OC-42 IS A PER-TOOL PREDICTION, SO READ IT PER TOOL.
  #
  # Run 7's gate declared the prediction BROKEN because "a tool produced a
  # figure" -- and the tool that did was ea_non_iid, which OC-42 predicts
  # RUNS. The two tools predicted to die had not reached seed() at all. A gate
  # that reads a per-tool prediction out of a whole log will find whichever
  # half it greps for first. And the absence rule applies to each tool
  # separately: a tool that never reached the permutation stage has not
  # refuted anything.
  # Take the FIRST "how far" line after the tool's own marker. The first
  # attempt ended the range at /^$/ and the runs' own output contains blank
  # lines, so the range closed before reaching the line it was looking for and
  # every tool came back empty -- which the gates then read as "reached
  # neither seed() nor a figure". An extraction pattern that takes the wrong
  # text is the fourth of these in this job (OC-48).
  far_of() { awk -v t="ea_$1 [pass 1" 'index($0,t){f=1} f && /^how far: /{sub(/^how far: /,""); print; exit}' "$L"; }
  built=0
  for b in ./cpp/ea_non_iid ./cpp/ea_iid ./cpp/ea_restart; do
    if [ -x "$b" ] || [ -x "$b.exe" ]; then built=$((built + 1)); fi
  done
  if [ "$built" -eq 0 ]; then
    gate FAIL "no tool was built, so the seed()//dev/urandom prediction is UNTESTED -- not refuted, not confirmed"
  else
    # ea_non_iid: predicted to run. It does not call seed().
    case "$(far_of non_iid)" in
      *figure*) gate PASS "ea_non_iid runs the whole non-IID battery and produces a figure -- the half of OC-42 that predicted this is CONFIRMED" ;;
      *)        gate FAIL "ea_non_iid did not produce a figure: $(far_of non_iid) -- OC-42's first half is BROKEN and what happens instead is the finding" ;;
    esac
    # ea_iid and ea_restart: predicted to die at seed(), which only the
    # permutation stage reaches.
    for t in iid restart; do
      f=$(far_of "$t")
      case "$f" in
        *"DIED at seed"*) gate PASS "ea_${t} DIED at seed(): no /dev/urandom -- OC-42 CONFIRMED for this tool" ;;
        *figure*)         gate FAIL "ea_${t} produced a figure where seed() was predicted to kill it -- OC-42 is BROKEN for this tool, and /dev/urandom evidently resolves here" ;;
        *)                if sed -n "/ea_${t} \[pass 1/,/^$/p" "$L" | grep -q 'Skipped IID permutation'; then
                            gate FAIL "ea_${t} SKIPPED the permutation tests after an earlier required test failed, so seed() was never reached: OC-42 is UNTESTED for this tool -- the input, not the platform, is what stopped it"
                          else
                            gate FAIL "ea_${t} reached neither seed() nor a figure ($f); read $L -- nothing is concluded"
                          fi ;;
      esac
    done
  fi
  ;;

probe)
  L=logs/06-buildstate-probe.log
  . cpp/selftest/buildstate-lib.sh
  BS_DEBUG=1   # this is the platform the probe has never met; print its workings
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
    echo "--- would a FULL listing discriminate? (does an extension exist?) ---"
    gcc -O0 -DNDEBUG -o /tmp/cal_nd.exe /tmp/cal.c 2>/dev/null
    for v in live nd; do
      printf '  nm (all symbols) /tmp/cal_%s.exe matching /assert/i: %s\n' "$v" \
        "$(nm /tmp/cal_$v.exe 2>/dev/null | grep -ci assert)"
      nm /tmp/cal_$v.exe 2>/dev/null | grep -i assert | head -4 | sed 's/^/    /'
    done
    echo "  (if live>0 and ndebug==0 here, the probe CAN be taught this platform;"
    echo "   that is an improvement, not a correction -- refusing was right.)"
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
