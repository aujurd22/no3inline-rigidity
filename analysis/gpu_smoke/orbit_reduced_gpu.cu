// orbit_reduced_gpu.cu
// Lemma‑1 reduced no‑three‑in-line solver: DFS over R180‑orbit space,
// GPU‑accelerated per‑node validation.
//
// For even n: pick n orbits from M=n²/2 candidates with pairwise distinct
// central directions and no forbidden orbit‑triple (off‑centre collinearity).
//
// Architecture (same proven pattern as n3line_gpu.cu):
//   CPU  — DFS traversal over orbit indices
//   GPU  — kernel 'safe_orbits' tests every remaining candidate orbit in parallel:
//           checks direction distinctness + forbidden triples with already-chosen set.
//   Randomised-restart mode (argv[3]=seed): shuffle within danger tiers.
//
// Honesty: exact exhaustive search within a given ordering. Any solution found
// is a valid no‑three‑in‑line configuration; existence is COMPUTATIONAL EVIDENCE.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <cuda_runtime.h>

typedef long long i64;
typedef unsigned int u32;

// ── kernel: mark safe orbit candidates given a partial selection ────
// d_orbit_pt : M × 2  — one seed point per orbit  (int pairs)
// d_dir      : M × 2  — canonical direction per orbit (int pairs)
// d_chosen   : k × 2   — (seed_r, seed_c) of already-chosen k orbits
// d_candidates: nc ints — orbit indices to test
// d_safe     : nc ints — 1 = safe to add, 0 = would create conflict
__global__ void safe_orbits(int n, int M, int k,
    const int* __restrict__ d_orbit_pt,   // M×2
    const int* __restrict__ d_dir,        // M×2
    const int* __restrict__ d_chosen,     // k×2  (seed points only)
    int nc, const int* __restrict__ d_candidates,
    int* __restrict__ d_safe) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nc) return;
    int vi = d_candidates[t];
    // --- direction check ---
    int da = d_dir[2 * vi], db = d_dir[2 * vi + 1];
    for (int i = 0; i < k; i++) {
        int ca = d_chosen[2 * i], cb = d_chosen[2 * i + 1]; // actually dir of chosen[i]
        // Wait — d_chosen stores seed points, not dirs. Need dir lookup.
        // Let's restructure: pass chosen ORBIT INDICES instead.
    }
    // Simplified: store chosen orbit indices, look up dirs directly.
    // (See host code for actual data layout.)
    d_safe[t] = 0; // placeholder — real logic below after restructure
}

// ── corrected kernel with index-based interface ──────────────
__global__ void safe_orbits_v2(int n, int M, int k,
    const int* __restrict__ d_orbit_pt,   // M×2  seed points
    const int* __restrict__ d_dir,        // M×2  canonical directions
    const int* __restrict__ dchosen_idx,  // k    chosen orbit indices
    int nc, const int* __restrict__ dcand,
    int* __restrict__ dsafe) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nc) return;
    int vi = dcand[t];

    // Direction distinctness
    int da = d_dir[2 * vi], db = d_dir[2 * vi + 1];
    for (int i = 0; i < k; i++) {
        int ci = dchosen_idx[i];
        if (d_dir[2 * ci] == da && d_dir[2 * ci + 1] == db) { dsafe[t] = 0; return; }
    }

    // Forbidden-triple check: for every pair (i,j) among chosen, test triple (vi,i,j)
    // Build local point arrays for the 3 orbits (6 points total).
    int P[6][2];  // orbit vi, then orbit ci, then orbit cj
    // Orbit vi:
    int r0 = d_orbit_pt[2 * vi], c0 = d_orbit_pt[2 * vi + 1];
    P[0][0] = r0; P[0][1] = c0;
    P[1][0] = n - 1 - r0; P[1][1] = n - 1 - c0;

    bool bad = false;
    for (int ai = 0; ai < k && !bad; ai++) {
        int ci = dchosen_idx[ai];
        int r1 = d_orbit_pt[2 * ci], c1 = d_orbit_pt[2 * ci + 1];
        P[2][0] = r1; P[2][1] = c1;
        P[3][0] = n - 1 - r1; P[3][1] = n - 1 - c1;
        for (int aj = ai + 1; aj < k && !bad; aj++) {
            int cj = dchosen_idx[aj];
            int r2 = d_orbit_pt[2 * cj], c2 = d_orbit_pt[2 * cj + 1];
            P[4][0] = r2; P[4][1] = c2;
            P[5][0] = n - 1 - r2; P[5][1] = n - 1 - c2;
            // Test all 20 triples of these 6 points for off-centre collinearity.
            // Use exact 64-bit cross product (coordinates fit in int16 for n < 2^15).
            for (int a = 0; a < 6 && !bad; a++)
                for (int b = a + 1; b < 6 && !bad; b++)
                    for (int c = b + 1; c < 6 && !bad; c++) {
                        i64 dx1 = P[b][0] - P[a][0], dy1 = P[b][1] - P[a][1];
                        i64 dx2 = P[c][0] - P[a][0], dy2 = P[c][1] - P[a][1];
                        if (dx1 * dy2 == dy1 * dx2) bad = true;
                    }
        }
    }
    dsafe[t] = bad ? 0 : 1;
}

