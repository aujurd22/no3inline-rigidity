// Route③: empirical test of single-cycle (terrace-style) constructions for m=37 (N=74).
// For each candidate single 37-cycle permutation pi (cells = (pi[i], pi[i+1 mod 37])):
//   - check it is a valid permutation forming ONE 37-cycle
//   - lift 4m points via C4, count ALL collinear triples (this is the rot4-NTIL test;
//     it automatically includes both (X) and (S) constraints; reports (X)-only vs (S)-only)
//   - report pass/fail + violation counts
// Plus a randomized search over random 37-cycles whose integer differences satisfy the Sidon
// bound (each |d| magnitude appears <=2 times), tracking the minimum (X) violations found.
#include <bits/stdc++.h>
using namespace std;

static const int M = 37, N = 74;
struct Pt { int x, y; };
Pt c4(int x, int y, int r) {
    if (r == 0) return {x, y};
    if (r == 1) return {N - 1 - y, x};
    if (r == 2) return {N - 1 - x, N - 1 - y};
    return {y, N - 1 - x};
}
inline bool coll(Pt p, Pt q, Pt r) {
    return (long long)(q.x - p.x) * (r.y - p.y) == (long long)(r.x - p.x) * (q.y - p.y);
}

bool isSingleCycle(const vector<int>& pi) {
    int n = pi.size();
    vector<bool> seen(n, false);
    int cnt = 0, cur = 0;
    while (!seen[cur]) { seen[cur] = true; cnt++; cur = pi[cur]; }
    return cnt == n;
}
// build 4m lifted points from a single-cycle pi; return points and the 3*M "cell-origin" index
// of each lifted point (0..M-1) so we can classify (X) [3 distinct cells] vs (S) [2 from same cell].
vector<Pt> liftPoints(const vector<int>& pi, vector<int>& origin) {
    vector<Pt> pts; origin.clear();
    for (int i = 0; i < M; i++) {
        int x = pi[i], y = pi[(i + 1) % M];
        for (int r = 0; r < 4; r++) { pts.push_back(c4(x, y, r)); origin.push_back(i); }
    }
    return pts;
}
// count collinear triples; classify
long long countViolations(const vector<int>& pi, long long& xv, long long& sv) {
    vector<int> origin; auto pts = liftPoints(pi, origin);
    long long tot = 0; xv = 0; sv = 0;
    int P = pts.size();
    for (int i = 0; i < P; i++)
        for (int j = i + 1; j < P; j++)
            for (int k = j + 1; k < P; k++) {
                if (coll(pts[i], pts[j], pts[k])) {
                    tot++;
                    // classify: are the 3 origins all distinct?
                    int a = origin[i], b = origin[j], c = origin[k];
                    if (a != b && a != c && b != c) xv++;   // genuine (X): 3 distinct cells
                    else sv++;                               // (S)-type: >=2 shares a cell
                }
            }
    return tot;
}

// ---- Family generators: each builds a sequence `seq` (a single 37-cycle ordering),
//      then converts to permutation pi via pi[seq[i]] = seq[(i+1)%M]. ----
vector<int> seq_to_pi(const vector<int>& seq) {
    vector<int> pi(M);
    for (int i = 0; i < M; i++) pi[seq[i]] = seq[(i + 1) % M];
    return pi;
}
bool isPermutation(const vector<int>& seq) {
    vector<bool> seen(M, false);
    for (int v : seq) { if (seen[v]) return false; seen[v] = true; }
    return seq.size() == M;
}
vector<int> fam_primitive_root() {  // 0 -> g^0 -> g^1 -> ... -> g^35 -> 0, g=2 primitive root mod 37
    int g = 2; vector<int> seq(M);
    seq[0] = 0;
    for (int i = 1; i < M; i++) seq[i] = (int)(((long long)pow(g, i - 1)) % M);
    return seq_to_pi(seq);
}
vector<int> fam_qr_order() {  // [0] + quadratic residues (asc) + non-residues (asc) as a cycle
    vector<int> seq; seq.push_back(0);
    vector<int> qr, nqr;
    for (int x = 1; x < M; x++) {
        long long v = ((long long)x * x) % M;
        bool isQR = false;
        for (int t = 1; t < M; t++) if (((long long)t * t) % M == v) { isQR = (t <= M / 2); break; }
        if (isQR) qr.push_back(x); else nqr.push_back(x);
    }
    sort(qr.begin(), qr.end()); sort(nqr.begin(), nqr.end());
    for (int v : qr) seq.push_back(v);
    for (int v : nqr) seq.push_back(v);
    return seq_to_pi(seq);
}
vector<int> fam_alt_starter() {  // partial sums of alternating-sign starter S={g^0..g^17}
    int g = 2; vector<int> S;
    for (int i = 0; i < 18; i++) S.push_back((int)(((long long)pow(g, i)) % M));
    vector<int> seq(M); seq[0] = 0;
    for (int i = 0; i < 36; i++) {
        int s = S[i / 2];
        if (i % 2 == 1) s = M - s;
        seq[i + 1] = (seq[i] + s) % M;
    }
    return seq_to_pi(seq);
}
vector<int> fam_skolem() {  // differences 1,1,2,2,...,18,18 via partial sums
    vector<int> seq(M); seq[0] = 0;
    for (int d = 1; d <= 18; d++) {
        seq[2 * d - 1] = (seq[2 * d - 2] + d) % M;
        seq[2 * d]     = (seq[2 * d - 1] - d + M) % M;
    }
    return seq_to_pi(seq);
}

