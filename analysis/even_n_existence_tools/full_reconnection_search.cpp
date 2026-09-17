// True full-reconnection local search for C4-symmetric NTIL configurations.
//
// A fundamental domain is a set of m directed cells (x,y) on [0,m)^2
// satisfying total_degree(v) = out_degree(v)+in_degree(v) = 2.
// Its four rotations give 4m points on the 2m by 2m board.
//
// For two directed cells, the previous csearch2 implementation only tested
// one of the two cross-pairings of their four endpoint occurrences:
//   YSWAP and XSWAP give the same unordered cell set,
//   XYSWAP is a no-op.
// Here we enumerate all three endpoint pairings and all edge orientations.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <random>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

using std::pair;
using std::string;
using std::unordered_map;
using std::unordered_set;
using std::vector;

using i64 = long long;
using u64 = std::uint64_t;

struct Cell {
    int x;
    int y;
};

struct Point {
    int x;
    int y;
};

static int m;
static int n;
static vector<Cell> cells;
static vector<Point> points;
static vector<unsigned char> point_present;
static vector<unsigned char> cell_present;
static unordered_map<u64, int> line_count;
static i64 energy;
static std::mt19937_64 rng;

static bool operator==(const Cell& first, const Cell& second) {
    return first.x == second.x && first.y == second.y;
}

static bool cell_less(const Cell& first, const Cell& second) {
    return first.x < second.x || (first.x == second.x && first.y < second.y);
}

static i64 choose_three(i64 value) {
    return value >= 3 ? value * (value - 1) * (value - 2) / 6 : 0;
}

static Point rotate_point(int x, int y, int rotation) {
    if (rotation == 0) return {x, y};
    if (rotation == 1) return {n - 1 - y, x};
    if (rotation == 2) return {n - 1 - x, n - 1 - y};
    return {y, n - 1 - x};
}

static int gcd_int(int first, int second) {
    first = std::abs(first);
    second = std::abs(second);
    while (second != 0) {
        int remainder = first % second;
        first = second;
        second = remainder;
    }
    return first;
}

static u64 line_key(const Point& first, const Point& second) {
    int a = -(second.y - first.y);
    int b = second.x - first.x;
    int c = (second.y - first.y) * first.x -
            (second.x - first.x) * first.y;
    int divisor = gcd_int(gcd_int(a, b), c);
    if (divisor != 0) {
        a /= divisor;
        b /= divisor;
        c /= divisor;
    }
    if (a < 0 || (a == 0 && b < 0) ||
        (a == 0 && b == 0 && c < 0)) {
        a = -a;
        b = -b;
        c = -c;
    }
    const i64 coordinate_offset = n - 1;
    const i64 constant_offset = static_cast<i64>(n - 1) * (n - 1);
    const u64 coordinate_span = static_cast<u64>(2 * n - 1);
    const u64 constant_span = static_cast<u64>(2 * constant_offset + 1);
    u64 key = static_cast<u64>(a + coordinate_offset);
    key = key * coordinate_span + static_cast<u64>(b + coordinate_offset);
    key = key * constant_span + static_cast<u64>(c + constant_offset);
    return key;
}

static void rebuild_points() {
    points.resize(4 * m);
    for (int index = 0; index < m; ++index) {
        for (int rotation = 0; rotation < 4; ++rotation) {
            points[4 * index + rotation] =
                rotate_point(cells[index].x, cells[index].y, rotation);
        }
    }
}

static vector<u64> incident_line_keys(int point_index) {
    vector<u64> keys;
    keys.reserve(4 * m);
    const Point point = points[point_index];
    for (int other = 0; other < 4 * m; ++other) {
        if (other == point_index || !point_present[other]) continue;
        if (points[other].x == point.x && points[other].y == point.y) continue;
        keys.push_back(line_key(point, points[other]));
    }
    std::sort(keys.begin(), keys.end());
    keys.erase(std::unique(keys.begin(), keys.end()), keys.end());
    return keys;
}

static void add_point(int point_index) {
    vector<u64> keys = incident_line_keys(point_index);
    for (u64 key : keys) {
        auto found = line_count.find(key);
        int old_count = (found == line_count.end()) ? 1 : found->second;
        energy += choose_three(old_count + 1) - choose_three(old_count);
        line_count[key] = old_count + 1;
    }
    point_present[point_index] = 1;
}

static void remove_point(int point_index) {
    point_present[point_index] = 0;
    vector<u64> keys = incident_line_keys(point_index);
    for (u64 key : keys) {
        auto found = line_count.find(key);
        if (found == line_count.end()) {
            std::fprintf(stderr, "missing line during point removal\n");
            std::abort();
        }
        int old_count = found->second;
        energy += choose_three(old_count - 1) - choose_three(old_count);
        if (old_count == 2) {
            line_count.erase(found);
        } else {
            found->second = old_count - 1;
        }
    }
}

