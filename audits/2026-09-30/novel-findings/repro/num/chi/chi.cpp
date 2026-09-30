#include "../src/iid/chi_square_tests.h"
int main(){
  // df values reachable: binary indep 2^m-2 (m=2..11), GOF 9, non-binary: q-k, 9(q-1) up to 65280
  int dfs[] = {1,2,6,9,14,30,62,126,254,510,1022,2046,2295,9*255,65280, 100000};
  for(int df: dfs){
    // sweep x across a wide range incl. extremes
    double xs[] = {0.0, 1e-300, 1e-10, 0.5, 1.0, (double)df*0.5, (double)df, df + 3.09*sqrt(2.0*df), df + 4*sqrt(2.0*df), df+10*sqrt(2.0*df), 2.0*df+50, 10.0*df+1000, 1e6, 1e9, 1e300, 1.0/0.0};
    for(double x: xs){ double p = chi_square_pvalue(x, df); printf("%d %.17g %.17g\n", df, x, p); }
  }
  // negative/zero df
  printf("%d %.17g %.17g\n", 0, 5.0, chi_square_pvalue(5.0, 0));
  printf("%d %.17g %.17g\n", -2, 5.0, chi_square_pvalue(5.0, -2));
  printf("%d %.17g %.17g\n", 9, 0.0/0.0, chi_square_pvalue(0.0/0.0, 9));
}
