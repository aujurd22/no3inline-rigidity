// Route⑤: EXACT Burnside orbit count for direction-KEY / LINE set X under C4.
// X = set of all geometric lines in the N x N grid containing >=2 grid points.
// We enumerate X exactly, apply C4 (90/180/270 rot) to each line, dedup orbits.
// Also corrects the prior doc's error: Fix(r) [90deg] = 0 (NOT 2N-1 anti-diagonals).
// And verifies the (X) orientation-triple Burnside count 22 -> 16 genuine forms.
#include <bits/stdc++.h>
using namespace std;

long long gcd3(long long a, long long b, long long c) {
    return gcd(abs(a), gcd(abs(b), abs(c)));
}
struct Line { long long A, B, C; };
bool operator==(const Line& l, const Line& r) { return l.A == r.A && l.B == r.B && l.C == r.C; }
struct LHash { size_t operator()(const Line& l) const {
    return (size_t)((l.A * 73856093) ^ (l.B * 19349663) ^ (l.C * 83492791)) >> 1; } };

Line normalize(long long A, long long B, long long C) {
    long long g = gcd3(A, B, C);
    if (g != 0) { A /= g; B /= g; C /= g; }
    if (A < 0 || (A == 0 && B < 0)) { A = -A; B = -B; C = -C; }
    return {A, B, C};
}
// line through two grid points
Line lineThrough(int x1, int y1, int x2, int y2) {
    long long A = (long long)y2 - y1;
    long long B = (long long)x1 - x2;
    long long C = -(A * x1 + B * y1);
    return normalize(A, B, C);
}
// C4 rotations on line normal form (N = grid size)
Line rot90(const Line& L, int N) { // (x,y)->(N-1-y,x): (A,B,C)->(-B,A,B*(N-1)+C)
    return normalize(-L.B, L.A, L.B * (N - 1) + L.C);
}
Line rot180(const Line& L, int N) { // (x,y)->(N-1-x,N-1-y): C -> -(A(N-1)+B(N-1)+C)
    return normalize(L.A, L.B, -(L.A * (N - 1) + L.B * (N - 1) + L.C));
}
Line rot270(const Line& L, int N) { // inverse 90
    return normalize(L.B, -L.A, L.A * (N - 1) + L.C);
}

int main() {
    printf("=== Part A: exact line-set Burnside under C4 ===\n");
    printf("N,|X|,|X/C4|,Fix(r90),Fix(r180),Fix(r270),L_c(through center),BurnsideCheck(|X|+2Fix90+Fix180)/4\n");
    for (int m : {10, 14, 18, 22, 26, 30, 37}) {
        int N = 2 * m;
        unordered_set<Line, LHash> X;
        for (int x1 = 0; x1 < N; x1++)
            for (int y1 = 0; y1 < N; y1++)
                for (int x2 = x1; x2 < N; x2++)
                    for (int y2 = (x2 == x1) ? y1 + 1 : 0; y2 < N; y2++) {
                        if (x1 == x2 && y1 == y2) continue;
                        X.insert(lineThrough(x1, y1, x2, y2));
                    }
        long long fix90 = 0, fix180 = 0, fix270 = 0;
        for (const Line& L : X) {
            if (rot90(L, N) == L) fix90++;
            if (rot180(L, N) == L) fix180++;
            if (rot270(L, N) == L) fix270++;
        }
        // orbit canonical rep = lexicographically smallest of {L, rL, r2L, r3L}
        unordered_set<Line, LHash> orbits;
        for (const Line& L : X) {
            Line best = L;
            Line cur = L;
            for (int k = 0; k < 4; k++) {
                cur = rot90(cur, N);
                if (cur.A < best.A || (cur.A == best.A && cur.B < best.B) ||
                    (cur.A == best.A && cur.B == best.B && cur.C < best.C)) best = cur;
            }
            orbits.insert(best);
        }
        long long Xc4 = (long long)orbits.size();
        long long burn = (X.size() + 2 * fix90 + fix180) / 4;
        printf("%d,%lld,%lld,%lld,%lld,%lld,%lld,%lld  (check=%s)\n",
               N, (long long)X.size(), Xc4, fix90, fix180, fix270, fix180, burn,
               (burn == Xc4) ? "OK" : "MISMATCH");
    }

    printf("\n=== Part B: (X) orientation-triple Burnside: 64 index triples -> 16 orbits (=16 genuine R8 forms, 0 degenerate) ===\n");
    // orientation triples (r1,r2,r3) in {0,1,2,3}^3, C4 acts diagonally (add k mod 4 to all).
    auto canon = [](int a, int b, int c) {
        int best = (a << 8) | (b << 4) | c;
        int x = a, y = b, z = c;
        for (int k = 0; k < 4; k++) {
            x = (x + 1) & 3; y = (y + 1) & 3; z = (z + 1) & 3;
            int v = (x << 8) | (y << 4) | z;
            if (v < best) best = v;
        }
        return best;
    };
    unordered_set<int> orbitReps;
    for (int a = 0; a < 4; a++) for (int b = 0; b < 4; b++) for (int c = 0; c < 4; c++)
        orbitReps.insert(canon(a, b, c));
    printf("Number of C4-orbits of (r1,r2,r3): %d (expected 22)\n", (int)orbitReps.size());

    // degenerate orbit = orientation triple with identically-zero determinant for generic cells.
    // det(C4(cell1,r1),C4(cell2,r2),C4(cell3,r3)) as poly in generic cells; test on random generic cells.
    auto c4v = [](int x, int y, int r, int N) -> pair<int,int> {
        if (r == 0) return {x, y};
        if (r == 1) return {N - 1 - y, x};
        if (r == 2) return {N - 1 - x, N - 1 - y};
        return {y, N - 1 - x};
    };
    int N = 200;
    int degenerateOrbits = 0;
    int checked = 0;
    for (int rep : orbitReps) {
        int a = (rep >> 8) & 15, b = (rep >> 4) & 15, c = rep & 15;
        bool allZero = true;
        // test on several generic random cell triples
        for (int t = 0; t < 8 && allZero; t++) {
            int x1 = rand() % 50, y1 = rand() % 50;
            int x2 = rand() % 50, y2 = rand() % 50;
            int x3 = rand() % 50, y3 = rand() % 50;
            if (x1 == x2 && y1 == y2) { y2++; }
            auto p = c4v(x1, y1, a, N), q = c4v(x2, y2, b, N), s = c4v(x3, y3, c, N);
            long long det = (long long)(q.first - p.first) * (s.second - p.second) -
                            (long long)(s.first - p.first) * (q.second - p.second);
            if (det != 0) allZero = false;
        }
        if (allZero) degenerateOrbits++;
        checked++;
    }
    printf("Degenerate orbits (identically-zero det): %d (expected 6). Genuine forms = %d (expected 16). [heuristic poly test]\n",
           degenerateOrbits, (int)orbitReps.size() - degenerateOrbits);
    return 0;
}
