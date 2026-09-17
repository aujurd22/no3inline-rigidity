"""
Radon–Birkhoff 多尺度整数化 PoC — n=8 起
核心：从 A⁰_xy=2/n 的分数矩阵出发，沿交替环舍入到 {0,1}，
同时保持所有含 ≥3 个格点的直线 R_ℓ(A) ≤ 2。

算法：
1. 初始化 A = 全 2/n 矩阵 (n×n)
2. 找一条行列约束的交替环（二分图 cycle）
3. 计算沿环可推的最大 ε (受限于 0≤A≤1 和所有 R_ℓ ≤ 2)
4. 推 ε → 更新 A → 重复
5. 若最终所有 A_xy ∈ {0,1} 且 R_ℓ ≤ 2 → 成功！
"""
import itertools, math, random, time, json
from collections import defaultdict

def build_lines(n):
    """生成 n×n 网格中所有含 ≥3 个格点的直线，去重"""
    lines_set = set()
    for dx in range(n):
        dy_start = -n + 1 if dx > 0 else 0
        for dy in range(dy_start, n):
            if dx == 0 and dy <= 0:
                continue
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            sx, sy = dx // g, dy // g
            for x0 in range(n):
                for y0 in range(n):
                    pts = []
                    x, y = x0, y0
                    while 0 <= x < n and 0 <= y < n:
                        pts.append((x, y))
                        x += sx
                        y += sy
                    if len(pts) >= 3:
                        lines_set.add(tuple(sorted(pts)))
    return [list(ln) for ln in lines_set]


def fractional_init(n):
    """初始化 A⁰_xy = 2/n"""
    return {(x, y): 2.0 / n for x in range(n) for y in range(n)}


def find_alternating_cycle(A, n):
    """
    在分数矩阵中找一个交替环：偶数位置的变量增大，奇数位置减小。
    环由行列交替构成：(x₀,y₀) → (x₀,y₁) → (x₁,y₁) → (x₁,y₀) → ...
    返回 list of (x,y,delta_sign) where delta_sign=+1 or -1
    """
    # 找一条有分数值的 4-环作为简化的交替环
    frac_entries = [(x, y) for (x, y), v in A.items() if 0 < v < 1]
    if len(frac_entries) < 4:
        return None

    random.shuffle(frac_entries)
    # 尝试前 20 个条目找 4-环
    for idx1, (x0, y0) in enumerate(frac_entries[:min(20, len(frac_entries))]):
        for idx2, (x1, y1) in enumerate(frac_entries[:min(20, len(frac_entries))]):
            if idx1 == idx2 or x0 == x1 or y0 == y1:
                continue
            # 检查 (x0,y1) 和 (x1,y0) 是否存在且有分数值
            if (x0, y1) in A and (x1, y0) in A:
                v2 = A.get((x0, y1), 0)
                v3 = A.get((x1, y0), 0)
                if 0 <= v2 <= 1 and 0 <= v3 <= 1:
                    # 交替环：(x0,y0)+ε, (x0,y1)-ε, (x1,y1)+ε, (x1,y0)-ε
                    # 保持行列和不变
                    cycle = [(x0, y0, +1), (x0, y1, -1),
                             (x1, y1, +1), (x1, y0, -1)]
                    return cycle
    return None


def max_epsilon(A, cycle, lines, n):
    """计算沿环可推的最大 ε，受限于 0≤A≤1 和所有 R_ℓ≤2"""
    eps_max = float('inf')

    # 边界约束：0 ≤ A+δ ≤ 1
    for x, y, sign in cycle:
        v = A.get((x, y), 0)
        if sign > 0:
            eps_max = min(eps_max, 1.0 - v)
        else:
            eps_max = min(eps_max, v)
    if eps_max <= 0:
        return 0

    # Radon 线约束：对每条含环中点的线，R_ℓ + ΔR_ℓ ≤ 2
    affected_lines = defaultdict(int)  # line_index → delta_sum
    for x, y, sign in cycle:
        # 找含 (x,y) 的所有线 (简化: 只检查线的 delta 是否会使 R>2)
        # 实际上需要用更高效的方法
        pass

    # 简化版：不检查线约束，直接推 ε，然后整体验证
    # 完整版需要 O(|lines|) 的增量子问题
    # 先用贪心 ε 然后外验
    return min(eps_max, 0.5)  # 保守步长


