#include <cstdio>
#include <cstdint>

__global__ void vec_add(const int* a, const int* b, int* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}

int main() {
    const int n = 1 << 20;
    int *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, n * sizeof(int));
    cudaMalloc(&d_b, n * sizeof(int));
    cudaMalloc(&d_c, n * sizeof(int));

    int *h_a = new int[n], *h_b = new int[n], *h_c = new int[n];
    for (int i = 0; i < n; i++) { h_a[i] = i; h_b[i] = 2 * i; }

    cudaMemcpy(d_a, h_a, n * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, n * sizeof(int), cudaMemcpyHostToDevice);

    int threads = 256;
    int blocks = (n + threads - 1) / threads;
    vec_add<<<blocks, threads>>>(d_a, d_b, d_c, n);
    cudaDeviceSynchronize();

    cudaMemcpy(h_c, d_c, n * sizeof(int), cudaMemcpyDeviceToHost);

    int errs = 0;
    for (int i = 0; i < n; i++) if (h_c[i] != 3 * i) errs++;
    printf("CUDA smoke test: n=%d, errors=%d\n", n, errs);

    int dev;
    cudaGetDevice(&dev);
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, dev);
    printf("Device %d: %s, %zu MiB global mem\n", dev, prop.name, prop.totalGlobalMem / (1024 * 1024));

    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
    delete[] h_a; delete[] h_b; delete[] h_c;
    return errs;
}
