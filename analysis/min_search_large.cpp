/*
 * Search for MIN dominating sets for larger n (13, 14, 15+).
 * Strategy: try different k values (starting from n-2 up to n+3).
 * Compile: g++ -O3 -march=native -std=c++17 -o min_search_large min_search_large.cpp -static
 */

#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <unordered_set>
#include <cstring>

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

int domination_score(const vector<Point>& pts) {
    unordered_set<Point, PointHash> pt_set(pts.begin(), pts.end());
    int score = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            Point p = {i, j};
            if (pt_set.count(p)) continue;
            for (size_t a = 0; a < pts.size(); a++) {
                for (size_t b = a+1; b < pts.size(); b++) {
                    if (collinear(pts[a], pts[b], p)) {
                        score++;
                        goto next_point;
                    }
                }
            }
            next_point:;
        }
    }
    return score;
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        cerr << "Usage: min_search_large <n> <k> <trials> [seed]" << endl;
        return 1;
    }
    
    N = atoi(argv[1]);
    int k = atoi(argv[2]);
    int trials = atoi(argv[3]);
    int seed = argc > 4 ? atoi(argv[4]) : 42;
    
    mt19937 rng(seed);
    
    vector<Point> all_pts;
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            all_pts.push_back({i, j});
    
    int total_exterior = N*N - k;
    int found_total = 0, found_missing = 0;
    
    auto start = chrono::steady_clock::now();
    
    for (int trial = 0; trial < trials; trial++) {
        if (trial % 500 == 0 && trial > 0) {
            auto now = chrono::steady_clock::now();
            double secs = chrono::duration<double>(now - start).count();
            cerr << "  n=" << N << " k=" << k << " trial " << trial << "/" << trials 
                 << " (found " << found_total << ", " << secs << "s)" << endl;
        }
        
        // Generate random k-point set with no collinearity
        vector<Point> cand;
        for (int attempt = 0; attempt < 2000; attempt++) {
            cand.clear();
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
        
        // Hill-climb
        int best_score = domination_score(cand);
        
        for (int iter = 0; iter < 80; iter++) {
            bool improved = false;
            for (int pi = 0; pi < k && !improved; pi++) {
                for (int ri = 0; ri < 50; ri++) {  // sample 50 replacement candidates
                    Point p_in = all_pts[rng() % all_pts.size()];
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
                        cand[pi] = old;
                    }
                }
            }
            if (!improved) break;
        }
        
        // Final check
        if (best_score >= total_exterior && is_maximal(cand)) {
            found_total++;
            
            // Check missing-center (quick computation)
            double cx = (N-1)/2.0, cy = (N-1)/2.0;
            vector<int> d2s;
            for (const auto& p : cand) {
                d2s.push_back((int)round((p.x-cx)*(p.x-cx) + (p.y-cy)*(p.y-cy)));
            }
            sort(d2s.begin(), d2s.end());
            int maxpop = 0;
            int i = 0;
            while (i < (int)d2s.size()) {
                int j = i;
                while (j < (int)d2s.size() && d2s[j] == d2s[i]) j++;
                maxpop = max(maxpop, j - i);
                i = j;
            }
            bool missing = (maxpop < 3);
            if (missing) found_missing++;
            
            if (found_total <= 5) {
                cout << "FOUND: {";
                bool first = true;
                for (const auto& p : cand) {
                    if (!first) cout << ",";
                    cout << "(" << p.x << "," << p.y << ")";
                    first = false;
                }
                cout << "} missing=" << (missing?"YES":"NO") << endl;
            }
        }
    }
    
    auto end = chrono::steady_clock::now();
    double total_secs = chrono::duration<double>(end - start).count();
    
    cout << "\nRESULTS for n=" << N << " k=" << k << " trials=" << trials << ":" << endl;
    cout << "  Total found: " << found_total << " distinct sets" << endl;
    if (found_total > 0) {
        cout << "  Missing-center: " << found_missing << "/" << found_total
             << " = " << (100.0 * found_missing / found_total) << "%" << endl;
    }
    cout << "  Time: " << total_secs << "s" << endl;
    
    return 0;
}
