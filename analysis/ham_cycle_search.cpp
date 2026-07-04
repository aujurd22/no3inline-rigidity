/**
 * ham_cycle_search.cpp
 * 
 * Direction 1: Hamiltonian cycle GA search in permutation space.
 * 
 * Encodes a solution as a permutation π of {0, ..., n-1} where row i
 * has points at columns (π[i], π[i+1]). This guarantees 2 per row/col.
 * 
 * Search: simulated annealing with targeted 2-opt swaps.
 * Compile: g++ -O3 -march=native -std=c++17 -static ham_cycle_search.cpp -o ham_cycle_search
 * Run: ./ham_cycle_search <n> [restarts] [iters]
 */

#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <vector>
#include <random>
#include <chrono>
#include <cstring>
using namespace std;

int N;
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Distance cache for each grid cell
vector<int> dist_cache;

void build_dist_cache() {
    dist_cache.resize(N * N);
    int cx2 = N - 1, cy2 = N - 1;
    for (int x = 0; x < N; x++)
        for (int y = 0; y < N; y++) {
            int dx = 2 * x - cx2;
            int dy = 2 * y - cy2;
            dist_cache[y * N + x] = dx * dx + dy * dy;
        }
}

inline int get_dist(int x, int y) {
    return dist_cache[y * N + x];
}

// Compute fitness for a permutation
// Returns (collinear_count, ring_overload, total = collinear*1000 + overload)
struct Fitness {
    int collinear;
    int overload;
    int total;
};

Fitness compute_fitness(const vector<int> &perm) {
    // Use forbid_accum to count collinear triples
    vector<uint64_t> forbid(N, 0);
    int collinear = 0;
    
    for (int r = 0; r < N; r++) {
        int c1 = perm[r];
        int c2 = perm[(r + 1) % N];
        
        if ((forbid[r] >> c1) & 1) collinear++;
        if ((forbid[r] >> c2) & 1) collinear++;
        
        // Update forbid for future rows
        for (int pr = 0; pr < r; pr++) {
            int pc1 = perm[pr];
            int pc2 = perm[(pr + 1) % N];
            
            int pairs[4][2] = {{pc1, c1}, {pc1, c2}, {pc2, c1}, {pc2, c2}};
            for (auto &p : pairs) {
                int pc = p[0], cc = p[1];
                int dr = r - pr;
                int dc = cc - pc;
                if (dr == 0) continue;
                for (int tr = r + 1; tr < N; tr++) {
                    int num = dc * (tr - pr);
                    if (num % dr == 0) {
                        int col = pc + num / dr;
                        if (col >= 0 && col < N)
                            forbid[tr] |= (1ULL << col);
                    }
                }
            }
        }
    }
    
    // Ring overload
    vector<int> ring_counts(2000, 0);  // d values are bounded by ~2*(N-1)²
    for (int r = 0; r < N; r++) {
        int c1 = perm[r];
        int c2 = perm[(r + 1) % N];
        ring_counts[get_dist(c1, r)]++;
        ring_counts[get_dist(c2, r)]++;
    }
    
    int overload = 0;
    for (int c : ring_counts)
        if (c > 2) overload += c - 2;
    
    return {collinear, overload, collinear * 1000 + overload};
}

// Find which rows are problematic
void find_problem_rows(const vector<int> &perm, vector<int> &problem_rows) {
    vector<uint64_t> forbid(N, 0);
    vector<int> ring_counts(2000, 0);
    vector<bool> has_collinear(N, false);
    vector<bool> has_overload(N, false);
    
    // Track ring counts
    for (int r = 0; r < N; r++) {
        int c1 = perm[r];
        int c2 = perm[(r + 1) % N];
        ring_counts[get_dist(c1, r)]++;
        ring_counts[get_dist(c2, r)]++;
    }
    
    // Find overloaded rows
    for (int r = 0; r < N; r++) {
        int c1 = perm[r];
        int c2 = perm[(r + 1) % N];
        if (ring_counts[get_dist(c1, r)] > 2) has_overload[r] = true;
        if (ring_counts[get_dist(c2, r)] > 2) has_overload[r] = true;
    }
    
    // Find collinear rows
    for (int r = 0; r < N; r++) {
        int c1 = perm[r];
        int c2 = perm[(r + 1) % N];
        
        if ((forbid[r] >> c1) & 1) has_collinear[r] = true;
        if ((forbid[r] >> c2) & 1) has_collinear[r] = true;
        
        for (int pr = 0; pr < r; pr++) {
            int pc1 = perm[pr];
            int pc2 = perm[(pr + 1) % N];
            int pairs[4][2] = {{pc1, c1}, {pc1, c2}, {pc2, c1}, {pc2, c2}};
            for (auto &p : pairs) {
                int pc = p[0], cc = p[1];
                int dr = r - pr;
                int dc = cc - pc;
                if (dr == 0) continue;
                for (int tr = r + 1; tr < N; tr++) {
                    int num = dc * (tr - pr);
                    if (num % dr == 0) {
                        int col = pc + num / dr;
                        if (col >= 0 && col < N)
                            forbid[tr] |= (1ULL << col);
                    }
                }
            }
        }
    }
    
    problem_rows.clear();
    for (int r = 0; r < N; r++)
        if (has_collinear[r] || has_overload[r])
            problem_rows.push_back(r);
}

