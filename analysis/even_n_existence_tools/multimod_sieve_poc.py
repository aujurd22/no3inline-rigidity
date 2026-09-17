"""
多模数行列式筛 PoC — n=74 起
核心：若 Σ_p T_p(S) log p > (每行列式素因子预算) → 不存在 2n 点 NTIL

步骤：
1. 对每个素数 p > n，计算模 p 共线三元组的 supersaturation 下界
2. 累计素因子预算
3. 若下界超过预算 → 证明不存在
"""
import math, itertools, json, time
from collections import defaultdict

def primes_upto(m):
    """埃拉托色尼筛法"""
    sieve = [True] * (m + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(m ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, m + 1, i):
                sieve[j] = False
    return [i for i in range(m + 1) if sieve[i]]


def determinant_budget(n):
    """
    每个非零行列式 |Δ| ≤ (n-1)² 的素因子对数预算
    Σ_{p|Δ} log p ≤ 2 log n
    因此全部 C(2n,3) 个三元组的总素因子预算：
    budget = C(2n,3) × 2 log n
    """
    n_triples = math.comb(2 * n, 3)
    return n_triples * 2 * math.log(n)


def supersaturation_lower_bound(n, p):
    """
    模 p 共线三元组的 supersaturation 下界
    基于有限仿射平面 AG(2,p) 的弧理论

    若 p ≤ n，每个含 L 格点的线产生 C(L,3) 模共线三元组
    最粗糙下界：n² 个格点在 AG(2,p) 中 → 至少 n²/p² 个点落在同一条模 p 线上

    精化：AG(2,p) 共有 p²+p 条线，每条线 p 个点。
    随机均匀分布下 E[一条线上的点数] = n²/(p+1)p ≈ n²/p²
    实际可能有更多

    这里用最保守的 pigeonhole 下界
    """
    if p <= n:
        # AG(2,p) 共有 p(p+1) 条线，每条线 p 个点
        # n² 个格点分配到 p(p+1) 条线 → 平均每线 n²/(p²+p) 个点
        avg = n * n / (p * p + p)
        # 若 avg ≥ 3，至少有一条线有 ≥ 3 个点
        if avg >= 3:
            # 每线至少 C(⌊avg⌋, 3) 个三元组，共 p(p+1) 条线
            pts_per_line = int(avg)
            per_line = math.comb(pts_per_line, 3) if pts_per_line >= 3 else 0
            total = p * (p + 1) * per_line
            return total
    return 0


def compute_sieve(n, max_p=None):
    """
    对给定 n，计算素因子预算 vs supersaturation 下界
    """
    if max_p is None:
        max_p = (n - 1) ** 2 + 1  # Δ max = (n-1)²

    budget = determinant_budget(n)
    primes = primes_upto(max_p)

    results = []
    total_lower_bound = 0

    for p in primes:
        lb = supersaturation_lower_bound(n, p)
        if lb > 0:
            contribution = lb * math.log(p)
            total_lower_bound += contribution
            results.append({
                "p": p, "triples_lb": lb, "log_contribution": contribution
            })

    feasible = total_lower_bound <= budget

    return {
        "n": n, "budget": budget,
        "total_lower_bound": total_lower_bound,
        "feasible": feasible,
        "n_primes": len(results),
        "top_primes": sorted(results, key=lambda x: -x["log_contribution"])[:10],
    }


# ===== 测试 =====
print("=" * 60)
print("Multi-modulus Determinant Sieve")
print("=" * 60)

for n in [10, 20, 30, 50, 74]:
    result = compute_sieve(n)
    print(f"\nn={n}:")
    print(f"  Budget = {result['budget']:.1f} log-units")
    print(f"  Lower bound = {result['total_lower_bound']:.1f}")
    print(f"  Feasible = {result['feasible']} ({result['n_primes']} primes)")
    print(f"  Ratio = {result['total_lower_bound']/result['budget']:.4f}")

    if result['top_primes']:
        print(f"  Top contributing primes:")
        for r in result['top_primes'][:5]:
            print(f"    p={r['p']}: {r['triples_lb']} triples × log(p)={r['log_contribution']:.1f}")

# 约束：p > n 的大素数只有有限个能整除同一 Δ
print(f"\n{'='*60}")
print("Large prime constraint (p > n)")
print(f"{'='*60}")
n = 74
max_det = (n - 1) ** 2
large_primes = [p for p in primes_upto(max_det) if p > n]
print(f"n={n}, max|Δ|={max_det}")
print(f"Large primes (>{n}): {len(large_primes)}")
print(f"Constraint: each non-zero Δ can contain at most ONE prime > n")
print(f"  (because product of two primes > n exceeds {(n-1)**2})")

# 这意味：对每个大素数 p，T_p(S) 必须被"容纳"到至少 T_p(S) 个不同的 Δ 中
# 但总共只有 C(2n,3) ≈ 530K 个行列式
# 若 Σ_{p>n} T_p(S) >> 530K → 必定存在矛盾
total_triples = math.comb(2 * n, 3)
print(f"Total triples: {total_triples}")
print(f"Each large prime requires its own distinct triples set")

# 简单下界：n² 个点，AG(2,p) 每条线 p 个点
# 平均每条模 p 线 n²/p² 个点，若 ≥ 3 则每线 ≥ 1 模共线三元组
# p(p+1) 条线 × 1 = O(p²) 个三元组 per prime > n
# Σ_{p>n}^{n²} p² ≈ n⁶/3 → 远超 budget
# 这说明这个原始下界太宽松，需要约束到"同时满足行/列=2"的条件

print("\nNote: current lower bound is too loose (doesn't enforce row/col=2).")
print("Need supersaturation theorem WITH double-permutation constraints!")
print("This is the core missing ingredient for the sieve.")

json.dump([compute_sieve(n) for n in [10, 20, 30, 50, 74]],
          open("sieve_results.json", "w"), indent=2)
print("\nResults saved to sieve_results.json")
