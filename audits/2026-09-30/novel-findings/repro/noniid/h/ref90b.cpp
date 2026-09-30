// Literal SP 800-90B 6.3.7-6.3.10 reference (C++ port of ref90b.py, same structure:
// separate update / predict phases, independent per-order lookups, correct[] array).
// Written from the spec pseudocode, not from the tool.  Prints C, r (=longest run+1), N.
// usage: ref90b <file> <bits> <lit|bit> <est...> ; est in mcw lag mmc lz
// Translation (lit): values masked to <bits>, mapped order-preservingly to 0..k-1.
// Bitstring (bit): MSB-first bits of the masked raw values.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <string>
#include <map>
#include <unordered_map>
#include <algorithm>
using namespace std;

static long longest_run(const vector<uint8_t> &c) {
  long best = 0, cur = 0;
  for (uint8_t v : c) { if (v) { if (++cur > best) best = cur; } else cur = 0; }
  return best;
}

static const int NUL = -1;
static int TIE_LARGEST = 1;  // env TIE=smallest flips

static void report(const char *name, long C, long N, long r) {
  printf("REF %s C=%ld r=%ld N=%ld\n", name, C, r, N);
}

// 6.3.7 -- naive argmax over the alphabet each step, tie -> most recent occurrence
static void mcw(const vector<int> &S, int k) {
  long L = S.size(); const int D = 4; long W[D] = {63, 255, 1023, 4095};
  if (L < W[0] + 2) { printf("REF mcw skipped\n"); return; }
  long N = L - W[0];
  vector<uint8_t> correct(N, 0);
  long score[D] = {0}; int winner = 0;
  vector<vector<long>> cnt(D, vector<long>(k, 0)), last(D, vector<long>(k, -1));
  for (long i1 = W[0] + 1; i1 <= L; i1++) {
    long i0 = i1 - 1; int fr[D];
    for (int j = 0; j < D; j++) {
      fr[j] = NUL;
      if (i1 > W[j]) {
        if (i1 == W[j] + 1) { // build window s_{i-w}..s_{i-1}
          for (long p = i0 - W[j]; p < i0; p++) { cnt[j][S[p]]++; last[j][S[p]] = p; }
        }
        long bc = -1, bp = -1; int by = NUL;
        for (int y = 0; y < k; y++) {
          if (cnt[j][y] == 0) continue;
          if (cnt[j][y] > bc || (cnt[j][y] == bc && last[j][y] > bp)) { bc = cnt[j][y]; bp = last[j][y]; by = y; }
        }
        fr[j] = by;
      }
    }
    int pred = fr[winner];
    if (pred != NUL && pred == S[i0]) correct[i1 - W[0] - 1] = 1;
    for (int j = 0; j < D; j++)
      if (fr[j] != NUL && fr[j] == S[i0]) { score[j]++; if (score[j] >= score[winner]) winner = j; }
    for (int j = 0; j < D; j++)
      if (i1 > W[j]) { cnt[j][S[i0 - W[j]]]--; cnt[j][S[i0]]++; last[j][S[i0]] = i0; }
  }
  long C = 0; for (auto c : correct) C += c;
  report("mcw", C, N, longest_run(correct) + 1);
}

// 6.3.8
static void lag(const vector<int> &S, int k) {
  long L = S.size(); const int D = 128; long N = L - 1;
  vector<uint8_t> correct(N, 0); long score[D + 1] = {0}; int winner = 1;
  for (long i = 2; i <= L; i++) {
    int lagv[D + 1];
    for (int d = 1; d <= D; d++) lagv[d] = (d < i) ? S[i - d - 1] : NUL;
    int pred = lagv[winner];
    if (pred != NUL && pred == S[i - 1]) correct[i - 2] = 1;
    for (int d = 1; d <= D; d++)
      if (lagv[d] != NUL && lagv[d] == S[i - 1]) { score[d]++; if (score[d] >= score[winner]) winner = d; }
  }
  long C = 0; for (auto c : correct) C += c;
  report("lag", C, N, longest_run(correct) + 1);
}

typedef map<int, long> Post;  // y -> count
static int argmax_y(const Post &p, long &cnt) {
  int by = NUL; long bc = -1;
  for (auto &kv : p) {
    if (kv.second > bc || (kv.second == bc && (TIE_LARGEST ? kv.first > by : kv.first < by))) { bc = kv.second; by = kv.first; }
  }
  cnt = bc; return by;
}
static string key(const vector<int> &S, long from0, long len) {  // 0-indexed start, len symbols
  string s; s.resize(len);
  for (long t = 0; t < len; t++) s[t] = (char)S[from0 + t];
  return s;
}

