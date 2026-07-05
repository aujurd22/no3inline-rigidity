/*
 * Fast search for minimal dominating sets (Martin Gardner's min no-3-in-line).
 * Uses hill-climbing with precomputed domination.
 * 
 * Compile: g++ -O3 -march=native -std=c++17 -o min_search min_search.cpp
 * Usage:   min_search <n> <k> <trials> [seed]
 */

#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>
#include <cmath>
#include <unordered_set>

using namespace std;

struct Point {
    int x, y;
    bool operator==(const Point& o) const { return x==o.x && y==o.y; }
    bool operator<(const Point& o) const { return x<o.x || (x==o.x && y<o.y); }
};

struct PointHash {
    size_t operator()(const Point& p) const {
        return (size_t)(p.x * 3137 + p.y);
    }
};

int N;

bool collinear(const Point& a, const Point& b, const Point& c) {
    return (b.x-a.x)*(c.y-a.y) == (c.x-a.x)*(b.y-a.y);
}

bool is_no3(const vector<Point>& pts) {
    for (size_t i = 0; i < pts.size(); i++)
        for (size_t j = i+1; j < pts.size(); j++)
            for (size_t k = j+1; k < pts.size(); k++)
                if (collinear(pts[i], pts[j], pts[k]))
                    return false;
    return true;
}

// Check if a set is maximal: for each empty grid point,
// there exists a pair in the set that's collinear with it
bool is_maximal(const vector<Point>& pts) {
    unordered_set<Point, PointHash> pt_set(pts.begin(), pts.end());
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            Point p = {i, j};
            if (pt_set.count(p)) continue;
            bool dominated = false;
            for (size_t a = 0; a < pts.size() && !dominated; a++) {
                for (size_t b = a+1; b < pts.size() && !dominated; b++) {
                    if (collinear(pts[a], pts[b], p))
                        dominated = true;
                }
            }
            if (!dominated) return false;
        }
    }
    return true;
}

// Quick domination score (number of exterior points dominated)
int domination_score(const vector<Point>& pts) {
    unordered_set<Point, PointHash> pt_set(pts.begin(), pts.end());
    int score = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            Point p = {i, j};
            if (pt_set.count(p)) continue;
            bool dominated = false;
            for (size_t a = 0; a < pts.size() && !dominated; a++) {
                for (size_t b = a+1; b < pts.size() && !dominated; b++) {
                    if (collinear(pts[a], pts[b], p))
                        dominated = true;
                }
            }
            if (dominated) score++;
        }
    }
    return score;
}

void ring_info(const vector<Point>& pts, int& nrings, int& maxpop, bool& missing) {
    double cx = (N-1)/2.0, cy = (N-1)/2.0;
    vector<int> d2s;
    for (const auto& p : pts) {
        double dx = p.x - cx, dy = p.y - cy;
        d2s.push_back((int)round(dx*dx + dy*dy));
    }
    sort(d2s.begin(), d2s.end());
    maxpop = 0;
    nrings = 0;
    int i = 0;
    while (i < (int)d2s.size()) {
        int j = i;
        while (j < (int)d2s.size() && d2s[j] == d2s[i]) j++;
        int pop = j - i;
        if (pop > maxpop) maxpop = pop;
        nrings++;
        i = j;
    }
    missing = (maxpop < 3);
}

