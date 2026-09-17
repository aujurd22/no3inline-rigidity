// csearch.cpp -- C++ 模拟退火/贪婪下降构造 rot4-NTIL (m=37, n=74 目标)
//
// 搜索空间: 完整 2-因子 (2-regular multigraph) 有序 cell 集, 覆盖置换型与非置换型
//   (R9c-T2: 真实解常为非置换, 故必须覆盖).
// 表示: xs[m], ys[m] (cell i = (xs[i], ys[i])); 满足对每个顶点 v,
//   c_x[v]+c_y[v]=2 (c_x=行计数, c_y=列计数) => 2-因子 (Th-44).
// 初始化: 随机类型分配 (type0: c_x=0,c_y=2; type1: 1,1; type2: 2,0) 保持 sum c_x=m,
//   构造 xs/ys 多集, 任意配对成 cell.
// 邻域: swap ys[i],ys[j] (保持 xs,ys 多集 => 保持 2-因子), 改变 cell i,j => 8 个提升点.
// 目标: 4m 个 C4 提升点中的 3-共线三元组数 (增量更新, O(64m)/move).
// 退火: 多 restart, 降温 + 卡住时回温(reheat).
// 贪婪下降 (--greedy): 每步扫描全部 (i,j) 对, 选严格降 B 的最佳交换; 无可用时随机 kick.
//   理论上依赖 gating 结果 (red_config_frac=1.0) 保证局部极小不存在, 收敛到 B=0.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <random>
#include <chrono>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <cctype>

using namespace std;

typedef uint64_t LK;

// 打包参数 (N=2m<=74): a,b in[-73,73]; c in[-10658,10658]
static const int AOFF = 200, BOFF = 200, COFF = 20000;
static const int ASPAN = 400, BSPAN = 400, CSPAN = 40000;

struct Pt { int x, y; };

// C4 旋转 (与 Python orbit_c4 一致): n=2m 网格
Pt c4(int x, int y, int r, int n) {
    if (r == 0) return {x, y};
    if (r == 1) return {n - 1 - y, x};
    if (r == 2) return {n - 1 - x, n - 1 - y};
    return {y, n - 1 - x};
}

static inline int igcd(int a, int b) { a = abs(a); b = abs(b); while (b) { int t = a % b; a = b; b = t; } return a; }

// 归一化齐次直线 (a,b,c) 并打包为 64-bit
static inline LK line_of(Pt p, Pt q) {
    int a = -(q.y - p.y), b = (q.x - p.x), c = (q.y - p.y) * p.x - (q.x - p.x) * p.y;
    int g = igcd(abs(a), abs(b)); g = igcd(g, abs(c));
    if (g != 0) { a /= g; b /= g; c /= g; }
    if (a < 0 || (a == 0 && b < 0) || (a == 0 && b == 0 && c < 0)) { a = -a; b = -b; c = -c; }
    LK K = (LK)(a + AOFF);
    K = K * BSPAN + (b + BOFF);
    K = K * CSPAN + (c + COFF);
    return K;
}

static inline void unpack(LK K, int& a, int& b, int& c) {
    c = (int)(K % CSPAN) - COFF; K /= CSPAN;
    b = (int)(K % BSPAN) - BOFF; K /= BSPAN;
    a = (int)K - AOFF;
}

int m, n;
vector<int> xs, ys;
vector<Pt> pts;                          // 4m 当前点
unordered_map<LK, unordered_set<int>> lpts;  // line -> 该线上的点索引集合 (持久精确)
long long total_bad;

mt19937 rng(1);

static inline long long C3(long long t) { return (t >= 3) ? t * (t - 1) * (t - 2) / 6 : 0; }
static inline long long C2(long long t) { return (t >= 2) ? t * (t - 1) / 2 : 0; }

void build_points() {
    pts.resize(4 * m);
    for (int i = 0; i < m; i++)
        for (int r = 0; r < 4; r++) pts[4 * i + r] = c4(xs[i], ys[i], r, n);
}

// present[idx]=true 表示 pts[idx] 当前在配置中. 增/删点时精确维护 total_bad.
vector<char> present;
vector<LK> g_touch;   // 复用缓冲