static void rebuild_energy() {
    rebuild_points();
    line_count.clear();
    energy = 0;
    point_present.assign(4 * m, 0);
    for (int index = 0; index < 4 * m; ++index) add_point(index);
}

static i64 direct_energy() {
    unordered_map<u64, unordered_set<int>> lines;
    for (int first = 0; first < 4 * m; ++first) {
        for (int second = first + 1; second < 4 * m; ++second) {
            if (points[first].x == points[second].x &&
                points[first].y == points[second].y) {
                continue;
            }
            u64 key = line_key(points[first], points[second]);
            lines[key].insert(first);
            lines[key].insert(second);
        }
    }
    i64 result = 0;
    for (const auto& item : lines) {
        result += choose_three(static_cast<i64>(item.second.size()));
    }
    return result;
}

static int cell_id(const Cell& cell) {
    return cell.x * m + cell.y;
}

static bool valid_replacement(
    int first_index,
    int second_index,
    const Cell& first,
    const Cell& second
) {
    if (first == second) return false;
    int first_id = cell_id(first);
    int second_id = cell_id(second);
    int old_first_id = cell_id(cells[first_index]);
    int old_second_id = cell_id(cells[second_index]);
    if (cell_present[first_id] &&
        first_id != old_first_id && first_id != old_second_id) {
        return false;
    }
    if (cell_present[second_id] &&
        second_id != old_first_id && second_id != old_second_id) {
        return false;
    }
    return true;
}

static void replace_pair(
    int first_index,
    int second_index,
    const Cell& new_first,
    const Cell& new_second
) {
    for (int rotation = 0; rotation < 4; ++rotation) {
        remove_point(4 * first_index + rotation);
        remove_point(4 * second_index + rotation);
    }
    cell_present[cell_id(cells[first_index])] = 0;
    cell_present[cell_id(cells[second_index])] = 0;
    cells[first_index] = new_first;
    cells[second_index] = new_second;
    cell_present[cell_id(cells[first_index])] = 1;
    cell_present[cell_id(cells[second_index])] = 1;
    for (int rotation = 0; rotation < 4; ++rotation) {
        points[4 * first_index + rotation] =
            rotate_point(new_first.x, new_first.y, rotation);
        points[4 * second_index + rotation] =
            rotate_point(new_second.x, new_second.y, rotation);
    }
    for (int rotation = 0; rotation < 4; ++rotation) {
        add_point(4 * first_index + rotation);
        add_point(4 * second_index + rotation);
    }
}

static u64 pair_key(Cell first, Cell second) {
    if (cell_less(second, first)) std::swap(first, second);
    u64 first_id = static_cast<u64>(cell_id(first));
    u64 second_id = static_cast<u64>(cell_id(second));
    return first_id * static_cast<u64>(m * m) + second_id;
}

static vector<pair<Cell, Cell>> reconnections(int first_index, int second_index) {
    const Cell old_first = cells[first_index];
    const Cell old_second = cells[second_index];
    int endpoint[4] = {
        old_first.x,
        old_first.y,
        old_second.x,
        old_second.y,
    };
    const int pairing[3][4] = {
        {0, 1, 2, 3},
        {0, 2, 1, 3},
        {0, 3, 1, 2},
    };
    const u64 old_key = pair_key(old_first, old_second);
    unordered_set<u64> seen;
    vector<pair<Cell, Cell>> result;
    for (const auto& selected_pairing : pairing) {
        for (int first_reverse = 0; first_reverse < 2; ++first_reverse) {
            for (int second_reverse = 0; second_reverse < 2; ++second_reverse) {
                Cell first = {
                    endpoint[selected_pairing[first_reverse ? 1 : 0]],
                    endpoint[selected_pairing[first_reverse ? 0 : 1]],
                };
                Cell second = {
                    endpoint[selected_pairing[second_reverse ? 3 : 2]],
                    endpoint[selected_pairing[second_reverse ? 2 : 3]],
                };
                if (!valid_replacement(
                        first_index,
                        second_index,
                        first,
                        second)) {
                    continue;
                }
                u64 key = pair_key(first, second);
                if (key == old_key || !seen.insert(key).second) continue;
                result.push_back({first, second});
            }
        }
    }
    return result;
}

