// n3line_gpu.cu
// GPU-accelerated no-three-in-line solver (2n-point, 2-per-row formulation).
//
// Core idea (Lemma-1 context): a solution is a set of 2n grid points, <=2 per row,
// with no three collinear. The expensive step in any backtracking search is, at each
// row, deciding which column-pair is still "safe" given the already-placed points.
// That decision is perfectly data-parallel, so we offload it to a CUDA kernel:
//   for every candidate column-pair (c1,c2) in the current row, test whether adding
//   {(row,c1),(row,c2)} to the placed set creates ANY three-collinear triple.
// The CPU does the DFS traversal; the GPU prunes each row's branching in parallel.
//
// Scope/honesty: this is an EXACT exhaustive search (no heuristic), validated against
// known small-n solutions. For n=74/76 it is a Heule-scale computation; a single run
// may not terminate in available time. Any solution found is COMPUTATIONAL EVIDENCE,
// not a proof. The deliverable is the working GPU pipeline + the attempt.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <cuda_runtime.h>

typedef long long i64;

// -------- kernel: mark safe column-pairs for one row given placed points --------
// d_px,d_py : placed points (k of them)
// d_comb    : 2*nc integers = nc column-pairs (c1,c2)
// d_safe    : nc ints, 1 = safe, 0 = creates a collinear triple
__global__ void safe_pairs_row(int n, int k, const int* d_px, const int* d_py,
                               int row, int nc, const int* d_comb, int* d_safe) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= nc) return;
    int c1 = d_comb[2 * t];
    int c2 = d_comb[2 * t + 1];
    // Build the (k+2) candidate points. k <= 2*n (<=152 for n=76) + 2 < 512.
    int X[512]; int Y[512];
    int m = 0;
    X[m] = row; Y[m] = c1; m++;
    X[m] = row; Y[m] = c2; m++;
    for (int i = 0; i < k; i++) { X[m] = d_px[i]; Y[m] = d_py[i]; m++; }
    // Only triples involving >=1 of the two new points can be newly collinear.
    // New-point indices: 0 and 1.
    bool bad = false;
    // both new + one placed
    for (int i = 0; i < k && !bad; i++) {
        int x1=X[0],y1=Y[0], x2=X[1],y2=Y[1], x3=X[2+i],y3=Y[2+i];
        if ((i64)(x2-x1)*(y3-y1) == (i64)(x3-x1)*(y2-y1)) bad = true;
    }
    // exactly one new + two placed
    // new point 0 with placed pair (i,j)
    for (int i = 0; i < k && !bad; i++) {
        for (int j = i+1; j < k && !bad; j++) {
            int x1=X[0],y1=Y[0], x2=X[2+i],y2=Y[2+i], x3=X[2+j],y3=Y[2+j];
            if ((i64)(x2-x1)*(y3-y1) == (i64)(x3-x1)*(y2-y1)) bad = true;
        }
    }
    // new point 1 with placed pair (i,j)
    for (int i = 0; i < k && !bad; i++) {
        for (int j = i+1; j < k && !bad; j++) {
            int x1=X[1],y1=Y[1], x2=X[2+i],y2=Y[2+i], x3=X[2+j],y3=Y[2+j];
            if ((i64)(x2-x1)*(y3-y1) == (i64)(x3-x1)*(y2-y1)) bad = true;
        }
    }
    d_safe[t] = bad ? 0 : 1;
}

// -------- host DFS --------
static int N = 0;
static int SOL_CAP = 1;
static int MAXC = 0;          // size of d_safe / d_comb allocations
static long long NODES = 0;
static std::vector<int> PX, PY;
// Each solution is stored as a flat vector: first 2N entries = rows, next 2N = cols.
static std::vector< std::vector<int> > SOLS;

static int* d_px = nullptr;
static int* d_py = nullptr;
static int* d_comb = nullptr;
static int* d_safe = nullptr;

// Randomized-restart mode: same EXACT search, but column pairs are visited in a
// per-row shuffled order. This does not change correctness (every pair is still
// considered); it only changes which solution is found first, which lets a single
// run locate a solution at large n without exhausting a lexicographic dead region.
static unsigned int g_seed = 0;
static bool g_shuffle = false;

