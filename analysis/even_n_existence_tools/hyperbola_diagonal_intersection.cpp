#include <algorithm>
#include <bit>
#include <cstdint>
#include <iostream>
#include <limits>
#include <numeric>
#include <utility>
#include <vector>

long long mod_inverse(long long value, long long p) {
    long long result = 1;
    long long exponent = p - 2;
    while (exponent) {
        if (exponent & 1) {
            result = result * value % p;
        }
        value = value * value % p;
        exponent >>= 1;
    }
    return result;
}

bool is_prime(int value) {
    if (value < 2) {
        return false;
    }
    for (int divisor = 2;
         static_cast<long long>(divisor) * divisor <= value;
         ++divisor) {
        if (value % divisor == 0) {
            return false;
        }
    }
    return true;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: hyperbola_diagonal_intersection p [p ...]\n";
        return 2;
    }
    for (int argument = 1; argument < argc; ++argument) {
        const int p = std::stoi(argv[argument]);
        if (!is_prime(p) || p == 2) {
            std::cerr << p << " is not an odd prime\n";
            return 2;
        }
        const int plus_count = 2 * p - 3;
        const int total_lines = 2 * plus_count;
        const int words = (total_lines + 63) / 64;
        std::vector<std::vector<std::uint64_t>> signatures(
            p, std::vector<std::uint64_t>(words)
        );
        std::vector<int> counts(total_lines);
        for (int multiplier = 1; multiplier < p; ++multiplier) {
            std::fill(counts.begin(), counts.end(), 0);
            for (int x = 1; x < p; ++x) {
                const int y = static_cast<int>(
                    static_cast<long long>(multiplier)
                    * mod_inverse(x, p) % p
                );
                const int plus_index = y - x + (p - 2);
                const int minus_index =
                    plus_count + (x + y - 2);
                ++counts[plus_index];
                ++counts[minus_index];
            }
            for (int line = 0; line < total_lines; ++line) {
                if (counts[line] >= 2) {
                    signatures[multiplier][line / 64]
                        |= std::uint64_t{1} << (line % 64);
                }
            }
        }
        int minimum = std::numeric_limits<int>::max();
        int maximum = 0;
        long long sum = 0;
        long long pair_count = 0;
        std::pair<int, int> minimum_pair;
        for (int first = 1; first < p; ++first) {
            for (int second = first + 1; second < p; ++second) {
                int intersection = 0;
                for (int word = 0; word < words; ++word) {
                    intersection += std::popcount(
                        signatures[first][word]
                        & signatures[second][word]
                    );
                }
                if (intersection < minimum) {
                    minimum = intersection;
                    minimum_pair = {first, second};
                }
                maximum = std::max(maximum, intersection);
                sum += intersection;
                ++pair_count;
            }
        }
        std::cout
            << "{\"p\":" << p
            << ",\"minimum\":" << minimum
            << ",\"minimum_pair\":[" << minimum_pair.first
            << "," << minimum_pair.second << "]"
            << ",\"maximum\":" << maximum
            << ",\"mean\":"
            << static_cast<double>(sum) / pair_count
            << "}\n";
    }
}
