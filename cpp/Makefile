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

CXXFLAGS = -std=c++11 $(OPENMP_CXXFLAGS) -O2 -ffloat-store -I/usr/include/jsoncpp
ifeq ($(ARCH),x86)
CXXFLAGS += -march=native
endif

#CXX = clang++-15
#CXXFLAGS = -g -Wno-padded -Wno-disabled-macro-expansion -Wno-gnu-statement-expression -Wno-bad-function-cast -fopenmp -O1 -fsanitize=address -fsanitize=undefined -fno-omit-frame-pointer -fdenormal-fp-math=ieee -msse2 -march=native -I/usr/include/jsoncpp
#static analysis in clang using
#scan-build-15 --use-c++=/usr/bin/clang++-15 make
LIB = -lbz2 -lpthread -ldivsufsort -ldivsufsort64 $(OPENMP_LIB)
COND_LIB = -lmpfr -lgmp
SHARED_LIB = -ljsoncpp -lcrypto
INC =

ifeq ($(UNAME_S),Darwin)
# macOS: Homebrew installs headers and libraries outside the compiler's
# default search path, and openssl@3 is keg-only, so point at them here.
#   brew install libdivsufsort jsoncpp openssl@3
BREW_PREFIX ?= $(shell brew --prefix 2>/dev/null || echo /opt/homebrew)
OPENSSL_PREFIX ?= $(shell brew --prefix openssl@3 2>/dev/null || echo $(BREW_PREFIX)/opt/openssl@3)
INC += -I$(BREW_PREFIX)/include -I$(OPENSSL_PREFIX)/include
LDFLAGS += -L$(BREW_PREFIX)/lib -L$(OPENSSL_PREFIX)/lib
endif

######
# Main operations
######

all:    iid non_iid restart conditioning transpose

clean:
	rm -f ea_iid ea_non_iid ea_restart ea_conditioning ea_transpose selftest/*.res

iid: iid_main.o
iid_main.o: iid_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) iid_main.cpp -o ea_iid $(LDFLAGS) $(LIB) $(SHARED_LIB)
	
non_iid: non_iid_main.o	
non_iid_main.o: non_iid_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) non_iid_main.cpp -o ea_non_iid $(LDFLAGS) $(LIB) $(SHARED_LIB)

restart: restart_main.o
restart_main.o: restart_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) restart_main.cpp -o ea_restart $(LDFLAGS) $(LIB) $(SHARED_LIB)

conditioning: conditioning_main.o
conditioning_main.o: conditioning_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) conditioning_main.cpp -o ea_conditioning $(LDFLAGS) $(LIB) $(COND_LIB) $(SHARED_LIB)

transpose: transpose_main.o
transpose_main.o: transpose_main.cpp
	$(CXX) $(CXXFLAGS) $(INC) transpose_main.cpp -o ea_transpose $(LDFLAGS) $(LIB) $(SHARED_LIB)
