// csearch_cuda.cu — GPU parallel SA for rot4-NTIL (m=37), one SA chain per CUDA thread.
//
// This is a faithful port of the verified CPU solver csearch2.cpp:
//   * each "cell" (x,y) in [0,m-1]^2 lifts via C4 to 4 points on the 2m x 2m grid;
//   * objective = number of collinear triples among the 4m lifted points (the (X) constraint;
//     (S) slope+-1 collinearity is a subset and handled automatically);
//   * moves: YSWAP / XSWAP / XYSWAP (same 3 types as csearch2);
//   * SA accept rule: identical to csearch2 (T0=3.0, Tend=0.005, geometric decay).
//
// Parallelism: nchains independent SA chains run simultaneously (embarrassingly parallel).
// Each chain owns a local hash table (per-chain slice of d_hash) tracking line->count,
// updated incrementally via an epoch tag for O(1) dedupe of lines through a moved point.
//
// BUILD (requires MSVC host compiler for nvcc; on this box: enter VsDevShell then:)
//   nvcc -O3 -arch=sm_89 csearch_cuda.cu -o csearch_cuda.exe
// (Verified to compile + run on RTX 4070 SUPER, 2026-07-13.)
//
// RUN:
//   csearch_cuda.exe --m 37 --nchains 8192 --moves 3000 --launches 30 --seed 1
// (host loop launches the SA kernel repeatedly, copies best_bad back, checks for a 0.)

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cuda_runtime.h>

typedef long long LL;

#define HSIZE 16384         // hash slots per chain (power of two; must exceed C(4m,2) lines, e.g. m=37 -> 10878)
#define AOFF 200
#define BOFF 200
#define COFF 20000
#define BSPAN 400
#define CSPAN 40000

struct Slot { long long key; int cnt; int epoch; };

__device__ __forceinline__ int igcd(int a, int b) {
    a = abs(a); b = abs(b);
    while (b) { int t = a % b; a = b; b = t; }
    return a;
}
__device__ __forceinline__ LL line_of(int px, int py, int qx, int qy) {
    int a = -(qy - py), b = (qx - px), c = (qy - py) * px - (qx - px) * py;
    int g = igcd(abs(a), abs(b)); g = igcd(g, abs(c));
    if (g) { a /= g; b /= g; c /= g; }
    if (a < 0 || (a == 0 && b < 0) || (a == 0 && b == 0 && c < 0)) { a = -a; b = -b; c = -c; }
    LL K = (LL)(a + AOFF); K = K * BSPAN + (b + BOFF); K = K * CSPAN + (c + COFF);
    return K;
}
__device__ __forceinline__ LL C3(LL t) { return (t >= 3) ? t * (t - 1) * (t - 2) / 6 : 0; }
__device__ __forceinline__ uint64_t xs_next(uint64_t &s) {
    s ^= s << 13; s ^= s >> 7; s ^= s << 17; return s;
}

__device__ __forceinline__ void get_pt(const int* xs, const int* ys, int m, int n, int idx, int &x, int &y) {
    int i = idx >> 2, r = idx & 3;
    int cx = xs[i], cy = ys[i];
    if (r == 0) { x = cx; y = cy; }
    else if (r == 1) { x = n - 1 - cy; y = cx; }
    else if (r == 2) { x = n - 1 - cx; y = n - 1 - cy; }
    else { x = cy; y = n - 1 - cx; }
}

__device__ void add_point(int c, int m, int n, const int* xs, const int* ys,
                          Slot* hash, LL* bad, int* epoch, int pidx) {
    int base = c * HSIZE;
    int px, py; get_pt(xs, ys, m, n, pidx, px, py);
    int E = (*epoch) + 1; *epoch = E;
    int total = 4 * m;
    for (int j = 0; j < total; j++) {
        if (j == pidx) continue;
        int qx, qy; get_pt(xs, ys, m, n, j, qx, qy);
        if (qx == px && qy == py) continue;
        LL key = line_of(px, py, qx, qy);
        unsigned h = (unsigned)((key * 2654435761ULL) & (HSIZE - 1));
        int probe = 0;
        while (hash[base + h].key != 0 && hash[base + h].key != key) { h = (h + 1) & (HSIZE - 1); if (++probe >= HSIZE) break; }
        Slot &s = hash[base + h];
        if (s.key == key) {
            if (s.epoch == E) continue;
            LL o = s.cnt; *bad += C3(o + 1) - C3(o); s.cnt = o + 1; s.epoch = E;
        } else {
            s.key = key; s.cnt = 1; s.epoch = E;
        }
    }
}
__device__ void remove_point(int c, int m, int n, const int* xs, const int* ys,
                             Slot* hash, LL* bad, int* epoch, int pidx) {
    int base = c * HSIZE;
    int px, py; get_pt(xs, ys, m, n, pidx, px, py);
    int E = (*epoch) + 1; *epoch = E;
    int total = 4 * m;
    for (int j = 0; j < total; j++) {
        if (j == pidx) continue;
        int qx, qy; get_pt(xs, ys, m, n, j, qx, qy);
        if (qx == px && qy == py) continue;
        LL key = line_of(px, py, qx, qy);
        unsigned h = (unsigned)((key * 2654435761ULL) & (HSIZE - 1));
        int probe = 0;
        while (hash[base + h].key != 0 && hash[base + h].key != key) { h = (h + 1) & (HSIZE - 1); if (++probe >= HSIZE) break; }
        Slot &s = hash[base + h];
        if (s.key == key) {
            if (s.epoch == E) continue;
            LL o = s.cnt; *bad += C3(o - 1) - C3(o); s.cnt = o - 1;
            if (s.cnt == 0) s.key = 0;
            s.epoch = E;
        }
    }
}

