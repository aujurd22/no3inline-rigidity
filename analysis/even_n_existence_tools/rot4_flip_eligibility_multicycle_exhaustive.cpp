#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <tuple>
#include <vector>

using U64 = std::uint64_t;
using Profile = std::tuple<int, int, int>;

static void positive_compositions(
    int total, int parts, std::vector<int>& current,
    const std::function<void(const std::vector<int>&)>& visit
) {
    if (parts == 1) {
        if (total >= 1) {
            current.push_back(total);
            visit(current);
            current.pop_back();
        }
        return;
    }
    for (int first = 1; first <= total - (parts - 1); ++first) {
        current.push_back(first);
        positive_compositions(total - first, parts - 1, current, visit);
        current.pop_back();
    }
}

static std::vector<U64> local_masks(
    const std::vector<int>& order, Profile profile
) {
    auto [n1, n2, n3] = profile;
    const int run_count = n1 + n2 + n3;
    if (run_count == 0) return {U64{0}};
    std::vector<int> runs;
    runs.insert(runs.end(), n1, 1);
    runs.insert(runs.end(), n2, 2);
    runs.insert(runs.end(), n3, 3);
    const int selected = n1 + 2 * n2 + 3 * n3;
    const int gap_total = static_cast<int>(order.size()) - selected;
    if (gap_total < run_count) return {};

    std::vector<U64> result;
    do {
        std::vector<int> gaps;
        positive_compositions(
            gap_total, run_count, gaps,
            [&](const std::vector<int>& composition) {
                for (int start = 0; start < static_cast<int>(order.size()); ++start) {
                    std::vector<int> starts(run_count);
                    int position = start;
                    for (int i = 0; i < run_count; ++i) {
                        starts[i] = position;
                        position = (
                            position + runs[i] + composition[i]
                        ) % static_cast<int>(order.size());
                    }
                    if (*std::min_element(starts.begin(), starts.end()) != start) {
                        continue;
                    }
                    U64 mask = 0;
                    for (int i = 0; i < run_count; ++i) {
                        for (int offset = 0; offset < runs[i]; ++offset) {
                            int position_index = (
                                starts[i] + offset
                            ) % static_cast<int>(order.size());
                            mask |= U64{1} << order[position_index];
                        }
                    }
                    result.push_back(mask);
                }
            }
        );
    } while (std::next_permutation(runs.begin(), runs.end()));
    std::sort(result.begin(), result.end());
    auto unique_end = std::unique(result.begin(), result.end());
    if (unique_end != result.end()) {
        std::cerr << "local generator produced duplicate masks\n";
        std::exit(3);
    }
    return result;
}

static void weak_compositions(
    int total, int parts, std::vector<int>& current,
    const std::function<void(const std::vector<int>&)>& visit
) {
    if (parts == 1) {
        current.push_back(total);
        visit(current);
        current.pop_back();
        return;
    }
    for (int first = 0; first <= total; ++first) {
        current.push_back(first);
        weak_compositions(total - first, parts - 1, current, visit);
        current.pop_back();
    }
}

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int component_count = 0;
    if (!(std::cin >> component_count) || component_count <= 0) return 2;
    std::vector<std::vector<int>> components(component_count);
    int total_edges = 0;
    for (auto& order : components) {
        int length = 0;
        std::cin >> length;
        total_edges += length;
        order.resize(length);
        for (int& value : order) std::cin >> value;
    }
    if (total_edges != 37) {
        std::cerr << "factor components must contain 37 edges\n";
        return 2;
    }

    int defect_count = 0;
    std::cin >> defect_count;
    std::vector<U64> defects(defect_count);
    for (U64& mask : defects) std::cin >> mask;
    std::array<std::vector<U64>, 37> flip_blockers;
    for (int edge = 0; edge < 37; ++edge) {
        int count = 0;
        std::cin >> count;
        flip_blockers[edge].resize(count);
        for (U64& mask : flip_blockers[edge]) std::cin >> mask;
    }

    std::vector<std::map<Profile, std::vector<U64>>> cache(component_count);
    auto fetch = [&](int component, Profile profile) -> const std::vector<U64>& {
        auto& table = cache[component];
        auto found = table.find(profile);
        if (found == table.end()) {
            found = table.emplace(
                profile, local_masks(components[component], profile)
            ).first;
        }
        return found->second;
    };

    U64 distinct_shape_masks = 0;
    U64 defect_hitting_masks = 0;
    std::array<U64, 13> histogram{};
    int maximum = -1;
    U64 witness = 0;

    std::vector<int> allocation1, allocation2, allocation3;
    weak_compositions(1, component_count, allocation1, [&](const auto& ones) {
        allocation1 = ones;
        weak_compositions(4, component_count, allocation2, [&](const auto& twos) {
            allocation2 = twos;
            weak_compositions(1, component_count, allocation3, [&](const auto& threes) {
                allocation3 = threes;
                std::vector<const std::vector<U64>*> lists;
                for (int i = 0; i < component_count; ++i) {
                    const auto& values = fetch(
                        i, Profile{ones[i], twos[i], threes[i]}
                    );
                    if (values.empty()) return;
                    lists.push_back(&values);
                }
                std::function<void(int, U64)> combine = [&](int index, U64 mask) {
                    if (index != component_count) {
                        for (U64 local : *lists[index]) {
                            combine(index + 1, mask | local);
                        }
                        return;
                    }
                    ++distinct_shape_masks;
                    bool hits = true;
                    for (U64 defect : defects) {
                        if ((mask & defect) == 0) {
                            hits = false;
                            break;
                        }
                    }
                    if (!hits) return;
                    ++defect_hitting_masks;
                    int eligible = 0;
                    for (int edge = 0; edge < 37; ++edge) {
                        if ((mask & (U64{1} << edge)) == 0) continue;
                        bool safe = true;
                        for (U64 blocker : flip_blockers[edge]) {
                            if ((mask & blocker) == 0) {
                                safe = false;
                                break;
                            }
                        }
                        eligible += safe;
                    }
                    ++histogram[eligible];
                    if (eligible > maximum) {
                        maximum = eligible;
                        witness = mask;
                    }
                };
                combine(0, 0);
            });
        });
    });

    std::cout << "{\n";
    std::cout << "  \"component_count\": " << component_count << ",\n";
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
}
