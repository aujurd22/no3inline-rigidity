#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <tuple>
#include <unordered_set>
#include <vector>

using U64 = std::uint64_t;
using Profile = std::array<int, 13>;

struct Cell {
    int u;
    int v;
    int id;
};

static std::array<std::vector<Cell>, 37> allowed_incident;
static std::unordered_set<U64> failed_states;
static std::vector<int> current_cells;
static std::vector<int> witness_cells;
static U64 current_nodes = 0;
static std::vector<std::vector<std::pair<int, int>>> line_terms(37 * 37);
static std::vector<int> line_remaining;

// --- All-completions additions --- //
// Per-mask state: all completions found for the current mask
static std::vector<std::vector<int>> current_mask_completions;
// Dedup: sorted(current_cells) -> count (so we can report if needed)
static std::set<std::vector<int>> dedup_set;
static bool current_truncated = false;
static constexpr U64 MAX_COMPLETIONS_PER_MASK = 500000;
static constexpr U64 MAX_NODES_PER_MASK = 100000000;
// --- End additions --- //

static bool cell_fits(int id) {
    for (auto [line, count] : line_terms[id])
        if (line_remaining[line] < count) return false;
    return true;
}

static void adjust_cell(int id, int sign) {
    for (auto [line, count] : line_terms[id])
        line_remaining[line] += sign * count;
}

static U64 encode_state(const std::array<int, 37>& deficit) {
    U64 code = 0;
    U64 place = 1;
    for (int value : deficit) {
        code += place * static_cast<U64>(value);
        place *= 3;
    }
    return code;
}

static std::vector<Cell> usable_nonloops(
    int u, const std::array<int, 37>& deficit
) {
    std::vector<Cell> result;
    for (const Cell& cell : allowed_incident[u]) {
        if (cell.u == cell.v) continue;
        if (!cell_fits(cell.id)) continue;
        int other = cell.u == u ? cell.v : cell.u;
        if (deficit[other] > 0) result.push_back(cell);
    }
    return result;
}

static U64 option_count(int u, const std::array<int, 37>& deficit) {
    if (deficit[u] == 1) {
        return usable_nonloops(u, deficit).size();
    }
    U64 count = 0;
    for (const Cell& cell : allowed_incident[u]) {
        if (cell.u == u && cell.v == u && cell_fits(cell.id)) ++count;
    }
    auto cells = usable_nonloops(u, deficit);
    for (std::size_t i = 0; i < cells.size(); ++i) {
        int first = cells[i].u == u ? cells[i].v : cells[i].u;
        for (std::size_t j = i + 1; j < cells.size(); ++j) {
            int second = cells[j].u == u ? cells[j].v : cells[j].u;
            if (first != second || deficit[first] >= 2) ++count;
        }
    }
    return count;
}

