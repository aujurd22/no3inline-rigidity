#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using U64 = std::uint64_t;

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int length = 0;
    if (!(std::cin >> length) || length != 37) {
        std::cerr << "expected one cycle of length 37\n";
        return 2;
    }
    std::vector<int> cycle_order(length);
    for (int &value : cycle_order) std::cin >> value;

    int defect_count = 0;
    std::cin >> defect_count;
    std::vector<U64> defects(defect_count);
    for (U64 &mask : defects) std::cin >> mask;

    std::array<std::vector<U64>, 37> flip_blockers;
    for (int edge = 0; edge < 37; ++edge) {
        int count = 0;
        std::cin >> count;
        flip_blockers[edge].resize(count);
        for (U64 &mask : flip_blockers[edge]) std::cin >> mask;
    }

    // A=6, B=1, C=0 on one 37-cycle forces run lengths
    // {1,2,2,2,2,3}; the six positive gaps sum to 25.
    std::array<int, 6> runs{1, 2, 2, 2, 2, 3};
    std::array<U64, 13> histogram{};
    U64 generated_representations = 0;
    U64 distinct_shape_masks = 0;
    U64 defect_hitting_masks = 0;
    int maximum = -1;
    U64 witness = 0;

    do {
        // Enumerate positive compositions of 25 into six parts by five cuts.
        for (int c1 = 1; c1 <= 20; ++c1)
        for (int c2 = c1 + 1; c2 <= 21; ++c2)
        for (int c3 = c2 + 1; c3 <= 22; ++c3)
        for (int c4 = c3 + 1; c4 <= 23; ++c4)
        for (int c5 = c4 + 1; c5 <= 24; ++c5) {
            const std::array<int, 6> gaps{
                c1, c2 - c1, c3 - c2, c4 - c3, c5 - c4, 25 - c5
            };
            for (int start = 0; start < length; ++start) {
                ++generated_representations;
                std::array<int, 6> starts{};
                int position = start;
                for (int i = 0; i < 6; ++i) {
                    starts[i] = position;
                    position = (position + runs[i] + gaps[i]) % length;
                }
                if (*std::min_element(starts.begin(), starts.end()) != start) {
                    continue;
                }

                U64 removed = 0;
                for (int i = 0; i < 6; ++i) {
                    for (int offset = 0; offset < runs[i]; ++offset) {
                        int cycle_position = (starts[i] + offset) % length;
                        removed |= U64{1} << cycle_order[cycle_position];
                    }
                }
                if (__builtin_popcountll(removed) != 12) {
                    std::cerr << "invalid generated mask\n";
                    return 3;
                }
                ++distinct_shape_masks;

                bool hits = true;
                for (U64 defect : defects) {
                    if ((removed & defect) == 0) {
                        hits = false;
                        break;
                    }
                }
                if (!hits) continue;
                ++defect_hitting_masks;

                int eligible = 0;
                for (int edge = 0; edge < 37; ++edge) {
                    if ((removed & (U64{1} << edge)) == 0) continue;
                    bool safe = true;
                    for (U64 blocker : flip_blockers[edge]) {
                        if ((removed & blocker) == 0) {
                            safe = false;
                            break;
                        }
                    }
                    eligible += safe;
                }
                ++histogram[eligible];
                if (eligible > maximum) {
                    maximum = eligible;
                    witness = removed;
                }
            }
        }
    } while (std::next_permutation(runs.begin(), runs.end()));

    std::cout << "{\n";
    std::cout << "  \"generated_representations\": "
              << generated_representations << ",\n";
    std::cout << "  \"distinct_shape_masks\": " << distinct_shape_masks << ",\n";
    std::cout << "  \"defect_hitting_masks\": " << defect_hitting_masks << ",\n";
    std::cout << "  \"maximum_eligible_flips\": " << maximum << ",\n";
    std::cout << "  \"witness_mask\": " << witness << ",\n";
    std::cout << "  \"eligibility_histogram\": {";
    bool first = true;
    for (int value = 0; value <= 12; ++value) {
        if (histogram[value] == 0) continue;
        if (!first) std::cout << ", ";
        first = false;
        std::cout << "\"" << value << "\": " << histogram[value];
    }
    std::cout << "}\n}\n";
    return 0;
}
