// Exact labelled C4-NTIL enumerator for small m.
//
// Enumerates every subset of m oriented fundamental cells (x,y) whose
// endpoint multidegrees are all two (a loop contributes two), while pruning
// immediately when the lifted C4 points create a third point on an old line.
// The output contains exact one-cell and two-cell occurrence counts.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <unordered_set>
#include <vector>

using namespace std;

struct Point { int x, y; };
struct Line {
    int a, b, c;
    bool operator==(const Line& z) const { return a == z.a && b == z.b && c == z.c; }
};
struct LineHash {
    size_t operator()(const Line& z) const {
        uint64_t h = uint32_t(z.a + 64);
        h = h * 1315423911u + uint32_t(z.b + 64);
        h = h * 2654435761u + uint32_t(z.c + 4096);
        return size_t(h ^ (h >> 29));
    }
};

static int M, N, NC;
static vector<int> degree_now, chosen;
static vector<Point> points_now;
static unordered_set<Line, LineHash> lines_now;
static vector<uint64_t> marginal_count, pair_count;
static uint64_t solution_count = 0, search_nodes = 0;

static Line line_key(const Point& p, const Point& q) {
    int a = q.y - p.y;
    int b = p.x - q.x;
    int c = -(a * p.x + b * p.y);
    int g = gcd(gcd(abs(a), abs(b)), abs(c));
    a /= g; b /= g; c /= g;
    if (a < 0 || (a == 0 && b < 0)) { a = -a; b = -b; c = -c; }
    return {a, b, c};
}

static bool add_orbit(int id, vector<Line>& inserted, int& old_points) {
    int x = id / M, y = id % M;
    Point orbit[4] = {{x, y}, {N - 1 - y, x},
                      {N - 1 - x, N - 1 - y}, {y, N - 1 - x}};
    old_points = int(points_now.size());
    for (const Point& p : orbit) {
        for (const Point& q : points_now) {
            Line key = line_key(p, q);
            if (lines_now.find(key) != lines_now.end()) {
                for (const Line& z : inserted) lines_now.erase(z);
                points_now.resize(old_points);
                return false;
            }
            lines_now.insert(key);
            inserted.push_back(key);
        }
        points_now.push_back(p);
    }
    return true;
}

static void remove_orbit(const vector<Line>& inserted, int old_points) {
    for (const Line& z : inserted) lines_now.erase(z);
    points_now.resize(old_points);
}

static bool future_degree_possible(int next_id) {
    // Cheap exact-capacity test: count incidences still available to each
    // vertex.  It is intentionally only a pruning condition, never a claim
    // that the remaining capacities can be satisfied jointly.
    for (int v = 0; v < M; ++v) {
        int need = 2 - degree_now[v], available = 0;
        if (need <= 0) continue;
        for (int id = next_id; id < NC && available < need; ++id) {
            int x = id / M, y = id % M;
            if (x == v && y == v) available += 2;
            else if (x == v || y == v) available += 1;
        }
        if (available < need) return false;
    }
    return true;
}

static void search(int start) {
    ++search_nodes;
    int used = int(chosen.size());
    if (used == M) {
        for (int d : degree_now) if (d != 2) return;
        ++solution_count;
        for (int a : chosen) ++marginal_count[a];
        for (size_t i = 0; i < chosen.size(); ++i)
            for (size_t j = i + 1; j < chosen.size(); ++j) {
                ++pair_count[chosen[i] * NC + chosen[j]];
                ++pair_count[chosen[j] * NC + chosen[i]];
            }
        return;
    }
    int left = M - used;
    if (NC - start < left || !future_degree_possible(start)) return;
    for (int id = start; id <= NC - left; ++id) {
        int x = id / M, y = id % M;
        if (x == y) {
            if (degree_now[x] != 0) continue;
            degree_now[x] += 2;
        } else {
            if (degree_now[x] >= 2 || degree_now[y] >= 2) continue;
            ++degree_now[x]; ++degree_now[y];
        }
        vector<Line> inserted;
        int old_points = 0;
        if (add_orbit(id, inserted, old_points)) {
            chosen.push_back(id);
            search(id + 1);
            chosen.pop_back();
            remove_orbit(inserted, old_points);
        }
        if (x == y) degree_now[x] -= 2;
        else { --degree_now[x]; --degree_now[y]; }
    }
}

int main(int argc, char** argv) {
    if (argc < 3) {
        cerr << "usage: exact_c4_pair_counts <m> <output.txt>\n";
        return 2;
    }
    M = stoi(argv[1]); N = 2 * M; NC = M * M;
    degree_now.assign(M, 0);
    marginal_count.assign(NC, 0);
    pair_count.assign(size_t(NC) * NC, 0);
    lines_now.reserve(4096);
    auto began = chrono::steady_clock::now();
    search(0);
    double seconds = chrono::duration<double>(chrono::steady_clock::now() - began).count();
    ofstream out(argv[2]);
    out << M << ' ' << solution_count << ' ' << search_nodes << ' ' << seconds << '\n';
    for (uint64_t v : marginal_count) out << v << ' ';
    out << '\n';
    for (uint64_t v : pair_count) out << v << ' ';
    out << '\n';
    cout << "m=" << M << " exact_solutions=" << solution_count
         << " nodes=" << search_nodes << " seconds=" << seconds << '\n';
    return 0;
}
