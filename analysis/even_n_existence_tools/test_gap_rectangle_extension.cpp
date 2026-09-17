// Test a concrete n -> n+2 induction template.
//
// Choose two new row coordinates R={r1,r2} and two new column
// coordinates C={c1,c2}.  Embed an old n by n solution order-preservingly
// into the complementary rows and columns of the (n+2) by (n+2) grid,
// then add the four forced points R x C.  The result has exactly two
// points in every row and column.  This program tests all choices of R,C
// for compact Flammenkamp records.
//
// A hit would be a genuine extension, verified by an independent
// normalised-direction no-three test.  A miss only rules out this narrow
// order-preserving two-gap template for the tested source configuration.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numeric>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_set>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

struct Point {
    int x;
    int y;
};

struct Direction {
    int dx;
    int dy;
    bool operator==(const Direction& other) const {
        return dx == other.dx && dy == other.dy;
    }
};

struct DirectionHash {
    std::size_t operator()(const Direction& direction) const {
        return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(direction.dx))
                << 32) ^
               static_cast<std::uint32_t>(direction.dy);
    }
};

Direction normalise(int dx, int dy) {
    int divisor = std::gcd(std::abs(dx), std::abs(dy));
    dx /= divisor;
    dy /= divisor;
    if (dx < 0 || (dx == 0 && dy < 0)) {
        dx = -dx;
        dy = -dy;
    }
    return {dx, dy};
}

bool no_three(const std::vector<Point>& points) {
    std::unordered_set<Direction, DirectionHash> seen;
    seen.reserve(points.size() * 2);
    for (std::size_t first = 0; first < points.size(); ++first) {
        seen.clear();
        for (std::size_t second = 0; second < points.size(); ++second) {
            if (first == second) {
                continue;
            }
            Direction direction = normalise(
                points[second].x - points[first].x,
                points[second].y - points[first].y
            );
            if (!seen.insert(direction).second) {
                return false;
            }
        }
    }
    return true;
}

std::vector<int> complement_map(int old_n, int first_gap, int second_gap) {
    std::vector<int> result;
    for (int coordinate = 0; coordinate < old_n + 2; ++coordinate) {
        if (coordinate != first_gap && coordinate != second_gap) {
            result.push_back(coordinate);
        }
    }
    return result;
}

const std::string ALPHABET =
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "#$%&@?!()[]<>{}=*+|-/~^_:;,.|";

bool is_marker(char character) {
    return std::string(".:/-ocx+*").find(character) != std::string::npos;
}

std::vector<Point> decode_compact(const std::string& raw, int n) {
    std::string line = raw;
    while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) {
        line.pop_back();
    }
    std::size_t offset = (!line.empty() && is_marker(line[0])) ? 1 : 0;
    if (line.size() < offset + static_cast<std::size_t>(2 * n)) {
        throw std::runtime_error("short compact record");
    }
    std::vector<Point> points;
    for (int row = 0; row < n; ++row) {
        for (int slot = 0; slot < 2; ++slot) {
            char symbol = line[offset + 2 * row + slot];
            std::size_t value = ALPHABET.find(symbol);
            if (value == std::string::npos) {
                throw std::runtime_error("unknown compact symbol");
            }
            points.push_back({row, static_cast<int>(value)});
        }
    }
    return points;
}

struct SearchResult {
    std::uint64_t tested = 0;
    std::uint64_t embedded_old_clean = 0;
    bool found = false;
    int r1 = -1;
    int r2 = -1;
    int c1 = -1;
    int c2 = -1;
    std::vector<Point> points;
};