// MODIFIED: save all completions, return false always (continue search)
static void factor_dfs_all(std::array<int, 37>& deficit) {
    ++current_nodes;
    if (current_nodes > MAX_NODES_PER_MASK) return;  // node cap
    if (current_mask_completions.size() >= MAX_COMPLETIONS_PER_MASK) return;  // completion cap

    U64 state = encode_state(deficit);
    if (state == 0) {
        // Found a completion — save it
        std::vector<int> comp = current_cells;
        std::sort(comp.begin(), comp.end());
        if (dedup_set.insert(comp).second) {
            current_mask_completions.push_back(current_cells);
        }
        return;  // continue search
    }
    if (line_remaining.empty() && failed_states.count(state)) return;

    int chosen = -1;
    U64 best_count = ~U64{0};
    for (int u = 0; u < 37; ++u) {
        if (deficit[u] == 0) continue;
        U64 count = option_count(u, deficit);
        if (count < best_count) {
            best_count = count;
            chosen = u;
        }
        if (count == 0) break;
    }
    if (chosen < 0) return;
    if (best_count == 0) {
        if (line_remaining.empty()) failed_states.insert(state);
        return;
    }

    const int need = deficit[chosen];
    if (need == 1) {
        for (const Cell& cell : usable_nonloops(chosen, deficit)) {
            int other = cell.u == chosen ? cell.v : cell.u;
            deficit[chosen] = 0;
            --deficit[other];
            current_cells.push_back(cell.id);
            adjust_cell(cell.id, -1);
            factor_dfs_all(deficit);
            adjust_cell(cell.id, 1);
            current_cells.pop_back();
            ++deficit[other];
            deficit[chosen] = 1;
            if (current_nodes > MAX_NODES_PER_MASK) return;
            if (current_mask_completions.size() >= MAX_COMPLETIONS_PER_MASK) return;
        }
    } else {
        for (const Cell& cell : allowed_incident[chosen]) {
            if (cell.u != chosen || cell.v != chosen) continue;
            if (!cell_fits(cell.id)) continue;
            deficit[chosen] = 0;
            current_cells.push_back(cell.id);
            adjust_cell(cell.id, -1);
            factor_dfs_all(deficit);
            adjust_cell(cell.id, 1);
            current_cells.pop_back();
            deficit[chosen] = 2;
            if (current_nodes > MAX_NODES_PER_MASK) return;
            if (current_mask_completions.size() >= MAX_COMPLETIONS_PER_MASK) return;
        }
        auto cells = usable_nonloops(chosen, deficit);
        for (std::size_t i = 0; i < cells.size(); ++i) {
            int first = cells[i].u == chosen ? cells[i].v : cells[i].u;
            for (std::size_t j = i + 1; j < cells.size(); ++j) {
                int second = cells[j].u == chosen ? cells[j].v : cells[j].u;
                if (first == second && deficit[first] < 2) continue;
                adjust_cell(cells[i].id, -1);
                if (!cell_fits(cells[j].id)) {
                    adjust_cell(cells[i].id, 1);
                    continue;
                }
                adjust_cell(cells[j].id, -1);
                deficit[chosen] = 0;
                --deficit[first];
                --deficit[second];
                current_cells.push_back(cells[i].id);
                current_cells.push_back(cells[j].id);
                factor_dfs_all(deficit);
                adjust_cell(cells[j].id, 1);
                adjust_cell(cells[i].id, 1);
                current_cells.pop_back();
                current_cells.pop_back();
                ++deficit[first];
                ++deficit[second];
                deficit[chosen] = 2;
                if (current_nodes > MAX_NODES_PER_MASK) return;
                if (current_mask_completions.size() >= MAX_COMPLETIONS_PER_MASK) return;
            }
        }
    }
    if (line_remaining.empty()) failed_states.insert(state);
}

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
    const std::vector<int>& order, const Profile& profile
) {
    int run_count = 0;
    int selected = 0;
    std::vector<int> runs;
    for (int length = 1; length <= 12; ++length) {
        run_count += profile[length];
        selected += length * profile[length];
        runs.insert(runs.end(), profile[length], length);
    }
    if (run_count == 0) return {U64{0}};
    int gap_total = static_cast<int>(order.size()) - selected;
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
                        position = (position + runs[i] + composition[i])
                            % static_cast<int>(order.size());
                    }
                    if (*std::min_element(starts.begin(), starts.end()) != start)
                        continue;
                    U64 mask = 0;
                    for (int i = 0; i < run_count; ++i)
                        for (int offset = 0; offset < runs[i]; ++offset)
                            mask |= U64{1} << order[
                                (starts[i] + offset)
                                % static_cast<int>(order.size())
                            ];
                    result.push_back(mask);
                }
            }
        );
    } while (std::next_permutation(runs.begin(), runs.end()));
    std::sort(result.begin(), result.end());
    result.erase(std::unique(result.begin(), result.end()), result.end());
    return result;
}

static void integer_partitions(
    int total,
    int parts,
    int maximum,
    std::vector<int>& current,
    const std::function<void(const std::vector<int>&)>& visit
) {
    if (parts == 0) {
        if (total == 0) visit(current);
        return;
    }
    int upper = std::min(maximum, total - (parts - 1));
    for (int first = upper; first >= 1; --first) {
        current.push_back(first);
        integer_partitions(
            total - first, parts - 1, first, current, visit
        );
        current.pop_back();
    }
}

