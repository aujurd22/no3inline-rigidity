"""
p-adic 行列式分离码 PoC — B=2, n=8 (3-bit)
核心：构造两个排列 F₀, F₁，使任意三点行列式的最低非零位 ≠ 0 mod B。
若成功：行列式 ≠ 0 → NTIL 解！

方法：
- x = x₀ + x₁·B + x₂·B² (bit expansion)
- F(x) = digit-wise mapping with carry state
- 行列式 p-adic 分析：从最低位逐位检查
"""
import itertools, math, random, time, json
from collections import defaultdict, Counter

def bit_expand(x, k):
    """将整数 x 展开为 k 个 B 进制的位"""
    bits = []
    for _ in range(k):
        bits.append(x % 2)
        x //= 2
    return bits  # LSB first


def bit_compact(bits, B=2):
    """从位数组压缩回整数"""
    x = 0
    for b in reversed(bits):
        x = x * B + b
    return x


def digit_permutation_f0(x_bits):
    """
    F₀: 简单的位反转排列
    输入: x 的 3 个 bit
    输出: y 的 3 个 bit (也是 0..7 的排列)
    """
    # 简单映射：位反转
    return list(reversed(x_bits))


def digit_permutation_f1(x_bits):
    """
    F₁: 带 carry 的位排列
    尝试在位层面引入非线性
    """
    b0, b1, b2 = x_bits
    # 低位: x₀ XOR x₁
    y0 = b0 ^ b1
    # 中位: x₁ XOR x₂ XOR carry₀ (carry₀ = b0 AND b1)
    c0 = b0 & b1
    y1 = b1 ^ b2 ^ c0
    # 高位: x₂ XOR carry₁
    c1 = (b1 & b2) | (b1 & c0) | (b2 & c0)
    y2 = b2 ^ c1
    return [y0, y1, y2]


def make_permutation(F_fn, n, B=2):
    """从位函数构造排列 pi : [0..n-1] → [0..n-1]"""
    k = n.bit_length() - 1  # n = 2^k
    pi = [0] * n
    for x in range(n):
        x_bits = bit_expand(x, k)
        y_bits = F_fn(x_bits)
        y = bit_compact(y_bits, B)
        pi[x] = y % n  # 确保在范围内
    return pi


def check_ntil(pi0, pi1, n):
    """检查双排列是否为 NTIL"""
    from itertools import combinations
    pts = [(i, pi0[i]) for i in range(n)] + [(i, pi1[i]) for i in range(n)]
    bad = 0
    for p1, p2, p3 in combinations(pts, 3):
        x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            bad += 1
            if bad <= 3:
                print(f"    collinear: {p1}, {p2}, {p3}")
    return bad == 0, bad


def p_adic_determinant_check(pi0, pi1, n, p=2):
    """
    p-adic 行列式分析：对每个三元组，检查最低非零位是否 ≠ 0 mod p
    """
    k = n.bit_length() - 1  # n = 2^k
    from itertools import combinations

    triples_checked = 0
    all_nonzero_lsb = 0  # 所有三元组的最低非零位 ≠ 0 mod p

    for i, j, kk in combinations(range(n), 3):
        triples_checked += 1

        # 三个可能的排列选择: 可以用 (pi0,pi0,pi0), (pi0,pi0,pi1), ...
        # 简化：只检查 (pi0, pi0, pi0) 类型
        for f_choice in [(pi0, pi0, pi0), (pi0, pi0, pi1),
                          (pi0, pi1, pi1), (pi1, pi1, pi1)]:
            f_i, f_j, f_k = f_choice
            yi, yj, yk = f_i[i], f_j[j], f_k[kk]

            # 行列式 = (j-i)(yk-yi) - (k-i)(yj-yi)
            # 展开为 p-adic 位
            det = (j - i) * (yk - yi) - (kk - i) * (yj - yi)
            if det == 0:
                # 整数行列式 = 0 → 失败
                continue

            # 找最低非零位
            v = abs(det)
            lsb = 0
            while v % p == 0:
                v //= p
                lsb += 1

            # 在某一位应该 ≠ 0 mod p
            # det / p^lsb mod p
            if (det // (p ** lsb)) % p != 0:
                all_nonzero_lsb += 1

    return triples_checked, all_nonzero_lsb


# ===== 测试 =====
n = 8
k = 3
B = 2

print("=" * 60)
print(f"p-adic digit code PoC: B={B}, n={n} ({k} bits)")
print("=" * 60)

# F₀: bit-reversal
pi0 = make_permutation(digit_permutation_f0, n, B)
pi1 = make_permutation(digit_permutation_f1, n, B)

print(f"\npi0 (bit-reversal) = {pi0}")
print(f"pi1 (digit-carry)  = {pi1}")

# 验证排列
assert len(set(pi0)) == n, "pi0 not a permutation!"
assert len(set(pi1)) == n, "pi1 not a permutation!"

# NTIL 检查
ok, n_bad = check_ntil(pi0, pi1, n)
print(f"\nNTIL check: {'OK' if ok else f'{n_bad} collinear triples'}")

# p-adic 分析
triples, nonzero_lsb = p_adic_determinant_check(pi0, pi1, n, p=2)
print(f"\np-adic analysis: {triples} triples checked")
print(f"  Nonzero LSB count: {nonzero_lsb}")

# 也测试随机排列作对比
print(f"\n{'='*60}")
print(f"Control: random permutations")
print(f"{'='*60}")
random.seed(42)
for trial in range(3):
    rpi0 = list(range(n)); random.shuffle(rpi0)
    rpi1 = list(range(n)); random.shuffle(rpi1)
    # 确保 pi0 != pi1
    while rpi1 == rpi0:
        random.shuffle(rpi1)
    ok, n_bad = check_ntil(rpi0, rpi1, n)
    print(f"  trial{trial}: {'OK' if ok else f'{n_bad} collinear'}")

# 保存
res = {
    "n": n, "B": B, "k": k,
    "pi0_bit_reversal": pi0,
    "pi1_digit_carry": pi1,
    "ntil_ok": ok,
    "n_collinear": n_bad,
}
json.dump(res, open("padic_digit_results.json", "w"), indent=2)
print(f"\nResults saved to padic_digit_results.json")
