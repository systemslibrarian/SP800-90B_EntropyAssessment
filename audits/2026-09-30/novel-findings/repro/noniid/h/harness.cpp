#include <climits>
// Calls the UNMODIFIED upstream estimator headers on one file.
// usage: harness <file> <bits|0> <lit|bit> <est...>   est in mcw lag mmc lz comp coll markov
#include "../cpp_rel_copy/shared/utils.h"
#include "../cpp_rel_copy/non_iid/non_iid_test_run.h"
#include "../cpp_rel_copy/non_iid/collision_test.h"
#include "../cpp_rel_copy/non_iid/lz78y_test.h"
#include "../cpp_rel_copy/non_iid/multi_mmc_test.h"
#include "../cpp_rel_copy/non_iid/lag_test.h"
#include "../cpp_rel_copy/non_iid/multi_mcw_test.h"
#include "../cpp_rel_copy/non_iid/compression_test.h"
#include "../cpp_rel_copy/non_iid/markov_test.h"
int main(int argc, char **argv) {
  data_t data; NonIidTestRun tr; data.word_size = atoi(argv[2]);
  if (!read_file_subset(argv[1], &data, ULONG_MAX, 0, &tr)) return 2;
  bool lit = !strcmp(argv[3], "lit");
  uint8_t *S = lit ? data.symbols : data.bsymbols; long L = lit ? data.len : data.blen; int k = lit ? data.alph_size : 2;
  const char *lab = lit ? "Literal" : "Bitstring";
  printf("L=%ld k=%d word=%d\n", L, k, data.word_size);
  for (int a = 4; a < argc; a++) {
    double h = -2;
    if (!strcmp(argv[a], "mcw")) h = multi_mcw_test(S, L, k, 3, lab);
    else if (!strcmp(argv[a], "lag")) h = lag_test(S, L, k, 3, lab);
    else if (!strcmp(argv[a], "mmc")) h = multi_mmc_test(S, L, k, 3, lab);
    else if (!strcmp(argv[a], "lz")) h = LZ78Y_test(S, L, k, 3, lab);
    else if (!strcmp(argv[a], "comp")) h = compression_test(S, L, 3, lab);
    else if (!strcmp(argv[a], "coll")) h = collision_test(S, L, 3, lab);
    else if (!strcmp(argv[a], "markov")) h = markov_test(S, L, 3, lab);
    printf("RESULT %s %s %.17g\n", lab, argv[a], h);
  }
  return 0;
}
