"""
============================================================
自包含边交换评估器：
1) 导入 signed_nae_core 的 geometry_bad_count
2) 用 SA 搜索 37 位取向的最优分配
3) 报告每个交换结果的坏三元组数
============================================================
"""
import json, os, sys, math, random, time
from collections import defaultdict
from itertools import combinations

# 导入核心函数
sys.path.insert(0, 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue')
from signed_nae_core import geometry_bad_count, enumerate_clauses, count_clause_violations

# ── 配置 ──
ARCHIVE = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue/outputs/exact_factor_archive.json'
m = 37

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

v40_ids = [f"v40_{i:02d}" for i in range(1, 5)]


# ── 对称差 → 交替圈 ──
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
        # 找起始点
        start = next((v for v in set(list(adj1.keys())+list(adj2.keys()))
                     if len(adj1[v]) + len(adj2[v]) > 0), None)
        if start is None:
            break
        
        # 第一步
        use_f1 = len(adj1.get(start, set())) > 0
        if use_f1:
            nxt = adj1[start].pop()
            adj1[nxt].discard(start)
        else:
            nxt = adj2[start].pop()
            adj2[nxt].discard(start)
        
        cycle = [start, nxt]
        curr = nxt
        while curr != start:
            if use_f1:  # 上一步走 F₁ → 下一步走 F₂
                candidates = list(adj2.get(curr, set()))
                if not candidates:
                    candidates = list(adj1.get(curr, set()))
                if not candidates:
                    break
                nxt = candidates[0]
                adj2[curr].discard(nxt); adj2[nxt].discard(curr)
                use_f1 = False
            else:  # 上一步走 F₂ → 下一步走 F₁
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


# ── 沿圈交换 ──
def swap_cycle(edges, cycle):
    """移除 F₁ 边（偶索引），添加 F₂ 边（奇索引+末-首）"""
    new_set = set(edges)
    for i in range(0, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_set.discard(e)
    for i in range(1, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_set.add(e)
    new_set.add(tuple(sorted((cycle[-1], cycle[0]))))
    return list(new_set)


# ── SA 取向优化 (37 bits) ──
def optimize_orientation(edges, clauses, n_iter=80000, seed=42):
    """SA 求使 clause violations 最小的 37 位取向"""
    rng = random.Random(seed)
    N = len(edges)
    
    bits = [rng.randint(0, 1) for _ in range(N)]
    best_bits = list(bits)
    best_v = count_clause_violations(clauses, bits)
    curr_v = best_v
    
    temp_start = 2.0
    temp_end = 0.01
    
    for i in range(n_iter):
        t = temp_start * (temp_end / temp_start) ** (i / n_iter)
        
        # 翻转 1-3 位
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
                bits[idx] ^= 1  # 回滚
    
    return best_bits, best_v


# ── 主评估 ──
print("=" * 65)
print("边交换实验：评估对称差短圈交换后的坏三元组")
print("=" * 65)

all_results = []

for a_id, b_id in combinations(v40_ids, 2):
    Fa = set(factors[a_id]['edges'])
    Fa_list = factors[a_id]['edges']
    Fb = set(factors[b_id]['edges'])
    Fb_list = factors[b_id]['edges']
    
    original_value = factors[a_id]['value']
    
    cycles = get_cycles(Fa, Fb)
    
    for ci, cycle in enumerate(cycles):
        if len(cycle) > 14:
            continue
        
        new_edges = swap_cycle(Fa_list, cycle)
        
        # 验证 2-因子
        deg = defaultdict(int)
        for u, v in new_edges:
            deg[u] += 1; deg[v] += 1
        if not (all(d == 2 for d in deg.values()) and len(deg) == 37):
            print(f"  {a_id}→{b_id} 圈{ci}(长{len(cycle)}): ✗ 非法 2-因子")
            continue
        
        # 生成子句
        clauses = enumerate_clauses(m, new_edges)
        print(f"\n  {a_id}→{b_id} 圈{ci}(长{len(cycle)}): {len(clauses)} 条子句")
        
        # SA 优化
        t0 = time.time()
        best_bits, best_v = optimize_orientation(new_edges, clauses, n_iter=100000)
        t1 = time.time()
        
        # 确认几何坏三元组
        geo = geometry_bad_count(m, new_edges, best_bits)
        geo_bad = geo['bad_triples']
        
        print(f"    SA违例: {best_v}, 几何坏三元组: {geo_bad} (最优原={original_value})")
        print(f"    耗时: {t1-t0:.1f}s, 点={geo['point_count']}, 不同点={geo['distinct_point_count']}")
        
        result = {
            'from': a_id, 'to': b_id,
            'cycle_idx': ci, 'cycle_len': len(cycle),
            'cycle_path': cycle,
            'original_value': original_value,
            'sa_violations': best_v,
            'geo_bad': geo_bad,
        }
        all_results.append(result)
        
        # 立即报告突破
        if geo_bad < original_value:
            print(f"    ★★★ 突破! {original_value} → {geo_bad} ★★★")
        
        # 同时用原有取向评估，作为基线
        orig_bits = factors[a_id]['bits']
        orig_geo = geometry_bad_count(m, new_edges, orig_bits)
        print(f"    原取向基线: {orig_geo['bad_triples']}")


# ── 完整报告 ──
print(f"\n{'='*65}")
print("最终结果汇总")
print(f"{'='*65}")

improvements = [r for r in all_results if r['geo_bad'] < r['original_value']]
worsenings = [r for r in all_results if r['geo_bad'] > r['original_value']]
same = [r for r in all_results if r['geo_bad'] == r['original_value']]

print(f"总交换数: {len(all_results)}")
print(f"改善 (小于原值): {len(improvements)}")
print(f"持平: {len(same)}")
print(f"变差: {len(worsenings)}")

if improvements:
    print(f"\n改善详情:")
    for r in sorted(improvements, key=lambda x: x['geo_bad']):
        delta = r['original_value'] - r['geo_bad']
        print(f"  {r['from']}→{r['to']} 圈{r['cycle_idx']}(长{r['cycle_len']}): "
              f"{r['original_value']} → {r['geo_bad']} (↓{delta})")

print(f"\n所有结果明细:")
for r in sorted(all_results, key=lambda x: x['geo_bad']):
    marker = " ★" if r['geo_bad'] < r['original_value'] else ""
    print(f"  {r['from']}→{r['to']} 圈{r['cycle_idx']}(长{r['cycle_len']}): "
          f"{r['original_value']} → {r['geo_bad']}{marker}")

# 保存结果
out_path = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/swap_experiment_results.json'
with open(out_path, 'w') as f:
    json.dump({
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(all_results),
        'improvements': len(improvements),
        'results': all_results,
    }, f, indent=2)

print(f"\n结果已保存至: {out_path}")
print("完成。")