// 6.3.9
static long MAXE = 100000;
static void mmc(const vector<int> &S, int k) {
  long L = S.size(); const int D = 16; long N = L - 2;
  vector<uint8_t> correct(N, 0); vector<long> entries(D + 1, 0);
  vector<unordered_map<string, Post>> M(D + 1);
  long score[D + 1] = {0}; int winner = 1; long winnerNull = 0, winnerNullAfterCorrect = 0;
  long orphanSteps = 0, orphanWinnerSteps = 0, orphanWinnerCorrect = 0;
  for (long i = 3; i <= L; i++) {
    for (int d = 1; d <= D; d++) {
      if (d < i - 1) {  // x = s_{i-d-1}..s_{i-2}, y = s_{i-1}
        string x = key(S, i - d - 2, d); int y = S[i - 2];
        auto it = M[d].find(x);
        if (it != M[d].end() && it->second.count(y)) it->second[y]++;
        else if (entries[d] < MAXE) { M[d][x][y] = 1; entries[d]++; }
      }
    }
    int sub[D + 1];
    for (int d = 1; d <= D; d++) {
      sub[d] = NUL;
      if (d < i) {
        string x = key(S, i - d - 1, d);
        auto it = M[d].find(x);
        if (it != M[d].end() && !it->second.empty()) { long c; sub[d] = argmax_y(it->second, c); }
      }
    }
    int pred = sub[winner];
    if (pred == NUL) { winnerNull++; if (i > 3 && correct[i - 4]) winnerNullAfterCorrect++; }
    { // F10 diagnostics: first absent order below a present order
      int firstAbsent = 0; bool orphanAny = false, orphanWinner = false;
      for (int d = 1; d <= D && d < i; d++) {
        if (sub[d] == NUL) { if (!firstAbsent) firstAbsent = d; }
        else if (firstAbsent) { orphanAny = true; if (d == winner) orphanWinner = true; }
      }
      if (orphanAny) orphanSteps++;
      if (orphanWinner) { orphanWinnerSteps++; if (pred == S[i - 1]) orphanWinnerCorrect++; }
    }
    if (pred != NUL && pred == S[i - 1]) correct[i - 3] = 1;
    for (int d = 1; d <= D; d++)
      if (sub[d] != NUL && sub[d] == S[i - 1]) { score[d]++; if (score[d] >= score[winner]) winner = d; }
  }
  long C = 0; for (auto c : correct) C += c;
  report("mmc", C, N, longest_run(correct) + 1);
  printf("REFINFO mmc scoreboard:"); for (int d = 1; d <= D; d++) printf(" %ld", score[d]); printf(" winner=%d\n", winner);
  printf("REFINFO mmc orphanSteps=%ld orphanWinnerSteps=%ld orphanWinnerCorrect=%ld\n", orphanSteps, orphanWinnerSteps, orphanWinnerCorrect);
  printf("REFINFO mmc winnerNull=%ld winnerNullAfterCorrect=%ld entries:", winnerNull, winnerNullAfterCorrect);
  for (int d = 1; d <= D; d++) printf(" %ld", entries[d]);
  printf("\n");
}


// Emulation of the TOOL's semantics, for causal attribution only:
//  CHAIN: order d is looked up only if order d-1 was found (else Null; F10)
//  CHAINUPD: in a chained-skip, the tool adds/increments via operator[] only if entries[d] < MAX and counts entries[d]++ unconditionally
//  NORESET: a Null prediction by the winner does not reset the run (F09)
static void mmc_emu(const vector<int> &S, int k, bool chain, bool noreset) {
  long L = S.size(); const int D = 16; long N = L - 2;
  vector<long> entries(D + 1, 0); vector<unordered_map<string, Post>> M(D + 1);
  long score[D + 1] = {0}; int winner = 1; long C = 0, run = 0, maxrun = 0;
  if (L >= 2) { M[1][key(S, 0, 1)][S[1]] = 1; entries[1] = 1; }  // spec step i=3 phase a: (s_1) -> s_2
  for (long i = 3; i <= L; i++) {
    int sub[D + 1]; bool found[D + 1];
    bool chainok = true;
    for (int d = 1; d <= D; d++) {
      sub[d] = NUL; found[d] = false;
      if (d < i - 1 + 1 && d <= i - 2) {  // tool: d (0-based) <= i-2 (0-based)  <=> spec d <= i-2
        if (!chain || chainok) {
          string x = key(S, i - d - 1, d);
          auto it = M[d].find(x);
          if (it != M[d].end() && !it->second.empty()) { long c; sub[d] = argmax_y(it->second, c); found[d] = true; }
          else chainok = false;
        }
      }
    }
    int pred = sub[winner];
    if (pred != NUL && pred == S[i - 1]) { C++; if (++run > maxrun) maxrun = run; }
    else if (pred != NUL || !noreset) run = 0;
    for (int d = 1; d <= D; d++)
      if (sub[d] != NUL && sub[d] == S[i - 1]) { score[d]++; if (score[d] >= score[winner]) winner = d; }
    // updates with y = s_i for contexts ending at s_{i-1} (spec does these at step i+1, phase a)
    for (int d = 1; d <= D; d++) {
      if (d <= i - 1) {
        string x = key(S, i - d - 1, d); int y = S[i - 1];
        if (found[d] || !chain) {
          auto it = M[d].find(x);
          if (it != M[d].end() && it->second.count(y)) it->second[y]++;
          else if (entries[d] < MAXE) { M[d][x][y] = 1; entries[d]++; }
        } else if (entries[d] < MAXE) {  // tool's chained-skip branch
          M[d][x][y] += 1; entries[d]++;
        }
      }
    }
  }
  printf("REF mmcemu%s%s C=%ld r=%ld N=%ld\n", chain ? "_chain" : "", noreset ? "_noreset" : "", C, maxrun + 1, N);
}