// ── host side ──────────────────────────────────────────────────
static int N = 0;          // grid size (even)
static int M = 0;          // number of orbits = N*N/2
static int SOL_CAP = 1;
static long long NODES = 0;
static std::vector<int> CHOSEN;  // chosen orbit indices

static int* d_orbit_pt = nullptr;   // M×2
static int* d_dir = nullptr;        // M×2
static int* dchosen_idx = nullptr;  // max N
static int* dcand_buf = nullptr;    // max M
static int* dsafe_buf = nullptr;    // max M

// Host-side orbit space
struct Orbit { int r, c, ar, ac; };  // seed point + canonical direction
static std::vector<Orbit> orbits;

int h_gcd(int a, int b) { a = abs(a); b = abs(b); while(b){int t=b;b=a%b;a=t;} return a?a:1; }

void build_orbits() {
    orbits.clear();
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++) {
            int rr = N - 1 - r, cc = N - 1 - c;
            if (r > rr || (r == rr && c > cc)) continue; // take lex-smaller rep
            int ar = 2 * r - (N - 1), ac = 2 * c - (N - 1);
            int g = h_gcd(ar, ac);
            orbits.push_back({r, c, ar / g, ac / g});
        }
    M = (int)orbits.size();  // = N*N/2
}

// Danger degree (CPU precomputation)
std::vector<int> compute_danger() {
    std::vector<int> danger(M, 0);
    auto is_bad = [&](int i, int j, int kk) -> bool {
        int P[6][2];
        auto pt = [&](int id, int slot) {
            P[slot][0] = orbits[id].r; P[slot][1] = orbits[id].c;
            P[slot+1][0] = N-1-orbits[id].r; P[slot+1][1] = N-1-orbits[id].c;
        };
        pt(i,0); pt(j,2); pt(kk,4);
        for (int a=0;a<6;a++) for (int b=a+1;b<6;b++) for (int c=b+1;c<6;c++){
            i64 dx1=P[b][0]-P[a][0],dy1=P[b][1]-P[a][1];
            i64 dx2=P[c][0]-P[a][0],dy2=P[c][1]-P[a][1];
            if(dx1*dy2==dy1*dx2)return true;
        }
        return false;
    };
    for (int i=0;i<M;i++) for (int j=i+1;j<M;j++) for (int k=j+1;k<M;k++)
        if(is_bad(i,j,k)){danger[i]++;danger[j]++;danger[k]++;}
    return danger;
}

// DFS
std::vector<int> order_global;  // visitation order (shuffled by danger)
static std::vector<std::vector<int>> FOUND_SOLS;  // global — survives recursion
static int FOUND_CAP = 1;