__global__ void init_kernel(int nchains, int m, int n, int* xs, int* ys,
                            Slot* hash, LL* bad, int* epoch, unsigned long long* rng) {
    int c = blockIdx.x * blockDim.x + threadIdx.x;
    if (c >= nchains) return;
    uint64_t st = rng[c] ? rng[c] : (c * 97813947ULL + 1ULL);
    for (int i = 0; i < m; i++) xs[c * m + i] = i;
    for (int i = m - 1; i > 0; i--) { int j = (int)(xs_next(st) % (i + 1)); int t = xs[c * m + i]; xs[c * m + i] = xs[c * m + j]; xs[c * m + j] = t; }
    for (int i = 0; i < m; i++) ys[c * m + i] = i;
    for (int i = m - 1; i > 0; i--) { int j = (int)(xs_next(st) % (i + 1)); int t = ys[c * m + i]; ys[c * m + i] = ys[c * m + j]; ys[c * m + j] = t; }
    for (int h = 0; h < HSIZE; h++) hash[c * HSIZE + h].key = 0;
    bad[c] = 0; epoch[c] = 0;
    for (int p = 0; p < 4 * m; p++) add_point(c, m, n, xs, ys, hash, bad, epoch, p);
    rng[c] = st;
}

__global__ void sa_kernel(int nchains, int m, int n, int* xs, int* ys,
                          Slot* hash, LL* bad, int* epoch, unsigned long long* rng,
                          LL moves, double T0, double Tend, int* found, int* fsol) {
    int c = blockIdx.x * blockDim.x + threadIdx.x;
    if (c >= nchains) return;
    uint64_t st = rng[c];
    double T = T0;
    double Tdec = pow(Tend / T0, 1.0 / (double)moves);
    for (LL mv = 0; mv < moves; mv++) {
        int i = (int)(xs_next(st) % m);
        int j = (int)(xs_next(st) % m);
        if (i == j) continue;
        int mt = (int)(xs_next(st) % 3);
        int oi[4], oj[4];
        for (int r = 0; r < 4; r++) { oi[r] = 4 * i + r; oj[r] = 4 * j + r; }
        LL before = bad[c];
        for (int r = 0; r < 4; r++) { remove_point(c, m, n, xs, ys, hash, bad, epoch, oi[r]); remove_point(c, m, n, xs, ys, hash, bad, epoch, oj[r]); }
        if (mt == 0) { int t = ys[c * m + i]; ys[c * m + i] = ys[c * m + j]; ys[c * m + j] = t; }
        else if (mt == 1) { int t = xs[c * m + i]; xs[c * m + i] = xs[c * m + j]; xs[c * m + j] = t; }
        else { int tx = xs[c * m + i], ty = ys[c * m + i]; xs[c * m + i] = xs[c * m + j]; ys[c * m + i] = ys[c * m + j]; xs[c * m + j] = tx; ys[c * m + j] = ty; }
        for (int r = 0; r < 4; r++) { add_point(c, m, n, xs, ys, hash, bad, epoch, oi[r]); add_point(c, m, n, xs, ys, hash, bad, epoch, oj[r]); }
        LL after = bad[c];
        double u = (double)(xs_next(st) >> 11) * (1.0 / (double)(1ULL << 53));
        if (after <= before || u < exp(-(double)(after - before) / T)) {
            if (after == 0) {
                if (atomicCAS(found, 0, 1) == 0) {
                    for (int k = 0; k < m; k++) { fsol[2 * k] = xs[c * m + k]; fsol[2 * k + 1] = ys[c * m + k]; }
                }
                rng[c] = st; return;
            }
        } else {
            for (int r = 0; r < 4; r++) { remove_point(c, m, n, xs, ys, hash, bad, epoch, oi[r]); remove_point(c, m, n, xs, ys, hash, bad, epoch, oj[r]); }
            if (mt == 0) { int t = ys[c * m + i]; ys[c * m + i] = ys[c * m + j]; ys[c * m + j] = t; }
            else if (mt == 1) { int t = xs[c * m + i]; xs[c * m + i] = xs[c * m + j]; xs[c * m + j] = t; }
            else { int tx = xs[c * m + i], ty = ys[c * m + i]; xs[c * m + i] = xs[c * m + j]; ys[c * m + i] = ys[c * m + j]; xs[c * m + j] = tx; ys[c * m + j] = ty; }
            for (int r = 0; r < 4; r++) { add_point(c, m, n, xs, ys, hash, bad, epoch, oi[r]); add_point(c, m, n, xs, ys, hash, bad, epoch, oj[r]); }
        }
        T *= Tdec;
    }
    rng[c] = st;
}