// 把点 i 加入所有其经过的直线; total_bad 增量更新. 前置: pts[i] 已设好坐标.
void add_point(int i) {
    g_touch.clear();
    Pt pi = pts[i];
    for (int j = 0; j < 4 * m; j++) {
        if (j == i || !present[j]) continue;
        if (pts[j].x == pi.x && pts[j].y == pi.y) continue;  // 同坐标退化
        LK k = line_of(pi, pts[j]);
        auto& S = lpts[k];
        if (S.insert(j).second) {}  // 确保线上每个 present 点都在集合里
        g_touch.push_back(k);
    }
    // 去重 + 加入 i, 更新 total_bad
    sort(g_touch.begin(), g_touch.end());
    g_touch.erase(unique(g_touch.begin(), g_touch.end()), g_touch.end());
    for (LK k : g_touch) {
        auto& S = lpts[k];
        long long old = (long long)S.size();
        S.insert(i);
        total_bad += C3(old + 1) - C3(old);
    }
    present[i] = 1;
}

// 从所有经过的直线移除点 i; total_bad 增量更新. 前置: pts[i] 坐标仍有效.
void remove_point(int i) {
    present[i] = 0;
    g_touch.clear();
    Pt pi = pts[i];
    for (int j = 0; j < 4 * m; j++) {
        if (j == i || !present[j]) continue;
        if (pts[j].x == pi.x && pts[j].y == pi.y) continue;
        g_touch.push_back(line_of(pi, pts[j]));
    }
    sort(g_touch.begin(), g_touch.end());
    g_touch.erase(unique(g_touch.begin(), g_touch.end()), g_touch.end());
    for (LK k : g_touch) {
        auto it = lpts.find(k);
        if (it == lpts.end()) continue;
        auto& S = it->second;
        long long cur = (long long)S.size();
        S.erase(i);
        total_bad += C3(cur - 1) - C3(cur);
        if (S.size() < 2) lpts.erase(it);
    }
}

void build_map() {
    // 全量重建持久点集 lpts + total_bad.
    lpts.clear(); total_bad = 0;
    present.assign(4 * m, 0);
    for (int i = 0; i < 4 * m; i++) add_point(i);
}

// 提交一次 swap (不回退): 移除 cell i,j 的 8 旧点 -> 交换 ys -> 加入 8 新点.
void commit_swap(int i, int j) {
    int oi[4], oj[4];
    for (int r = 0; r < 4; r++) { oi[r] = 4 * i + r; oj[r] = 4 * j + r; }
    for (int r = 0; r < 4; r++) { remove_point(oi[r]); remove_point(oj[r]); }
    int t = ys[i]; ys[i] = ys[j]; ys[j] = t;
    for (int r = 0; r < 4; r++) { pts[oi[r]] = c4(xs[i], ys[i], r, n); pts[oj[r]] = c4(xs[j], ys[j], r, n); }
    for (int r = 0; r < 4; r++) { add_point(oi[r]); add_point(oj[r]); }
}

// 测量 swap(i,j) 的 B 变化量, 不改变配置 (测完从 xs0,ys0 全量重建回退,
// 避开手动 pts 恢复导致的 lpts 结构软损坏).
long long meas_swap(int i, int j) {
    int oi[4], oj[4];
    for (int r = 0; r < 4; r++) { oi[r] = 4 * i + r; oj[r] = 4 * j + r; }
    vector<int> xs0 = xs, ys0 = ys;
    long long before = total_bad;
    for (int r = 0; r < 4; r++) { remove_point(oi[r]); remove_point(oj[r]); }
    int t = ys[i]; ys[i] = ys[j]; ys[j] = t;
    for (int r = 0; r < 4; r++) { pts[oi[r]] = c4(xs[i], ys[i], r, n); pts[oj[r]] = c4(xs[j], ys[j], r, n); }
    for (int r = 0; r < 4; r++) { add_point(oi[r]); add_point(oj[r]); }
    long long delta = total_bad - before;
    // 从快照全量还原 (xs0,ys0)
    xs = xs0; ys = ys0;
    build_points(); build_map();
    return delta;
}

// 贪婪下降 + 卡住时随机 kick. 依赖 gating 的 red_config_frac=1.0.
void init_random();
bool greedy_restart(long long max_steps, long long& best_out, vector<int>& bxs, vector<int>& bys, bool keep_init) {
    if (!keep_init) init_random();
    long long cur = total_bad;
    best_out = cur; bxs = xs; bys = ys;
    long long tot_meas = 0;
    for (long long step = 0; step < max_steps; step++) {
        int bi = -1, bj = -1; long long best_d = 0;
        for (int ii = 0; ii < m; ii++)
            for (int jj = ii + 1; jj < m; jj++) {
                long long d = meas_swap(ii, jj);
                if (d < best_d) { best_d = d; bi = ii; bj = jj; }
                tot_meas++;
            }
        if (best_d < 0) {
            commit_swap(bi, bj);
            cur = total_bad;
            if (cur < best_out) { best_out = cur; bxs = xs; bys = ys; }
            if (cur == 0) return true;
        } else {
            // 卡住 (局部极小): 随机 kick 逃离
            int ii = rng() % m, jj = rng() % m;
            if (ii != jj) commit_swap(ii, jj);
            cur = total_bad;
            if (cur < best_out) { best_out = cur; bxs = xs; bys = ys; }
            if (cur == 0) return true;
        }
    }
    best_out = cur;
    return false;
}