void dfs(int pos) {
    if ((int)FOUND_SOLS.size() >= FOUND_CAP) return;
    if ((int)CHOSEN.size() == N) {
        FOUND_SOLS.push_back(CHOSEN);
        return;
    }
    NODES++;
    int k = (int)CHOSEN.size();

    // Build candidate list: all order[pos..Norder-1]
    int Norder = (int)order_global.size();
    std::vector<int> cand;
    for (int p = pos; p < Norder; p++) cand.push_back(order_global[p]);
    int nc = (int)cand.size();
    if (nc == 0) return;

    // Upload chosen indices
    cudaMemcpy(dchosen_idx, CHOSEN.data(), k * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(dcand_buf, cand.data(), nc * sizeof(int), cudaMemcpyHostToDevice);

    cudaMemset(dsafe_buf, 0, (size_t)M * sizeof(int));
    int threads = 256;
    int blocks = (nc + threads - 1) / threads;
    safe_orbits_v2<<<blocks, threads>>>(N, M, k, d_orbit_pt, d_dir,
                                       dchosen_idx, nc, dcand_buf, dsafe_buf);
    cudaDeviceSynchronize();
    cudaError_t ke = cudaGetLastError();
    if (ke != cudaSuccess) printf("KERNEL ERROR: %s\n", cudaGetErrorString(ke));

    // Download results
    std::vector<int> safe(nc);
    cudaMemcpy(safe.data(), dsafe_buf, nc * sizeof(int), cudaMemcpyDeviceToHost);

    // Recurse into safe candidates
    for (int t = 0; t < nc; t++) {
        if (safe[t] == 0) continue;
        int vi = cand[t];
        CHOSEN.push_back(vi);
        // Find position of vi in order_global to advance correctly
        int next_pos = pos;
        while (next_pos < Norder && order_global[next_pos] != vi) next_pos++;
        dfs(next_pos + 1);
        CHOSEN.pop_back();
        if ((int)FOUND_SOLS.size() >= FOUND_CAP) return;
    }
}

int main(int argc, char** argv) {
    N = (argc > 1) ? atoi(argv[1]) : 12;
    unsigned int seed = (argc > 2) ? (unsigned int)atoi(argv[2]) : 42;
    int exclude_dirs = (argc > 3) ? atoi(argv[3]) : 0;  // NEW: exclude top-K dangerous dirs

    printf("=== orbit-reduced GPU solver  n=%d  seed=%u  exclude_dirs=%d ===\n", N, seed, exclude_dirs);

    build_orbits();
    printf("M=%d orbits (before filtering)\n", M);

    // Compute danger & build ordered list
    std::vector<int> danger = compute_danger();
    printf("danger computed.\n");

    // --- Filter: exclude most dangerous directions ---
    std::vector<int> effective_indices;
    if (exclude_dirs > 0) {
        // Compute per-direction danger (sum of orbit dangers on each direction)
        std::map<std::pair<int,int>, std::vector<int>> dir_groups;
        for (int i = 0; i < M; i++)
            dir_groups[{orbits[i].ar, orbits[i].ac}].push_back(i);
        // Get direction danger totals
        std::vector<std::pair<int, std::pair<int,int>>> dir_ranks;
        for (auto& kv : dir_groups) {
            int total = 0;
            for (int oi : kv.second) total += danger[oi];
            dir_ranks.push_back({total, kv.first});
        }
        std::sort(dir_ranks.begin(), dir_ranks.end(),
                  [](auto& a, auto& b) { return a.first > b.first; });
        // Collect the top-K dangerous directions
        std::set<std::pair<int,int>> excluded;
        for (int i = 0; i < exclude_dirs && i < (int)dir_ranks.size(); i++)
            excluded.insert(dir_ranks[i].second);
        // Keep only orbits NOT on excluded directions
        for (int i = 0; i < M; i++) {
            auto dkey = std::make_pair(orbits[i].ar, orbits[i].ac);
            if (excluded.count(dkey) == 0)
                effective_indices.push_back(i);
        }
        printf("excluded %d directions, remaining: %d orbits (from %d)\n",
               exclude_dirs, (int)effective_indices.size(), M);
        if ((int)effective_indices.size() < N) {
            printf("ERROR: only %d orbits remain, need %d\n", (int)effective_indices.size(), N);
            return 1;
        }
    } else {
        for (int i = 0; i < M; i++) effective_indices.push_back(i);
    }
    // --- end filter ---

    order_global = effective_indices;  // only consider non-excluded orbits
    int Neff = (int)order_global.size();
    std::sort(order_global.begin(), order_global.end(),
              [&](int a, int b) { return danger[a] < danger[b]; });
    // Shuffle within tiers using seed
    unsigned int s = seed;
    for (int i = 0; i < Neff;) {
        int j = i + 1;
        while (j < Neff && danger[order_global[j]] == danger[order_global[i]]) j++;
        // Fisher-Yates chunk [i,j)
        for (int x = j - 1; x > i; x--) {
            s = s * 1664525u + 1013904223u;
            int y = (int)(s % (unsigned int)(x - i + 1)) + i;
            std::swap(order_global[x], order_global[y]);
        }
        i = j;
    }

    // Allocate GPU memory
    cudaMalloc(&d_orbit_pt, (size_t)M * 2 * sizeof(int));
    cudaMalloc(&d_dir, (size_t)M * 2 * sizeof(int));
    cudaMalloc(&dchosen_idx, (size_t)N * sizeof(int));
    cudaMalloc(&dcand_buf, (size_t)M * sizeof(int));
    cudaMalloc(&dsafe_buf, (size_t)M * sizeof(int));

    // Upload static data
    std::vector<int> h_pt(M * 2), h_dir(M * 2);
    for (int i = 0; i < M; i++) {
        h_pt[2*i] = orbits[i].r;     h_pt[2*i+1] = orbits[i].c;
        h_dir[2*i] = orbits[i].ar;   h_dir[2*i+1] = orbits[i].ac;
    }
    cudaMemcpy(d_orbit_pt, h_pt.data(), (size_t)M * 2 * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_dir, h_dir.data(), (size_t)M * 2 * sizeof(int), cudaMemcpyHostToDevice);

    // Run
    cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
    cudaEventRecord(t0);
    dfs(0);
    cudaEventRecord(t1); cudaEventSynchronize(t1);
    float ms = 0; cudaEventElapsedTime(&ms, t0, t1);

    int nfound = (int)FOUND_SOLS.size();
    printf("n=%d  solutions_found=%d  nodes=%lld  gpu_time=%.3fs\n",
           N, nfound, NODES, ms / 1000.0f);

    if (nfound > 0) {
        printf("solution orbits (seed -> direction):\n");
        for (int idx : FOUND_SOLS[0])
            printf("  (%d,%d) -> (%d,%d)\n",
                   orbits[idx].r, orbits[idx].c,
                   orbits[idx].ar, orbits[idx].ac);
    } else {
        printf("No solution found in this search tree.\n");
    }

    cudaFree(d_orbit_pt); cudaFree(d_dir); cudaFree(dchosen_idx);
    cudaFree(dcand_buf); cudaFree(dsafe_buf);
    return 0;
}
