#ifndef EA_OS_RANDOM_H
#define EA_OS_RANDOM_H

// The one place this fork reads operating-system randomness (C25, OC-131).
//
// Two consumers: seed() in utils.h, which seeds xoshiro256** for the IID
// permutation tests, and writeJsonReport() in TestRunUtils.h, which names the
// report's temporary file (F03 / OC-121). Both read /dev/urandom, and a native
// MinGW binary has no /dev/urandom: seed() therefore killed ea_iid and
// ea_restart on Windows (OC-42, measured OC-48), and since OC-121 removed the
// derivable fallback the report writer refused EVERY -o write there (C25,
// measured OC-130). The same fact, met twice; answered once, here.
//
//   POSIX    /dev/urandom, read exactly as before -- the macOS and Linux
//            behaviour of both consumers is unchanged.
//   Windows  BCryptGenRandom(NULL, buf, n, BCRYPT_USE_SYSTEM_PREFERRED_RNG),
//            the documented system CSPRNG (bcrypt.h, -lbcrypt; Vista SP1 and
//            later). CryptGenRandom is deprecated in favour of it; rand_s
//            yields four bytes a call and depends on the CRT; RtlGenRandom is
//            exported by name only as SystemFunction036. std::random_device is
//            REFUSED as a candidate: on MinGW libstdc++ it has historically
//            been a deterministic PRNG, which would make the permutation
//            tests' p-values meaningless while every surface sign said the
//            tool worked (BUILDING.md).
//   test     EA_TEST_RANDOM_SOURCE=<path>, on EVERY platform, replaces the
//            source with that file so a regression can observe the refusal
//            (OC-121: the only way the failure limb is ever exercised on a
//            host whose /dev/urandom works). Not a command-line option and
//            not documented as one.
//
// FAIL-CLOSED. The function returns true only when ALL n bytes were obtained;
// on any failure it returns false, fills *why with a one-line reason, and
// leaves the caller to refuse. There is no weaker fallback of any kind.

#include <cerrno>    // errno for strerror: not left to whoever included us first
#include <climits>   // ULONG_MAX, for the cbBuffer range check under _WIN32
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <bcrypt.h>
#endif

static inline const char *eaTestRandomSourcePath() {
    const char *p = getenv("EA_TEST_RANDOM_SOURCE");
    return (p != NULL && p[0] != '\0') ? p : NULL;
}

// What the error message should name as the source consulted.
static inline const char *eaRandomSourceName() {
    const char *t = eaTestRandomSourcePath();
    if (t != NULL) return t;
#ifdef _WIN32
    return "BCryptGenRandom, the Windows system CSPRNG";
#else
    return "/dev/urandom";
#endif
}

static inline bool eaReadRandomFromPath(const char *path, void *buf, size_t n, std::string *why) {
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        if (why != NULL) *why = std::string("cannot open '") + path + "': " + strerror(errno);
        return false;
    }
    size_t got = fread(buf, 1, n, f);
    int closed = fclose(f);
    if (got != n) {
        if (why != NULL) {
            char b[96];
            snprintf(b, sizeof(b), "read %lu of %lu bytes from '", (unsigned long) got, (unsigned long) n);
            *why = std::string(b) + path + "'";
        }
        return false;
    }
    if (closed != 0) {
        if (why != NULL) *why = std::string("close failed on '") + path + "': " + strerror(errno);
        return false;
    }
    return true;
}

// Fill buf[0..n) from the operating system's CSPRNG (or the test override).
static inline bool eaReadOsRandom(void *buf, size_t n, std::string *why) {
    const char *t = eaTestRandomSourcePath();
    if (t != NULL) return eaReadRandomFromPath(t, buf, n, why);
#ifdef _WIN32
    // cbBuffer is a 32-bit ULONG on LLP64; the two callers ask for 32 and 8
    // bytes, but a helper that truncated silently would be the C18 shape again.
    if (n > (size_t) ULONG_MAX) {
        if (why != NULL) *why = "request larger than BCryptGenRandom's ULONG cbBuffer";
        return false;
    }
    // BCRYPT_USE_SYSTEM_PREFERRED_RNG requires hAlgorithm == NULL (Microsoft
    // Learn, BCryptGenRandom). The result is an NTSTATUS, a signed 32-bit LONG
    // whose top two bits are the severity: success and informational are
    // non-negative, warning and error negative. That sign test is what
    // bcrypt.h's BCRYPT_SUCCESS() expands to; it is written out here so the
    // test does not depend on which SDK's bcrypt.h defines the macro, and
    // because comparing against STATUS_SUCCESS alone is the mistake Microsoft
    // documents (it misses the informational successes, and STATUS_SUCCESS is
    // not defined by <windows.h>+<bcrypt.h> on mingw-w64 at all).
    NTSTATUS st = BCryptGenRandom(NULL, (PUCHAR) buf, (ULONG) n, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (((LONG) st) < 0) {
        if (why != NULL) {
            char b[96];
            snprintf(b, sizeof(b), "BCryptGenRandom failed, NTSTATUS 0x%08lx", (unsigned long) (ULONG) st);
            *why = b;
        }
        return false;
    }
    return true;
#else
    return eaReadRandomFromPath("/dev/urandom", buf, n, why);
#endif
}

#endif // EA_OS_RANDOM_H
