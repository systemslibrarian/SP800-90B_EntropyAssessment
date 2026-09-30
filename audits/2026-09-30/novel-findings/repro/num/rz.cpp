#include "src/shared/utils.h"
#include <fenv.h>
#include <random>
int main(){
  std::mt19937_64 g(1);
  double worst=0; int cnt=0, diffcnt=0;
  for(int t=0;t<3000;t++){
    long N = 1000 + (long)(g()% 8000000);
    int k = (g()%2)? 2 : 256;
    double pg = (k==2? 0.5 + 0.5*((g()%100000)/100000.0) : (1.0/256)*(1+ (g()%1000)/100.0));
    if(pg>=0.9999) pg=0.9999;
    long C = (long)(pg*N);
    // choose r near typical-longest-run so p_local path is exercised
    double q=1-pg; long r = (long)(log((double)N*q)/-log(pg)) + (long)(g()%20) - 5; if(r<1) r=1; if(r>C) r=C;
    fesetround(FE_TONEAREST);
    double a = predictionEstimate(C, N, r, k, "t", 0, "x");
    fesetround(FE_TOWARDZERO);
    double b = predictionEstimate(C, N, r, k, "t", 0, "x");
    fesetround(FE_TONEAREST);
    cnt++;
    if(a!=b){ diffcnt++; double rel=fabs(a-b)/fabs(a); if(rel>worst){worst=rel; printf("N=%ld C=%ld r=%ld k=%d near=%.17g rz=%.17g rel=%.3g\n",N,C,r,k,a,b,rel);} }
  }
  printf("cases=%d differ=%d worst=%.3g\n",cnt,diffcnt,worst);
}