void dfs(int row) {
    if ((int)SOLS.size() >= SOL_CAP) return;
    if (row == N) {
        // success: 2N points placed. Store rows then cols so points pair as (sol[i], sol[2N+i]).
        std::vector<int> sol;
        sol.reserve(2 * PX.size());
        sol.insert(sol.end(), PX.begin(), PX.end());
        sol.insert(sol.end(), PY.begin(), PY.end());
        SOLS.push_back(sol);
        return;
    }
    NODES++;
    // Build column pairs for THIS row (local — must not be shared across recursion).
    std::vector<int> host_comb;
    for (int c1 = 0; c1 < N; c1++)
        for (int c2 = c1 + 1; c2 < N; c2++) {
            host_comb.push_back(c1); host_comb.push_back(c2);
        }
    if (g_shuffle) {
        unsigned int s = g_seed + 0x9E3779B9u * (unsigned int)row;
        int nc0 = (int)host_comb.size() / 2;
        for (int i = nc0 - 1; i > 0; i--) {
            s = s * 1664525u + 1013904223u;
            int j = (int)(s % (unsigned int)(i + 1));
            if (i != j) {
                std::swap(host_comb[2 * i], host_comb[2 * j]);
                std::swap(host_comb[2 * i + 1], host_comb[2 * j + 1]);
            }
        }
    }
    int nc = (int)host_comb.size() / 2;
    // upload
    cudaMemcpy(d_px, PX.data(), PX.size() * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_py, PY.data(), PY.size() * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_comb, host_comb.data(), host_comb.size() * sizeof(int), cudaMemcpyHostToDevice);
    int threads = 256;
    int blocks = (nc + threads - 1) / threads;
    cudaMemset(d_safe, 0, (size_t)MAXC * sizeof(int));
    safe_pairs_row<<<blocks, threads>>>(N, (int)PX.size(), d_px, d_py, row, nc, d_comb, d_safe);
    cudaDeviceSynchronize();
    cudaError_t ke = cudaGetLastError();
    if (ke != cudaSuccess) printf("KERNEL ERROR row=%d: %s\n", row, cudaGetErrorString(ke));
    // Local safe vector — each recursion level owns its own so it survives the
    // recursive call (the previous bug shared this across levels and got clobbered).
    std::vector<int> host_safe(nc);
    cudaMemcpy(host_safe.data(), d_safe, nc * sizeof(int), cudaMemcpyDeviceToHost);
    if (row == 0) {
        int sc = 0; for (int t = 0; t < nc; t++) sc += host_safe[t];
        printf("DEBUG row0: nc=%d safe_pairs=%d k=%d\n", nc, sc, (int)PX.size());
    }
    int rec = 0;
    for (int t = 0; t < nc; t++) {
        if (host_safe[t] == 0) continue;
        int c1 = host_comb[2 * t], c2 = host_comb[2 * t + 1];
        PX.push_back(row); PY.push_back(c1);
        PX.push_back(row); PY.push_back(c2);
        rec++;
        dfs(row + 1);
        PX.pop_back(); PY.pop_back();
        PX.pop_back(); PY.pop_back();
        if ((int)SOLS.size() >= SOL_CAP) return;
    }
    if (row == 0) printf("DEBUG row0 recursed into row1: %d times; total nodes=%lld\n", rec, NODES);
}

int main(int argc, char** argv) {
    N = (argc > 1) ? atoi(argv[1]) : 12;
    SOL_CAP = (argc > 2) ? atoi(argv[2]) : 1;
    if (argc > 3) { g_seed = (unsigned int)atoi(argv[3]); g_shuffle = true; }
    MAXC = N * N + 16;
    int maxpts = 2 * N + 16;
    cudaMalloc(&d_px, maxpts * sizeof(int));
    cudaMalloc(&d_py, maxpts * sizeof(int));
    cudaMalloc(&d_comb, 2 * MAXC * sizeof(int));
    cudaMalloc(&d_safe, MAXC * sizeof(int));

    cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
    cudaEventRecord(t0);
    dfs(0);
    cudaEventRecord(t1); cudaEventSynchronize(t1);
    float ms = 0; cudaEventElapsedTime(&ms, t0, t1);

    printf("n=%d  solutions_found=%d  nodes=%lld  gpu_time=%.3fs\n",
           N, (int)SOLS.size(), NODES, ms / 1000.0);
    if (!SOLS.empty()) {
        const auto& s = SOLS[0];
        int half = (int)s.size() / 2;  // first half = rows, second half = cols
        printf("first solution (r,c) pairs:\n");
        for (int i = 0; i < half; i++) {
            printf("  pt %d: (%d,%d)\n", i, s[i], s[half + i]);
        }
    }
    cudaFree(d_px); cudaFree(d_py); cudaFree(d_comb); cudaFree(d_safe);
    return 0;
}
