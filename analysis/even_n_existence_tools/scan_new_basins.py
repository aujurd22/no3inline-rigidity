#!/usr/bin/env python3
"""
随机 37-顶点 2-因子搜索（序列版，带进度刷新）
=================================================
方向壳分析确认 V20 六盆地的 MUS 高度各异、无方向壳偏斜，
触发决策树：停止加 k，转向新 2-因子基的正面构造。
"""

import itertools
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

N = 74
M = 37

# ── C₄ 几何函数 ──

def c4_lifts(cell):
    x, y = cell
    result = []
    for _ in range(4):
        result.append((x, y))
        x, y = N - 1 - y, x
    return tuple(result)

def rotate(point):
    return N - 1 - point[1], point[0]

def canonical_triple(triple):
    values = []
    current = tuple(sorted(triple))
    for _ in range(4):
        values.append(current)
        current = tuple(sorted(rotate(p) for p in current))
    return min(values)

def line_key(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        return None
    divisor = math.gcd(abs(dx), abs(dy))
    a, b = dy // divisor, -dx // divisor
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    return (a, b, a * p[0] + b * p[1])

# ── 2-因子生成 ──

def random_2factor(rng):
    """生成一个随机 2-因子（无自环、无重边）"""
    while True:
        perm = list(range(M))
        rng.shuffle(perm)
        # 检测 2-循环（会产生重边）
        has_2cycle = any(
            perm[perm[i]] == i and perm[i] != i
            for i in range(M)
        )
        if has_2cycle:
            continue
        edges_set = set()
        for i in range(M):
            u, v = i, perm[i]
            if u == v:
                continue
            key = (min(u, v), max(u, v))
            edges_set.add(key)
        if len(edges_set) != M:
            continue
        edges = sorted(edges_set)
        deg = Counter()
        for u, v in edges:
            deg[u] += 1
            deg[v] += 1
        if all(d == 2 for d in deg.values()):
            return edges

def compute_defects(edges):
    """计算 2-因子的 C₄ 提升缺陷数"""
    bits = [0] * len(edges)
    directed = [((v, u) if b else (u, v)) for (u, v), b in zip(edges, bits)]
    points = []
    for owner, cell in enumerate(directed):
        points.extend(c4_lifts(cell))
    if len(points) != 148 or len(set(points)) != 148:
        return None, None
    
    # 预计算所有点的 line_key 字典，加速碰撞检测
    # 对每个点对计算 line_key
    line_members = defaultdict(set)
    # 只检查一次每个点对
    np = len(points)
    for i in range(np):
        pi = points[i]
        for j in range(i + 1, np):
            key = line_key(pi, points[j])
            if key is None:
                continue
            line_members[key].add(i)
            line_members[key].add(j)
    
    bad_triples = 0
    orbit_owners = {}
    for key, members in line_members.items():
        if len(members) < 3:
            continue
        # members 是无序的 set，排序为列表
        sorted_m = sorted(members)
        for i, j, k in itertools.combinations(sorted_m, 3):
            # 跳过有索引差的组合优化？没必要，line 上 n>=3 时 3-combination 数量有限
            triple = (points[i], points[j], points[k])
            canonical = canonical_triple(triple)
            # 不需要 owner_set 检测，只计数
            orbit_owners[canonical] = True
            bad_triples += 1
    
    return bad_triples, len(orbit_owners)


def main():
    n_trials = 50000
    output_path = Path(__file__).parent / "new_basin_search_results.json"
    rng = random.Random(42)
    
    print(f"搜索 {n_trials} 个随机 2-因子（序列执行）...")
    print(f"{'='*50}")
    
    best = []
    total_valid = 0
    start_time = time.time()
    last_report = 0
    
    for trial in range(n_trials):
        edges = random_2factor(rng)
        n_bad, n_orb = compute_defects(edges)
        if n_bad is None:
            continue
        total_valid += 1
        
        rec = {
            "seed": trial,
            "trial": trial,
            "edges": edges,
            "bad_triples": n_bad,
            "defect_orbits": n_orb,
        }
        
        if n_bad < 50:
            best.append(rec)
            best.sort(key=lambda x: x["bad_triples"])
            best = best[:10]
        
        if trial - last_report >= 500:
            last_report = trial
            elapsed = time.time() - start_time
            rate = (trial + 1) / max(elapsed, 0.001)
            eta = (n_trials - trial - 1) / max(rate, 0.001)
            min_v = best[0]["bad_triples"] if best else "?"
            sys.stdout.write(
                f"\r  [{trial+1:>6}/{n_trials}] 有效={total_valid:>5} "
                f"最佳V={min_v} {elapsed:>5.0f}s "
                f"ETA={eta:>5.0f}s     "
            )
            sys.stdout.flush()
    
    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"完成! 共 {total_valid} 个有效 2-因子, 耗时 {elapsed:.0f}s")
    print(f"找到 {len(best)} 个 V<50 的候选")
    print(f"\nTop 3 最佳:")
    for i, b in enumerate(best[:3]):
        print(f"  #{i+1}: V={b['bad_triples']} orbits={b['defect_orbits']} trial={b['trial']}")
    
    # 最少 V 值
    min_v = best[0]["bad_triples"] if best else None
    
    if min_v is not None:
        if min_v < 20:
            print(f"\n** 突破! V={min_v} < 20 — 发现更优基! **")
        elif min_v == 20:
            print(f"\n  找到 V=20 的新基 (与现有六盆地同级别)")
        else:
            print(f"\n  最小 V={min_v}，未找到比 V20 更优的基")
    
    output = {
        "n_trials": n_trials,
        "total_valid_2factors": total_valid,
        "elapsed_seconds": elapsed,
        "top_candidates": best[:5],
        "minimum_V": min_v,
        "V20_baseline": 20,
        "is_better_than_V20": min_v < 20 if min_v else None,
    }
    
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n写入 {output_path}")

if __name__ == "__main__":
    main()
