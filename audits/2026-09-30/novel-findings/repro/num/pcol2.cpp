#include <cstdio>
#include <cmath>
#include <vector>
using namespace std;
bool fails(int k, long L){ // balanced counts, L divisible by k
  long c=L/k; vector<double> p(k,0.0);
  for(int i=0;i<k;i++) p[i]=c;
  for(int i=0;i<k;i++) p[i] /= (double)(int)L;
  long double pcol=0.0L; for(unsigned i=0;i<p.size();i++) pcol += powl((long double)p[i], 2.0L);
  return !(pcol >= 1.0L/((long double)k));
}
int main(){
  printf("k failing (any balanced L):");
  for(int k=2;k<=256;k++) if(fails(k, (long)k*4000)) printf(" %d",k);
  printf("\nk dividing 1e6 that fail at L=1e6:");
  for(int k=2;k<=256;k++) if(1000000%k==0 && fails(k,1000000)) printf(" %d",k);
  printf("\n");
}
