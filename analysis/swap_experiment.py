"""
============================================================
边交换实验：对 v40 解的对称差短圈做边交换
用 CP-SAT 精确评估交换后的取向最优值和坏三元组数
============================================================
"""
import json, os, sys, math, time
from collections import defaultdict
from itertools import combinations

# ── 路径 ──
ARCHIVE_FILE = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue/outputs/exact_factor_archive.json'
SOLVE_DIR = 'D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/m37_continue'
sys.path.insert(0, SOLVE_DIR)

import subprocess

# ── 加载数据 ──
with open(ARCHIVE_FILE) as f:
    archive_data = json.load(f)

all_factors = {}
for entry in archive_data['archive']:
    eid = entry['id']
    edges = [tuple(sorted(e)) for e in entry['edges']]
    all_factors[eid] = {
        'edges_set': set(edges),
        'edges_list': edges,
        'value': entry['value'],
        'bits': entry['bits'],
        'safe': entry.get('diagonal_safe', False),
    }

m = 37

# ── 对称差 → 圈 ──
def get_cycles(F1, F2):
    sd = F1 ^ F2
    adj1, adj2 = defaultdict(set), defaultdict(set)
    for e in sd:
        u, v = e
        if e in F1:
            adj1[u].add(v); adj1[v].add(u)
        else:
            adj2[u].add(v); adj2[v].add(u)
    
    cycles = []
    while any(adj1.values()) or any(adj2.values()):
        start = None
        for v in set(list(adj1.keys()) + list(adj2.keys())):
            if len(adj1[v]) + len(adj2[v]) > 0:
                start = v; break
        if start is None: break
        
        if adj1.get(start):
            use_f1 = True
            nxt = adj1[start].pop()
            adj1[nxt].discard(start)
        elif adj2.get(start):
            use_f1 = False
            nxt = adj2[start].pop()
            adj2[nxt].discard(start)
        else:
            break
        
        cycle = [start, nxt]
        curr = nxt
        while curr != start:
            prev = cycle[-2]
            if use_f1:
                candidates = list(adj2.get(curr, set()))
                if not candidates:
                    # fallback to adj1
                    candidates = list(adj1.get(curr, set()))
                if not candidates:
                    break
                nxt = candidates[0]
                (adj2 if use_f1 else adj1)[curr].discard(nxt)
                (adj2 if use_f1 else adj1)[nxt].discard(curr)
                use_f1 = False
            else:
                candidates = list(adj1.get(curr, set()))
                if not candidates:
                    candidates = list(adj2.get(curr, set()))
                if not candidates:
                    break
                nxt = candidates[0]
                (adj1 if not use_f1 else adj2)[curr].discard(nxt)
                (adj1 if not use_f1 else adj2)[nxt].discard(curr)
                use_f1 = True
            cycle.append(nxt)
            curr = nxt
        cycles.append(cycle[:-1])
    return cycles


