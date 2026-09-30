# Independent reference for the ea_restart sanity-check cutoff.
#  (a) SP 800-90B 3.1.4.3 literal: fail iff P(Bin(1000,p) >= X_max) < alpha, alpha = 0.000005, p = 2^-H_I
#      -> largest passing X_max, U_spec = max{x : P(Bin>=x) >= alpha}
#  (b) the tool's own model (restart_main.cpp simulateBound): max count of 1000 draws from the
#      "inverted near-uniform" distribution (floor(1/p) symbols of prob p, one residual symbol),
#      alpha' = 1-0.99^(1/2000); exact smallest c with P(max > c) <= alpha'  (the tool estimates this by simulation)
import sys, math
sys.path.insert(0, __file__.rsplit('/',1)[0] + '/pylib/site')
import mpmath
mpmath.mp.dps = 50
N = 1000

def binom_tail_ge(x, p):  # P(Bin(N,p) >= x), exact via mpmath
    p = mpmath.mpf(p)
    return mpmath.fsum(mpmath.binomial(N, j) * p**j * (1-p)**(N-j) for j in range(x, N+1))

def spec_U(p, alpha=mpmath.mpf('0.000005')):
    # largest x with P(X >= x) >= alpha ; binary search on monotone tail
    lo, hi = 0, N+1   # tail(0)=1>=alpha ; tail(N+1)=0<alpha
    while hi - lo > 1:
        mid = (lo+hi)//2
        if binom_tail_ge(mid, p) >= alpha: lo = mid
        else: hi = mid
    return lo

def model_probs(p):
    m = math.floor(1.0/p)
    probs = [p]*m
    q = 1.0 - m*p
    if math.ceil(1.0/p) > m and q > 0: probs.append(q)
    return probs

def p_max_le(c, probs):
    # P(all multinomial(N, probs) counts <= c), sequential conditional binomial DP in mpmath-free doubles w/ log pmf
    # f[n] = P(remaining symbols all <= c | n trials left among them)
    k = len(probs)
    S = [0.0]*(k+1)
    for i in range(k-1, -1, -1): S[i] = S[i+1] + probs[i]
    f = [1.0 if n <= c else 0.0 for n in range(N+1)]   # last symbol takes everything
    lg = [math.lgamma(n+1) for n in range(N+1)]
    for i in range(k-2, -1, -1):
        pi = probs[i] / S[i]
        if pi >= 1.0: pi = 1.0
        lp = math.log(pi) if pi > 0 else -math.inf
        lq = math.log1p(-pi) if pi < 1 else -math.inf
        g = [0.0]*(N+1)
        for n in range(N+1):
            acc = 0.0
            for j in range(0, min(c, n)+1):
                fn = f[n-j]
                if fn == 0.0: continue
                e = lg[n]-lg[j]-lg[n-j] + (j*lp if j else 0.0) + ((n-j)*lq if n-j else 0.0)
                acc += math.exp(e) * fn
            g[n] = acc
        f = g
    return f[N]

def model_cutoff(p, alpha, start=None):
    probs = model_probs(p)
    # start near the mean and walk
    c = start if start is not None else max(int(N*p), 1)
    while 1.0 - p_max_le(c, probs) > alpha: c += 1
    while c > 0 and 1.0 - p_max_le(c-1, probs) <= alpha: c -= 1
    tails = {cc: 1.0 - p_max_le(cc, probs) for cc in (c-1, c, c+1)}
    return c, tails

if __name__ == '__main__':
    alpha_tool = 1 - math.exp(math.log(0.99)/2000)
    for s in sys.argv[1:]:
        H = float(s); p = 2.0**-H
        U = spec_U(p)
        c, tails = model_cutoff(p, alpha_tool, start=U)
        print(f"H_I={H}  p={p:.6g}  spec_U(alpha=5e-6,binomial)={U}  P_binom(X>={U})={float(binom_tail_ge(U,p)):.4g} P_binom(X>={U+1})={float(binom_tail_ge(U+1,p)):.4g} | model c*={c} tails: " + ", ".join(f"P(max>{k})={v:.4g}" for k,v in sorted(tails.items())))