static std::vector<U64> local_masks_size_adjacency(
    const std::vector<int>& order, int selected, int adjacency
) {
    int length = static_cast<int>(order.size());
    if (selected == 0)
        return adjacency == 0 ? std::vector<U64>{U64{0}} : std::vector<U64>{};
    if (selected == length) {
        if (adjacency != length) return {};
        U64 mask = 0;
        for (int edge : order) mask |= U64{1} << edge;
        return {mask};
    }
    int run_count = selected - adjacency;
    if (run_count < 1 || run_count > selected || run_count > length - selected)
        return {};
    std::vector<U64> result;
    std::vector<int> current;
    integer_partitions(
        selected,
        run_count,
        selected,
        current,
        [&](const std::vector<int>& runs) {
            Profile profile{};
            for (int run : runs) ++profile[run];
            auto values = local_masks(order, profile);
            result.insert(result.end(), values.begin(), values.end());
        }
    );
    std::sort(result.begin(), result.end());
    result.erase(std::unique(result.begin(), result.end()), result.end());
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

    int component_count;
    if (!(std::cin >> component_count) || component_count <= 0) return 2;
    std::vector<std::vector<int>> components(component_count);
    int total_edges = 0;
    for (auto& order : components) {
        int length;
        std::cin >> length;
        total_edges += length;
        order.resize(length);
        for (int& value : order) std::cin >> value;
    }
    if (total_edges != 37) return 2;
    int enumeration_mode;
    std::cin >> enumeration_mode;
    Profile global_profile{};
    int global_run_count = 0;
    int target_selected = 0;
    int target_adjacency = -1;
    int required_full_cycle_length = -1;
    std::vector<U64> explicit_masks;
    if (enumeration_mode == 0) {
        for (int length = 1; length <= 12; ++length) {
            std::cin >> global_profile[length];
            global_run_count += global_profile[length];
            target_selected += length * global_profile[length];
        }
        if (global_run_count <= 0) return 2;
    } else if (enumeration_mode == 1 || enumeration_mode == 2) {
        std::cin >> target_selected >> target_adjacency;
        if (target_selected < 1 || target_selected > 12) return 2;
        if (target_adjacency < 0 || target_adjacency > target_selected) return 2;
        if (enumeration_mode == 2) {
            std::cin >> required_full_cycle_length;
            int matching_components = 0;
            for (const auto& component : components)
                matching_components += (
                    static_cast<int>(component.size())
                    == required_full_cycle_length
                );
            if (matching_components != 1) return 2;
        }
    } else if (enumeration_mode == 3) {
        U64 mask_count;
        std::cin >> target_selected >> mask_count;
        if (target_selected < 1 || target_selected > 37) return 2;
        explicit_masks.resize(mask_count);
        for (U64& mask : explicit_masks) {
            std::cin >> mask;
            if (__builtin_popcountll(mask) != target_selected) return 2;
        }
    } else {
        return 2;
    }

    std::array<std::pair<int, int>, 37> base_edges;
    std::array<int, 37> base_bits;
    std::array<bool, 37 * 37> exact_old{};
    for (int i = 0; i < 37; ++i) {
        std::cin >> base_edges[i].first >> base_edges[i].second >> base_bits[i];
        int u = base_edges[i].first, v = base_edges[i].second;
        if (base_bits[i]) std::swap(u, v);
        exact_old[u * 37 + v] = true;
    }

    int defect_count;
    std::cin >> defect_count;
    std::vector<U64> defects(defect_count);
    for (U64& value : defects) std::cin >> value;

    std::array<std::vector<U64>, 37 * 37> blockers;
    for (auto& values : blockers) {
        int count;
        std::cin >> count;
        values.resize(count);
        for (U64& value : values) std::cin >> value;
    }

    int line_capacity_count = 0;
    std::vector<std::array<int, 3>> line_keys;
    if (std::cin >> line_capacity_count) {
        if (line_capacity_count < 0) return 2;
        line_keys.resize(line_capacity_count);
        for (auto& key : line_keys)
            std::cin >> key[0] >> key[1] >> key[2];
    } else {
        std::cin.clear();
        line_capacity_count = 0;
    }
    std::vector<std::vector<int>> base_line_counts(
        37, std::vector<int>(line_capacity_count)
    );
    std::vector<int> old_line_totals(line_capacity_count);
    line_terms.assign(37 * 37, {});
    auto orbit_line_count = [](
        int u, int v, const std::array<int, 3>& key
    ) {
        int count = 0;
        int x = u, y = v;
        for (int rotation = 0; rotation < 4; ++rotation) {
            count += key[0] * x + key[1] * y == key[2];
            int next_x = 73 - y;
            y = x;
            x = next_x;
        }
        return count;
    };
    for (int id = 0; id < 37 * 37; ++id) {
        int u = id / 37, v = id % 37;
        for (int line = 0; line < line_capacity_count; ++line) {
            int count = orbit_line_count(u, v, line_keys[line]);
            if (count) line_terms[id].push_back({line, count});
        }
    }
    for (int edge = 0; edge < 37; ++edge) {
        int u = base_edges[edge].first, v = base_edges[edge].second;
        if (base_bits[edge]) std::swap(u, v);
        for (int line = 0; line < line_capacity_count; ++line) {
            int count = orbit_line_count(u, v, line_keys[line]);
            base_line_counts[edge][line] = count;
            old_line_totals[line] += count;
        }
    }

    std::vector<std::map<Profile, std::vector<U64>>> cache(component_count);
    auto fetch = [&](int component, Profile profile) -> const std::vector<U64>& {
        auto& table = cache[component];
        auto found = table.find(profile);
        if (found == table.end())
            found = table.emplace(
                profile, local_masks(components[component], profile)
            ).first;
        return found->second;
    };

    U64 distinct_shape_masks = 0;
    U64 defect_hitting_masks = 0;
    U64 factor_feasible_masks = 0;
    U64 total_factor_nodes = 0;
    U64 maximum_factor_nodes = 0;
    U64 first_feasible_mask = 0;
    std::vector<int> first_feasible_cells;
    std::vector<U64> feasible_masks;
    // v9w_all: collect ALL completions per mask, with truncated flag
    std::vector<std::pair<U64, std::vector<int>>> witness_factors;
    std::vector<U64> sample_hitting_masks;
    std::array<U64, 3> root_zero_option_by_deficit{};
    std::array<U64, 8> search_node_histogram{};
    // Per-mask output: completion count + truncated flag per mask
    struct MaskCompletionInfo {
        U64 mask;
        U64 completion_count;
        bool truncated;
    };
    std::vector<MaskCompletionInfo> mask_completion_info;

    auto test_mask = [&](U64 removed) {
        ++distinct_shape_masks;
        for (U64 defect : defects)
            if ((removed & defect) == 0) return;
        ++defect_hitting_masks;
        if (sample_hitting_masks.size() < 10)
            sample_hitting_masks.push_back(removed);

        line_remaining.assign(line_capacity_count, 0);
        for (int line = 0; line < line_capacity_count; ++line)
            line_remaining[line] = 2 - old_line_totals[line];
        for (int edge = 0; edge < 37; ++edge) {
            if ((removed & (U64{1} << edge)) == 0) continue;
            for (int line = 0; line < line_capacity_count; ++line)
                line_remaining[line] += base_line_counts[edge][line];
        }
        if (std::any_of(
            line_remaining.begin(), line_remaining.end(),
            [](int value) { return value < 0; }
        )) return;

        std::array<int, 37> deficit{};
        for (int edge = 0; edge < 37; ++edge) {
            if ((removed & (U64{1} << edge)) == 0) continue;
            ++deficit[base_edges[edge].first];
            ++deficit[base_edges[edge].second];
        }
        for (auto& values : allowed_incident) values.clear();
        for (int u = 0; u < 37; ++u) {
            if (deficit[u] == 0) continue;
            for (int v = 0; v < 37; ++v) {
                if (deficit[v] == 0) continue;
                if (u == v && deficit[u] < 2) continue;
                int id = u * 37 + v;
                if (exact_old[id]) continue;
                bool safe = true;
                for (U64 blocker : blockers[id]) {
                    if ((removed & blocker) == 0) {
                        safe = false;
                        break;
                    }
                }
                if (!safe) continue;
                if (!cell_fits(id)) continue;
                Cell cell{u, v, id};
                allowed_incident[u].push_back(cell);
                if (u != v) allowed_incident[v].push_back(cell);
            }
        }
        failed_states.clear();
        current_cells.clear();
        witness_cells.clear();
        current_nodes = 0;
        current_mask_completions.clear();
        dedup_set.clear();
        current_truncated = false;

        int root_vertex = -1;
        U64 root_options = ~U64{0};
        for (int u = 0; u < 37; ++u) {
            if (deficit[u] == 0) continue;
            U64 count = option_count(u, deficit);
            if (count < root_options) {
                root_options = count;
                root_vertex = u;
            }
        }
        if (root_options == 0 && root_vertex >= 0)
            ++root_zero_option_by_deficit[deficit[root_vertex]];

        factor_dfs_all(deficit);

        // After full search, check caps
        if (current_nodes > MAX_NODES_PER_MASK) {
            current_truncated = true;
        }
        if (current_mask_completions.size() >= MAX_COMPLETIONS_PER_MASK) {
            current_truncated = true;
        }

        total_factor_nodes += current_nodes;
        maximum_factor_nodes = std::max(maximum_factor_nodes, current_nodes);
        ++search_node_histogram[std::min<U64>(
            current_nodes, search_node_histogram.size() - 1
        )];

        bool feasible = !current_mask_completions.empty();
        if (feasible) {
            ++factor_feasible_masks;
            if (
                enumeration_mode == 3
                || feasible_masks.size() < 1000
            )
                feasible_masks.push_back(removed);
            if (first_feasible_cells.empty()) {
                first_feasible_mask = removed;
                // For first_feasible_cells, just take the first completion
                witness_cells = current_mask_completions.front();
                first_feasible_cells = witness_cells;
            }
            if (enumeration_mode == 3) {
                for (auto& cells : current_mask_completions) {
                    witness_factors.emplace_back(removed, cells);
                }
            }
        }

        mask_completion_info.push_back({
            removed,
            static_cast<U64>(current_mask_completions.size()),
            current_truncated
        });

        if (defect_hitting_masks % 10000 == 0)
            std::cerr << "hit=" << defect_hitting_masks
                      << " feasible=" << factor_feasible_masks
                      << " nodes=" << total_factor_nodes << "\n";
    };

    if (enumeration_mode == 0) {
        std::vector<Profile> component_profiles(component_count);
        std::function<void(int)> allocate_length = [&](int length) {
            if (length <= 12) {
                std::vector<int> allocation;
                weak_compositions(
                    global_profile[length],
                    component_count,
                    allocation,
                    [&](const std::vector<int>& values) {
                        for (int i = 0; i < component_count; ++i)
                            component_profiles[i][length] = values[i];
                        allocate_length(length + 1);
                    }
                );
                return;
            }
            std::vector<const std::vector<U64>*> lists;
            for (int i = 0; i < component_count; ++i) {
                const auto& values = fetch(i, component_profiles[i]);
                if (values.empty()) return;
                lists.push_back(&values);
            }
            std::function<void(int, U64)> combine = [&](int index, U64 mask) {
                if (index < component_count) {
                    for (U64 local : *lists[index])
                        combine(index + 1, mask | local);
                } else {
                    test_mask(mask);
                }
            };
            combine(0, 0);
        };
        allocate_length(1);
    } else if (enumeration_mode == 1 || enumeration_mode == 2) {
        std::vector<std::map<std::pair<int, int>, std::vector<U64>>>
            size_adjacency_cache(component_count);
        auto fetch_size_adjacency = [&](
            int component, int selected, int adjacency
        ) -> const std::vector<U64>& {
            auto key = std::make_pair(selected, adjacency);
            auto& table = size_adjacency_cache[component];
            auto found = table.find(key);
            if (found == table.end())
                found = table.emplace(
                    key,
                    local_masks_size_adjacency(
                        components[component], selected, adjacency
                    )
                ).first;
            return found->second;
        };
        using FeasibleTable = std::array<std::array<bool, 13>, 13>;
        std::vector<FeasibleTable> suffix_feasible(component_count + 1);
        suffix_feasible[component_count][0][0] = true;
        for (int component = component_count - 1; component >= 0; --component) {
            int length = static_cast<int>(components[component].size());
            for (int selected = 0;
                 selected <= std::min(length, target_selected);
                 ++selected) {
                std::vector<int> adjacency_values;
                if (selected == 0) {
                    adjacency_values = {0};
                } else if (selected == length) {
                    adjacency_values = {length};
                } else {
                    int max_runs = std::min(selected, length - selected);
                    for (int runs = 1; runs <= max_runs; ++runs)
                        adjacency_values.push_back(selected - runs);
                }
                if (
                    enumeration_mode == 2
                    && length == required_full_cycle_length
                    && selected != length
                ) continue;
                for (int adjacency : adjacency_values) {
                    for (int tail_selected = 0;
                         selected + tail_selected <= target_selected;
                         ++tail_selected) {
                        for (int tail_adjacency = 0;
                             adjacency + tail_adjacency <= target_adjacency;
                             ++tail_adjacency) {
                            if (!suffix_feasible[component + 1]
                                    [tail_selected][tail_adjacency])
                                continue;
                            suffix_feasible[component]
                                [selected + tail_selected]
                                [adjacency + tail_adjacency] = true;
                        }
                    }
                }
            }
        }
        std::vector<const std::vector<U64>*> lists;
        std::function<void(int, int, int)> allocate_component = [&](
            int component, int remaining_selected, int remaining_adjacency
        ) {
            if (
                remaining_selected < 0 || remaining_selected > target_selected
                || remaining_adjacency < 0
                || remaining_adjacency > target_adjacency
                || !suffix_feasible[component]
                    [remaining_selected][remaining_adjacency]
            ) return;
            if (component == component_count) {
                if (remaining_selected != 0 || remaining_adjacency != 0) return;
                std::function<void(int, U64)> combine = [&](int index, U64 mask) {
                    if (index < component_count) {
                        for (U64 local : *lists[index])
                            combine(index + 1, mask | local);
                    } else {
                        test_mask(mask);
                    }
                };
                combine(0, 0);
                return;
            }
            int length = static_cast<int>(components[component].size());
            int future_required = 0;
            if (enumeration_mode == 2) {
                for (int future = component + 1; future < component_count; ++future) {
                    int future_length = static_cast<int>(
                        components[future].size()
                    );
                    if (future_length == required_full_cycle_length)
                        future_required += future_length;
                }
            }
            int max_selected = std::min(
                length, remaining_selected - future_required
            );
            if (max_selected < 0) return;
            int min_selected = 0;
            if (component + 1 == component_count) {
                min_selected = remaining_selected;
                max_selected = remaining_selected;
            }
            if (
                enumeration_mode == 2
                && length == required_full_cycle_length
            ) {
                min_selected = std::max(min_selected, length);
                max_selected = length;
            }
            for (int selected = min_selected; selected <= max_selected; ++selected) {
                std::vector<int> adjacency_values;
                if (selected == 0) {
                    adjacency_values = {0};
                } else if (selected == length) {
                    adjacency_values = {length};
                } else {
                    int max_runs = std::min(selected, length - selected);
                    for (int runs = 1; runs <= max_runs; ++runs)
                        adjacency_values.push_back(selected - runs);
                }
                if (component + 1 == component_count) {
                    adjacency_values.erase(
                        std::remove_if(
                            adjacency_values.begin(),
                            adjacency_values.end(),
                            [&](int value) {
                                return value != remaining_adjacency;
                            }
                        ),
                        adjacency_values.end()
                    );
                }
                for (int adjacency : adjacency_values) {
                    if (
                        adjacency
                        > remaining_adjacency - future_required
                    ) continue;
                    if (
                        !suffix_feasible[component + 1]
                            [remaining_selected - selected]
                            [remaining_adjacency - adjacency]
                    ) continue;
                    const auto& values = fetch_size_adjacency(
                        component, selected, adjacency
                    );
                    if (values.empty()) continue;
                    lists.push_back(&values);
                    allocate_component(
                        component + 1,
                        remaining_selected - selected,
                        remaining_adjacency - adjacency
                    );
                    lists.pop_back();
                }
            }
        };
        allocate_component(0, target_selected, target_adjacency);
    } else {
        for (U64 mask : explicit_masks) test_mask(mask);
    }

    std::cout << "{\n"
              << "  \"component_count\": " << component_count << ",\n"
              << "  \"enumeration_mode\": \""
              << (
                  enumeration_mode == 0
                  ? "run_profile"
                  : (
                      enumeration_mode == 1
                      ? "fixed_adjacency"
                      : (
                          enumeration_mode == 2
                          ? "fixed_adjacency_with_required_full_cycle"
                          : "explicit_masks"
                      )
                  )
              )
              << "\",\n";
    std::cout << "  \"target_selected\": " << target_selected << ",\n";
    std::cout << "  \"line_capacity_count\": "
              << line_capacity_count << ",\n";
    if (enumeration_mode == 1 || enumeration_mode == 2) {
        std::cout << "  \"target_adjacency\": " << target_adjacency << ",\n";
        if (enumeration_mode == 2)
            std::cout << "  \"required_full_cycle_length\": "
                      << required_full_cycle_length << ",\n";
    } else if (enumeration_mode == 0) {
        std::cout
              << "  \"run_lengths\": [";
        bool first_run = true;
        for (int length = 1; length <= 12; ++length) {
            for (int count = 0; count < global_profile[length]; ++count) {
                if (!first_run) std::cout << ", ";
                first_run = false;
                std::cout << length;
            }
        }
        std::cout << "],\n";
    } else {
        std::cout << "  \"explicit_mask_count\": "
                  << explicit_masks.size() << ",\n";
    }
    std::cout
              << "  \"distinct_shape_masks\": " << distinct_shape_masks << ",\n"
              << "  \"defect_hitting_masks\": " << defect_hitting_masks << ",\n"
              << "  \"factor_feasible_masks\": " << factor_feasible_masks << ",\n"
              << "  \"all_factor_infeasible\": "
              << (factor_feasible_masks == 0 ? "true" : "false") << ",\n"
              << "  \"total_factor_search_nodes\": " << total_factor_nodes << ",\n"
              << "  \"maximum_factor_search_nodes\": " << maximum_factor_nodes << ",\n"
              << "  \"root_zero_option_by_deficit\": {\"1\": "
              << root_zero_option_by_deficit[1] << ", \"2\": "
              << root_zero_option_by_deficit[2] << "},\n"
              << "  \"search_node_histogram\": {";
    bool first_histogram = true;
    for (std::size_t i = 0; i < search_node_histogram.size(); ++i) {
        if (search_node_histogram[i] == 0) continue;
        if (!first_histogram) std::cout << ", ";
        first_histogram = false;
        std::cout << "\"" << (i + 1 == search_node_histogram.size()
            ? std::to_string(i) + "+"
            : std::to_string(i))
                  << "\": " << search_node_histogram[i];
    }
    std::cout << "},\n"
              << "  \"sample_hitting_masks\": [";
    for (std::size_t i = 0; i < sample_hitting_masks.size(); ++i) {
        if (i) std::cout << ", ";
        std::cout << sample_hitting_masks[i];
    }
    std::cout << "],\n"
              << "  \"feasible_masks\": [";
    for (std::size_t i = 0; i < feasible_masks.size(); ++i) {
        if (i) std::cout << ", ";
        std::cout << feasible_masks[i];
    }
    std::cout << "],\n"
              << "  \"first_feasible_mask\": " << first_feasible_mask << ",\n"
              << "  \"first_feasible_cells\": [";
    for (std::size_t i = 0; i < first_feasible_cells.size(); ++i) {
        if (i) std::cout << ", ";
        int id = first_feasible_cells[i];
        std::cout << "[" << id / 37 << ", " << id % 37 << "]";
    }
    std::cout << "],\n";
    std::cout << "  \"witness_factors\": [";
    for (std::size_t w = 0; w < witness_factors.size(); ++w) {
        if (w) std::cout << ", ";
        std::cout << "{\"mask\": " << witness_factors[w].first << ", \"cells\": [";
        const auto& cells = witness_factors[w].second;
        for (std::size_t i = 0; i < cells.size(); ++i) {
            if (i) std::cout << ", ";
            int id = cells[i];
            std::cout << "[" << id / 37 << ", " << id % 37 << "]";
        }
        std::cout << "]}";
    }
    std::cout << "],\n";
    // New: mask completion info (count + truncated flag per mask)
    std::cout << "  \"mask_completion_info\": [";
    for (std::size_t m = 0; m < mask_completion_info.size(); ++m) {
        if (m) std::cout << ", ";
        std::cout << "{\"mask\": " << mask_completion_info[m].mask
                  << ", \"completion_count\": " << mask_completion_info[m].completion_count
                  << ", \"truncated\": "
                  << (mask_completion_info[m].truncated ? "true" : "false")
                  << "}";
    }
    std::cout << "]\n}\n";
}
