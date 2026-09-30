// F14 demonstration: call the UNMODIFIED compression_test() on a bitstring with more than
// 2^32 6-bit blocks without allocating it: a 1.5 MB memfd holding the bit pattern 000001
// (every 6-bit block identical -> every D_i = 1 -> correct X-bar = 0, entropy 0) is mapped
// repeatedly over one contiguous virtual range.
#include <climits>
#include "../cpp_rel_copy/shared/utils.h"
#include "../cpp_rel_copy/non_iid/compression_test.h"
#include <sys/mman.h>
#include <unistd.h>
int main(int argc, char **argv) {
  long extra = atol(argv[1]);                 // blocks beyond 2^32
  long num_blocks = (1L << 32) + extra;
  long len = num_blocks * 6;
  const long CH = 12288L * 128;               // multiple of 6 and of the page size
  int fd = memfd_create("pat", 0);
  if (fd < 0 || ftruncate(fd, CH)) { perror("memfd"); return 2; }
  uint8_t *pat = (uint8_t *)mmap(NULL, CH, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  for (long i = 0; i < CH; i++) pat[i] = (i % 6 == 5) ? 1 : 0;
  long total = ((len + CH - 1) / CH) * CH;
  uint8_t *base = (uint8_t *)mmap(NULL, total, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
  if (base == MAP_FAILED) { perror("reserve"); return 2; }
  for (long off = 0; off < total; off += CH)
    if (mmap(base + off, CH, PROT_READ, MAP_SHARED | MAP_FIXED, fd, 0) == MAP_FAILED) { perror("map"); return 2; }
  printf("len=%ld bits, num_blocks=%ld (2^32+%ld)\n", len, num_blocks, extra); fflush(stdout);
  double h = compression_test(base, len, 3, "F14");
  printf("RESULT compression min-entropy = %.17g\n", h);
  return 0;
}