int main(int argc, char** argv) {
    int m = 37, nchains = 8192, seed = 1;
    LL moves = 8000; int launches = 200;
    for (int a = 1; a < argc; a++) {
        if (!strcmp(argv[a], "--m") && a + 1 < argc) m = atoi(argv[++a]);
        else if (!strcmp(argv[a], "--nchains") && a + 1 < argc) nchains = atoi(argv[++a]);
        else if (!strcmp(argv[a], "--moves") && a + 1 < argc) moves = atoll(argv[++a]);
        else if (!strcmp(argv[a], "--launches") && a + 1 < argc) launches = atoi(argv[++a]);
        else if (!strcmp(argv[a], "--seed") && a + 1 < argc) seed = atoi(argv[++a]);
    }
    int n = 2 * m;
    Slot* d_hash; int* d_xs; int* d_ys; LL* d_bad; int* d_epoch; unsigned long long* d_rng; int* d_found; int* d_sol;
    cudaMalloc(&d_hash, (size_t)nchains * HSIZE * sizeof(Slot));
    cudaMalloc(&d_xs, (size_t)nchains * m * sizeof(int));
    cudaMalloc(&d_ys, (size_t)nchains * m * sizeof(int));
    cudaMalloc(&d_bad, (size_t)nchains * sizeof(LL));
    cudaMalloc(&d_epoch, (size_t)nchains * sizeof(int));
    cudaMalloc(&d_rng, (size_t)nchains * sizeof(unsigned long long));
    cudaMalloc(&d_found, sizeof(int));
    cudaMalloc(&d_sol, (size_t)2 * m * sizeof(int));
    unsigned long long* hr = (unsigned long long*)malloc((size_t)nchains * sizeof(unsigned long long));
    for (int c = 0; c < nchains; c++) hr[c] = (unsigned long long)(c + 1) * 2654435761ULL ^ (unsigned long long)seed;
    cudaMemcpy(d_rng, hr, (size_t)nchains * sizeof(unsigned long long), cudaMemcpyHostToDevice);
    cudaMemset(d_found, 0, sizeof(int));
    int TPB = 256; int NB = (nchains + TPB - 1) / TPB;
    init_kernel<<<NB, TPB>>>(nchains, m, n, d_xs, d_ys, d_hash, d_bad, d_epoch, d_rng);
    cudaDeviceSynchronize();
    { cudaError_t e = cudaGetLastError(); if (e != cudaSuccess) { printf("CUDA init error: %s\n", cudaGetErrorString(e)); fflush(stdout); return 1; } }

    LL best_overall = 1e18; bool found = false;
    LL* hbad = (LL*)malloc((size_t)nchains * sizeof(LL));
    printf("GPU start: m=%d nchains=%d moves=%lld launches=%d TPB=%d NB=%d\n", m, nchains, moves, launches, TPB, NB); fflush(stdout);
    for (int l = 0; l < launches && !found; l++) {
        sa_kernel<<<NB, TPB>>>(nchains, m, n, d_xs, d_ys, d_hash, d_bad, d_epoch, d_rng, moves, 3.0, 0.005, d_found, d_sol);
        { cudaError_t e = cudaDeviceSynchronize(); if (e != cudaSuccess) { printf("CUDA sa error (launch %d): %s\n", l, cudaGetErrorString(e)); fflush(stdout); break; } }
        cudaMemcpy(hbad, d_bad, (size_t)nchains * sizeof(LL), cudaMemcpyDeviceToHost);
        LL mn = hbad[0]; for (int c = 1; c < nchains; c++) if (hbad[c] < mn) mn = hbad[c];
        if (mn < best_overall) best_overall = mn;
        int f; cudaMemcpy(&f, d_found, sizeof(int), cudaMemcpyDeviceToHost);
        if (f) { found = true; int* hs = (int*)malloc((size_t)2 * m * sizeof(int)); cudaMemcpy(hs, d_sol, (size_t)2 * m * sizeof(int), cudaMemcpyDeviceToHost);
            printf("FOUND m=%d\ncells:", m); for (int k = 0; k < m; k++) printf(" (%d,%d)", hs[2 * k], hs[2 * k + 1]); printf("\n"); fflush(stdout); free(hs); break; }
        if (l % 10 == 0) { printf("launch %d best_bad=%lld\n", l, best_overall); fflush(stdout); }
    }
    if (!found) { printf("NOTFOUND m=%d best_bad=%lld launches=%d\n", m, best_overall, launches); fflush(stdout); }
    return 0;
}