def verify_radon(A, lines, n):
    """检查所有 Radon 线是否 ≤ 2"""
    violations = []
    for idx, line in enumerate(lines):
        r = sum(A.get(p, 0) for p in line)
        if r > 2 + 1e-9:
            violations.append((idx, line, r))
    return violations


def radon_birkhoff_rounding(n, max_iter=5000):
    """
    Radon–Birkhoff 多尺度整数化主循环。
    返回 (A_final, success, stats)
    """
    A = fractional_init(n)
    lines = build_lines(n)
    print(f"n={n}: {len(lines)} lines, starting with A=2/n")

    stats = {"iterations": 0, "eps_total": 0, "violations": 0,
             "integer_vars": 0, "frac_vars": n * n}

    for it in range(max_iter):
        # 统计分数变量
        frac_count = sum(1 for v in A.values() if 0 < v < 1)
        if frac_count == 0:
            print(f"  [{it}] All integer! Checking Radon...")
            viols = verify_radon(A, lines, n)
            if not viols:
                return A, True, stats
            print(f"  VIOLATIONS: {len(viols)} lines exceed 2")
            # 尝试修复：对违规线中的分数点加约束
            return A, False, stats

        cycle = find_alternating_cycle(A, n)
        if cycle is None:
            print(f"  [{it}] No cycle found, {frac_count} fractional vars remain")
            break

        eps = max_epsilon(A, cycle, lines, n)
        if eps < 1e-12:
            eps = 0.1 / n  # 固定小步长
            # 但在验证前先推
            pass

        # 应用
        for x, y, sign in cycle:
            A[(x, y)] = A.get((x, y), 0) + sign * eps

        stats["iterations"] += 1
        stats["eps_total"] += eps

        if it % 200 == 0:
            viols = verify_radon(A, lines, n)
            n_int = sum(1 for v in A.values() if abs(v) < 1e-12 or abs(v - 1) < 1e-12)
            frac = n * n - n_int
            print(f"  [{it}] frac={frac} viols={len(viols)} eps={eps:.4f}")

        # 验证线约束；若违规则回滚
        viols = verify_radon(A, lines, n)
        if viols:
            for x, y, sign in cycle:
                A[(x, y)] = A.get((x, y), 0) - sign * eps
            stats["violations"] += 1

    return A, False, stats


def extract_solution(A, n):
    """从 A 的 {0,1} 值提取 NTIL 候选点集"""
    pts = [(x, y) for (x, y), v in A.items() if abs(v - 1) < 1e-9]
    return pts


# ===== 主测试 =====
if __name__ == "__main__":
    for n in [6, 8, 10]:
        print(f"\n{'='*60}")
        print(f"Radon–Birkhoff 舍入: n={n}")
        print(f"{'='*60}")
        t0 = time.time()
        A_final, success, stats = radon_birkhoff_rounding(n, max_iter=3000)
        elapsed = time.time() - t0

        n_int = sum(1 for v in A_final.values()
                    if abs(v) < 1e-12 or abs(v - 1) < 1e-12)
        pts = extract_solution(A_final, n)

        print(f"\nResult: success={success} int_vars={n_int}/{n*n} "
              f"pts={len(pts)} time={elapsed:.1f}s")

        if success:
            # NTIL verification
            bad = 0
            for p1, p2, p3 in itertools.combinations(pts, 3):
                x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
                if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                    bad += 1
            print(f"NTIL check: {bad} collinear triples (should be 0)")

        # 保存
        res = {"n": n, "success": success, "n_int": n_int,
               "n_pts": len(pts), "time": elapsed, "stats": stats}
        # 追加到文件
        try:
            all_res = json.load(open("radon_birkhoff_results.json"))
        except (FileNotFoundError, json.JSONDecodeError):
            all_res = []
        all_res.append(res)
        json.dump(all_res, open("radon_birkhoff_results.json", "w"), indent=2)
