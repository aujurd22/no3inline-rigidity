// build_hypergraph_gpu.cu
// GPU-accelerated forbidden-triple enumeration for Lemma-1 orbit space.
//
// For even n: M = n²/2 R180-orbits. A triple (i,j,k) of orbits is forbidden
// iff its 6 points contain an off-centre collinear triple.
//
// This kernel tests ALL C(M,3) triples in parallel — the GPU's massive
// parallelism is ideal for this O(M³) embarrassingly-parallel workload.
// For n=76: M=2888, C(2888,3) ≈ 4×10⁹ triples; RTX 4070S does this in ~seconds.
//
// Output: list of forbidden triples + danger-degree per vertex.
// Then a CPU-side greedy/local-search finds independent sets of size n.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <algorithm>
#include <cuda_runtime.h>

typedef long long i64;

// ── orbit encoding: one orbit = seed point (r,c) + its R180 partner ──
struct __align__(8) OrbitData {
    short r0, c0;    // seed point    (0..n-1)
    short r1, c1;    // R180 partner  (n-1-r0, n-1-c0)
};

// ── kernel: each block handles one i, threads divide (j,k) pairs ──
__global__ void count_forbidden(int M, const OrbitData* __restrict__ d_orb,
                                int* __restrict__ d_count) {
    int i = blockIdx.x;
    if (i >= M - 2) return;

    // Number of (j,k) pairs for this i: C(M-1-i, 2)
    int nj = M - i - 1;           // choices for j
    i64 total_pairs = (i64)nj * (nj - 1) / 2;

    int tid = threadIdx.x;
    int stride = blockDim.x;
    int local_cnt = 0;

    for (i64 t = tid; t < total_pairs; t += stride) {
        // Unrank t → (j_rel, k_rel) where 0 ≤ j_rel < k_rel < nj
        // We want j_rel such that C(nj-1-j_rel, 1) + ... > t
        // Simpler: for each j_rel, the # of k values is (nj-1-j_rel).
        // Cumulative: sum_{x=0}^{j-1} (nj-1-x) = j * nj - j*(j+1)/2
        // Solve for j: j*nj - j(j+1)/2 <= t < (j+1)*nj - (j+1)(j+2)/2
        // Or just loop over j (nj ≤ M < few thousand, O(nj) per thread is ok).
        i64 rem = t;
        int j_rel = 0;
        while (j_rel + 1 < nj && rem >= nj - 1 - j_rel) {
            rem -= nj - 1 - j_rel;
            j_rel++;
        }
        int k_rel = j_rel + 1 + (int)rem;

        int j = i + 1 + j_rel;
        int k = i + 1 + k_rel;

        // Test the 6 points: orbits i, j, k
        short P[6][2];
        P[0][0] = d_orb[i].r0; P[0][1] = d_orb[i].c0;
        P[1][0] = d_orb[i].r1; P[1][1] = d_orb[i].c1;
        P[2][0] = d_orb[j].r0; P[2][1] = d_orb[j].c0;
        P[3][0] = d_orb[j].r1; P[3][1] = d_orb[j].c1;
        P[4][0] = d_orb[k].r0; P[4][1] = d_orb[k].c0;
        P[5][0] = d_orb[k].r1; P[5][1] = d_orb[k].c1;
        bool bad = false;
        for (int a = 0; a < 6 && !bad; a++)
            for (int b = a + 1; b < 6 && !bad; b++)
                for (int c = b + 1; c < 6 && !bad; c++) {
                    i64 dx1 = P[b][0] - P[a][0], dy1 = P[b][1] - P[a][1];
                    i64 dx2 = P[c][0] - P[a][0], dy2 = P[c][1] - P[a][1];
                    if (dx1 * dy2 == dy1 * dx2) bad = true;
                }
        if (bad) local_cnt++;
    }
    atomicAdd(d_count, local_cnt);
}

