# Host detection (used to locate Homebrew packages on macOS below).
UNAME_S := $(shell uname -s 2>/dev/null)
UNAME_M := $(shell uname -m 2>/dev/null)

# -march=native is added only for ARCH=x86 (below). Upstream defaults ARCH
# to x86; on an Apple-silicon Mac default it to the host instead so the
# x86-only flag is not passed to an arm64 compile. Any ARCH given on the
# command line or in the environment still wins.
ifeq ($(UNAME_S)/$(UNAME_M),Darwin/arm64)
ARCH ?= arm64
else
ARCH ?= x86
endif

CXX ?= $(CROSS_COMPILE)g++

ifeq ($(UNAME_S),Darwin)
# macOS: Apple clang ships no OpenMP runtime and rejects a bare -fopenmp,
# so use Homebrew's libomp (brew install libomp). Homebrew GCC is not an
# option here: Homebrew's jsoncpp is built against libc++, so a
# libstdc++ (GCC) build fails to link Json::Value/StyledWriter symbols.
CXX = clang++
LIBOMP_PREFIX ?= $(shell brew --prefix libomp 2>/dev/null || echo /opt/homebrew/opt/libomp)
OPENMP_CXXFLAGS = -Xpreprocessor -fopenmp -I$(LIBOMP_PREFIX)/include
OPENMP_LIB = -L$(LIBOMP_PREFIX)/lib -lomp
else
OPENMP_CXXFLAGS = -fopenmp
OPENMP_LIB =
endif

# OC-121: -ffloat-store IS PASSED ONLY WHERE THE COMPILER HONOURS IT.
#
# It had been unconditional for the life of this fork, and Apple clang
# DISCARDED IT ON EVERY BUILD -- "warning: optimization flag '-ffloat-store' is
# not supported [-Wignored-optimization-argument]", three times per full build,
# once per tool, visible every time and never read. So any claim that this fork
# controlled excess precision through that flag WAS NEVER TRUE on macOS. It
# was true on Linux/GCC, which does honour it.
#
# The flag is probed rather than assumed: compile an empty translation unit
# with it and keep it only if the compiler does not complain. On arm64 there is
# no x87 excess precision for it to suppress, so dropping it is expected to
# change nothing there -- an expectation that is NOT measured, because the GCC
# build that would measure it cannot link jsoncpp on this host.
FLOAT_STORE := $(shell printf 'int main(void){return 0;}' > /tmp/.ea_fs_$$.c 2>/dev/null;     if $(CXX) -x c++ -ffloat-store -c /tmp/.ea_fs_$$.c -o /dev/null 2>&1        | grep -q 'ignored-optimization-argument\|not supported\|unrecognized';     then echo ""; else echo "-ffloat-store"; fi; rm -f /tmp/.ea_fs_$$.c)

# AND A SILENTLY IGNORED FLAG NOW FAILS THE BUILD RATHER THAN WARNING, so this
# cannot recur. Probed too, since only clang has this warning name.
IGNORED_FLAG_IS_ERROR := $(shell printf 'int main(void){return 0;}' > /tmp/.ea_wf_$$.c 2>/dev/null;     if $(CXX) -x c++ -Werror=ignored-optimization-argument -c /tmp/.ea_wf_$$.c -o /dev/null 2>/dev/null;     then echo "-Werror=ignored-optimization-argument"; else echo ""; fi; rm -f /tmp/.ea_wf_$$.c)

CXXFLAGS = -std=c++11 $(OPENMP_CXXFLAGS) -O2 $(FLOAT_STORE) $(IGNORED_FLAG_IS_ERROR) -I/usr/include/jsoncpp
ifeq ($(ARCH),x86)
CXXFLAGS += -march=native
endif

#CXX = clang++-15
#CXXFLAGS = -g -Wno-padded -Wno-disabled-macro-expansion -Wno-gnu-statement-expression -Wno-bad-function-cast -fopenmp -O1 -fsanitize=address -fsanitize=undefined -fno-omit-frame-pointer -fdenormal-fp-math=ieee -msse2 -march=native -I/usr/include/jsoncpp
#static analysis in clang using
#scan-build-15 --use-c++=/usr/bin/clang++-15 make
# C25 (OC-131): on Windows the OS randomness both seed() and the report
# writer read comes from BCryptGenRandom in bcrypt.dll (shared/os_random.h).
# Its import library ships with mingw-w64's CRT, so this adds no package
# beyond the toolchain. uname -s in an MSYS2 shell is MINGW64_NT-..., MSYS_NT-...
ifneq (,$(findstring MINGW,$(UNAME_S))$(findstring MSYS,$(UNAME_S))$(findstring CYGWIN,$(UNAME_S)))
PLATFORM_LIB = -lbcrypt
else
PLATFORM_LIB =
endif
LIB = -lbz2 -lpthread -ldivsufsort -ldivsufsort64 $(OPENMP_LIB) $(PLATFORM_LIB)
COND_LIB = -lmpfr -lgmp
SHARED_LIB = -ljsoncpp -lcrypto
INC =

