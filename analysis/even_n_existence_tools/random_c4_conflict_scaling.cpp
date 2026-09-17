#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
#include <unordered_map>
#include <vector>

struct Point {
    int x;
    int y;
};

struct Line {
    int a;
    int b;
    int c;
    bool operator==(const Line& other) const {
        return a == other.a && b == other.b && c == other.c;
    }
};

struct LineHash {
    std::size_t operator()(const Line& line) const {
        std::uint64_t value =
            static_cast<std::uint32_t>(line.a + 4096);
        value = value * 1315423911u
            + static_cast<std::uint32_t>(line.b + 4096);
        value = value * 2654435761u
            + static_cast<std::uint32_t>(line.c + 16777216);
        return static_cast<std::size_t>(value ^ (value >> 32));
    }
};

Line canonical_line(const Point& first, const Point& second) {
    long long a = second.y - first.y;
    long long b = first.x - second.x;
    long long c =
        static_cast<long long>(second.x) * first.y
        - static_cast<long long>(first.x) * second.y;
    long long divisor =
        std::gcd(std::llabs(a), std::gcd(std::llabs(b), std::llabs(c)));
    a /= divisor;
    b /= divisor;
    c /= divisor;
    if (a < 0 || (a == 0 && b < 0)) {
        a = -a;
        b = -b;
        c = -c;
    }
    return {
        static_cast<int>(a),
        static_cast<int>(b),
        static_cast<int>(c),
    };
}

long long collinear_triples(const std::vector<Point>& points) {
    std::unordered_map<Line, int, LineHash> pair_counts;
    const std::size_t point_count = points.size();
    pair_counts.reserve(point_count * point_count / 2);
    for (std::size_t first = 0; first < point_count; ++first) {
        for (std::size_t second = first + 1; second < point_count; ++second) {
            ++pair_counts[canonical_line(points[first], points[second])];
        }
    }
    long long total = 0;
    for (const auto& entry : pair_counts) {
        const int pairs = entry.second;
        if (pairs < 3) {
            continue;
        }
        // pairs = q(q-1)/2 for q selected points on the line.
        const int q = static_cast<int>(
            (1.0 + std::sqrt(1.0 + 8.0 * pairs)) / 2.0 + 0.5
        );
        if (q * (q - 1) / 2 != pairs) {
            std::cerr << "invalid pair count " << pairs << "\n";
            std::exit(2);
        }
        total += static_cast<long long>(q) * (q - 1) * (q - 2) / 6;
    }
    return total;
}

std::vector<Point> random_permutation_orbit(
    int n, std::mt19937_64& generator
) {
    const int m = n / 2;
    std::vector<int> permutation(m);
    std::iota(permutation.begin(), permutation.end(), 0);
    std::shuffle(permutation.begin(), permutation.end(), generator);
    std::vector<Point> points;
    points.reserve(4 * m);
    for (int x = 0; x < m; ++x) {
        Point point{x, permutation[x]};
        for (int turn = 0; turn < 4; ++turn) {
            points.push_back(point);
            point = {n - 1 - point.y, point.x};
        }
    }
    return points;
}

int main(int argc, char** argv) {
    if (argc < 4) {
        std::cerr
            << "usage: random_c4_conflict_scaling samples seed n [n ...]\n";
        return 2;
    }
    const int samples = std::stoi(argv[1]);
    const std::uint64_t seed = std::stoull(argv[2]);
    std::mt19937_64 generator(seed);
    for (int index = 3; index < argc; ++index) {
        const int n = std::stoi(argv[index]);
        if (n % 2 || n < 4) {
            std::cerr << "orders must be even and at least four\n";
            return 2;
        }
        long double sum = 0;
        long double sum_squares = 0;
        long long minimum = -1;
        long long maximum = 0;
        for (int sample = 0; sample < samples; ++sample) {
            const long long conflicts =
                collinear_triples(random_permutation_orbit(n, generator));
            sum += conflicts;
            sum_squares +=
                static_cast<long double>(conflicts) * conflicts;
            if (minimum < 0 || conflicts < minimum) {
                minimum = conflicts;
            }
            maximum = std::max(maximum, conflicts);
        }
        const long double mean = sum / samples;
        const long double variance =
            std::max<long double>(0, sum_squares / samples - mean * mean);
        std::cout
            << "{\"n\":" << n
            << ",\"samples\":" << samples
            << ",\"mean\":" << static_cast<double>(mean)
            << ",\"sd\":" << static_cast<double>(std::sqrt(variance))
            << ",\"minimum\":" << minimum
            << ",\"maximum\":" << maximum
            << ",\"mean_over_n_log_n\":"
            << static_cast<double>(mean / (n * std::log(n)))
            << "}\n";
    }
    return 0;
}
