"""
============================================================
冲突引导的大跨度边修改

1) 统计每条边在不同 value 的解中的出现频率
2) 为 v40 解的每条边计算"冲突分数"(参与多少坏三元组)
3) 尝试替换高冲突边为低冲突边
============================================================
"""
import json, os, sys, math, random, time
from collections import defaultdict, Counter

sys.path.insert(0, 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue')
from signed_nae_core import geometry_bad_count, enumerate_clauses, count_clause_violations

ARCHIVE = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue/outputs/exact_factor_archive.json'
m = 37

with open(ARCHIVE) as f:
    data = json.load(f)

factors = {}
for e in data['archive']:
    factors[e['id']] = {
        'edges': [tuple(sorted(ee)) for ee in e['edges']],
        'bits': e['bits'],
        'value': e['value'],
    }

print(f"加载 {len(factors)} 个 2-因子")

# ── 1. 边频率统计 ──
print(f"\n{'='*65}")
print("边频率统计：按价值层分")
print(f"{'='*65}")

# 按价值分层
value_layers = defaultdict(list)
for fid, fdata in factors.items():
    value_layers[fdata['value']].append(fid)

edge_freq = {}  # edge -> {value: count}
total_edges_by_value = defaultdict(int)

for value, fids in sorted(value_layers.items()):
    print(f"\n  value={value} ( {len(fids)} 个解 ):")
    freq = Counter()
    for fid in fids:
        for e in factors[fid]['edges']:
            freq[e] += 1
    edge_freq[value] = freq
    total_edges_by_value[value] = sum(freq.values())
    
    # 打印最高频的边
    common = freq.most_common(10)
    for e, cnt in common:
        pct = cnt / len(fids) * 100
        print(f"    {e}: {cnt}/{len(fids)} = {pct:.0f}%")

# ── 2. 跨层边出现对比 ──
print(f"\n{'='*65}")
print("跨层对比：好的边 vs 差的边")
print(f"{'='*65}")

good_value = 40
good_edges = set()
for fid in value_layers[good_value]:
    good_edges.update(factors[fid]['edges'])

bad_values = sorted([v for v in value_layers.keys() if v >= 56])
bad_edges = set()
for v in bad_values:
    for fid in value_layers[v]:
        bad_edges.update(factors[fid]['edges'])

only_good = good_edges - bad_edges
only_bad = bad_edges - good_edges
shared = good_edges & bad_edges

print(f"v40 解中独有的边 (不在 ≥56 的解中出现): {len(only_good)}")
print(f"≥56 的解中独有的边 (不在 v40 中出现): {len(only_bad)}")
print(f"共有的边: {len(shared)}")

# 打印 v40 独有的边
if only_good:
    print(f"\nv40 独有边 ({len(only_good)}):")
    for e in sorted(only_good):
        # 在 v40 中的频率
        cnt_good = edge_freq[good_value].get(e, 0)
        print(f"  {e}: v40出现{cnt_good}/4次")

# ── 3. 冲突分析：v40 每条边的坏三元组参与数 ──
print(f"\n{'='*65}")
print("冲突分析：v40 解中每条边参与了多少个坏三元组")
print(f"{'='*65}")

for fid in [f"v40_{i:02d}" for i in range(1, 5)]:
    edges = factors[fid]['edges']
    bits = factors[fid]['bits']
    
    # 计算每个坏三元组，追踪涉及哪些边
    result = geometry_bad_count(m, edges, bits)
    total_bad = result['bad_triples']
    
    # 方法：枚举所有三元组找出坏的三元组
    clauses = enumerate_clauses(m, edges)
    
    # 每条边参与的违例子句数
    edge_violations = defaultdict(int)
    for a, b, c, bits_pat in clauses:
        if factors[fid]['bits'][a] == ((bits_pat >> 0) & 1) and \
           factors[fid]['bits'][b] == ((bits_pat >> 1) & 1) and \
           factors[fid]['bits'][c] == ((bits_pat >> 2) & 1):
            edge_violations[a] += 1
            edge_violations[b] += 1
            edge_violations[c] += 1
    
    print(f"\n  {fid} (总坏={total_bad}):")
    print(f"  最高冲突边:")
    for idx in sorted(edge_violations, key=edge_violations.get, reverse=True)[:10]:
        e = edges[idx]
        print(f"    {fid}[{idx}] = {e}: 参与 {edge_violations[idx]} 个违例子句")

# ── 4. 尝试替换高冲突边 ──
print(f"\n{'='*65}")
print("定向替换实验：替换 v40_01 中冲突最高的边")
print(f"{'='*65}")

def sa_orient(edges, clauses, n_iter=80000, seed=42):
    rng = random.Random(seed)
    N = len(edges)
    bits = [rng.randint(0, 1) for _ in range(N)]
    best_bits = list(bits)
    curr_v = count_clause_violations(clauses, bits)
    best_v = curr_v
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

def find_2swap_candidates(edges, conflict_idx, all_edges_pool, max_candidates=200):
    """
    找 2-swap 候选：移除 edges[conflict_idx] = (u,v) 和另一条边 (w,x)，
    添加 (u,x) 和 (v,w) 保持 2-正则性
    """
    N = len(edges)
    u, v = edges[conflict_idx]
    
    candidates = []
    for other_idx, (w, x) in enumerate(edges):
        if other_idx == conflict_idx:
            continue
        
        # 4 个顶点必须互异
        vertices = {u, v, w, x}
        if len(vertices) < 4:
            continue
        
        # 两种 2-swap 方式
        for (a, b, c, d) in [(u, v, w, x), (u, v, x, w)]:
            new_e1 = tuple(sorted((a, d)))  # (u, x) 或 (u, w)
            new_e2 = tuple(sorted((b, c)))  # (v, w) 或 (v, x)
            
            if new_e1 in all_edges_pool or new_e2 in all_edges_pool:
                continue
            if len({new_e1, new_e2}) < 2:
                continue
            
            # 验证
            test_edges = set(edges)
            test_edges.discard((u, v))
            test_edges.discard((w, x))
            test_edges.add(new_e1)
            test_edges.add(new_e2)
            
            deg = [0] * m
            for e in test_edges:
                deg[e[0]] += 1
                deg[e[1]] += 1
            
            if all(d == 2 for d in deg):
                candidates.append((other_idx, (w, x), new_e1, new_e2, list(test_edges), conflict_idx))
                if len(candidates) >= max_candidates:
                    break
        if len(candidates) >= max_candidates:
            break
    
    return candidates

# 对 v40_01 的每条高冲突边尝试替换
fid = 'v40_01'
edges = factors[fid]['edges']
all_edge_set = set(edges)

# 计算边的冲突
clauses = enumerate_clauses(m, edges)
edge_viol = defaultdict(int)
for a, b, c, bp in clauses:
    if factors[fid]['bits'][a] == ((bp >> 0) & 1) and \
       factors[fid]['bits'][b] == ((bp >> 1) & 1) and \
       factors[fid]['bits'][c] == ((bp >> 2) & 1):
        edge_viol[a] += 1; edge_viol[b] += 1; edge_viol[c] += 1

conflict_sorted = sorted(range(m), key=lambda i: edge_viol.get(i, 0), reverse=True)

print(f"尝试对 v40_01 的高冲突边做 2-swap:")
for rank, idx in enumerate(conflict_sorted[:5]):
    old_e = edges[idx]
    print(f"\n  2-swap 边 #{idx} = {old_e} (冲突={edge_viol.get(idx, 0)})")
    
    candidates = find_2swap_candidates(edges, idx, all_edge_set)
    print(f"    候选 2-swap 数: {len(candidates)}")
    
    for cand_idx, (other_idx, other_e, new_e1, new_e2, new_edges, _) in enumerate(candidates[:5]):
        deg = [0] * m
        for e in new_edges:
            deg[e[0]] += 1; deg[e[1]] += 1
        if not all(d == 2 for d in deg):
            continue
        
        new_clauses = enumerate_clauses(m, new_edges)
        best_bits, best_v = sa_orient(new_edges, new_clauses, n_iter=50000)
        geo = geometry_bad_count(m, new_edges, best_bits)
        bad = geo['bad_triples']
        
        marker = " ★★★" if bad < 40 else ""
        print(f"    移除 {old_e}+{other_e} → 添加 {new_e1}+{new_e2}: "
              f"SA={best_v}, 几何坏={bad}{marker}")
        
        if bad < 40:
            print(f"      ★★★ 突破! 40 → {bad}! 保存结果...")
            # 保存突破结果
            result = {
                'method': '2swap',
                'base': fid,
                'bad': bad,
                'edges': [[int(x), int(y)] for x, y in new_edges],
                'bits': best_bits,
            }
            with open('D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/breakthrough_candidate.json', 'w') as f:
                json.dump(result, f, indent=2)

print(f"\n{'='*65}")
print("完成。")
