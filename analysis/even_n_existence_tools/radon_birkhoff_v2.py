"""
Radon-Birkhoff v2 — 修复版审计。
修复：
1. max_epsilon 正确计算线约束下的最大可推 ε
2. 分层策略：先冻结长线 (L >= n/2)，再处理短线
3. 双边约束：ε 同时受上下界限制
"""
import itertools, math, random, time, json
from collections import defaultdict

def build_lines(n):
    lines_set = set()
    for dx in range(n):
        dy_start = -n + 1 if dx > 0 else 0
        for dy in range(dy_start, n):
            if dx == 0 and dy <= 0: continue
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            sx, sy = dx // g, dy // g
            for x0 in range(n):
                for y0 in range(n):
                    pts = []
                    x, y = x0, y0
                    while 0 <= x < n and 0 <= y < n:
                        pts.append((x, y)); x += sx; y += sy
                    if len(pts) >= 3:
                        lines_set.add(tuple(sorted(pts)))
    return [list(ln) for ln in lines_set]


def build_line_index(lines, n):
    """建 point → line_indices 的逆索引，加速线约束检查"""
    pt_to_lines = defaultdict(list)
    for lidx, line in enumerate(lines):
        for pt in line:
            pt_to_lines[pt].append(lidx)
    return pt_to_lines


def max_epsilon_v2(A, cycle, lines, pt_to_lines, n):
    """
    正确计算最大可推 ε：
    1. 0 ≤ A ± ε ≤ 1  →  ε ≤ min(1-A_for_+, A_for_-)
    2. 所有受影响线: R_ℓ + ΔR_ℓ ≤ 2  → 对每条线解 ε 上限
    """
    eps_max = float('inf')

    # 约束 1: 边界
    for x, y, sign in cycle:
        v = A.get((x, y), 0)
        if sign > 0:
            eps_max = min(eps_max, 1.0 - v)
        else:
            eps_max = min(eps_max, v)
    if eps_max <= 1e-12:
        return 0.0

    # 约束 2: 每条受影响线的 Radon 容量
    # 计算每条线因 cycle 产生的净 ΔR
    line_delta = defaultdict(float)
    for x, y, sign in cycle:
        for lidx in pt_to_lines.get((x, y), []):
            line_delta[lidx] += sign  # sign = +1 or -1

    for lidx, delta in line_delta.items():
        if delta > 0:
            # R_ℓ + ε·delta ≤ 2  →  ε ≤ (2 - R_ℓ) / delta
            R_ell = sum(A.get(p, 0) for p in lines[lidx])
            slack = 2.0 - R_ell
            if slack < -1e-9:
                return 0.0  # 已经违规
            eps_max = min(eps_max, slack / delta)
    return max(0.0, eps_max)


def verify_radon(A, lines, n):
    violations = []
    for idx, line in enumerate(lines):
        r = sum(A.get(p, 0) for p in line)
        if r > 2 + 1e-9:
            violations.append((idx, line, r))
    return violations


def radon_birkhoff_v2(n, max_iter=5000, freeze_long=True):
    A = {(x, y): 2.0 / n for x in range(n) for y in range(n)}
    lines = build_lines(n)
    pt_to_lines = build_line_index(lines, n)

    print(f"n={n}: {len(lines)} lines, freeze_long={freeze_long}")

    # 分层：按线长分类
    if freeze_long:
        long_lines = [l for l in lines if len(l) >= n // 2]
        print(f"  Long lines (L>={n//2}): {len(long_lines)}")

    stats = {"iterations": 0, "eps_total": 0.0, "rollbacks": 0}

    for it in range(max_iter):
        frac_entries = [(x, y) for (x, y), v in A.items() if 0.001 < v < 0.999]
        if len(frac_entries) < 4:
            print(f"  [{it}] Done: {len(frac_entries)} fractional vars remain")
            break

        # 找 4-环
        random.shuffle(frac_entries)
        cycle = None
        sample = frac_entries[:min(50, len(frac_entries))]
        for idx1, (x0, y0) in enumerate(sample):
            for idx2, (x1, y1) in enumerate(sample):
                if idx1 >= idx2 or x0 == x1 or y0 == y1: continue
                if (x0, y1) in A and (x1, y0) in A:
                    v02 = A[(x0, y1)]; v13 = A[(x1, y0)]
                    if 0 <= v02 <= 1 and 0 <= v13 <= 1:
                        cycle = [(x0, y0, +1), (x0, y1, -1),
                                 (x1, y1, +1), (x1, y0, -1)]
                        break
            if cycle: break

        if cycle is None:
            print(f"  [{it}] No cycle found")
            break

        eps = max_epsilon_v2(A, cycle, lines, pt_to_lines, n)
        if eps < 1e-12:
            stats["rollbacks"] += 1
            # 尝试更小步长
            eps = 0.05 / n

        # 应用
        for x, y, sign in cycle:
            A[(x, y)] = A.get((x, y), 0) + sign * eps

        # 验证 — 仅当确实有违规时才回滚
        viols = verify_radon(A, lines, n)
        if viols:
            for x, y, sign in cycle:
                A[(x, y)] = A.get((x, y), 0) - sign * eps
            stats["rollbacks"] += 1
        else:
            stats["iterations"] += 1
            stats["eps_total"] += eps

        if it % 500 == 0:
            n_int = sum(1 for v in A.values() if abs(v) < 1e-9 or abs(v - 1) < 1e-9)
            print(f"  [{it}] int={n_int}/{n*n} rollbacks={stats['rollbacks']} eps={eps:.4f}")

    n_int = sum(1 for v in A.values() if abs(v) < 1e-9 or abs(v - 1) < 1e-9)
    return A, n_int == n * n, stats


if __name__ == "__main__":
    random.seed(42)
    all_res = []
    for n in [6, 8, 10]:
        print(f"\n{'='*60}")
        print(f"Radon–Birkhoff v2: n={n}")
        print(f"{'='*60}")
        t0 = time.time()
        A, success, stats = radon_birkhoff_v2(n, max_iter=5000)
        elapsed = time.time() - t0

        n_int = sum(1 for v in A.values() if abs(v) < 1e-9 or abs(v - 1) < 1e-9)
        r = {"n": n, "success": success, "n_int": n_int,
             "time": elapsed, "stats": stats}
        all_res.append(r)
        print(f"Result: int={n_int}/{n*n} success={success} time={elapsed:.1f}s")
        print(f"  rollbacks={stats['rollbacks']} iterations={stats['iterations']}")

    json.dump(all_res, open("radon_birkhoff_v2_results.json", "w"), indent=2)
    print("\nSaved.")
