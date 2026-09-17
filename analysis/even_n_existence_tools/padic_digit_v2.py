"""
p-adic 行列式分离码 v2 — 审计修正版。
修正：
1. 枚举全部 8 种 (π₀/π₁) 函数选择，非仅 4 种
2. 验证 F₁ 是双射（排列）
3. 检查 B=2, n=8 时 bit 压缩的正确性
4. 正确统计素数可除率
"""
import itertools, math, random, time, json
from collections import defaultdict

def bit_expand(x, k):
    bits = []
    for _ in range(k):
        bits.append(x & 1)
        x >>= 1
    return bits  # LSB first

def bit_compact(bits):
    x = 0
    for b in reversed(bits):
        x = (x << 1) | b
    return x

# ===== F0: 位反转 (标准排列 — 已验证双射) =====
def f0_bitrev(x_bits):
    return list(reversed(x_bits))

# ===== F1: 带 carry 的位排列 (需验证双射!) =====
def f1_digit_carry(x_bits):
    b0, b1, b2 = x_bits
    y0 = b0 ^ b1
    c0 = b0 & b1
    y1 = b1 ^ b2 ^ c0
    c1 = (b1 & b2) | (b1 & c0) | (b2 & c0)
    y2 = b2 ^ c1
    return [y0, y1, y2]

def verify_bijection(F_fn, n, k):
    """验证位函数产生双射"""
    seen = set()
    for x in range(n):
        xb = bit_expand(x, k)
        yb = F_fn(xb)
        y = bit_compact(yb)
        if y >= n:
            return False, f"output {y} >= {n}"
        if y in seen:
            return False, f"collision at x={x} → y={y}"
        seen.add(y)
    return len(seen) == n, "OK"

def make_permutation(F_fn, n, k):
    pi = [0] * n
    for x in range(n):
        xb = bit_expand(x, k)
        yb = F_fn(xb)
        pi[x] = bit_compact(yb)
    return pi

def check_all_8_choices(pi0, pi1, n):
    """
    枚举全部 2^3 = 8 种 (π₀/π₁) 赋值组合对三元组 (i,j,k)。
    返回 (total_triples_checked, total_collinear, prime_factor_counts)
    """
    pf = defaultdict(int)  # p → count of triples where det % p == 0
    total = 0
    collinear = 0

    for i, j, k in itertools.combinations(range(n), 3):
        # 8 种选择: 每种选 π₀ 或 π₁ 作为行 i,j,k 的 y 坐标
        for choice_mask in range(8):
            f_i = pi0 if (choice_mask & 1) else pi1
            f_j = pi0 if (choice_mask & 2) else pi1
            f_k = pi0 if (choice_mask & 4) else pi1
            yi, yj, yk = f_i[i], f_j[j], f_k[k]
            det = (j - i) * (yk - yi) - (k - i) * (yj - yi)
            total += 1
            if det == 0:
                collinear += 1
            else:
                d = abs(det)
                for p in [2, 3, 5, 7]:
                    if d % p == 0:
                        pf[p] += 1
    return total, collinear, dict(pf)

# ===== 测试 =====
print("=" * 64)
print("p-adic v2: 审计修正版")
print("=" * 64)

for n in [8, 16, 32, 64]:
    k = n.bit_length() - 1  # n = 2^k
    print(f"\n--- n={n} (k={k} bits) ---")

    # 验证双射
    ok_f0, msg0 = verify_bijection(f0_bitrev, n, k)
    ok_f1, msg1 = verify_bijection(f1_digit_carry, n, k)
    print(f"  F0 (bitrev) bijection: {ok_f0} {msg0}")
    print(f"  F1 (carry)   bijection: {ok_f1} {msg1}")

    if not ok_f0 or not ok_f1:
        print(f"  SKIP: need bijective permutations")
        continue

    pi0 = make_permutation(f0_bitrev, n, k)
    pi1 = make_permutation(f1_digit_carry, n, k)
    assert len(set(pi0)) == len(set(pi1)) == n

    # 完整 NTIL 检查
    pts = [(i, pi0[i]) for i in range(n)] + [(i, pi1[i]) for i in range(n)]
    n_pts = len(set(pts))
    n_collinear = sum(1 for p1, p2, p3 in itertools.combinations(pts, 3)
                      if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
    print(f"  Unique points: {n_pts}/{2*n}")
    print(f"  Collinear triples: {n_collinear} (0 = NTIL)")

    # 完整 8 型素数可除率
    total, coll, pf = check_all_8_choices(pi0, pi1, n)
    print(f"  Total triples checked (8-type): {total}")
    print(f"  Zero det: {coll} ({100*coll/total:.2f}%)")
    for p in [2, 3, 5, 7]:
        if p in pf:
            print(f"  p={p}: det%p==0 in {pf[p]}/{total-coll} non-zero dets "
                  f"({100*pf[p]/(total-coll):.1f}%)")

# 保存
print("\nDone.")
