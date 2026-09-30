#include "/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/rel/cpp/shared/utils.h"
#include <map>
int main(){
  uint64_t st[4]; seed(st);
  // 1) FY uniformity on n=4 (24 perms), 2.4M shuffles
  std::map<uint32_t,long> cnt; uint8_t a[4],b[4];
  for(long it=0; it<2400000; it++){ for(int i=0;i<4;i++){a[i]=i;b[i]=i;} FYshuffle(a,b,4,st);
     uint32_t k=a[0]|(a[1]<<8)|(a[2]<<16)|(a[3]<<24); cnt[k]++; if(memcmp(a,b,4)) {printf("desync\n"); return 1;} }
  double chi=0; for(auto&kv:cnt){ double e=100000; chi+=(kv.second-e)*(kv.second-e)/e; }
  printf("perms=%zu chi2(23df)=%.3f\n", cnt.size(), chi);
  // 2) randomRange64 on awkward bound s=2^63 (range [0,2^63]) and s=5: bucket test
  long c6[6]={0}; for(long i=0;i<6000000;i++) c6[randomRange64(5,st)]++;
  chi=0; for(int i=0;i<6;i++){double e=1e6; chi+=(c6[i]-e)*(c6[i]-e)/e;} printf("range[0,5] chi2(5df)=%.3f\n",chi);
  uint64_t s=(1ULL<<63)+(1ULL<<62); long top=0,N=4000000; for(long i=0;i<N;i++){ uint64_t v=randomRange64(s,st); if(v>s){printf("OOR\n");return 1;} if(v> (s/3)*2) top++; }
  printf("range[0,3*2^62] upper-third fraction=%.5f (expect ~0.33333)\n",(double)top/N);
  // 3) jump streams differ
  uint64_t s0[4],s1[4]; seed(s0); memcpy(s1,s0,sizeof s0); xoshiro_jump(1,s1);
  int same=0; for(int i=0;i<1000;i++) if(xoshiro256starstar(s0)==xoshiro256starstar(s1)) same++; printf("jump collisions in 1000 draws: %d\n",same);
}
