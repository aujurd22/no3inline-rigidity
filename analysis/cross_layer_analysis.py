"""
============================================================
跨层对称差分析（并行于后台主实验）
============================================================
目标：比较不同价值层的 2-因子结构差异
- v40 之间的对称差（已在 swap_evaluator 中做过）
- v44 之间的对称差
- v40 ↔ v44 的对比
- 寻找"好边"（仅出现在 v40 中）和"坏边"（仅出现在 ≥56 中）
- 尝试从 v44/48 解出发做边交换看能不能降到 ≤40
============================================================
"""
import json, sys, math, random, time
from collections import defaultdict, Counter
from itertools import combinations

sys.path.insert(0, 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue')
from signed_nae_core import geometry_bad_count, enumerate_clauses, count_clause_violations

ARCHIVE = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue/outputs/exact_factor_archive.json'
OUT_DIR = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results'
m = 37

with open(ARCHIVE) as f:
    data = json.load(f)

factors = {}
for e in data['archive']:
    factors[e['id']] = {
        'edges_set': set(tuple(sorted(ee)) for ee in e['edges']),
        'edges_list': [tuple(sorted(ee)) for ee in e['edges']],
        'bits': e['bits'],
        'value': e['value'],
    }

print(f"加载 {len(factors)} 个 2-因子")
val_counts = Counter(f['value'] for f in factors.values())
print(f"值分布: {dict(sorted(val_counts.items()))}")

# 按价值分组
by_value = defaultdict(list)
for fid, fdata in factors.items():
    by_value[fdata['value']].append(fid)


# ── 1. 各层的边频率对比 ──
print(f"\n{'='*65}")
print("各价值层出现频次最高的边")
print(f"{'='*65}")

for val in sorted(by_value.keys()):
    ids = by_value[val]
    n_sols = len(ids)
    edge_freq = Counter()
    for fid in ids:
        edge_freq.update(factors[fid]['edges_list'])
    
    # 所有解中共有的边 (出现 n_sols 次)
    universal = [e for e, c in edge_freq.items() if c == n_sols]
    # 只出现一次的边
    unique = [e for e, c in edge_freq.items() if c == 1]
    
    print(f"\n  value={val} ({n_sols}个解):")
    print(f"    所有解共有边: {len(universal)}")
    if universal and len(universal) <= 20:
        print(f"    {sorted(universal)}")
    print(f"    仅出现一次的边: {len(unique)}")


# ── 2. 跨层边集对比 ──
print(f"\n{'='*65}")
print("跨层边集对比")
print(f"{'='*65}")

layers = {}
for val in sorted(by_value.keys()):
    layerset = set()
    for fid in by_value[val]:
        layerset.update(factors[fid]['edges_set'])
    layers[val] = layerset
    print(f"  value={val}: {len(layerset)} 不同的边")

# v40 独有的边（不在任何 ≥44 的解中出现）
v40_only = layers[40].copy()
for val in [v for v in sorted(by_value.keys()) if v > 40]:
    v40_only -= layers[val]
print(f"\nv40 独有边 (不在 >40 的解中): {len(v40_only)}")
if v40_only:
    print(f"  {sorted(v40_only)}")

# ≥56 独有的边（不在任何 ≤44 的解中出现）
bad_set = set()
for val in [v for v in sorted(by_value.keys()) if v >= 56]:
    bad_set |= layers[val]
bad_only = bad_set.copy()
for val in [v for v in sorted(by_value.keys()) if v <= 44]:
    bad_only -= layers[val]
print(f"\n≥56 独有边 (不在 ≤44 的解中): {len(bad_only)}")
if bad_only and len(bad_only) <= 50:
    print(f"  {sorted(bad_only)}")


# ── 3. 跨层最小距离（对称差大小）──
print(f"\n{'='*65}")
print("跨层最小对称差大小")
print(f"{'='*65}")

for val_a in sorted(by_value.keys()):
    best = float('inf')
    best_pair = None
    for val_b in sorted(by_value.keys()):
        if val_b <= val_a:
            continue
        # 计算这个层之间的最小对称差
        min_sd = float('inf')
        for fid_a in by_value[val_a][:5]:  # 每层只取前 5 个
            for fid_b in by_value[val_b][:5]:
                sd_size = len(factors[fid_a]['edges_set'] ^ factors[fid_b]['edges_set'])
                if sd_size < min_sd:
                    min_sd = sd_size
        print(f"  {val_a} ↔ {val_b}: 最小对称差={min_sd} 条边")


# ── 4. 从 v44 解出发尝试 2-swap 改进 ──
print(f"\n{'='*65}")
print("从 v44 解出发做 2-swap → 看是否能降到 ≤40")
print(f"{'='*65}")

def sa_quick(edges, clauses, n_iter=30000, seed=42):
    """快速 SA 优化取向"""
    rng = random.Random(seed)
    N = len(edges)
    bits = [rng.randint(0, 1) for _ in range(N)]
    best_bits = list(bits)
    best_v = count_clause_violations(clauses, bits)
    curr_v = best_v
    temp_start, temp_end = 2.0, 0.01
    
    for i in range(n_iter):
        t = temp_start * (temp_end / temp_start) ** (i / n_iter)
        n_flip = 1 if rng.random() < 0.8 else rng.randint(2, 3)
        flip_idx = rng.sample(range(N), n_flip)
        for idx in flip_idx:
            bits[idx] ^= 1
        new_v = count_clause_violations(clauses, bits)
        delta = new_v - curr_v
        if delta < 0 or rng.random() < math.exp(-delta / t):
            curr_v = new_v
            if curr_v < best_v:
                best_v = curr_v
                best_bits = list(bits)
        else:
            for idx in flip_idx:
                bits[idx] ^= 1
    return best_bits, best_v


if 44 in by_value:
    v44_ids = by_value[44]
    print(f"v44 解数: {len(v44_ids)}")
    
    total_tested = 0
    improvements = []
    
    for fid in v44_ids[:3]:  # 只试前 3 个
        base_edges = factors[fid]['edges_list']
        base_bits = factors[fid]['bits']
        base_set = set(base_edges)
        
        # 枚举 2-swap
        edge_list = list(base_edges)
        N = len(edge_list)
        
        # 先评估原解（确认 SA 能找到 44）
        clauses_base = enumerate_clauses(m, base_edges)
        bb, bv = sa_quick(base_edges, clauses_base, n_iter=50000)
        geo_base = geometry_bad_count(m, base_edges, bb)
        print(f"\n  {fid} 基线确认: SA违例={bv}, 几何坏={geo_base['bad_triples']}")
        
        # 随机采样 500 个 2-swap
        sample_count = 0
        for i in range(N):
            u, v = edge_list[i]
            for j in range(i+1, N):
                if sample_count >= 500:
                    break
                w, x = edge_list[j]
                if len({u, v, w, x}) < 4:
                    continue
                
                for (a, b, c, d), (p, q) in [
                    ((u, v, w, x), ((u, x), (v, w))),
                    ((u, v, x, w), ((u, w), (v, x))),
                ]:
                    e1, e2 = tuple(sorted(p)), tuple(sorted(q))
                    if e1 in base_set or e2 in base_set or e1 == e2:
                        continue
                    
                    new_set = set(base_edges)
                    new_set.discard((u, v))
                    new_set.discard((w, x))
                    new_set.add(e1)
                    new_set.add(e2)
                    
                    deg = [0] * m
                    valid = True
                    for e in new_set:
                        deg[e[0]] += 1; deg[e[1]] += 1
                    if not all(d == 2 for d in deg):
                        continue
                    
                    clauses = enumerate_clauses(m, list(new_set))
                    bits, v = sa_quick(list(new_set), clauses, n_iter=30000)
                    geo = geometry_bad_count(m, list(new_set), bits)
                    bad = geo['bad_triples']
                    total_tested += 1
                    
                    if bad <= 44:
                        improvements.append((fid, bad, (u,v), (w,x), e1, e2))
                        marker = ""
                        if bad < 44:
                            marker = " ★★★ 突破!"
                        if bad == 44:
                            marker = " 持平"
                        print(f"    {fid}: 交换({u,v}|{w,x})→({e1},{e2}): {bad}{marker}")
                    
                    sample_count += 1
                    if sample_count >= 500:
                        break
            if sample_count >= 500:
                break
    
    print(f"\n  总测试: {total_tested}")
    below44 = [r for r in improvements if r[1] < 44]
    eq44 = [r for r in improvements if r[1] == 44]
    print(f"  低于 44: {len(below44)}")
    print(f"  等于 44: {len(eq44)}")
    if below44:
        print(f"  最佳: {min(below44, key=lambda x: x[1])}")


print(f"\n{'='*65}")
print("完成。")
