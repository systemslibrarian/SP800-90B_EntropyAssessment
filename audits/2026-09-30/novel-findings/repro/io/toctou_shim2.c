/* LD_PRELOAD shim: on the Nth fopen() of $TOCTOU_PATH, overwrite that file in place
   with the bytes of $TOCTOU_SRC before letting the real fopen() proceed.
   Models a concurrent writer (e.g. an acquisition job still appending/rewriting)
   deterministically, between sha256_file()'s pass and read_file_subset()'s pass. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int count = 0;
FILE *fopen(const char *path, const char *mode) {
    static FILE *(*real)(const char *, const char *) = NULL;
    if (!real) real = (FILE *(*)(const char *, const char *))dlsym(RTLD_NEXT, "fopen");
    const char *t = getenv("TOCTOU_PATH"), *src = getenv("TOCTOU_SRC"), *n = getenv("TOCTOU_N");
    int nth = n ? atoi(n) : 2;
    if (t && src && strcmp(path, t) == 0 && ++count == nth) {
        FILE *in = real(src, "rb"), *out = real(t, getenv("TOCTOU_APPEND") ? "ab" : "wb");
        char buf[65536]; size_t k;
        while ((k = fread(buf, 1, sizeof buf, in)) > 0) fwrite(buf, 1, k, out);
        fclose(in); fclose(out);
        fprintf(stderr, "[shim] rewrote %s from %s before open #%d\n", t, src, nth);
    }
    return real(path, mode);
}
