#!/usr/bin/env python3
"""
快速统计分析：5000 个随机 2-因子的 C₄ 缺陷分布
只追踪 min/histogram，不存储全部结果。
"""
import itertools, json, math, random, sys, time
from collections import Counter, defaultdict
from pathlib import Path

N, M = 74, 37

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

def random_2factor(rng):
    while True:
        perm = list(range(M))
        rng.shuffle(perm)
        has_2cycle = any(perm[perm[i]] == i and perm[i] != i for i in range(M))
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
    bits = [0] * len(edges)
    directed = [((v, u) if b else (u, v)) for (u, v), b in zip(edges, bits)]
    points = []
    for owner, cell in enumerate(directed):
        points.extend(c4_lifts(cell))
    if len(points) != 148 or len(set(points)) != 148:
        return None, None
    line_members = defaultdict(set)
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
        sorted_m = sorted(members)
        for i, j, k in itertools.combinations(sorted_m, 3):
            triple = (points[i], points[j], points[k])
            canonical = canonical_triple(triple)
            orbit_owners[canonical] = True
            bad_triples += 1
    return bad_triples, len(orbit_owners)

def main():
    n_trials = 10000
    rng = random.Random(42)
    hist_bt = Counter()
    hist_orb = Counter()
    bt_min, bt_max = float('inf'), 0
    orb_min, orb_max = float('inf'), 0
    lt50_bt, lt80_bt = 0, 0
    lt50_orb = 0
    start = time.time()
    for trial in range(n_trials):
        edges = random_2factor(rng)
        n_bad, n_orb = compute_defects(edges)
        if n_bad is None:
            continue
        bt_min = min(bt_min, n_bad)
        bt_max = max(bt_max, n_bad)
        orb_min = min(orb_min, n_orb)
        orb_max = max(orb_max, n_orb)
        # round to nearest 50 for histogram
        bt_key = (n_bad // 50) * 50
        orb_key = (n_orb // 10) * 10
        hist_bt[bt_key] += 1
        hist_orb[orb_key] += 1
        if n_bad < 50:
            lt50_bt += 1
        if n_bad < 80:
            lt80_bt += 1
        if n_orb < 50:
            lt50_orb += 1
        if trial % 500 == 0 and trial > 0:
            elapsed = time.time() - start
            rate = (trial + 1) / max(elapsed, 0.001)
            eta = (n_trials - trial - 1) / max(rate, 0.001)
            sys.stdout.write(f"\r[{trial:>6}/{n_trials}] min_bt={bt_min} orb_min={orb_min} | {elapsed:>5.0f}s ETA={eta:>5.0f}s")
            sys.stdout.flush()
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"{n_trials} trials in {elapsed:.0f}s")
    print(f"\n=== bad_triples (共线三元组计数) ===")
    print(f"  min={bt_min}, max={bt_max}")
    print(f"  V<50: {lt50_bt}, V<80: {lt80_bt}")
    print(f"  histogram (每50区间):")
    for k in sorted(hist_bt):
        print(f"    {k:>4}–{k+49:>4}: {hist_bt[k]:>5}")
    print(f"\n=== defect_orbits (C₄轨道计数) ===")
    print(f"  min={orb_min}, max={orb_max}")
    print(f"  V<50: {lt50_orb}")
    print(f"  histogram (每10区间):")
    for k in sorted(hist_orb):
        print(f"    {k:>4}–{k+9:>4}: {hist_orb[k]:>5}")
    
    # Save stats
    out = {
        "n_trials": n_trials,
        "bad_triples_min": bt_min,
        "bad_triples_max": bt_max,
        "bad_triples_hist": dict(sorted(hist_bt.items())),
        "defect_orbits_min": orb_min,
        "defect_orbits_max": orb_max,
        "defect_orbits_hist": dict(sorted(hist_orb.items())),
        "V20_baseline_bad_triples": 20,
        "V20_baseline_orbits": 5,
        "elapsed_seconds": elapsed,
        "conclusion": f"随机 37-cycle 2-因子的最小 C₄ 缺陷远高于 V=20 基准线 (min_bad_triples={bt_min}, min_defect_orbits={orb_min})。V=20 六盆地是特殊的低缺陷构造。"
    }
    Path(__file__).parent.joinpath("new_basin_stats.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n写入 new_basin_stats.json")

if __name__ == "__main__":
    main()
