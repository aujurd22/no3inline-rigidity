"""
多模数行列式筛の严格化——带双排列边际条件。

[math-skill-audit] 审计要点:
1. 区分 "模 p 零行列式" 和 "整数零行列式"——前者多得多
2. 行列式预算: 每个非零 det |Δ|≤(n-1)², 且 ∑_{p|Δ} log p ≤ 2 log n
3. T_p(S) 下界必须考虑双排列约束——不是 uniform random subset

核心问题: 对最优双排列 S, ∑_p T_p(S) log p 的最小值是多少?
若最小值超过预算 → 证明不存在; 若远低于预算 → 筛子不work.
"""
import itertools, math, random, json
from collections import Counter, defaultdict
sys_path = '.'
import sys; sys.path.insert(0, sys_path)

def compute_prime_budget(n):
    """行列式素因子预算: 每个三重积的 |det|≤(n-1)², 素因子 log 和 ≤ 2log n"""
    return 2 * math.log(n)

def compute_det_factor_cost(det):
    """单个非零行列式的素因子和 (log形式)"""
    if det == 0:
        return float('inf')
    d = abs(det)
    total = 0
    p = 2
    while p * p <= d:
        while d % p == 0:
            total += math.log(p)
            d //= p
        p += 1 if p == 2 else 2
    if d > 1:
        total += math.log(d)
    return total

def compute_Tp(pi0, pi1, n, primes_to_check):
    """计算每个素数的 T_p(S) = 行列式 mod p = 0 的三元组数"""
    Tp = {p: 0 for p in primes_to_check}
    zero_count = 0
    total = 0
    all_dets = []

    for i, j, k in itertools.combinations(range(n), 3):
        for mask in range(8):
            fi = pi0 if (mask & 1) else pi1
            fj = pi0 if (mask & 2) else pi1
            fk = pi0 if (mask & 4) else pi1
            det = (j - i) * (fk[k] - fi[i]) - (k - i) * (fj[j] - fi[i])
            total += 1
            if det == 0:
                zero_count += 1
            else:
                all_dets.append(abs(det))
                for p in primes_to_check:
                    if det % p == 0:
                        Tp[p] += 1

    return Tp, zero_count, total, all_dets

def compute_total_cost(Tp, zero_count, primes_to_check):
    """计算总素因子开销 = ∑_p T_p log p + zero_count * ∞"""
    if zero_count > 0:
        return float('inf'), "有整数零行列式"
    total = sum(Tp[p] * math.log(p) for p in primes_to_check)
    return total, f"{total:.1f}"

def analyze_known_solutions():
    """分析已知NTIL解 (m=5,10,14,36 rot4 + CP-SAT发现的小n非对合解)"""
    from validate_solver import load_positive

    # 已知 rot4 解的双排列提取
    solutions = {}

    # CP-SAT 发现的解 (from earlier experiments)
    solutions['n=8_cpsat'] = (
        [1, 5, 7, 2, 0, 6, 4, 3],  # pi
        [7, 3, 1, 5, 2, 0, 6, 4],  # sigma
        8
    )
    solutions['n=10_cpsat'] = (
        [4, 2, 8, 0, 3, 1, 5, 7, 6, 9],
        [5, 8, 6, 9, 0, 2, 7, 1, 3, 4],
        10
    )

    # 提取 rot4 解的双排列 (使用之前的 BFS 着色方法)
    from collections import defaultdict
    from validate_solver import c4_lifts_n

    for m_val, label in [(5, 'm=5_rot4'), (10, 'm=10_rot4'),
                          (14, 'm=14_rot4'), (36, 'm=36_rot4')]:
        try:
            edges, bits, src = load_positive(m_val)
            N = 2 * m_val
            pts = {}
            for idx, ((u, v), b) in enumerate(zip(edges, bits)):
                dc = (v, u) if b else (u, v)
                for pt in c4_lifts_n(dc, N):
                    pts[pt] = idx

            row_ps = defaultdict(list)
            for (x, y) in pts:
                row_ps[x].append(y)

            col_g = defaultdict(set)
            for x, ys in row_ps.items():
                if len(ys) >= 2:
                    col_g[ys[0]].add(ys[1])
                    col_g[ys[1]].add(ys[0])

            color = {}
            for y in range(N):
                if y in color:
                    continue
                stack = [(y, 0)]
                while stack:
                    cy, c = stack.pop()
                    if cy in color:
                        continue
                    color[cy] = c
                    for ny in col_g[cy]:
                        if ny not in color:
                            stack.append((ny, 1 - c))

            pi = [0] * N
            sigma = [0] * N
            for x in range(N):
                ys = row_ps.get(x, [])
                if len(ys) >= 2:
                    if color.get(ys[0], 0) == 0:
                        pi[x] = ys[0]
                        sigma[x] = ys[1]
                    else:
                        pi[x] = ys[1]
                        sigma[x] = ys[0]

            solutions[label] = (pi, sigma, N)
        except Exception as e:
            print(f"  {label}: 提取失败 {e}")

    return solutions