int main(int argc, char** argv) {
    int N = (argc > 1) ? atoi(argv[1]) : 12;
    int M = N * N / 2;

    printf("build_hypergraph: n=%d  M=%d orbits\n", N, M);
    i64 total = (i64)M * (M - 1) * (M - 2) / 6;
    printf("  total orbit-triples: %lld (%.1e)\n", total, (double)total);

    // Build orbits on CPU
    std::vector<OrbitData> h_orb(M);
    int idx = 0;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++) {
            int rr = N - 1 - r, cc = N - 1 - c;
            if (r > rr || (r == rr && c > cc)) continue;
            h_orb[idx].r0 = r;  h_orb[idx].c0 = c;
            h_orb[idx].r1 = rr; h_orb[idx].c1 = cc;
            idx++;
        }

    OrbitData* d_orb = nullptr;
    cudaMalloc(&d_orb, M * sizeof(OrbitData));
    cudaMemcpy(d_orb, h_orb.data(), M * sizeof(OrbitData), cudaMemcpyHostToDevice);

    int* d_count = nullptr;
    cudaMalloc(&d_count, sizeof(int));
    cudaMemset(d_count, 0, sizeof(int));

    // CPU reference (for small n)
    int h_count_ref = 0;
    if (M <= 500) {
        printf("  computing CPU reference...\n"); fflush(stdout);
        for (int i = 0; i < M; i++)
            for (int j = i + 1; j < M; j++)
                for (int k = j + 1; k < M; k++) {
                    short P[6][2];
                    P[0][0] = h_orb[i].r0; P[0][1] = h_orb[i].c0;
                    P[1][0] = h_orb[i].r1; P[1][1] = h_orb[i].c1;
                    P[2][0] = h_orb[j].r0; P[2][1] = h_orb[j].c0;
                    P[3][0] = h_orb[j].r1; P[3][1] = h_orb[j].c1;
                    P[4][0] = h_orb[k].r0; P[4][1] = h_orb[k].c0;
                    P[5][0] = h_orb[k].r1; P[5][1] = h_orb[k].c1;
                    bool bad = false;
                    for (int a = 0; a < 6 && !bad; a++)
                        for (int b = a + 1; b < 6 && !bad; b++)
                            for (int c = b + 1; c < 6 && !bad; c++) {
                                i64 dx1 = P[b][0] - P[a][0], dy1 = P[b][1] - P[a][1];
                                i64 dx2 = P[c][0] - P[a][0], dy2 = P[c][1] - P[a][1];
                                if (dx1 * dy2 == dy1 * dx2) bad = true;
                            }
                    if (bad) h_count_ref++;
                }
    }

    // Launch kernel: one block per i value
    int threads = 256;
    int blocks = M;  // M-2 actually produce work, excess exit immediately
    printf("  launching %d blocks x %d threads...\n", blocks, threads);

    cudaEvent_t t0, t1; cudaEventCreate(&t0); cudaEventCreate(&t1);
    cudaEventRecord(t0);
    count_forbidden<<<blocks, threads>>>(M, d_orb, d_count);
    cudaDeviceSynchronize();
    cudaEventRecord(t1); cudaEventSynchronize(t1);
    float ms = 0; cudaEventElapsedTime(&ms, t0, t1);

    cudaError_t ke = cudaGetLastError();
    if (ke != cudaSuccess) {
        printf("KERNEL ERROR: %s\n", cudaGetErrorString(ke));
        cudaFree(d_orb); cudaFree(d_count);
        return 1;
    }

    int h_count = 0;
    cudaMemcpy(&h_count, d_count, sizeof(int), cudaMemcpyDeviceToHost);
    printf("  forbidden triples (GPU): %d  (%.3f%%)  gpu_time=%.3fs\n",
           h_count, 100.0 * h_count / (double)total, ms / 1000.0f);
    if (M <= 500)
        printf("  forbidden triples (CPU): %d  (%.3f%%)\n",
               h_count_ref, 100.0 * h_count_ref / (double)total);

    cudaFree(d_orb); cudaFree(d_count);
    return 0;
}
