// Route②: EXACT structural conflict-hypergraph degree / co-degree.
// Hypergraph H: vertices = m^2 quadrant cells. Hyperedges:
//   (X) ternary: 3 distinct cells {a,b,c} s.t. EXISTS orientation triple
//                 (r1,r2,r3) making their C4-lifted points collinear.
//   (S) binary : 2 distinct cells sharing a slope-+-1 line after C4 lift.
// We compute EXACT degree of every cell, EXACT co-degree of every cell-pair,
// and total hyperedge counts. N = 2m. C4 lift ground truth from verify_cells.py.
#include <bits/stdc++.h>
using namespace std;

struct Pt { int x, y; };
Pt c4(int x, int y, int r, int N) {
    if (r == 0) return {x, y};
    if (r == 1) return {N - 1 - y, x};
    if (r == 2) return {N - 1 - x, N - 1 - y};
    return {y, N - 1 - x};
}
inline bool coll(Pt p, Pt q, Pt r) {
    return (long long)(q.x - p.x) * (r.y - p.y) == (long long)(r.x - p.x) * (q.y - p.y);
}

int main() {
    vector<int> ms = {10, 14, 18, 22, 26, 30, 37};
    printf("m,N,NC,totalX,maxDeg,avgDeg,maxCoDeg,avgCoDegActive,activePairs,totalS,maxSdeg,avgSdeg\n");
    for (int m : ms) {
        int N = 2 * m;
        int NC = m * m;
        vector<array<Pt, 4>> lift(NC);
        for (int i = 0; i < m; i++) for (int j = 0; j < m; j++) {
            int c = i * m + j;
            for (int r = 0; r < 4; r++) lift[c][r] = c4(i, j, r, N);
        }
        vector<long long> deg(NC, 0);
        vector<long long> cod((size_t)NC * NC, 0);  // pair (a,b), a<b -> a*NC+b
        long long totalX = 0;
        for (int a = 0; a < NC; a++) {
            for (int b = a + 1; b < NC; b++) {
                for (int c = b + 1; c < NC; c++) {
                    bool isX = false;
                    for (int r1 = 0; r1 < 4 && !isX; r1++)
                        for (int r2 = 0; r2 < 4 && !isX; r2++)
                            for (int r3 = 0; r3 < 4 && !isX; r3++) {
                                Pt p = lift[a][r1], q = lift[b][r2], s = lift[c][r3];
                                if (p.x == q.x && p.y == q.y) continue;
                                if (p.x == s.x && p.y == s.y) continue;
                                if (q.x == s.x && q.y == s.y) continue;
                                if (coll(p, q, s)) isX = true;
                            }
                    if (isX) {
                        totalX++;
                        deg[a]++; deg[b]++; deg[c]++;
                        cod[(size_t)a * NC + b]++;
                        cod[(size_t)a * NC + c]++;
                        cod[(size_t)b * NC + c]++;
                    }
                }
            }
        }
        long long mx = 0, sumdeg = 0;
        for (long long d : deg) { mx = max(mx, d); sumdeg += d; }
        double avg = (double)sumdeg / NC;
        long long mxco = 0, sumco = 0, npair = 0;
        for (size_t i = 0; i < cod.size(); i++) if (cod[i] > 0) { mxco = max(mxco, cod[i]); sumco += cod[i]; npair++; }
        double avgco = npair ? (double)sumco / npair : 0;

        // (S) edges
        long long totalS = 0; vector<long long> sdeg(NC, 0);
        for (int a = 0; a < NC; a++)
            for (int b = a + 1; b < NC; b++) {
                bool sE = false;
                for (int r1 = 0; r1 < 4 && !sE; r1++)
                    for (int r2 = 0; r2 < 4 && !sE; r2++) {
                        Pt p = lift[a][r1], q = lift[b][r2];
                        if (p.y - p.x == q.y - q.x) sE = true;   // slope +1 line
                        if (p.y + p.x == q.y + q.x) sE = true;   // slope -1 line
                    }
                if (sE) { totalS++; sdeg[a]++; sdeg[b]++; }
            }
        long long mxs = 0, sumsd = 0;
        for (long long d : sdeg) { mxs = max(mxs, d); sumsd += d; }
        double avgs = (double)sumsd / NC;

        printf("%d,%d,%d,%lld,%lld,%.4f,%lld,%.4f,%lld,%lld,%lld,%.4f\n",
               m, N, NC, totalX, mx, avg, mxco, avgco, npair, totalS, mxs, avgs);
    }
    return 0;
}