# ── 沿圈交换边 ──
def swap_along_cycle(base_edges, cycle):
    """沿 cycle 交换边：移除 F₁ 边、添加 F₂ 边"""
    new_set = set(base_edges)
    # 移除偶索引边（起点→v1, v2→v3, ...）
    for i in range(0, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_set.discard(e)
    # 添加奇索引边（v1→v2, v3→v4, ..., 最后→起点）
    for i in range(1, len(cycle), 2):
        e = tuple(sorted((cycle[i], cycle[(i+1) % len(cycle)])))
        new_set.add(e)
    last_e = tuple(sorted((cycle[-1], cycle[0])))
    new_set.add(last_e)
    
    assert len(new_set) == m
    return list(new_set)


# ── CP-SAT 评估 ──
def evaluate_factor(edge_list, label, timeout_seconds=60):
    """用 CP-SAT 求取向最优值"""
    # 写临时 JSON
    tmp_json = f'/tmp/eval_{label}.json'
    with open(tmp_json, 'w') as f:
        json.dump({
            'edges': [[int(u), int(v)] for u, v in edge_list],
            'm': m,
            'label': label
        }, f)
    
    # 调用求解脚本（如果有的话）
    solver_script = os.path.join(SOLVE_DIR, 'solve_orientation.py')
    if not os.path.exists(solver_script):
        # 尝试其他求解器
        solver_script = os.path.join(SOLVE_DIR, '..', '..', 'solve_m37_r9b.py')
    
    if os.path.exists(solver_script):
        cmd = [
            sys.executable, solver_script,
            '--input', tmp_json,
            '--timeout', str(timeout_seconds)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds+10)
        # 解析输出
        output = result.stdout + result.stderr
        for line in output.split('\n'):
            if 'bad' in line.lower() or 'value' in line.lower() or 'triple' in line.lower():
                pass
        print(f"    {label}: 返回码={result.returncode}")
        if result.returncode == 0:
            print(f"    输出(前3行): " + "\n    ".join(output.split('\n')[:3]))
        return result.returncode, output
    else:
        print(f"    ⚠️ 找不到求解器 {solver_script}")
        return -1, ""


# ── 主实验：v40 对之间的短圈交换 ──
print("=" * 65)
print("边交换实验：v40 解的对称差短圈")
print("=" * 65)

v40_ids = [f"v40_{i:02d}" for i in range(1, 5)]
experiments_done = 0

for a, b in combinations(v40_ids, 2):
    Fa = all_factors[a]['edges_set']
    Fa_list = all_factors[a]['edges_list']
    Fb = all_factors[b]['edges_set']
    
    cycles = get_cycles(Fa, Fb)
    
    for cycle_idx, cycle in enumerate(cycles):
        if len(cycle) > 12:
            continue  # 只试短圈
        
        experiments_done += 1
        new_edges = swap_along_cycle(Fa_list, cycle)
        label = f"swap_{a}_to_{b}_c{cycle_idx}_len{len(cycle)}"
        
        # 基本检查
        deg = defaultdict(int)
        for u, v in new_edges:
            deg[u] += 1; deg[v] += 1
        valid = all(d == 2 for d in deg.values()) and len(deg) == 37
        
        print(f"\n实验 #{experiments_done}: {a}→{b} 圈{cycle_idx}(长{len(cycle)})")
        print(f"  路径: {cycle}")
        print(f"  有效2-因子: {'✓' if valid else '✗'}")
        
        if not valid:
            continue
        
        # 用 CP-SAT 评估
        evaluate_factor(new_edges, label)


# ── 额外实验：同时交换两个 4-圈 ──
print(f"\n{'='*65}")
print("额外实验：同时交换 v40_03→v40_04 的两个 4-圈")
print(f"{'='*65}")

Fa = all_factors['v40_03']['edges_set']
Fa_list = all_factors['v40_03']['edges_list']
Fb = all_factors['v40_04']['edges_set']

cycles = get_cycles(Fa, Fb)
short_cycles = [c for c in cycles if len(c) <= 6]

if len(short_cycles) >= 2:
    # 逐个交换
    for c in short_cycles:
        new_edges1 = swap_along_cycle(Fa_list, c)
        label1 = f"swap_v40_03_to_04_c{cycles.index(c)}_len{len(c)}"
        evaluate_factor(new_edges1, label1)
    
    # 一起交换
    new_set = set(Fa_list)
    for c in short_cycles:
        for i in range(0, len(c), 2):
            e = tuple(sorted((c[i], c[(i+1) % len(c)])))
            new_set.discard(e)
        for i in range(1, len(c), 2):
            e = tuple(sorted((c[i], c[(i+1) % len(c)])))
            new_set.add(e)
        last_e = tuple(sorted((c[-1], c[0])))
        new_set.add(last_e)
    
    new_edges_both = list(new_set)
    assert len(new_edges_both) == m
    evaluate_factor(new_edges_both, "swap_v40_03_to_04_both4cycles")


print(f"\n{'='*65}")
print(f"共完成 {experiments_done} 个实验")
print(f"{'='*65}")