// 初始化随机 2-因子
void init_random() {
    xs.assign(m, 0); ys.assign(m, 0);
    vector<int> type(m, 1);
    int conversions = (int)(0.35 * m);
    for (int t = 0; t < conversions; t++) {
        int a = rng() % m, b = (a + 1 + rng() % (m - 1)) % m;  // ensure distinct
        if (type[a] == 1 && type[b] == 1) { type[a] = 2; type[b] = 0; }
    }
    vector<int> X, Y;
    for (int v = 0; v < m; v++) {
        if (type[v] >= 1) X.push_back(v);
        if (type[v] == 2) X.push_back(v);
        if (type[v] <= 1) Y.push_back(v);
        if (type[v] == 0) Y.push_back(v);
    }
    shuffle(X.begin(), X.end(), rng);
    shuffle(Y.begin(), Y.end(), rng);
    xs = X; ys = Y;
    build_points();
    build_map();
}

bool try_restart(long long max_moves, double T0, double Tend, long long& best_bad_out,
                 vector<int>& best_xs, vector<int>& best_ys, bool keep_init=false) {
    if (!keep_init) init_random();
    long long cur = total_bad;
    long long best = cur;
    best_xs = xs; best_ys = ys;
    double T = T0;
    double Tdec = pow(Tend / T0, 1.0 / max_moves);
    uniform_real_distribution<double> ur(0.0, 1.0);
    long long last_improve = 0;
    int stale = 0;
    for (long long mv = 0; mv < max_moves; mv++) {
        int i = rng() % m, j = rng() % m;
        if (i == j) continue;
        int oi[4], oj[4];
        for (int r = 0; r < 4; r++) { oi[r] = 4 * i + r; oj[r] = 4 * j + r; }
        long long cur_before = total_bad;
        for (int r = 0; r < 4; r++) { remove_point(oi[r]); remove_point(oj[r]); }
        int t = ys[i]; ys[i] = ys[j]; ys[j] = t;
        for (int r = 0; r < 4; r++) {
            pts[oi[r]] = c4(xs[i], ys[i], r, n);
            pts[oj[r]] = c4(xs[j], ys[j], r, n);
        }
        for (int r = 0; r < 4; r++) { add_point(oi[r]); add_point(oj[r]); }
        long long newbad = total_bad;
        if (newbad <= cur_before || ur(rng) < exp(-(newbad - cur_before) / T)) {
            cur = newbad;
            if (cur < best) { best = cur; best_xs = xs; best_ys = ys; last_improve = mv; stale = 0; }
            if (cur == 0) { best_bad_out = 0; return true; }
        } else {
            for (int r = 0; r < 4; r++) { remove_point(oi[r]); remove_point(oj[r]); }
            int t2 = ys[i]; ys[i] = ys[j]; ys[j] = t2;
            for (int r = 0; r < 4; r++) {
                pts[oi[r]] = c4(xs[i], ys[i], r, n);
                pts[oj[r]] = c4(xs[j], ys[j], r, n);
            }
            for (int r = 0; r < 4; r++) { add_point(oi[r]); add_point(oj[r]); }
            cur = total_bad;
        }
        T *= Tdec;
        if (++stale > max_moves / 20) { T = max(T, T0 * 0.4); stale = 0; }
    }
    best_bad_out = best;
    return false;
}