static i64 measure_replacement(
    int first_index,
    int second_index,
    const Cell& new_first,
    const Cell& new_second
) {
    const Cell old_first = cells[first_index];
    const Cell old_second = cells[second_index];
    i64 before = energy;
    replace_pair(
        first_index,
        second_index,
        new_first,
        new_second);
    i64 delta = energy - before;
    replace_pair(
        first_index,
        second_index,
        old_first,
        old_second);
    if (energy != before) {
        std::fprintf(
            stderr,
            "incremental rollback mismatch: before=%lld after=%lld\n",
            before,
            energy);
        std::abort();
    }
    return delta;
}

static void initialize_hamilton_cycle() {
    vector<int> order(m);
    std::iota(order.begin(), order.end(), 0);
    std::shuffle(order.begin(), order.end(), rng);
    cells.clear();
    cells.reserve(m);
    cell_present.assign(m * m, 0);
    for (int index = 0; index < m; ++index) {
        int first = order[index];
        int second = order[(index + 1) % m];
        if ((rng() & 1ULL) != 0) std::swap(first, second);
        Cell cell = {first, second};
        cells.push_back(cell);
        cell_present[cell_id(cell)] = 1;
    }
    rebuild_energy();
}

struct Move {
    int first_index = -1;
    int second_index = -1;
    Cell first = {-1, -1};
    Cell second = {-1, -1};
    i64 delta = 0;
};

static bool greedy_descent(int maximum_steps, bool best_improvement) {
    for (int step = 0; step < maximum_steps && energy > 0; ++step) {
        Move best;
        best.delta = 0;
        i64 candidate_count = 0;
        for (int first_index = 0; first_index < m; ++first_index) {
            for (int second_index = first_index + 1;
                 second_index < m;
                 ++second_index) {
                vector<pair<Cell, Cell>> alternatives =
                    reconnections(first_index, second_index);
                for (const auto& alternative : alternatives) {
                    ++candidate_count;
                    i64 delta = measure_replacement(
                        first_index,
                        second_index,
                        alternative.first,
                        alternative.second);
                    if (delta < best.delta) {
                        best = {
                            first_index,
                            second_index,
                            alternative.first,
                            alternative.second,
                            delta,
                        };
                        if (!best_improvement) break;
                    }
                }
                if (!best_improvement && best.delta < 0) break;
            }
            if (!best_improvement && best.delta < 0) break;
        }
        if (best.delta >= 0) {
            std::printf(
                "LOCAL_MIN step=%d energy=%lld candidates=%lld\n",
                step,
                energy,
                candidate_count);
            std::fflush(stdout);
            return false;
        }
        replace_pair(
            best.first_index,
            best.second_index,
            best.first,
            best.second);
        std::printf(
            "STEP %d energy=%lld delta=%lld candidates=%lld\n",
            step + 1,
            energy,
            best.delta,
            candidate_count);
        std::fflush(stdout);
    }
    return energy == 0;
}

static bool simulated_annealing(
    i64 maximum_moves,
    double initial_temperature,
    double final_temperature
) {
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    i64 best_energy = energy;
    vector<Cell> best_cells = cells;
    double temperature = initial_temperature;
    double decay = std::pow(
        final_temperature / initial_temperature,
        1.0 / std::max<i64>(1, maximum_moves));
    for (i64 move = 0; move < maximum_moves && energy > 0; ++move) {
        int first_index = static_cast<int>(rng() % m);
        int second_index = static_cast<int>(rng() % m);
        if (first_index == second_index) continue;
        if (first_index > second_index) std::swap(first_index, second_index);
        vector<pair<Cell, Cell>> alternatives =
            reconnections(first_index, second_index);
        if (alternatives.empty()) continue;
        const auto& selected = alternatives[rng() % alternatives.size()];
        Cell old_first = cells[first_index];
        Cell old_second = cells[second_index];
        i64 before = energy;
        replace_pair(
            first_index,
            second_index,
            selected.first,
            selected.second);
        i64 delta = energy - before;
        bool accept = delta <= 0 ||
                      uniform(rng) < std::exp(-static_cast<double>(delta) /
                                              temperature);
        if (!accept) {
            replace_pair(
                first_index,
                second_index,
                old_first,
                old_second);
        } else if (energy < best_energy) {
            best_energy = energy;
            best_cells = cells;
            if (best_energy % 10 == 0 || best_energy < 10) {
                std::printf(
                    "SA_BEST move=%lld energy=%lld\n",
                    move,
                    best_energy);
                std::fflush(stdout);
            }
        }
        temperature *= decay;
    }
    if (best_energy < energy) {
        cells = best_cells;
        cell_present.assign(m * m, 0);
        for (const Cell& cell : cells) cell_present[cell_id(cell)] = 1;
        rebuild_energy();
    }
    return energy == 0;
}

