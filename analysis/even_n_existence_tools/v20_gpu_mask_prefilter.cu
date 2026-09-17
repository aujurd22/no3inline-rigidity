#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>

using U32 = std::uint32_t;
using U64 = std::uint64_t;

constexpr int EDGE_COUNT = 37;
constexpr int BIN_COUNT = 38;

static void check(cudaError_t status, const char* action) {
    if (status != cudaSuccess) {
        std::cerr << action << ": " << cudaGetErrorString(status) << "\n";
        std::exit(2);
    }
}

__global__ void count_masks(
    const U32* low_masks,
    U64 low_count,
    const U32* high_masks,
    U64 high_count,
    const int* first_edge,
    const int* second_edge,
    const U64* defects,
    int defect_count,
    unsigned long long* shape_by_adjacency,
    unsigned long long* hit_by_adjacency
) {
    __shared__ unsigned long long local_shapes[BIN_COUNT];
    __shared__ unsigned long long local_hits[BIN_COUNT];
    for (int bin = threadIdx.x; bin < BIN_COUNT; bin += blockDim.x) {
        local_shapes[bin] = 0;
        local_hits[bin] = 0;
    }
    __syncthreads();

    const U64 total = low_count * high_count;
    for (
        U64 index = static_cast<U64>(blockIdx.x) * blockDim.x + threadIdx.x;
        index < total;
        index += static_cast<U64>(gridDim.x) * blockDim.x
    ) {
        U64 removed = static_cast<U64>(low_masks[index / high_count])
            | (static_cast<U64>(high_masks[index % high_count]) << 18);
        int adjacency = 0;
        #pragma unroll
        for (int vertex = 0; vertex < EDGE_COUNT; ++vertex) {
            U64 first = U64{1} << first_edge[vertex];
            U64 second = U64{1} << second_edge[vertex];
            adjacency += ((removed & first) != 0) && ((removed & second) != 0);
        }
        bool hits = true;
        for (int index = 0; index < defect_count; ++index) {
            if ((removed & defects[index]) == 0) {
                hits = false;
                break;
            }
        }
        atomicAdd(&local_shapes[adjacency], 1ULL);
        if (hits) atomicAdd(&local_hits[adjacency], 1ULL);
    }
    __syncthreads();
    for (int bin = threadIdx.x; bin < BIN_COUNT; bin += blockDim.x) {
        atomicAdd(&shape_by_adjacency[bin], local_shapes[bin]);
        atomicAdd(&hit_by_adjacency[bin], local_hits[bin]);
    }
}

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int k, defect_count;
    if (!(std::cin >> k >> defect_count) || k < 0 || k > 37) return 2;
    std::vector<U64> defects(defect_count);
    for (U64& value : defects) std::cin >> value;
    std::vector<int> first_edge(EDGE_COUNT), second_edge(EDGE_COUNT);
    for (int vertex = 0; vertex < EDGE_COUNT; ++vertex)
        std::cin >> first_edge[vertex] >> second_edge[vertex];

    std::vector<std::vector<U32>> low_by_weight(19), high_by_weight(20);
    for (U32 mask = 0; mask < (U32{1} << 18); ++mask)
        low_by_weight[__popcnt(mask)].push_back(mask);
    for (U32 mask = 0; mask < (U32{1} << 19); ++mask)
        high_by_weight[__popcnt(mask)].push_back(mask);

    int* device_first = nullptr;
    int* device_second = nullptr;
    U64* device_defects = nullptr;
    unsigned long long* device_shapes = nullptr;
    unsigned long long* device_hits = nullptr;
    check(cudaMalloc(&device_first, EDGE_COUNT * sizeof(int)), "cudaMalloc first");
    check(cudaMalloc(&device_second, EDGE_COUNT * sizeof(int)), "cudaMalloc second");
    check(cudaMalloc(&device_defects, defects.size() * sizeof(U64)), "cudaMalloc defects");
    check(cudaMalloc(&device_shapes, BIN_COUNT * sizeof(unsigned long long)), "cudaMalloc shapes");
    check(cudaMalloc(&device_hits, BIN_COUNT * sizeof(unsigned long long)), "cudaMalloc hits");
    check(cudaMemcpy(
        device_first, first_edge.data(), EDGE_COUNT * sizeof(int),
        cudaMemcpyHostToDevice
    ), "copy first");
    check(cudaMemcpy(
        device_second, second_edge.data(), EDGE_COUNT * sizeof(int),
        cudaMemcpyHostToDevice
    ), "copy second");
    check(cudaMemcpy(
        device_defects, defects.data(), defects.size() * sizeof(U64),
        cudaMemcpyHostToDevice
    ), "copy defects");
    check(cudaMemset(
        device_shapes, 0, BIN_COUNT * sizeof(unsigned long long)
    ), "clear shapes");
    check(cudaMemset(
        device_hits, 0, BIN_COUNT * sizeof(unsigned long long)
    ), "clear hits");

    auto started = std::chrono::steady_clock::now();
    for (int low_weight = 0; low_weight <= 18; ++low_weight) {
        int high_weight = k - low_weight;
        if (high_weight < 0 || high_weight > 19) continue;
        const auto& low = low_by_weight[low_weight];
        const auto& high = high_by_weight[high_weight];
        if (low.empty() || high.empty()) continue;
        U32* device_low = nullptr;
        U32* device_high = nullptr;
        check(cudaMalloc(&device_low, low.size() * sizeof(U32)), "cudaMalloc low");
        check(cudaMalloc(&device_high, high.size() * sizeof(U32)), "cudaMalloc high");
        check(cudaMemcpy(
            device_low, low.data(), low.size() * sizeof(U32),
            cudaMemcpyHostToDevice
        ), "copy low");
        check(cudaMemcpy(
            device_high, high.data(), high.size() * sizeof(U32),
            cudaMemcpyHostToDevice
        ), "copy high");
        U64 total = static_cast<U64>(low.size()) * high.size();
        int blocks = static_cast<int>(std::min<U64>(
            65535, (total + 255) / 256
        ));
        count_masks<<<blocks, 256>>>(
            device_low,
            low.size(),
            device_high,
            high.size(),
            device_first,
            device_second,
            device_defects,
            defect_count,
            device_shapes,
            device_hits
        );
        check(cudaGetLastError(), "launch count_masks");
        check(cudaFree(device_low), "cudaFree low");
        check(cudaFree(device_high), "cudaFree high");
    }
    check(cudaDeviceSynchronize(), "synchronize");
    double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started
    ).count();

    std::vector<unsigned long long> shapes(BIN_COUNT), hits(BIN_COUNT);
    check(cudaMemcpy(
        shapes.data(), device_shapes, BIN_COUNT * sizeof(unsigned long long),
        cudaMemcpyDeviceToHost
    ), "copy shapes back");
    check(cudaMemcpy(
        hits.data(), device_hits, BIN_COUNT * sizeof(unsigned long long),
        cudaMemcpyDeviceToHost
    ), "copy hits back");

    std::cout << "{\n  \"k\": " << k << ",\n";
    std::cout << "  \"elapsed_s\": " << elapsed << ",\n";
    std::cout << "  \"shape_by_adjacency\": [";
    for (int bin = 0; bin < BIN_COUNT; ++bin) {
        if (bin) std::cout << ", ";
        std::cout << shapes[bin];
    }
    std::cout << "],\n  \"hit_by_adjacency\": [";
    for (int bin = 0; bin < BIN_COUNT; ++bin) {
        if (bin) std::cout << ", ";
        std::cout << hits[bin];
    }
    std::cout << "]\n}\n";

    cudaFree(device_first);
    cudaFree(device_second);
    cudaFree(device_defects);
    cudaFree(device_shapes);
    cudaFree(device_hits);
}