bool rot2_symmetry(const vector<Point>& pts) {
    unordered_set<Point, PointHash> s(pts.begin(), pts.end());
    for (const auto& p : pts) {
        Point p2 = {N-1 - p.x, N-1 - p.y};
        if (!s.count(p2)) return false;
    }
    return true;
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        cerr << "Usage: min_search <n> <k> <trials> [seed]" << endl;
        return 1;
    }
    
    N = atoi(argv[1]);
    int k = atoi(argv[2]);
    int trials = atoi(argv[3]);
    int seed = argc > 4 ? atoi(argv[4]) : 42;
    
    mt19937 rng(seed);
    uniform_int_distribution<int> dist(0, N-1);
    
    // All grid points
    vector<Point> all_pts;
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            all_pts.push_back({i, j});
    
    int total_exterior = N*N - k;
    vector<vector<Point>> found;
    int found_missing = 0, found_has = 0;
    
    auto start = chrono::steady_clock::now();
    
    for (int trial = 0; trial < trials; trial++) {
        if (trial % 200 == 0 && trial > 0) {
            auto now = chrono::steady_clock::now();
            double secs = chrono::duration<double>(now - start).count();
            cerr << "  n=" << N << " trial " << trial << "/" << trials 
                 << " (found " << found.size() << ", "
                 << secs << "s)" << endl;
        }
        
        // Generate random k-point set with no collinearity
        vector<Point> cand;
        for (int attempt = 0; attempt < 5000; attempt++) {
            cand.clear();
            // Shuffle and take first k that work
            vector<Point> shuffled = all_pts;
            shuffle(shuffled.begin(), shuffled.end(), rng);
            for (const auto& p : shuffled) {
                cand.push_back(p);
                if (!is_no3(cand)) {
                    cand.pop_back();
                }
                if ((int)cand.size() == k) break;
            }
            if ((int)cand.size() == k) break;
        }
        if ((int)cand.size() != k) continue;
        
        // Hill-climb to maximize domination
        int best_score = domination_score(cand);
        
        bool improved = true;
        for (int iter = 0; iter < 100 && improved; iter++) {
            improved = false;
            for (int pi = 0; pi < k && !improved; pi++) {
                for (const auto& p_in : all_pts) {
                    if (find(cand.begin(), cand.end(), p_in) != cand.end())
                        continue;
                    
                    Point old = cand[pi];
                    cand[pi] = p_in;
                    
                    if (!is_no3(cand)) {
                        cand[pi] = old;
                        continue;
                    }
                    
                    int score = domination_score(cand);
                    if (score > best_score) {
                        best_score = score;
                        improved = true;
                        break;
                    } else {
                        cand[pi] = old; // revert
                    }
                }
            }
        }
        
        // Check if it's actually maximal
        if (best_score >= total_exterior && is_maximal(cand)) {
            // Check if we already found this one
            bool duplicate = false;
            for (const auto& existing : found) {
                if (existing.size() != cand.size()) continue;
                set<Point> s1(existing.begin(), existing.end());
                set<Point> s2(cand.begin(), cand.end());
                if (s1 == s2) { duplicate = true; break; }
            }
            if (!duplicate) {
                found.push_back(cand);
                int nrings, maxpop;
                bool missing;
                ring_info(cand, nrings, maxpop, missing);
                if (missing) found_missing++;
                else found_has++;
                
                cout << "FOUND: {";
                bool first = true;
                for (const auto& p : cand) {
                    if (!first) cout << ",";
                    cout << "(" << p.x << "," << p.y << ")";
                    first = false;
                }
                cout << "} missing=" << (missing?"YES":"NO")
                     << " rings=" << nrings
                     << " maxpop=" << maxpop
                     << endl;
            }
        }
    }
    
    auto end = chrono::steady_clock::now();
    double total_secs = chrono::duration<double>(end - start).count();
    
    cout << "\nRESULTS for n=" << N << " k=" << k << " trials=" << trials << ":" << endl;
    cout << "  Total found: " << found.size() << " distinct sets" << endl;
    if (found.size() > 0) {
        cout << "  Missing-center: " << found_missing << "/" << found.size()
             << " = " << (100.0 * found_missing / found.size()) << "%" << endl;
        cout << "  Has-center:     " << found_has << "/" << found.size()
             << " = " << (100.0 * found_has / found.size()) << "%" << endl;
    }
    cout << "  Time: " << total_secs << "s" << endl;
    
    return 0;
}
