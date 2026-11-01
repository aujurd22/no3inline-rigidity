// T42j: exhaustive coarse D(m) enumeration with corrected kill taxonomy
// (mixed-triple ground truth: cent/main/anti/G) + family-tower survival.
// Compile: g++ -O2 -o t42j t42j_confinement_enum.cpp ; run: ./t42j <m>
#include <bits/stdc++.h>
using namespace std;
int m; long long n2; // n2 = 2m (fine n)
vector<array<int,2>> chosen; // coarse points
long long sols = 0;
map<string,long long> prof;
vector<vector<array<int,2>>> gonly;

bool col3(long long x3, long long y3) {
    int k = chosen.size();
    for (int a = 0; a < k; a++)
        for (int b = a+1; b < k; b++) {
            long long x1 = chosen[a][0], y1 = chosen[a][1];
            long long x2 = chosen[b][0], y2 = chosen[b][1];
            if ((x2-x1)*(y3-y1) == (y2-y1)*(x3-x1)) return true;
        }
    return false;
}

struct Fam { int al, be; };
bool fam_kill(const vector<array<int,2>>& S, Fam f) {
    long long nb = 2*m - 1;
    map<long long,int> M;
    for (auto &p : S) M[(long long)f.al*p[0] - 2LL*f.be*p[1]]++;
    for (auto &kv : M) {
        if (kv.second >= 2) {
            long long cs = -kv.first + (long long)(f.al - f.be) * nb;
            auto it = M.find(cs);
            if (it != M.end() && it->second >= 1) return true;
        }
    }
    return false;
}

bool cent_kill(const vector<array<int,2>>& S) {
    long long nb = 2*m - 1;
    int k = S.size();
    for (int i = 0; i < k; i++)
        for (int j = i+1; j < k; j++) {
            long long u1 = 2*S[i][0]-nb, w1 = 4*S[i][1]-nb;
            long long u2 = 2*S[j][0]-nb, w2 = 4*S[j][1]-nb;
            if (u1*w2 == u2*w1) return true;
        }
    return false;
}

void classify(const vector<array<int,2>>& S) {
    int k = S.size();
    bool hasMain=false, hasAnti=false, hasCent=false, hasG=false;
    for (int i = 0; i < k; i++)
        for (int j = i+1; j < k; j++)
            for (int t = 0; t < k; t++) {
                long long ax = S[i][0],      ay = 2LL*S[i][1];
                long long bx = S[j][0],      by = 2LL*S[j][1];
                long long cx = n2-1-S[t][0], cy = n2-1-2LL*S[t][1];
                if ((bx-ax)*(cy-ay) != (by-ay)*(cx-ax)) continue;
                if (t == i || t == j) hasCent = true;
                else {
                    long long dx = bx-ax, dy = by-ay;
                    if (dx == 0 || dy == 0) hasG = true;
                    else if (dx == dy || dx == -dy) { if (dx*dy > 0) hasMain = true; else hasAnti = true; }
                    else hasG = true;
                }
            }
    char buf[32];
    snprintf(buf, sizeof buf, "%d%d%d%d", (int)hasMain, (int)hasAnti, (int)hasCent, (int)hasG);
    prof[buf]++;
    if (!hasMain && !hasAnti && !hasCent) gonly.push_back(S);
}

void dfs(int row, vector<int>& colcnt) {
    if (row == m) {
        for (int c = 0; c < m; c++) if (colcnt[c] != 2) return;
        sols++;
        classify(chosen);
        return;
    }
    for (int c1 = 0; c1 < m; c1++) {
        if (colcnt[c1] >= 2) continue;
        if (col3(c1, row)) continue;
        chosen.push_back({c1, row});
        for (int c2 = c1+1; c2 < m; c2++) {
            if (colcnt[c2] >= 2) continue;
            if (col3(c2, row)) continue;
            chosen.push_back({c2, row});
            colcnt[c1]++; colcnt[c2]++;
            dfs(row+1, colcnt);
            colcnt[c1]--; colcnt[c2]--;
            chosen.pop_back();
        }
        chosen.pop_back();
    }
}

int main(int argc, char** argv) {
    m = atoi(argv[1]);
    n2 = 2*m;
    vector<int> colcnt(m, 0);
    dfs(0, colcnt);
    printf("m=%d sols=%lld\n", m, sols);
    for (auto &kv : prof) printf("  profile(main,anti,cent,G)=%s: %lld\n", kv.first.c_str(), kv.second);
    vector<Fam> t3 = {{1,-2}};
    vector<Fam> t5 = {{1,-2},{1,2},{1,-3},{1,3}};
    vector<Fam> t7 = {{1,-2},{1,2},{1,-3},{1,3},{2,-1},{2,1}};
    for (auto &nt : vector<pair<string,vector<Fam>>>{{"3fam",t3},{"5fam",t5},{"7fam",t7}}) {
        long long surv = 0;
        for (auto &S : gonly) {
            bool killed = false;
            for (auto f : nt.second) if (fam_kill(S, f)) { killed = true; break; }
            if (!killed) surv++;
        }
        printf("  G-only=%zu, %s survivors=%lld\n", gonly.size(), nt.first.c_str(), surv);
    }
    return 0;
}
