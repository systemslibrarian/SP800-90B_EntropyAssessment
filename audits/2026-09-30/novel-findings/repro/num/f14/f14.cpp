#include "../src/shared/utils.h"
#include "../src/non_iid/compression_test_w.h"
#include <random>
int main(int argc,char**argv){
  long n = atol(argv[1]); double p1 = atof(argv[2]);
  std::mt19937_64 g(5); std::bernoulli_distribution d(p1);
  uint8_t *b = new uint8_t[n]; for(long i=0;i<n;i++) b[i]=d(g);
  double e = compression_test(b, n, 0, "Bitstring");
  printf("n=%ld blocks=%ld p1=%g compression_estimate=%.17g\n", n, n/6, p1, e);
}
