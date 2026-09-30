#include "/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/rel/cpp/shared/utils.h"
#include "/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad/audit/rel/cpp/iid/chi_square_tests.h"
#include <cstdio>
int main(){ double x,k; while(scanf("%lf %lf",&x,&k)==2) printf("%.17g %.17g %.17g\n",x,k,chi_square_pvalue(x,k)); }