# ── 主程序 ──
print("=" * 64)
print("多模数筛子: 已知 NTIL 解的素因子预算分析")
print("=" * 64)

solutions = analyze_known_solutions()

# 选择相关素数: p≤n (在行列式范围内有意义的素数)
for name, (pi, sigma, n) in solutions.items():
    primes = [p for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
              if p <= n]
    primes_large = [p for p in [41, 43, 47, 53, 59, 61, 67, 71, 73]
                    if p > n and p <= 2 * n]

    Tp, zero_count, total, all_dets = compute_Tp(pi, sigma, n, primes + primes_large)
    cost, cost_str = compute_total_cost(Tp, zero_count, primes + primes_large)
    budget = compute_prime_budget(n)
    budget_per_triple = budget * math.comb(2 * n, 3) if zero_count == 0 else float('inf')

    print(f"\n{'='*40}")
    print(f"{name}: n={n}, 总三元组={total}")
    print(f"  整数零行列式: {zero_count} (应为 0)")
    print(f"  行列式 budget: {budget:.2f} log-units / non-zero det")
    print(f"  总 budget (all triples): {budget_per_triple:.0f}")

    if zero_count == 0:
        actual_cost = sum(Tp[p] * math.log(p) for p in primes + primes_large)
        print(f"  实际素因子开销: {actual_cost:.0f}")
        print(f"  开销/预算比: {actual_cost / budget_per_triple:.2f}")

        # 关键分析: p > n 的素数各自能"claim"多少三元组?
        large_p_claims = {p: Tp[p] for p in primes_large if Tp[p] > 0}
        if large_p_claims:
            print(f"  大素数 (p>{n}) claims: {large_p_claims}")
            # 每个 p>n 的三元组只能被这一个素数整除
            # (因为两个 >n 的素数之积 > (n-1)²)
            total_large_claims = sum(large_p_claims.values())
            print(f"  总大素数 claims: {total_large_claims}")
            print(f"  大素数 claim / 三元组数: {total_large_claims / total:.4f}")

        # 分析 T_p 的分布: 是否存在某些 p 异常高?
        print(f"  T_p (p≤n):")
        for p in primes:
            if Tp[p] > 0:
                expected = total / p  # naive expectation
                ratio = Tp[p] / expected if expected > 0 else float('inf')
                print(f"    p={p:2d}: T_p={Tp[p]:4d} (exp={expected:.0f}, ratio={ratio:.2f})")

print("\n" + "=" * 64)
print("外推到 n=74")
print("=" * 64)

# n=74 的预算
n74 = 74
budget74 = compute_prime_budget(n74)
total_triples_74 = math.comb(2 * n74, 3)  # C(148, 3)
total_budget_74 = budget74 * total_triples_74
print(f"n=74: budget={total_budget_74:.0f} log-units")
print(f"  三元组数: {total_triples_74}")

# 大素数 (n < p ≤ (n-1)² ≈ 5329): 太多了
# 关键素数: p > n 且 p ≤ 2n (73 < p ≤ 148)
large_primes_74 = [p for p in [79, 83, 89, 97, 101, 103, 107, 109, 113,
                                127, 131, 137, 139] if p > 74]
print(f"  大素数 (74 < p ≤ 148): {len(large_primes_74)} 个")

# 如果每个大素数 p 能 claim T_p 个三元组，
# 且每个三元组最多被一个 >n 的素数整除，
# 则所有大素数的 claim 之和不能超过总三元组数。
# 这本身是一个平凡约束——关键是证下界。

# 从已知 n=36 解的 T_p 趋势外推 n=74:
# n=36 解的 T_p/p 比预期低还是高?
print("\n需要实际 n=36 rot4 解的 T_p 数据来进行外推——等待数据...")
