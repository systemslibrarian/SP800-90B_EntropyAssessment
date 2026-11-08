# Spec-only model of SP 800-90B 5.2.1 (PDF p. 44) bin construction and degrees of freedom.
# Written from the standard's text; it does not read cpp/. Inputs: symbol counts c_i and L.
#   p_i = c_i / L ; e_ij = p_i p_j L/2 (L even here, so floor(L/2) == L/2)
#   sort pairs ascending by e (ties by pair index, the order Example 11's table uses)
#   assign consecutive pairs to a bin until the bin's sum >= 5, then start the next bin;
#   if the last bin < 5, merge the last two. nbin = number of bins; df = nbin - k.
import sys, math
def nbin_df(counts, L):
    k = len(counts); p = [c / L for c in counts]
    pairs = sorted(((p[i] * p[j] * (L / 2), i * k + j) for i in range(k) for j in range(k)))
    bins = []; cur = 0.0
    for e, _ in pairs:
        if cur >= 5.0:
            bins.append(cur); cur = 0.0
        cur += e
    if bins and cur < 5.0:
        bins[-1] += cur
    else:
        bins.append(cur)
    return len(bins), len(bins) - k
def mcv_bits(counts, L):
    # 6.3.1 MCV: p_u = min(1, p_max + 2.576 sqrt(p_max (1-p_max)/L)); H = -log2(p_u)
    pm = max(counts) / L
    pu = min(1.0, pm + 2.576 * math.sqrt(pm * (1 - pm) / L))
    return -math.log2(pu)
if __name__ == "__main__":
    # Example 11 (PDF p. 44): k=3, p = .21/.41/.38, L=100 -> nbin = 6, df = 3
    n, d = nbin_df([21, 41, 38], 100); print(f"example11 L=100 counts=21/41/38 nbin={n} df={d} (spec: nbin=6, df=3)")
    for label, counts, L in [
        ("repro   ", [1992, 4, 4], 2000),
        ("control ", [700, 650, 650], 2000),
        ("df0-mut ", [1980, 10, 10], 2000),
        ("edge4   ", [999992, 4, 4], 1000000),
        ("k3-10x  ", [999980, 10, 10], 1000000),
        ("k3-11x  ", [999978, 11, 11], 1000000),
    ]:
        n, d = nbin_df(counts, L)
        print(f"{label} L={L} counts={'/'.join(map(str,counts))} nbin={n} df={d} applied={'yes' if d >= 1 else 'NO (df<1)'} MCV={mcv_bits(counts, L):.4f} bit")
    # k = 256 at L = 1e6: h heavy symbols sharing the mass, (256-h) symbols occurring once each
    L = 1000000
    for h in (12, 13, 14, 15, 16):
        singles = 256 - h; heavy_total = L - singles
        base, extra = divmod(heavy_total, h)
        counts = [base + 1] * extra + [base] * (h - extra) + [1] * singles
        assert sum(counts) == L and len(counts) == 256
        n, d = nbin_df(counts, L)
        print(f"k256 h={h:2d} L={L} heavy~{base} singles={singles} nbin={n} df={d} applied={'yes' if d >= 1 else 'NO (df<1)'} MCV={mcv_bits(counts, L):.4f} bit")
