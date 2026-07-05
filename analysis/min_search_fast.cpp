#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <unordered_set>
#include <cmath>
#include <numeric>
using namespace std;

struct Point { int x,y; };
bool operator==(const Point& a, const Point& b) { return a.x==b.x && a.y==b.y; }

int N, total_rings;
int ring_id[100][100];
vector<vector<Point>> ring_points;
mt19937 rng;

bool collinear(const Point& a, const Point& b, const Point& c) {
    return (b.x-a.x)*(c.y-a.y) == (c.x-a.x)*(b.y-a.y);
}

bool is_no3(const vector<Point>& pts) {
    for (size_t i=0;i<pts.size();i++)
        for (size_t j=i+1;j<pts.size();j++)
            for (size_t k=j+1;k<pts.size();k++)
                if (collinear(pts[i],pts[j],pts[k])) return false;
    return true;
}

int dom_score(const vector<Point>& pts) {
    unordered_set<int> ps;
    for (auto& p : pts) ps.insert(p.x*N+p.y);
    int s = 0;
    for (int i=0;i<N;i++) for (int j=0;j<N;j++) {
        if (ps.count(i*N+j)) continue;
        for (size_t a=0;a<pts.size();a++)
            for (size_t b=a+1;b<pts.size();b++)
                if (collinear(pts[a],pts[b],{i,j})) { s++; goto next; }
        next:;
    }
    return s;
}

int max_ring_pop(const vector<Point>& pts) {
    vector<int> cnt(total_rings,0);
    for (auto& p : pts) cnt[ring_id[p.x][p.y]]++;
    int m=0;
    for (int c : cnt) if (c>m) m=c;
    return m;
}

// Smart init: pick points from DISTINCT distance rings (promotes missing-center)
// Ensures no-3 property during construction
vector<Point> smart_init(int k) {
    vector<Point> result;
    vector<int> used_ring(total_rings,0);
    vector<int> rorder(total_rings);
    iota(rorder.begin(), rorder.end(), 0);
    shuffle(rorder.begin(), rorder.end(), rng);
    
    // Phase 1: try to pick from distinct rings, checking no-3
    for (int ri : rorder) {
        if ((int)result.size() >= k) break;
        if (ring_points[ri].empty()) continue;
        shuffle(ring_points[ri].begin(), ring_points[ri].end(), rng);
        for (Point p : ring_points[ri]) {
            if (result.size() >= (size_t)k) break;
            if (find(result.begin(),result.end(),p) != result.end()) continue;
            result.push_back(p);
            if (!is_no3(result)) { result.pop_back(); continue; }
            used_ring[ri]++; break;
        }
    }
    // Phase 2: fill remaining with no-3 checked points
    int fails=0;
    while ((int)result.size() < k && fails < 500) {
        fails++;
        vector<double> w(total_rings,0);
        for (int i=0;i<total_rings;i++) {
            if (ring_points[i].empty()) continue;
            w[i] = 1.0 / (1 + used_ring[i]);
        }
        discrete_distribution<int> dist(w.begin(), w.end());
        int ri = dist(rng);
        int idx = rng() % ring_points[ri].size();
        Point p = ring_points[ri][idx];
        if (find(result.begin(),result.end(),p) != result.end()) continue;
        result.push_back(p);
        if (!is_no3(result)) { result.pop_back(); continue; }
        used_ring[ri]++; fails=0;
    }
    return result;
}

int main(int argc, char* argv[]) {
    if (argc < 5) {
        cerr << "Usage: " << argv[0] << " N k trials seed" << endl;
        return 1;
    }
    N = atoi(argv[1]); int k = atoi(argv[2]);
    int trials = atoi(argv[3]); rng = mt19937(atoi(argv[4]));

    // Precompute distance rings
    double cx = (N-1)/2.0, cy = (N-1)/2.0;
    vector<int> d2map;
    for (int i=0;i<N;i++) for (int j=0;j<N;j++) {
        int d2 = (int)round((i-cx)*(i-cx)+(j-cy)*(j-cy));
        auto it = find(d2map.begin(), d2map.end(), d2);
        int rid = it == d2map.end() ? (d2map.push_back(d2), d2map.size()-1) : it-d2map.begin();
        ring_id[i][j] = rid;
    }
    total_rings = d2map.size();
    ring_points.resize(total_rings);
    for (int i=0;i<N;i++) for (int j=0;j<N;j++)
        ring_points[ring_id[i][j]].push_back({i,j});
    
    int need = N*N - k;
    int found=0, found_miss=0;
    auto start = chrono::steady_clock::now();

    for (int trial=0; trial<trials; trial++) {
        if (trial%2000==0 && trial>0) {
            double el = chrono::duration<double>(chrono::steady_clock::now()-start).count();
            cerr << trial << "/" << trials << " found=" << found << " " << el << "s" << endl;
        }
        vector<Point> cand = smart_init(k);
        if (!is_no3(cand)) continue;
        
        int best = dom_score(cand);
        // Hill-climb: try replacing each point, preferring missing-center bonus
        for (int it=0;it<400;it++) {
            bool imp=false;
            for (int pi=0;pi<k && !imp;pi++) {
                Point old = cand[pi];
                for (int t=0;t<40;t++) {
                    int ri = rng() % total_rings;
                    if (ring_points[ri].empty()) continue;
                    int idx = rng() % ring_points[ri].size();
                    Point pn = ring_points[ri][idx];
                    if (find(cand.begin(),cand.end(),pn)!=cand.end()) continue;
                    cand[pi] = pn;
                    if (!is_no3(cand)) { cand[pi]=old; continue; }
                    int mp = max_ring_pop(cand);
                    int sc = dom_score(cand) + (mp>=3 ? -500 : 0); // strong missing-center bonus
                    if (sc > best) { best=sc; imp=true; break; }
                    else cand[pi] = old;
                }
            }
            if (!imp) break;
        }
        
        if (best >= need) {
            // Final verification
            unordered_set<int> ps;
            for (auto& p : cand) ps.insert(p.x*N+p.y);
            bool maximal = true;
            for (int i=0;i<N&&maximal;i++) for (int j=0;j<N&&maximal;j++) {
                if (ps.count(i*N+j)) continue;
                bool ok=false;
                for (size_t a=0;a<cand.size()&&!ok;a++)
                    for (size_t b=a+1;b<cand.size()&&!ok;b++)
                        if (collinear(cand[a],cand[b],{i,j})) ok=true;
                if (!ok) maximal=false;
            }
            if (maximal) {
                found++;
                int mp = max_ring_pop(cand);
                bool miss = (mp < 3);
                if (miss) found_miss++;
                cout << "FOUND #" << found << " pts=" << k << " missing=" << (miss?"YES":"NO")
                     << " max_ring=" << mp << " rings_used=";
                vector<int> rcnt(total_rings,0);
                for (auto& p : cand) rcnt[ring_id[p.x][p.y]]++;
                int ru=0; for (int c : rcnt) if (c>0) ru++;
                cout << ru << "/" << total_rings << " {";
                for (auto& p : cand) cout << "(" << p.x << "," << p.y << ")";
                cout << "}" << endl;
            }
        }
    }
    double elapsed = chrono::duration<double>(chrono::steady_clock::now()-start).count();
    cout << "\nRESULTS n=" << N << " k=" << k << " trials=" << trials
         << " found=" << found << " missing=" << found_miss
         << " rate=" << (found?100.0*found_miss/found:0) << "% time=" << elapsed << "s" << endl;
}