SearchResult search_extension(
    const std::vector<Point>& old_points,
    int n,
    std::uint64_t candidate_limit
) {
    SearchResult result;
    for (int r1 = 0; r1 < n + 2; ++r1) {
        for (int r2 = r1 + 1; r2 < n + 2; ++r2) {
            const auto row_map = complement_map(n, r1, r2);
            for (int c1 = 0; c1 < n + 2; ++c1) {
                for (int c2 = c1 + 1; c2 < n + 2; ++c2) {
                    if (candidate_limit && result.tested >= candidate_limit) {
                        return result;
                    }
                    ++result.tested;
                    const auto column_map = complement_map(n, c1, c2);
                    std::vector<Point> embedded;
                    embedded.reserve(old_points.size() + 4);
                    for (const auto& point : old_points) {
                        embedded.push_back({row_map[point.x], column_map[point.y]});
                    }
                    if (!no_three(embedded)) {
                        continue;
                    }
                    ++result.embedded_old_clean;
                    embedded.push_back({r1, c1});
                    embedded.push_back({r1, c2});
                    embedded.push_back({r2, c1});
                    embedded.push_back({r2, c2});
                    if (no_three(embedded)) {
                        result.found = true;
                        result.r1 = r1;
                        result.r2 = r2;
                        result.c1 = c1;
                        result.c2 = c2;
                        result.points = std::move(embedded);
                        return result;
                    }
                }
            }
        }
    }
    return result;
}

int main(int argc, char** argv) {
    fs::path cache;
    int minimum_n = 2;
    int maximum_n = 30;
    std::uint64_t candidate_limit = 0;
    int record_limit = 1;
    for (int index = 1; index < argc; ++index) {
        std::string argument = argv[index];
        if (argument == "--cache" && index + 1 < argc) {
            cache = argv[++index];
        } else if (argument == "--minimum-n" && index + 1 < argc) {
            minimum_n = std::stoi(argv[++index]);
        } else if (argument == "--maximum-n" && index + 1 < argc) {
            maximum_n = std::stoi(argv[++index]);
        } else if (argument == "--candidate-limit" && index + 1 < argc) {
            candidate_limit = std::stoull(argv[++index]);
        } else if (argument == "--record-limit" && index + 1 < argc) {
            record_limit = std::stoi(argv[++index]);
        } else {
            std::cerr << "unknown or incomplete argument: " << argument << "\n";
            return 2;
        }
    }
    if (cache.empty()) {
        std::cerr << "--cache is required\n";
        return 2;
    }

    for (int n = minimum_n; n <= maximum_n; ++n) {
        if (n % 2) {
            continue;
        }
        fs::path path = cache / ("n" + std::to_string(n) + "_rot4");
        if (!fs::exists(path)) {
            path += ".few";
        }
        if (!fs::exists(path)) {
            continue;
        }
        std::ifstream input(path);
        std::string line;
        int record = 0;
        bool any_found = false;
        auto start = std::chrono::steady_clock::now();
        while (record < record_limit && std::getline(input, line)) {
            if (line.empty()) {
                continue;
            }
            auto old_points = decode_compact(line, n);
            if (!no_three(old_points)) {
                throw std::runtime_error("source record failed independent NTIL check");
            }
            SearchResult result =
                search_extension(old_points, n, candidate_limit);
            double seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - start
            ).count();
            std::cout << "{\"n\":" << n
                      << ",\"record\":" << record
                      << ",\"tested\":" << result.tested
                      << ",\"embedded_old_clean\":" << result.embedded_old_clean
                      << ",\"found\":" << (result.found ? "true" : "false")
                      << ",\"seconds\":" << seconds;
            if (result.found) {
                std::cout << ",\"row_gaps\":[" << result.r1 << "," << result.r2
                          << "],\"column_gaps\":[" << result.c1 << "," << result.c2
                          << "],\"points\":[";
                for (std::size_t i = 0; i < result.points.size(); ++i) {
                    if (i) {
                        std::cout << ",";
                    }
                    std::cout << "[" << result.points[i].x << ","
                              << result.points[i].y << "]";
                }
                std::cout << "]";
            }
            std::cout << "}\n" << std::flush;
            ++record;
            if (result.found) {
                any_found = true;
                break;
            }
        }
        (void) any_found;
    }
    return 0;
}