ifeq ($(UNAME_S),Darwin)
# macOS: Homebrew installs headers and libraries outside the compiler's
# default search path, and openssl@3 is keg-only, so point at them here.
#   brew install libdivsufsort jsoncpp openssl@3
BREW_PREFIX ?= $(shell brew --prefix 2>/dev/null || echo /opt/homebrew)
OPENSSL_PREFIX ?= $(shell brew --prefix openssl@3 2>/dev/null || echo $(BREW_PREFIX)/opt/openssl@3)
# THE PINNED PREFIX GOES FIRST, OR IT IS NOT A PIN (PROV-15, audit of
# 2026-11-07).
#
# These two lines had the generic prefix first for the life of this fork, and
# the generic prefix is where Homebrew links the UNVERSIONED `openssl` formula:
# $(BREW_PREFIX)/include/openssl and $(BREW_PREFIX)/lib/libcrypto.dylib point
# at whatever that formula is today. Installing afl++ on 2026-11-07 pulled in
# openssl@4 and re-pointed both at 4.1.0, and the three tools built that minute
# compiled against OpenSSL 4 headers and load libcrypto.4.dylib (otool -L),
# while this file, BUILDING.md's pin table and the 2026-10-20 build all say
# openssl@3. The compiler and the linker each take the FIRST directory that has
# the file, so a pinned -I/-L placed second can only win when the generic prefix
# has nothing -- it pinned nothing. Reordering is the whole fix: the Homebrew
# dylib's install name is already the absolute openssl@3 path, so no -rpath is
# needed, and -lcrypto stays as it is because SHARED_LIB is shared with the
# non-Darwin line. selftest/regression-openssl-pin.sh reads this order from
# `make -n` and the load command from the built binaries.
INC += -I$(OPENSSL_PREFIX)/include -I$(BREW_PREFIX)/include
LDFLAGS += -L$(OPENSSL_PREFIX)/lib -L$(BREW_PREFIX)/lib
endif

######
# Main operations
######

# The supported fork build is deliberately limited to the three assessed and
# regression-tested executables. conditioning and transpose remain explicit
# development targets, but must never enter this aggregate without also
# changing the documented support boundary and its failing regression guard.
SUPPORTED_TARGETS := iid non_iid restart

all: $(SUPPORTED_TARGETS)

clean:
	rm -f ea_iid ea_non_iid ea_restart ea_conditioning ea_transpose ea_non_iid_identity_test selftest/restart-report-label-test selftest/*.res

iid: iid_main.o
iid_main.o: iid_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) iid_main.cpp -o ea_iid $(LDFLAGS) $(LIB) $(SHARED_LIB)
	
non_iid: non_iid_main.o	
non_iid_main.o: non_iid_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) non_iid_main.cpp -o ea_non_iid $(LDFLAGS) $(LIB) $(SHARED_LIB)

# N-07 regression-only build. The synchronization hook is compiled out of all
# supported production targets.
non_iid_identity_test:
	$(CXX) $(CXXFLAGS) -DEA_TEST_INPUT_IDENTITY_HOOK $(INC) non_iid_main.cpp -o ea_non_iid_identity_test $(LDFLAGS) $(LIB) $(SHARED_LIB)

restart: restart_main.o
restart_main.o: restart_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) restart_main.cpp -o ea_restart $(LDFLAGS) $(LIB) $(SHARED_LIB)

# NOVEL-03 regression-only unit: exercise report population without running
# the 10,000-round row and column permutation batteries.
selftest/restart-report-label-test: selftest/restart-report-label-test.cpp
	$(CXX) $(CXXFLAGS) $(INC) selftest/restart-report-label-test.cpp -o $@ $(LDFLAGS) $(LIB) $(SHARED_LIB)

conditioning: conditioning_main.o
conditioning_main.o: conditioning_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) conditioning_main.cpp -o ea_conditioning $(LDFLAGS) $(LIB) $(COND_LIB) $(SHARED_LIB)

transpose: transpose_main.o
transpose_main.o: transpose_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) transpose_main.cpp -o ea_transpose $(LDFLAGS) $(LIB) $(SHARED_LIB)
