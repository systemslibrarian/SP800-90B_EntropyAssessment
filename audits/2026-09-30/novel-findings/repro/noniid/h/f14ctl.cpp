#include <climits>
#include "../cpp_rel_copy/shared/utils.h"
#include "../cpp_rel_copy/non_iid/compression_test.h"
int main(int argc, char **argv) {
  long len = atol(argv[1]); uint8_t *d = (uint8_t*)malloc(len);
  for (long i = 0; i < len; i++) d[i] = (i % 6 == 5);
  printf("RESULT %.17g\n", compression_test(d, len, 3, "CTL"));
}