bool satisfiesSidon(const vector<int>& pi) {
    vector<int> cnt(2 * M + 1, 0);  // index by |d| in 1..36
    for (int i = 0; i < M; i++) {
        int x = pi[i], y = pi[(i + 1) % M];
        int d = y - x;
        int ad = abs(d);
        if (ad == 0) return false;
        cnt[ad]++;
        if (cnt[ad] > 2) return false;
    }
    return true;
}

int main() {
    srand(12345);
    printf("=== Part A: named single-cycle families for m=37 ===\n");
    printf("family,validSingleCycle,sidonOK,totalViol,xViol,sViol,NTILpass\n");
    auto testFam = [&](const string& name, vector<int> pi) {
        bool single = isSingleCycle(pi);
        if (!single) { printf("%s,0,0,NA,NA,NA,0   (construction is NOT a valid single 37-cycle permutation)\n", name.c_str()); return; }
        bool sid = satisfiesSidon(pi);
        long long xv, sv, tot;
        tot = countViolations(pi, xv, sv);
        bool pass = (tot == 0);
        printf("%s,1,%d,%lld,%lld,%lld,%d\n", name.c_str(), sid, tot, xv, sv, pass);
    };
    testFam("primitive_root", fam_primitive_root());
    testFam("qr_order", fam_qr_order());
    testFam("alt_starter", fam_alt_starter());
    testFam("skolem", fam_skolem());

    printf("\n=== Part B: randomized Sidon single-cycle search (T trials) ===\n");
    int T = 300000;
    // fixed 37-cycle sigma for conjugation
    vector<int> sig(M);
    for (int i = 0; i < M; i++) sig[i] = (i + 1) % M;
    long long best = 1e18;
    int bestSeed = -1;
    int nSingle = 0, nSidon = 0, nZero = 0;
    vector<int> bestPi;
    for (int t = 0; t < T; t++) {
        vector<int> tau(M); iota(tau.begin(), tau.end(), 0);
        random_shuffle(tau.begin(), tau.end());
        vector<int> inv(M); for (int i = 0; i < M; i++) inv[tau[i]] = i;
        vector<int> pi(M);
        for (int i = 0; i < M; i++) pi[tau[i]] = tau[sig[i]];
        if (!isSingleCycle(pi)) continue;
        nSingle++;
        if (!satisfiesSidon(pi)) continue;
        nSidon++;
        long long xv, sv, tot;
        tot = countViolations(pi, xv, sv);
        if (tot < best) { best = tot; bestSeed = t; bestPi = pi; }
        if (tot == 0) { nZero++; printf("  FOUND ZERO-VIOLATION at trial %d\n", t); break; }
    }
    printf("trials=%d singleCycles=%d sidonSingleCycles=%d zeroViolationFound=%d bestViolations=%lld (seed=%d)\n",
           T, nSingle, nSidon, nZero, best, bestSeed);
    if (bestSeed >= 0 && best > 0) {
        // dump best permutation
        printf("bestPi=");
        for (int v : bestPi) printf("%d ", v);
        printf("\n");
    }
    return 0;
}
