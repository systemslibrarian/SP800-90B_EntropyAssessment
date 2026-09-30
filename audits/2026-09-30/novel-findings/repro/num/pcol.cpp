#include <cstdio>
#include <cmath>
#include <vector>
using namespace std;
int main(){
  // replicate calc_proportions + calc_collision_proportion for exactly balanced counts
  int fails=0;
  for(int k=2;k<=256;k++){
    for(long c : {1000L, 3906L, 3907L, 4000L, 10000L, 333334L, 1000000L/ (long)k, 1000000L/(long)k + 1}){
      long L = c*k;
      if (L > 2147483647L) continue;
      vector<double> p(k,0.0);
      for(int i=0;i<k;i++) p[i]=c;           // counts
      for(int i=0;i<k;i++) p[i] /= (double)(int)L;  // same as calc_proportions (sample_size is int)
      long double pcol=0.0L;
      for(unsigned i=0;i<p.size();i++) pcol += powl((long double)p[i], 2.0L);
      if(!(pcol >= 1.0L/((long double)k))) { if(fails<40) printf("FAIL k=%d c=%ld L=%ld pcol-1/k=%Lg\n",k,c,L,pcol-1.0L/k); fails++; }
    }
  }
  printf("fails=%d\n",fails);
}
