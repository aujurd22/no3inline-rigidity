"""
============================================================
多 2-swap + 冲突引导的大扰动实验 (m=37)
============================================================
核心策略：
- 单 2-swap (改 2 边) 不足以破 40
- 多个不相交 2-swap 同时进行 → 4/6/8/10 边变化
- SA 多种子 (5 restarts × 100k) 确保取向优化质量
- 增量保存结果，不怕中断
============================================================
"""
import json, os, sys, math, random, time
from collections import defaultdict, Counter
from itertools import combinations
from copy import deepcopy

sys.path.insert(0, 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue')
from signed_nae_core import geometry_bad_count, enumerate_clauses, count_clause_violations

ARCHIVE = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue/outputs/exact_factor_archive.json'
OUT_DIR = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results'
m = 37

# ── 对称差 → 交替圈（swap_evaluator 内联版） ──
def get_cycles(F1, F2):
    """交替走对称差的边，分解为偶圈"""
    sd = F1 ^ F2
    adj1, adj2 = defaultdict(set), defaultdict(set)
    for e in sd:
        u, v = e
        (adj1 if e in F1 else adj2)[u].add(v)
        (adj1 if e in F1 else adj2)[v].add(u)
    
    cycles = []
    while True:
        start = next((v for v in set(list(adj1.keys())+list(adj2.keys()))
                     if len(adj1[v]) + len(adj2[v]) > 0), None)
        if start is None:
            break
        
        use_f1 = len(adj1.get(start, set())) > 0
        if use_f1:
            nxt = adj1[start].pop(); adj1[nxt].discard(start)
        else:
            nxt = adj2[start].pop(); adj2[nxt].discard(start)
        
        cycle = [start, nxt]
        curr = nxt
        while curr != start:
            if use_f1:
                candidates = list(adj2.get(curr, set()))
                if not candidates:
                    candidates = list(adj1.get(curr, set()))
                if not candidates:
                    break
                nxt = candidates[0]
                adj2[curr].discard(nxt); adj2[nxt].discard(curr)
                use_f1 = False
            else:
                candidates = list(adj1.get(curr, set()))
                if not candidates:
                    candidates = list(adj2.get(curr, set()))
                if not candidates:
                    break
                nxt = candidates[0]
                adj1[curr].discard(nxt); adj1[nxt].discard(curr)
                use_f1 = True
            cycle.append(nxt)
            curr = nxt
        cycles.append(cycle[:-1])
    return cycles


def swap_cycle(edges, cycle):
    """沿圈交换边：移除 F₁ 边（偶索引），添加 F₂ 边（奇索引）"""
    new_set = set(edges)
    for i in range(0, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_set.discard(e)
    for i in range(1, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_set.add(e)
    new_set.add(tuple(sorted((cycle[-1], cycle[0]))))
    return list(new_set)

# ── 加载数据 ──
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

v40_ids = [f"v40_{i:02d}" for i in range(1, 5)]
v40_edges = {fid: factors[fid]['edges'] for fid in v40_ids}


# ── 2-swap 生成 ──
def generate_2swaps(edges, max_candidates=10000):
    """
    枚举所有合法的 2-swap：选两对边 (a,b), (c,d) 要求 4 顶点互异，
    交换后得到 (a,d)+(b,c) 或 (a,c)+(b,d)，保持 2-正则。
    返回 [(desc, new_edges), ...]
    """
    N = len(edges)
    candidates = []
    edge_list = list(edges)
    
    for i in range(N):
        u, v = edge_list[i]
        for j in range(i+1, N):
            w, x = edge_list[j]
            # 要求 4 顶点互异
            if len({u, v, w, x}) < 4:
                continue
            
            # 两种交换方式
            for (a, b, c, d), (p, q) in [
                ((u, v, w, x), ((u, x), (v, w))),
                ((u, v, x, w), ((u, w), (v, x))),
            ]:
                e1, e2 = tuple(sorted(p)), tuple(sorted(q))
                if e1 in edges or e2 in edges:
                    continue
                if e1 == e2:
                    continue
                
                new_set = set(edges)
                new_set.discard((u, v))
                new_set.discard((w, x))
                new_set.add(e1)
                new_set.add(e2)
                
                # 验证 2-正则
                deg = [0] * m
                valid = True
                for e in new_set:
                    deg[e[0]] += 1
                    deg[e[1]] += 1
                if all(d == 2 for d in deg):
                    candidates.append((f"2swap({u},{v}|{w,x})→({e1},{e2})",
                                       list(new_set)))
                    if len(candidates) >= max_candidates:
                        return candidates
    return candidates


def sample_disjoint_multi_2swaps(base_edges, k, num_samples=5000, seed=42):
    """
    生成 k 个不相交 2-swap 的组合（构成大扰动）。
    策略：先枚举全部 2-swap 候选，然后随机选 k 个互不相交的合并。
    """
    rng = random.Random(seed)
    all_2swaps = []
    
    # 先枚举全部 2-swap
    N = len(base_edges)
    edge_list = list(base_edges)
    for i in range(N):
        u, v = edge_list[i]
        for j in range(i+1, N):
            w, x = edge_list[j]
            if len({u, v, w, x}) < 4:
                continue
            for (a, b, c, d), (p, q) in [
                ((u, v, w, x), ((u, x), (v, w))),
                ((u, v, x, w), ((u, w), (v, x))),
            ]:
                e1, e2 = tuple(sorted(p)), tuple(sorted(q))
                if e1 in base_edges or e2 in base_edges:
                    continue
                if e1 == e2:
                    continue
                # 记录涉及的四条边和输出边
                all_2swaps.append(({i, j}, {e1, e2}))
    
    if not all_2swaps:
        return []
    
    print(f"  总 2-swap 候选: {len(all_2swaps)}")
    
    # 多次采样
    results = []
    for sample in range(num_samples):
        rng.shuffle(all_2swaps)
        
        selected_swaps = []
        used_edge_indices = set()
        used_new_edges = set()
        
        for swap in all_2swaps:
            idx_set, new_edge_set = swap
            if idx_set & used_edge_indices:
                continue
            if new_edge_set & used_new_edges:
                continue
            
            selected_swaps.append(swap)
            used_edge_indices |= idx_set
            used_new_edges |= new_edge_set
            
            if len(selected_swaps) >= k:
                break
        
        if len(selected_swaps) == k:
            # 合并
            new_edges = set(base_edges)
            for idx_set, new_edge_set in selected_swaps:
                # 移除原边
                for idx in idx_set:
                    new_edges.discard(edge_list[idx])
                # 添加新边
                new_edges.update(new_edge_set)
            
            desc = f"multi{k}-{sample}"
            results.append((desc, list(new_edges)))
            
            if len(results) >= 200:  # 每种子 k 只取前 200
                break
    
    return results


# ── 多种子 SA 取向优化 ──
def optimize_sa_multi(edges, clauses, n_restarts=5, n_iter=80000):
    """多种子 SA，返回最佳 (bits, violations)"""
    best_bits = None
    best_v = float('inf')
    
    for seed in range(42, 42 + n_restarts):
        rng = random.Random(seed)
        N = len(edges)
        
        bits = [rng.randint(0, 1) for _ in range(N)]
        curr_v = count_clause_violations(clauses, bits)
        
        temp_start = 2.0
        temp_end = 0.01
        
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


# ── 增量保存 ──
def save_result(out_path, entry):
    """增量保存单条结果"""
    existing = []
    if os.path.exists(out_path):
        try:
            with open(out_path) as f:
                existing = json.load(f)
        except:
            existing = []
    existing.append(entry)
    with open(out_path, 'w') as f:
        json.dump(existing, f, indent=2)


# ════════════════════════════════════════
# 实验 1: 单 2-swap 系统扫描
# ════════════════════════════════════════
print(f"\n{'='*65}")
print("实验 1: 单 2-swap 系统扫描 — 从 v40_01 出发")
print(f"{'='*65}")

out_path1 = os.path.join(OUT_DIR, 'single_2swap_results.json')
base = v40_edges['v40_01']

# 生成全部 2-swap
all_2swaps = generate_2swaps(set(base))

# 先快速 SA 筛选（1 种子 × 30k 迭代）
print(f"共 {len(all_2swaps)} 个 2-swap 候选")
print(f"快速筛选 SA (1种子×30k)...")

screened = []
for desc, new_edges in all_2swaps[:500]:  # 先试前 500
    clauses = enumerate_clauses(m, new_edges)
    # 快速 SA
    bits, v = optimize_sa_multi(new_edges, clauses, n_restarts=1, n_iter=30000)
    geo = geometry_bad_count(m, new_edges, bits)
    bad = geo['bad_triples']
    
    entry = {
        'desc': desc,
        'sa_violations': v,
        'geo_bad': bad,
        'edges': [[int(x), int(y)] for x, y in new_edges],
        'bits': bits,
    }
    save_result(out_path1, entry)
    
    if bad < 40:
        print(f"  ★★★ {desc}: {bad}")
        break
    elif bad == 40:
        print(f"  持平: {desc}")
    else:
        pass  # 不打印每个

print(f"结果已保存: {out_path1}")


# ════════════════════════════════════════
# 实验 2: 多 2-swap 组合（大扰动）
# ════════════════════════════════════════
print(f"\n{'='*65}")
print("实验 2: 多 2-swap 组合")
print(f"{'='*65}")

out_path2 = os.path.join(OUT_DIR, 'multi_2swap_results.json')

for k in [2, 3, 4, 5]:  # 同时做 2-5 个 2-swap
    print(f"\n--- k={k} (修改 {2*k} 条边) ---")
    candidates = sample_disjoint_multi_2swaps(set(base), k, num_samples=20000)
    print(f"  生成 {len(candidates)} 个独立样本")
    
    for desc, new_edges in candidates:
        clauses = enumerate_clauses(m, new_edges)
        bits, v = optimize_sa_multi(new_edges, clauses, n_restarts=3, n_iter=50000)
        geo = geometry_bad_count(m, new_edges, bits)
        bad = geo['bad_triples']
        
        entry = {
            'desc': desc,
            'k': k,
            'sa_violations': v,
            'geo_bad': bad,
            'edges': [[int(x), int(y)] for x, y in new_edges],
            'bits': bits,
        }
        save_result(out_path2, entry)
        
        if bad < 40:
            print(f"  ★★★ {desc}: {bad} (k={k}) ★★★")
        elif bad == 40:
            print(f"  持平: {desc} (k={k})")

print(f"结果已保存: {out_path2}")


# ════════════════════════════════════════
# 实验 3: 跨解杂交（对称差多圈交换组合）
# ════════════════════════════════════════
print(f"\n{'='*65}")
print("实验 3: 跨解杂交 — 合并多个圈的交换")
print(f"{'='*65}")

out_path3 = os.path.join(OUT_DIR, 'hybrid_swap_results.json')

for a_id, b_id in combinations(v40_ids, 2):
    Fa = set(v40_edges[a_id])
    Fb = set(v40_edges[b_id])
    Fa_list = v40_edges[a_id]
    
    # 对称差 → 圈分解
    cycles = get_cycles(Fa, Fb)
    short_cycles = [c for c in cycles if len(c) <= 10]
    
    print(f"\n  {a_id} Δ {b_id}: {len(short_cycles)} 个短圈 (≤10)")
    
    # 尝试各种圈组合
    # 1. 单圈（已有）
    for ci, cycle in enumerate(short_cycles):
        new_edges = swap_cycle(Fa_list, cycle)
        
        clauses = enumerate_clauses(m, new_edges)
        bits, v = optimize_sa_multi(new_edges, clauses, n_restarts=3, n_iter=50000)
        geo = geometry_bad_count(m, new_edges, bits)
        bad = geo['bad_triples']
        
        entry = {
            'desc': f"{a_id}→{b_id} 圈{ci}(长{len(cycle)})",
            'a_id': a_id, 'b_id': b_id,
            'cycle_len': len(cycle),
            'sa_violations': v,
            'geo_bad': bad,
            'edges': [[int(x), int(y)] for x, y in new_edges],
            'bits': bits,
        }
        save_result(out_path3, entry)
        
        marker = " ★★★" if bad < 40 else (" 持平" if bad == 40 else "")
        if bad <= 40:
            print(f"  圈{ci}(长{len(cycle)}): {bad}{marker}")
    
    # 2. 多圈组合（合并 2 个短圈的交换）
    if len(short_cycles) >= 2:
        for ci, cj in combinations(range(len(short_cycles)), 2):
            # 边集 = base，对两个圈都做交换
            new_set = set(Fa_list)
            c1, c2 = short_cycles[ci], short_cycles[cj]
            
            for c in [c1, c2]:  # 对每个圈做交换
                # 手动做圈交换（不能直接用 swap_cycle 因为它基于 Fa_list）
                for i in range(0, len(c), 2):
                    e = tuple(sorted((c[i], c[(i+1) % len(c)])))
                    new_set.discard(e)
                for i in range(1, len(c), 2):
                    e = tuple(sorted((c[i], c[(i+1) % len(c)])))
                    new_set.add(e)
                new_set.add(tuple(sorted((c[-1], c[0]))))
            
            if len(new_set) != 37:
                continue  # 非法
            
            clauses = enumerate_clauses(m, list(new_set))
            bits, v = optimize_sa_multi(list(new_set), clauses, n_restarts=3, n_iter=50000)
            geo = geometry_bad_count(m, list(new_set), bits)
            bad = geo['bad_triples']
            
            entry = {
                'desc': f"{a_id}→{b_id} 圈{ci}+{cj}",
                'a_id': a_id, 'b_id': b_id,
                'cycle_lens': [len(c1), len(c2)],
                'sa_violations': v,
                'geo_bad': bad,
                'edges': [[int(x), int(y)] for x, y in new_set],
                'bits': bits,
            }
            save_result(out_path3, entry)
            
            marker = " ★★★" if bad < 40 else (" 持平" if bad == 40 else "")
            if bad <= 40:
                print(f"  圈{ci}(长{len(c1)})+圈{cj}(长{len(c2)}): {bad}{marker}")

print(f"结果已保存: {out_path3}")


# ── 汇总 ──
print(f"\n{'='*65}")
print("完成。所有结果增量保存。")
print(f"  - {out_path1}")
print(f"  - {out_path2}")
print(f"  - {out_path3}")

# 打印最佳结果
print(f"\n最佳结果总览:")
for path in [out_path1, out_path2, out_path3]:
    if os.path.exists(path):
        with open(path) as f:
            results = json.load(f)
        best = min(results, key=lambda x: x['geo_bad'])
        print(f"  {os.path.basename(path)}: best={best['geo_bad']} ({best['desc']})")