// Simulated annealing search
vector<int> search(int restarts, int max_iters) {
    vector<int> best_perm;
    int best_total = INT_MAX;
    
    auto t0 = chrono::high_resolution_clock::now();
    
    for (int restart = 0; restart < restarts; restart++) {
        // Random initial permutation
        vector<int> perm(N);
        iota(perm.begin(), perm.end(), 0);
        shuffle(perm.begin(), perm.end(), rng);
        
        Fitness fit = compute_fitness(perm);
        int current = fit.total;
        
        if (current < best_total) {
            best_total = current;
            best_perm = perm;
        }
        
        if (current == 0) {
            auto t1 = chrono::high_resolution_clock::now();
            double sec = chrono::duration<double>(t1 - t0).count();
            printf("✅ Found at restart %d (%.1fs)\n", restart + 1, sec);
            return perm;
        }
        
        double temp_start = 10.0;
        double temp_end = 0.01;
        
        for (int iter = 0; iter < max_iters; iter++) {
            double T = temp_start * pow(temp_end / temp_start, (double)iter / max_iters);
            
            // Find problem rows
            vector<int> problem_rows;
            find_problem_rows(perm, problem_rows);
            
            // Targeted swap
            int i, j;
            if (problem_rows.empty()) {
                i = rng() % N;
                j = rng() % N;
                while (j == i) j = rng() % N;
            } else {
                i = problem_rows[rng() % problem_rows.size()];
                j = rng() % N;
                while (j == i) j = rng() % N;
            }
            
            vector<int> new_perm = perm;
            swap(new_perm[i], new_perm[j]);
            
            Fitness new_fit = compute_fitness(new_perm);
            int delta = new_fit.total - current;
            
            if (delta < 0 || (double)rng() / rng.max() < exp(-delta / max(T, 0.001))) {
                perm = new_perm;
                current = new_fit.total;
                
                if (current < best_total) {
                    best_total = current;
                    best_perm = perm;
                    
                    if (current == 0) {
                        auto t1 = chrono::high_resolution_clock::now();
                        double sec = chrono::duration<double>(t1 - t0).count();
                        printf("✅ Found at restart %d, iter %d (%.1fs)\n", restart + 1, iter, sec);
                        return perm;
                    }
                }
            }
        }
        
        if ((restart + 1) % 5 == 0) {
            auto t1 = chrono::high_resolution_clock::now();
            double sec = chrono::duration<double>(t1 - t0).count();
            printf("R%d/%d: best=%d [%.1fs]\n", restart + 1, restarts, best_total, sec);
        }
    }
    
    auto t1 = chrono::high_resolution_clock::now();
    double sec = chrono::duration<double>(t1 - t0).count();
    printf("❌ Not found in %d restarts [%.1fs]. Best fitness: %d\n", restarts, sec, best_total);
    
    return best_perm;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <n> [restarts] [iters]\n", argv[0]);
        return 1;
    }
    
    N = atoi(argv[1]);
    int restarts = (argc > 2) ? atoi(argv[2]) : 200;
    int iters = (argc > 3) ? atoi(argv[3]) : 20000;
    
    build_dist_cache();
    
    // Compute permutation count
    long long perm_count = 1;
    for (int i = 2; i <= N; i++) perm_count *= i;
    
    printf("Hamiltonian Cycle Search: n=%d\n", N);
    printf("  Restarts: %d, Iters/restart: %d\n", restarts, iters);
    printf("  Perm space: %lld possibilities\n", perm_count);
    printf("\n");
    
    vector<int> result = search(restarts, iters);
    
    if (!result.empty()) {
        Fitness fit = compute_fitness(result);
        printf("\nResult: fitness=%d\n", fit.total);
        printf("  Collinear: %d\n", fit.collinear);
        printf("  Ring overload: %d\n", fit.overload);
        
        if (fit.total == 0) {
            printf("  Permutation: [");
            for (int i = 0; i < N; i++)
                printf("%d%c", result[i], i < N-1 ? ',' : ']');
            printf("\n  Solution:\n");
            for (int r = 0; r < N; r++) {
                int c1 = result[r];
                int c2 = result[(r + 1) % N];
                printf("    Row %2d: (%d,%d) d=%d, (%d,%d) d=%d\n",
                       r, c1, r, get_dist(c1, r), c2, r, get_dist(c2, r));
            }
        }
    }
    
    return 0;
}
