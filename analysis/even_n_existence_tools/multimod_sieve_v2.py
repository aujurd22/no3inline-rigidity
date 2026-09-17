"""
多模数行列式筛 v2 — 审计修正版。
修正：
1. T_p(S) 是挑选的 2n 点中的共线三元组，非全 n² 格点
2. 包含 p > n 的大素数（每个最多整除一个 Δ）
3. 正确计算"预算"：C(2n,3) 个非零 Δ，每个的 log-素因子 ≤ 2log n
4. 区分"全 n² 点均匀分布" vs "2n 点 NTIL 配置"的超饱和下界
"""
import math, json
from collections import defaultdict

def primes_upto(m):
    sieve = [True] * (m + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(m ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, m + 1, i):
                sieve[j] = False
    return [i for i in range(m + 1) if sieve[i]]


def correct_budget(n):
    """
    正确预算：
    - 共 C(2n, 3) 个三元组（选自 2n 个点）
    - 每个非零 Δ 满足 |Δ| ≤ (n-1)²
    - Σ_{p|Δ} log p = log|Δ| ≤ 2 log(n-1) ≈ 2 log n
    - 但并非所有三元组都有非零 Δ（NTIL 要求全非零）
    - 预算 = C(2n,3) × 2 log n
    """
    n_triples = math.comb(2 * n, 3)
    return n_triples * 2 * math.log(n)


def modular_collinear_lower_bound(n, p):
    """
    模 p 共线三元组的 supersaturation 下界 — 仅针对挑选的 2n 点。
    
    关键观察：选中的 2n 个点分布在 n×n 网格中，每行/每列恰好 2 个。
    在 AG(2,p) 中，这 2n 个点落在 p² 个 residue class 中。
    
    方法：pigeonhole on residue classes。
    若 p ≤ n，AG(2,p) 有 p² 个 residue class。
    2n 个点 → 平均 2n/p² 个点 per class。
    
    更精细：每个含 L 个选中点的 AG(2,p) 直线贡献 C(L,3) 模共线三元组。
    但一条 AG(2,p) 直线可能对应网格中多条不同几何直线！
    
    这里用最保守：若 2n ≥ 3p(p+1)，至少有一条 AG(2,p) 直线含 ≥ 3 个选中点。
    每条这样的直线至少贡献 1 个模共线三元组。
    """
    if p > n:
        # 大素数：用 AG(2,p) 含 p²+p 条线，线长 p
        # 2n 个点随机分布在 p² 个 residue 中
        # 保守：pigeonhole → 至少 2n/p² 个点 per residue（太弱）
        return 0
    
    # p ≤ n: 用 AG(2,p) 的直线作为模共线的等价类
    # 但网格中的几何直线 ≠ AG(2,p) 直线！
    # AG(2,p) 直线捕捉的是 (ax+by ≡ c mod p) 而非几何共线
    # 
    # 正确方法：对每条 AG(2,p) 线，计算其上 SELECTED 点的数量
    # 这取决于具体的配置 S，不是均匀分布可以推导的
    #
    # 保守下界：用 double counting
    # 每条含 ≥3 个选中点的 AG(2,p) 线贡献 ≥1 个模共线三元组
    return 0  # 无配置无关（configuration-independent）的非平凡下界


def compute_sieve_v2(n):
    """
    正确版本：计算素因子预算，识别缺口。
    不做无配置假设的 supersaturation 估计。
    """
    budget = correct_budget(n)
    max_det = (n - 1) ** 2
    n_triples = math.comb(2 * n, 3)

    # 大素数约束
    large_primes = [p for p in primes_upto(max_det) if p > n]
    small_primes = [p for p in primes_upto(n) if p >= 2]

    print(f"n={n}:")
    print(f"  Budget = {budget:.1f} log-units (total)")
    print(f"  Total triples: {n_triples}")
    print(f"  Max |Δ| = {max_det}")
    print(f"  Large primes (>{n}): {len(large_primes)}")
    print(f"  Small primes (≤{n}): {len(small_primes)}")

    # 大素数约束的严格数学分析
    # 每个非零 Δ 最多含 1 个大素数因子（两 >n 的素数积 > n² > (n-1)²）
    # 所以 Σ_{p>n} T_p(S) ≤ n_triples（因为每个大素数需要不同的三元组）
    # 
    # 反过来：若对某大素数 p，我们能证明 T_p(S) ≥ K，
    # 则至少需要 K 个不同的三元组"承载"这个 p
    # 且这些三元组不能再承载其他大素数
    #
    # 关键缺口：需要带"行/列=2"约束的 T_p(S) 下界

    # 简单下界（无行列约束——太弱）
    # 2n 个点在 AG(2,p) 中 → pigeonhole 于 p² 个 residue
    # 平均 2n/p²，对 p ≤ √(2n/3) 可能 ≥ 3
    max_p_for_avg3 = int(math.sqrt(2 * n / 3))
    print(f"\n  若忽略行列约束：p ≤ {max_p_for_avg3} 时每 residue 平均 ≥3 点")
    print(f"  但行列约束强制 2n 点中每行每列各 2——完全改变分布！")
    print(f"  结论：需要 '带双排列边际的模共线 supersaturation 定理'")

    return {
        "n": n, "budget": budget, "n_triples": n_triples,
        "max_det": max_det, "n_large_primes": len(large_primes),
        "n_small_primes": len(small_primes),
        "max_p_for_avg3": max_p_for_avg3,
    }


# ===== 测试 =====
print("=" * 64)
print("Multi-modulus Sieve v2: 审计修正版")
print("=" * 64)

results = []
for n in [10, 20, 30, 50, 74]:
    r = compute_sieve_v2(n)
    results.append(r)
    print()

# 关键定量分析：n=74
n = 74
max_det = (n - 1) ** 2
large_primes = [p for p in primes_upto(max_det) if p > n]
print(f"\n{'='*64}")
print(f"n=74 大素数约束详细分析")
print(f"{'='*64}")
print(f"max|Δ| = {max_det}")
print(f"Large primes > {n}: {len(large_primes)} primes from {n+1} to {max_det}")

# 每个大素数 p，若 T_p(S) > 0，至少需要 T_p(S) 个不同三元组承载
# 如果对所有大素数 T_p(S) 总和 > n_triples → 矛盾证明不存在
# 但 T_p(S) 下界依赖于特定配置... 
# 真正的缺口：需要证明 2n 点配置中，大素数可除的三元组数有非平凡下界

n_triples = math.comb(2 * n, 3)
print(f"Total available triples: {n_triples}")
print(f"Per-triple budget: {max_det} (max |Δ|)")

# 反证框架：假设存在 NTIL 配置 S
# 则所有 Δ ≠ 0，每个 Δ 有素因子分解
# 所有素因子对数总和 ≤ n_triples × 2log(n)
# 若我们能证明 Σ_{p|Δ} log p 的期望下界超过预算 → 矛盾
# 但这需要对 S 的全局性质做假设

# 此时唯一的"硬"结论：
# 对任何 NTIL 配置，大素数的贡献 ≤ n_triples（每个三元组最多承载1个大素数）
# 所以若 Σ_{p>n} T_p(S) > n_triples → 矛盾
# 但目前无法不依赖配置地给 T_p(S) 下界

# 路径：用 Dirichlet's pigeonhole on slopes
# 在 2n 点中，有 2n 个不同的行 → 2n(2n-1)/2 对点
# 每对点定义一个方向向量 (dx, dy) with gcd=1
# 方向总数 ≤ max_det = 73² = 5329（因为每个非零方向向量都可归一化）
# 但 n=74 有 74² = 5476 个可能方向... 
# 
# 这导出：pigeonhole → 某些方向有多对点
# 每对同方向点构成一个潜在的共线三点

n_pairs = 2 * n * (2 * n - 1) // 2
n_directions = max_det  # 上界（归一化方向数）
print(f"\n方向 pigeonhole:")
print(f"  Point pairs: {n_pairs}")
print(f"  Max distinct directions: {n_directions}")
print(f"  Average pairs per direction: {n_pairs/n_directions:.1f}")
if n_pairs > n_directions:
    print(f"  ★ Pigeonhole: some direction has multiple pairs → collinearity risk!")

json.dump(results, open("sieve_v2_results.json", "w"), indent=2)
print(f"\nResults saved to sieve_v2_results.json")