// 6.3.10
static long MAXD = 65536;
static void lz(const vector<int> &S, int k) {
  long L = S.size(); const int B = 16; long N = L - B - 1;
  vector<uint8_t> correct(N, 0);
  unordered_map<string, Post> Dct; long size = 0;
  for (long i = B + 2; i <= L; i++) {
    for (int j = B; j >= 1; j--) {  // prev = s_{i-j-1}..s_{i-2}, y = s_{i-1}
      string prev = key(S, i - j - 2, j); int y = S[i - 2];
      auto it = Dct.find(prev);
      if (it == Dct.end() && size < MAXD) { Dct[prev][y] = 0; size++; it = Dct.find(prev); }
      if (it != Dct.end()) it->second[y]++;
    }
    long maxcount = 0; int pred = NUL;
    for (int j = B; j >= 1; j--) {
      string prev = key(S, i - j - 1, j);
      auto it = Dct.find(prev);
      if (it != Dct.end()) { long c; int y = argmax_y(it->second, c); if (c > maxcount) { pred = y; maxcount = c; } }
    }
    if (pred != NUL && pred == S[i - 1]) correct[i - B - 2] = 1;
  }
  long C = 0; for (auto c : correct) C += c;
  report("lz", C, N, longest_run(correct) + 1);
  printf("REFINFO lz dict_size=%ld\n", size);
}

int main(int argc, char **argv) {
  if (getenv("TIE") && !strcmp(getenv("TIE"), "smallest")) TIE_LARGEST = 0;
  if (getenv("MAXE")) MAXE = atol(getenv("MAXE"));
  if (getenv("MAXD")) MAXD = atol(getenv("MAXD"));
  FILE *f = fopen(argv[1], "rb"); if (!f) return 2;
  vector<uint8_t> raw; int c; while ((c = fgetc(f)) != EOF) raw.push_back((uint8_t)c); fclose(f);
  int bits = atoi(argv[2]);
  if (bits == 0) { uint8_t m = 0; for (auto v : raw) m |= v; bits = 8; while (bits > 1 && !(m & (1 << (bits - 1)))) bits--; }
  int mask = (1 << bits) - 1;
  vector<int> S; int k;
  if (!strcmp(argv[3], "lit")) {
    vector<int> present(256, 0); for (auto v : raw) present[v & mask] = 1;
    vector<int> tab(256, -1); k = 0; for (int v = 0; v < 256; v++) if (present[v]) tab[v] = k++;
    for (auto v : raw) S.push_back(tab[v & mask]);
  } else {
    k = 2; for (auto v : raw) for (int j = 0; j < bits; j++) S.push_back(((v & mask) >> (bits - 1 - j)) & 1);
  }
  printf("REF L=%zu k=%d bits=%d\n", S.size(), k, bits);
  for (int a = 4; a < argc; a++) {
    if (!strcmp(argv[a], "mcw")) mcw(S, k);
    else if (!strcmp(argv[a], "lag")) lag(S, k);
    else if (!strcmp(argv[a], "mmc")) mmc(S, k);
    else if (!strcmp(argv[a], "lz")) lz(S, k);
    else if (!strcmp(argv[a], "emu")) { mmc_emu(S, k, false, false); mmc_emu(S, k, true, false); mmc_emu(S, k, false, true); mmc_emu(S, k, true, true); }
  }
  return 0;
}