static bool verify_degrees_and_cells() {
    vector<int> degree(m, 0);
    unordered_set<int> seen;
    for (const Cell& cell : cells) {
        if (!seen.insert(cell_id(cell)).second) return false;
        ++degree[cell.x];
        ++degree[cell.y];
    }
    return std::all_of(
        degree.begin(),
        degree.end(),
        [](int value) { return value == 2; });
}

static void print_solution() {
    std::printf("SOLUTION m=%d n=%d energy=%lld cells=", m, n, energy);
    for (const Cell& cell : cells) {
        std::printf("(%d,%d)", cell.x, cell.y);
    }
    std::printf("\npoints=");
    for (const Point& point : points) {
        std::printf("(%d,%d)", point.x, point.y);
    }
    std::printf("\n");
    std::fflush(stdout);
}

int main(int argc, char** argv) {
    m = 14;
    int restarts = 10;
    int greedy_steps = 500;
    i64 annealing_moves = 0;
    int seed = 1;
    bool best_improvement = true;
    bool self_test = false;
    for (int index = 1; index < argc; ++index) {
        string argument = argv[index];
        if (argument == "--m" && index + 1 < argc) {
            m = std::atoi(argv[++index]);
        } else if (argument == "--restarts" && index + 1 < argc) {
            restarts = std::atoi(argv[++index]);
        } else if (argument == "--greedy-steps" && index + 1 < argc) {
            greedy_steps = std::atoi(argv[++index]);
        } else if (argument == "--sa-moves" && index + 1 < argc) {
            annealing_moves = std::atoll(argv[++index]);
        } else if (argument == "--seed" && index + 1 < argc) {
            seed = std::atoi(argv[++index]);
        } else if (argument == "--first-improvement") {
            best_improvement = false;
        } else if (argument == "--self-test") {
            self_test = true;
        }
    }
    if (m < 3) {
        std::fprintf(stderr, "m must be at least 3\n");
        return 2;
    }
    n = 2 * m;
    rng.seed(static_cast<u64>(seed));

    if (self_test) {
        initialize_hamilton_cycle();
        for (int iteration = 0; iteration < 1000; ++iteration) {
            int first_index = static_cast<int>(rng() % m);
            int second_index = static_cast<int>(rng() % m);
            if (first_index == second_index) continue;
            if (first_index > second_index) std::swap(first_index, second_index);
            auto alternatives = reconnections(first_index, second_index);
            if (alternatives.empty()) continue;
            const auto& alternative = alternatives[rng() % alternatives.size()];
            i64 before = energy;
            i64 delta = measure_replacement(
                first_index,
                second_index,
                alternative.first,
                alternative.second);
            if (energy != before) {
                std::fprintf(stderr, "measurement leaked state\n");
                return 3;
            }
            Cell old_first = cells[first_index];
            Cell old_second = cells[second_index];
            replace_pair(
                first_index,
                second_index,
                alternative.first,
                alternative.second);
            if (energy - before != delta ||
                direct_energy() != energy ||
                !verify_degrees_and_cells()) {
                std::fprintf(
                    stderr,
                    "self-test mismatch at iteration %d\n",
                    iteration);
                return 4;
            }
            replace_pair(
                first_index,
                second_index,
                old_first,
                old_second);
            if (energy != before || direct_energy() != energy) {
                std::fprintf(stderr, "rollback failed\n");
                return 5;
            }
        }
        std::printf("SELF_TEST_OK m=%d energy=%lld\n", m, energy);
        return 0;
    }

    auto started = std::chrono::steady_clock::now();
    i64 global_best = -1;
    vector<Cell> global_best_cells;
    for (int restart = 0; restart < restarts; ++restart) {
        initialize_hamilton_cycle();
        std::printf(
            "RESTART %d initial_energy=%lld\n",
            restart,
            energy);
        std::fflush(stdout);
        if (annealing_moves > 0) {
            simulated_annealing(annealing_moves, 4.0, 0.02);
            std::printf(
                "POST_SA restart=%d energy=%lld\n",
                restart,
                energy);
            std::fflush(stdout);
        }
        bool found = greedy_descent(greedy_steps, best_improvement);
        if (global_best < 0 || energy < global_best) {
            global_best = energy;
            global_best_cells = cells;
        }
        if (found) {
            print_solution();
            auto elapsed = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - started).count();
            std::printf("FOUND elapsed_seconds=%.6f\n", elapsed);
            return 0;
        }
    }
    cells = global_best_cells;
    cell_present.assign(m * m, 0);
    for (const Cell& cell : cells) cell_present[cell_id(cell)] = 1;
    rebuild_energy();
    auto elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started).count();
    std::printf(
        "NOT_FOUND best_energy=%lld elapsed_seconds=%.6f\n",
        global_best,
        elapsed);
    print_solution();
    return 1;
}
