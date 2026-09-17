#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

// For H_a={(X,Y) in [1,p-1]^2: XY=a mod p}, enumerate ordinary grid
// lines that contain two points of H_a and two points of H_b.  Such a line
// immediately destroys H_a union H_b.  Report whether this simple four-point
// obstruction covers every unordered multiplier pair.

struct Result {
  int p;
  int covered_pairs;
  int total_pairs;
  int maximum_first_direction_norm;
  std::pair<int, int> first_uncovered;
  std::vector<int64_t> first_norm_histogram;
};

Result scan_prime(int p) {
  const int total_pairs = (p - 1) * (p - 2) / 2;
  std::vector<int> first_norm((p - 1) * (p - 1), -1);
  auto index = [p](int a, int b) { return a * (p - 1) + b; };
  int covered = 0;
  int max_first_norm = 0;
  std::vector<int64_t> histogram(p, 0);

  // A line with four grid points has primitive step infinity norm <=(p-2)/3.
  const int max_step = (p - 2) / 3;
  for (int norm = 1; norm <= max_step; ++norm) {
    std::vector<std::pair<int, int>> directions;
    for (int dx = 1; dx <= norm; ++dx) {
      for (int dy = -norm; dy <= norm; ++dy) {
        if (std::max(dx, std::abs(dy)) != norm) continue;
        if (std::gcd(dx, std::abs(dy)) != 1) continue;
        directions.emplace_back(dx, dy);
      }
    }
    // Vertical lines cannot repeat XY for fixed X, so omit dx=0.
    for (const auto [dx, dy] : directions) {
      for (int x = 1; x < p; ++x) {
        for (int y = 1; y < p; ++y) {
          if (1 <= x - dx && x - dx < p && 1 <= y - dy &&
              y - dy < p) {
            continue;  // not the first point of the maximal line
          }
          if (!(1 <= x + 3 * dx && x + 3 * dx < p &&
                1 <= y + 3 * dy && y + 3 * dy < p)) {
            continue;  // fewer than four grid points
          }
          std::vector<int> counts(p, 0);
          int xx = x, yy = y;
          while (1 <= xx && xx < p && 1 <= yy && yy < p) {
            ++counts[(xx * yy) % p];
            xx += dx;
            yy += dy;
          }
          std::vector<int> doubled;
          for (int a = 1; a < p; ++a) {
            if (counts[a] >= 2) doubled.push_back(a);
          }
          for (int i = 0; i < static_cast<int>(doubled.size()); ++i) {
            for (int j = i + 1; j < static_cast<int>(doubled.size()); ++j) {
              int a = doubled[i], b = doubled[j];
              if (a > b) std::swap(a, b);
              if (first_norm[index(a - 1, b - 1)] == -1) {
                first_norm[index(a - 1, b - 1)] = norm;
                ++covered;
                ++histogram[norm];
                max_first_norm = std::max(max_first_norm, norm);
              }
            }
          }
        }
      }
    }
  }

  std::pair<int, int> first_uncovered{-1, -1};
  for (int a = 1; a < p && first_uncovered.first == -1; ++a) {
    for (int b = a + 1; b < p; ++b) {
      if (first_norm[index(a - 1, b - 1)] == -1) {
        first_uncovered = {a, b};
        break;
      }
    }
  }
  return {p, covered, total_pairs, max_first_norm, first_uncovered, histogram};
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: hyperbola_common_chord_scan p [p ...]\n";
    return 2;
  }
  for (int arg = 1; arg < argc; ++arg) {
    const int p = std::stoi(argv[arg]);
    Result result = scan_prime(p);
    std::cout << "{\"p\":" << result.p
              << ",\"covered_pairs\":" << result.covered_pairs
              << ",\"total_pairs\":" << result.total_pairs
              << ",\"all_covered\":"
              << (result.covered_pairs == result.total_pairs ? "true" : "false")
              << ",\"maximum_first_direction_norm\":"
              << result.maximum_first_direction_norm
              << ",\"first_uncovered_pair\":["
              << result.first_uncovered.first << ","
              << result.first_uncovered.second << "],\"first_norm_histogram\":{";
    bool first = true;
    for (int norm = 1;
         norm < static_cast<int>(result.first_norm_histogram.size()); ++norm) {
      if (result.first_norm_histogram[norm] == 0) continue;
      if (!first) std::cout << ",";
      first = false;
      std::cout << "\"" << norm << "\":"
                << result.first_norm_histogram[norm];
    }
    std::cout << "}}\n";
  }
}