int main(int argc, char** argv) {
    string initfile;
    m = 10;
    int restarts = 200;
    long long max_moves = 20000000LL;
    int seed = 1;
    bool greedy = false;
    bool selftest = false;
    int pos = 0;
    for (int a = 1; a < argc; a++) {
        string s = argv[a];
        if (s == "--init" && a + 1 < argc) initfile = argv[++a];
        else if (s == "--m" && a + 1 < argc) m = atoi(argv[++a]);
        else if (s == "--restarts" && a + 1 < argc) restarts = atoi(argv[++a]);
        else if (s == "--moves" && a + 1 < argc) max_moves = atoll(argv[++a]);
        else if (s == "--seed" && a + 1 < argc) seed = atoi(argv[++a]);
        else if (s == "--greedy") greedy = true;
        else if (s == "--selftest") selftest = true;
        else if (!s.empty() && s[0] != '-') {
            if (pos == 0) m = atoi(s.c_str());
            else if (pos == 1) restarts = atoi(s.c_str());
            else if (pos == 2) max_moves = atoll(s.c_str());
            else if (pos == 3) seed = atoi(s.c_str());
            pos++;
        }
    }
    n = 2 * m;
    rng = mt19937(seed);

    // ---- selftest: 验证 meas_swap 无泄漏且 delta 精确 ----
    if (selftest) {
        init_random();
        int leaks = 0, mism = 0;
        for (int t = 0; t < 3000; t++) {
            int i = rng() % m, j = rng() % m; if (i == j) continue;
            long long b0 = total_bad;
            long long d = meas_swap(i, j);
            long long b1 = total_bad;
            if (b1 != b0) { printf("LEAK t=%d: %lld -> %lld\n", t, b0, b1); if (++leaks > 3) break; continue; }
            commit_swap(i, j);
            long long d_true = total_bad - b0;
            if (d != d_true) { printf("MISMATCH t=%d: measure=%lld true=%lld\n", t, d, d_true); if (++mism > 3) break; }
            int tt = ys[i]; ys[i] = ys[j]; ys[j] = tt;
            build_points(); build_map();
        }
        printf("SELFTEST done: leaks=%d mismatches=%d (total_bad now %lld)\n", leaks, mism, total_bad);
        return 0;
    }

    // ---- 正常分支 ----
    bool use_init = !initfile.empty();
    if (use_init) {
        ifstream f(initfile);
        if (!f) { fprintf(stderr, "cannot open %s\n", initfile.c_str()); return 1; }
        string content((istreambuf_iterator<char>(f)), istreambuf_iterator<char>());
        size_t c0 = content.find("\"cells\"");
        if (c0 == string::npos) { fprintf(stderr, "no 'cells' in %s\n", initfile.c_str()); return 1; }
        size_t c1 = content.find("\"cycles\"");
        if (c1 == string::npos) c1 = content.find("\"verify\"");
        if (c1 == string::npos) c1 = content.size();
        string sec = content.substr(c0, c1 - c0);
        xs.clear(); ys.clear();
        size_t p = 0;
        while ((p = sec.find('[', p)) != string::npos) {
            size_t j = p + 1;
            while (j < sec.size() && isspace((unsigned char)sec[j])) j++;
            if (j >= sec.size() || (!isdigit((unsigned char)sec[j]) && sec[j] != '-')) { p = p + 1; continue; }
            size_t q = sec.find(']', p);
            if (q == string::npos) break;
            int x = 0, y = 0;
            sscanf(sec.substr(p + 1, q - p - 1).c_str(), "%d,%d", &x, &y);
            xs.push_back(x); ys.push_back(y);
            p = q + 1;
        }
        m = (int)xs.size();
        n = 2 * m;
        build_points(); build_map();
        fprintf(stderr, "[init] %s -> m=%d bad=%lld\n", initfile.c_str(), m, total_bad);
    }

    auto t0 = chrono::high_resolution_clock::now();
    bool found = false;
    long long best_overall = 1e18;
    vector<int> bxs, bys;
    for (int rs = 0; rs < restarts && !found; rs++) {
        long long best = 0;
        vector<int> rsx, rsy;
        bool ok;
        if (greedy) ok = greedy_restart(max_moves, best, rsx, rsy, use_init && rs == 0);
        else ok = try_restart(max_moves, 3.0, 0.005, best, rsx, rsy, use_init && rs == 0);
        if (best < best_overall) { best_overall = best; bxs = rsx; bys = rsy; }
        if (ok) { found = true; bxs = rsx; bys = rsy; break; }
        if (rs % 20 == 0) fprintf(stderr, "  rs=%d best=%lld\n", rs, best);
    }
    auto t1 = chrono::high_resolution_clock::now();
    double secs = chrono::duration<double>(t1 - t0).count();

    if (found) {
        xs = bxs; ys = bys; build_points(); build_map();
        printf("verify_bad=%lld npts=%d\n", total_bad, (int)pts.size());
        if (total_bad != 0) {
            fprintf(stderr, "WARN: incremental cur==0 but verify_bad=%lld (drift)\n", total_bad);
            if (total_bad < best_overall) best_overall = total_bad;
            found = false;
        }
    }
    if (found) {
        printf("FOUND m=%d  time=%.2fs\n", m, secs);
        printf("cells:");
        for (int i = 0; i < m; i++) printf(" (%d,%d)", bxs[i], bys[i]);
        printf("\n");
    } else {
        printf("NOTFOUND m=%d best_bad=%lld time=%.2fs restarts=%d\n", m, best_overall, secs, restarts);
    }
    return 0;
}