#include <cuda.h>
#include <nvrtc.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using U32 = std::uint32_t;
using U64 = std::uint64_t;

constexpr int EDGE_COUNT = 37;
constexpr int BIN_COUNT = 38;

static void check_cuda(CUresult status, const char* action) {
    if (status == CUDA_SUCCESS) return;
    const char* text = nullptr;
    cuGetErrorString(status, &text);
    std::cerr << action << ": " << (text ? text : "CUDA error") << "\n";
    std::exit(2);
}

static void check_nvrtc(nvrtcResult status, const char* action) {
    if (status == NVRTC_SUCCESS) return;
    std::cerr << action << ": " << nvrtcGetErrorString(status) << "\n";
    std::exit(2);
}

static const char* KERNEL_SOURCE = R"cuda(
__device__ bool safe_cell(
    int id,
    unsigned long long removed,
    const unsigned char* exact_old,
    const int* blocker_offsets,
    const unsigned long long* blockers
) {
    if (exact_old[id]) return false;
    for (int at = blocker_offsets[id]; at < blocker_offsets[id + 1]; ++at)
        if ((removed & blockers[at]) == 0) return false;
    return true;
}

extern "C" __global__ void count_masks(
    const unsigned int* low_masks,
    unsigned long long low_count,
    const unsigned int* high_masks,
    unsigned long long high_count,
    const int* first_edge,
    const int* second_edge,
    const unsigned long long* defects,
    int defect_count,
    const unsigned char* exact_old,
    const int* blocker_offsets,
    const unsigned long long* blockers,
    unsigned long long* shape_by_adjacency,
    unsigned long long* hit_by_adjacency,
    unsigned long long* root_by_adjacency,
    unsigned long long* survivor_count,
    unsigned long long* survivor_masks,
    unsigned long long survivor_capacity
) {
    __shared__ unsigned long long local_shapes[38];
    __shared__ unsigned long long local_hits[38];
    __shared__ unsigned long long local_roots[38];
    for (int bin = threadIdx.x; bin < 38; bin += blockDim.x) {
        local_shapes[bin] = 0;
        local_hits[bin] = 0;
        local_roots[bin] = 0;
    }
    __syncthreads();
    const unsigned long long total = low_count * high_count;
    for (
        unsigned long long index =
            (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
        index < total;
        index += (unsigned long long)gridDim.x * blockDim.x
    ) {
        unsigned long long removed =
            (unsigned long long)low_masks[index / high_count]
            | ((unsigned long long)high_masks[index % high_count] << 18);
        int adjacency = 0;
        #pragma unroll
        for (int vertex = 0; vertex < 37; ++vertex) {
            unsigned long long first = 1ULL << first_edge[vertex];
            unsigned long long second = 1ULL << second_edge[vertex];
            adjacency += ((removed & first) != 0) && ((removed & second) != 0);
        }
        bool hits = true;
        for (int defect = 0; defect < defect_count; ++defect) {
            if ((removed & defects[defect]) == 0) {
                hits = false;
                break;
            }
        }
        atomicAdd(&local_shapes[adjacency], 1ULL);
        if (!hits) continue;
        atomicAdd(&local_hits[adjacency], 1ULL);

        unsigned char deficit[37];
        #pragma unroll
        for (int vertex = 0; vertex < 37; ++vertex) {
            int first = first_edge[vertex];
            int second = second_edge[vertex];
            deficit[vertex] =
                ((removed >> first) & 1ULL) + ((removed >> second) & 1ULL);
        }
        bool root_nonzero = true;
        for (int u = 0; u < 37 && root_nonzero; ++u) {
            if (deficit[u] == 0) continue;
            bool has_option = false;
            if (
                deficit[u] == 2
                && safe_cell(
                    u * 37 + u, removed, exact_old,
                    blocker_offsets, blockers
                )
            ) {
                has_option = true;
            } else {
                int first_other = -1;
                for (int v = 0; v < 37 && !has_option; ++v) {
                    if (v == u || deficit[v] == 0) continue;
                    int ids[2] = {u * 37 + v, v * 37 + u};
                    #pragma unroll
                    for (int orientation = 0; orientation < 2; ++orientation) {
                        if (!safe_cell(
                            ids[orientation], removed, exact_old,
                            blocker_offsets, blockers
                        )) continue;
                        if (deficit[u] == 1) {
                            has_option = true;
                            break;
                        }
                        if (first_other < 0) {
                            first_other = v;
                        } else if (v != first_other || deficit[v] >= 2) {
                            has_option = true;
                            break;
                        }
                    }
                }
            }
            if (!has_option) root_nonzero = false;
        }
        if (root_nonzero) {
            atomicAdd(&local_roots[adjacency], 1ULL);
            unsigned long long position = atomicAdd(survivor_count, 1ULL);
            if (position < survivor_capacity) survivor_masks[position] = removed;
        }
    }
    __syncthreads();
    for (int bin = threadIdx.x; bin < 38; bin += blockDim.x) {
        atomicAdd(&shape_by_adjacency[bin], local_shapes[bin]);
        atomicAdd(&hit_by_adjacency[bin], local_hits[bin]);
        atomicAdd(&root_by_adjacency[bin], local_roots[bin]);
    }
}
)cuda";

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
    std::vector<unsigned char> exact_old(EDGE_COUNT * EDGE_COUNT);
    std::vector<int> blocker_offsets(EDGE_COUNT * EDGE_COUNT + 1);
    std::vector<U64> blockers;
    for (int id = 0; id < EDGE_COUNT * EDGE_COUNT; ++id) {
        int exact, count;
        std::cin >> exact >> count;
        exact_old[id] = exact != 0;
        blocker_offsets[id] = static_cast<int>(blockers.size());
        while (count--) {
            U64 value;
            std::cin >> value;
            blockers.push_back(value);
        }
    }
    blocker_offsets.back() = static_cast<int>(blockers.size());

    nvrtcProgram program;
    check_nvrtc(
        nvrtcCreateProgram(
            &program, KERNEL_SOURCE, "mask_prefilter.cu", 0, nullptr, nullptr
        ),
        "nvrtcCreateProgram"
    );
    const char* options[] = {
        "--gpu-architecture=compute_89",
        "--std=c++17",
        "--use_fast_math",
    };
    nvrtcResult compile_status = nvrtcCompileProgram(program, 3, options);
    std::size_t log_size = 0;
    nvrtcGetProgramLogSize(program, &log_size);
    if (log_size > 1) {
        std::string log(log_size, '\0');
        nvrtcGetProgramLog(program, log.data());
        std::cerr << log;
    }
    check_nvrtc(compile_status, "nvrtcCompileProgram");
    std::size_t ptx_size = 0;
    check_nvrtc(nvrtcGetPTXSize(program, &ptx_size), "nvrtcGetPTXSize");
    std::string ptx(ptx_size, '\0');
    check_nvrtc(nvrtcGetPTX(program, ptx.data()), "nvrtcGetPTX");
    nvrtcDestroyProgram(&program);

    check_cuda(cuInit(0), "cuInit");
    CUdevice device;
    check_cuda(cuDeviceGet(&device, 0), "cuDeviceGet");
    CUcontext context;
    check_cuda(cuCtxCreate(&context, nullptr, 0, device), "cuCtxCreate");
    CUmodule module;
    check_cuda(cuModuleLoadData(&module, ptx.data()), "cuModuleLoadData");
    CUfunction kernel;
    check_cuda(
        cuModuleGetFunction(&kernel, module, "count_masks"),
        "cuModuleGetFunction"
    );

    std::vector<std::vector<U32>> low_by_weight(19), high_by_weight(20);
    for (U32 mask = 0; mask < (U32{1} << 18); ++mask)
        low_by_weight[__builtin_popcount(mask)].push_back(mask);
    for (U32 mask = 0; mask < (U32{1} << 19); ++mask)
        high_by_weight[__builtin_popcount(mask)].push_back(mask);

    CUdeviceptr device_first, device_second, device_defects;
    CUdeviceptr device_exact, device_offsets, device_blockers;
    CUdeviceptr device_shapes, device_hits, device_roots;
    CUdeviceptr device_survivor_count, device_survivors;
    // k=14 raises per-basin root candidates far above the original 1M cap.
    // RTX 4070 (12 GB) holds this comfortably. Completeness flag stays valid
    // as long as the true survivor count does not exceed this capacity.
    constexpr U64 SURVIVOR_CAPACITY = 300'000'000;
    check_cuda(
        cuMemAlloc(&device_first, EDGE_COUNT * sizeof(int)), "cuMemAlloc first"
    );
    check_cuda(
        cuMemAlloc(&device_second, EDGE_COUNT * sizeof(int)), "cuMemAlloc second"
    );
    check_cuda(
        cuMemAlloc(&device_defects, defects.size() * sizeof(U64)),
        "cuMemAlloc defects"
    );
    check_cuda(
        cuMemAlloc(&device_exact, exact_old.size()), "cuMemAlloc exact"
    );
    check_cuda(
        cuMemAlloc(&device_offsets, blocker_offsets.size() * sizeof(int)),
        "cuMemAlloc offsets"
    );
    check_cuda(
        cuMemAlloc(&device_blockers, blockers.size() * sizeof(U64)),
        "cuMemAlloc blockers"
    );
    check_cuda(
        cuMemAlloc(&device_shapes, BIN_COUNT * sizeof(U64)), "cuMemAlloc shapes"
    );
    check_cuda(
        cuMemAlloc(&device_hits, BIN_COUNT * sizeof(U64)), "cuMemAlloc hits"
    );
    check_cuda(
        cuMemAlloc(&device_roots, BIN_COUNT * sizeof(U64)), "cuMemAlloc roots"
    );
    check_cuda(
        cuMemAlloc(&device_survivor_count, sizeof(U64)),
        "cuMemAlloc survivor count"
    );
    check_cuda(
        cuMemAlloc(&device_survivors, SURVIVOR_CAPACITY * sizeof(U64)),
        "cuMemAlloc survivors"
    );
    check_cuda(
        cuMemcpyHtoD(
            device_first, first_edge.data(), EDGE_COUNT * sizeof(int)
        ),
        "copy first"
    );
    check_cuda(
        cuMemcpyHtoD(
            device_second, second_edge.data(), EDGE_COUNT * sizeof(int)
        ),
        "copy second"
    );
    check_cuda(
        cuMemcpyHtoD(
            device_defects, defects.data(), defects.size() * sizeof(U64)
        ),
        "copy defects"
    );
    check_cuda(
        cuMemcpyHtoD(device_exact, exact_old.data(), exact_old.size()),
        "copy exact"
    );
    check_cuda(
        cuMemcpyHtoD(
            device_offsets,
            blocker_offsets.data(),
            blocker_offsets.size() * sizeof(int)
        ),
        "copy offsets"
    );
    check_cuda(
        cuMemcpyHtoD(
            device_blockers, blockers.data(), blockers.size() * sizeof(U64)
        ),
        "copy blockers"
    );
    check_cuda(cuMemsetD8(device_shapes, 0, BIN_COUNT * sizeof(U64)), "clear shapes");
    check_cuda(cuMemsetD8(device_hits, 0, BIN_COUNT * sizeof(U64)), "clear hits");
    check_cuda(cuMemsetD8(device_roots, 0, BIN_COUNT * sizeof(U64)), "clear roots");
    check_cuda(cuMemsetD8(device_survivor_count, 0, sizeof(U64)), "clear survivor count");

    auto started = std::chrono::steady_clock::now();
    for (int low_weight = 0; low_weight <= 18; ++low_weight) {
        int high_weight = k - low_weight;
        if (high_weight < 0 || high_weight > 19) continue;
        const auto& low = low_by_weight[low_weight];
        const auto& high = high_by_weight[high_weight];
        if (low.empty() || high.empty()) continue;
        CUdeviceptr device_low, device_high;
        check_cuda(
            cuMemAlloc(&device_low, low.size() * sizeof(U32)), "cuMemAlloc low"
        );
        check_cuda(
            cuMemAlloc(&device_high, high.size() * sizeof(U32)), "cuMemAlloc high"
        );
        check_cuda(
            cuMemcpyHtoD(device_low, low.data(), low.size() * sizeof(U32)),
            "copy low"
        );
        check_cuda(
            cuMemcpyHtoD(device_high, high.data(), high.size() * sizeof(U32)),
            "copy high"
        );
        U64 low_count = low.size();
        U64 high_count = high.size();
        U64 survivor_capacity = SURVIVOR_CAPACITY;
        U64 total = low_count * high_count;
        unsigned int blocks = static_cast<unsigned int>(
            std::min<U64>(65535, (total + 255) / 256)
        );
        void* arguments[] = {
            &device_low,
            &low_count,
            &device_high,
            &high_count,
            &device_first,
            &device_second,
            &device_defects,
            &defect_count,
            &device_exact,
            &device_offsets,
            &device_blockers,
            &device_shapes,
            &device_hits,
            &device_roots,
            &device_survivor_count,
            &device_survivors,
            &survivor_capacity,
        };
        check_cuda(
            cuLaunchKernel(
                kernel,
                blocks, 1, 1,
                256, 1, 1,
                0, nullptr,
                arguments, nullptr
            ),
            "cuLaunchKernel"
        );
        check_cuda(cuMemFree(device_low), "cuMemFree low");
        check_cuda(cuMemFree(device_high), "cuMemFree high");
    }
    check_cuda(cuCtxSynchronize(), "cuCtxSynchronize");
    double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started
    ).count();

    std::vector<U64> shapes(BIN_COUNT), hits(BIN_COUNT), roots(BIN_COUNT);
    U64 survivor_count = 0;
    check_cuda(
        cuMemcpyDtoH(
            shapes.data(), device_shapes, BIN_COUNT * sizeof(U64)
        ),
        "copy shapes back"
    );
    check_cuda(
        cuMemcpyDtoH(hits.data(), device_hits, BIN_COUNT * sizeof(U64)),
        "copy hits back"
    );
    check_cuda(
        cuMemcpyDtoH(roots.data(), device_roots, BIN_COUNT * sizeof(U64)),
        "copy roots back"
    );
    check_cuda(
        cuMemcpyDtoH(&survivor_count, device_survivor_count, sizeof(U64)),
        "copy survivor count back"
    );
    std::vector<U64> survivors(std::min(survivor_count, SURVIVOR_CAPACITY));
    if (!survivors.empty()) {
        check_cuda(
            cuMemcpyDtoH(
                survivors.data(),
                device_survivors,
                survivors.size() * sizeof(U64)
            ),
            "copy survivors back"
        );
        std::sort(survivors.begin(), survivors.end());
    }

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
    std::cout << "],\n  \"root_nonzero_by_adjacency\": [";
    for (int bin = 0; bin < BIN_COUNT; ++bin) {
        if (bin) std::cout << ", ";
        std::cout << roots[bin];
    }
    std::cout << "],\n  \"root_nonzero_count\": " << survivor_count << ",\n";
    bool count_only = std::getenv("V20_COUNT_ONLY") != nullptr;
    std::cout << "  \"survivor_masks_complete\": "
              << (survivor_count <= SURVIVOR_CAPACITY ? "true" : "false")
              << ",\n  \"survivor_masks\": [";
    if (!count_only) {
        for (std::size_t index = 0; index < survivors.size(); ++index) {
            if (index) std::cout << ", ";
            std::cout << survivors[index];
        }
    }
    std::cout << "]\n}\n";

    cuMemFree(device_first);
    cuMemFree(device_second);
    cuMemFree(device_defects);
    cuMemFree(device_exact);
    cuMemFree(device_offsets);
    cuMemFree(device_blockers);
    cuMemFree(device_shapes);
    cuMemFree(device_hits);
    cuMemFree(device_roots);
    cuMemFree(device_survivor_count);
    cuMemFree(device_survivors);
    cuModuleUnload(module);
    cuCtxDestroy(context);
}
