"""
挖掘前人 rot4 NTIL 解的本质 —— 基本域 2-因子结构分析

目标（用户指令：深挖已有解数据，找隐藏公式/本质，不求解 m=37）：
  1) 把每个 rot4 解提取为基本域 m 个 cell (a,b) ∈ [0,m-1]^2
     → 验证这些 cell 构成 2-因子（每值出现恰好 2 次）
  2) 把 2-因子当代数对象挖掘：
     - 圈分解（undirected 2-factor 的圈数/长度）
     - 取向置换 pi 的圈结构（"时间演化"）
     - 斜率残差 (b-a) mod m：是否常数（线性映射 b=a+k）？
     - 是否匹配已知构造（二次剩余 / 加倍映射 / 平移）
     - 不变量：Sigma x^2, Sigma xy, Sigma(x^2+y^2) [链接 Trace]
  3) 跨 n 规律：单圈解占比、斜率残差分布、是否存在贯穿所有 n 的正则解
  4) 升维视角：把解嵌入置换矩阵空间、当作离散动力系统

纯分析，不搜 m=37。
"""
import os, sys, json, math
from collections import defaultdict, Counter
from itertools import combinations

ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}
SYMM = set('.:/-ocx+*')
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def decode_line(line, n):
    line = line.strip()
    body = line[1:] if line and line[0] in SYMM else line
    pts = []
    for r in range(n):
        c1 = VAL[body[2 * r]]
        c2 = VAL[body[2 * r + 1]]
        pts.append((c1, r))
        pts.append((c2, r))
    return pts

def load_rot4(n, cap=None):
    for ext in ('', '.few', '.mvr'):
        path = os.path.join(CACHE, f'n{n}_rot4{ext}')
        if not os.path.exists(path):
            continue
        sols = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                pts = decode_line(line, n)
                if len(pts) == 2 * n:
                    sols.append(pts)
                    if cap and len(sols) >= cap:
                        break
        return sols
    return []

def extract_cells(pts, m):
    """取第一象限 x<m,y<m 的 m 个 cell (a,b) ∈ [0,m-1]^2。
    每 C4 轨道恰一个（已验证 c4_lifts 能完美重建整个解）。"""
    cells = [(x, y) for (x, y) in pts if x < m and y < m]
    return cells

def antipodal_project(cell, m):
    """对跖投影 P(x)=min(x, 2m-1-x) ∈ [0,m-1]。
    基本域 cell (u,v) 投成 (P(u),P(v)) 后构成顶点集 [0,m-1] 上的 2-因子：
    每个值在合并列表 (P(u)∪P(v)) 中恰好出现 2 次。"""
    n = 2 * m
    u, v = cell
    return (min(u, n - 1 - u), min(v, n - 1 - v))

def project_cells(cells, m):
    return [antipodal_project(c, m) for c in cells]

def is_two_factor(proj, m):
    """proj = m 个投影后 cell (pu,pv) ∈ [0,m-1]^2。
    2-因子判据：每个值 0..m-1 在合并列表 (pu ∪ pv) 中恰好出现 2 次。"""
    combined = [pu for pu, pv in proj] + [pv for pu, pv in proj]
    if len(combined) != 2 * m:
        return False, f"combined len {len(combined)} != {2*m}"
    c = Counter(combined)
    if any(v != 2 for v in c.values()):
        return False, f"degree not 2: {dict(c)}"
    return True, ""

def cycle_decomp(cells, m):
    """undirected 2-factor 圈分解。顶点 0..m-1，边 (a,b)。"""
    adj = defaultdict(list)
    for a, b in cells:
        adj[a].append(b)
        adj[b].append(a)
    visited = set()
    cycles = []
    for s in range(m):
        if s in visited or s not in adj:
            continue
        cyc = []
        cur = s; prev = -1
        while cur not in visited:
            visited.add(cur)
            cyc.append(cur)
            nxts = [x for x in adj[cur] if x != prev]
            if not nxts:
                break
            prev, cur = cur, nxts[0]
        cycles.append(cyc)
    return cycles

def orient_perm(cells, m):
    """把 2-因子取向成一个置换 pi：每个顶点选一条出边。
    规则：按 (a,b) 排序，pi[a]=b（若 a 出现两次则取第一次出现的 b 作为主出边，
    第二次作为另一条；实际形成的是 union of directed cycles）。
    这里构造一个确定性的置换：把 cell 列表看作有向边 a->b，但若 a 出度 2 则需拆分。
    更干净：把 undirected 2-factor 定向成 directed 2-regular = 对每个顶点选一条入一条出。
    我们用固定规则：pi[a] = 第一个 b 使 (a,b) in cells；另一条边 (a,b2) 对应 pi^{-1} 方向。
    为得到'置换'，直接取 cell 列表排序后 a 唯一映射（但 a 出现 2 次！）。
    因此改用：把 2-factor 的圈按顺序定向。返回所有 directed cycles。"""
    cycles = cycle_decomp(cells, m)
    directed = []
    for cyc in cycles:
        # cyc 是顶点环，定向为 i -> next
        d = [(cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc))]
        directed.append(d)
    return directed

def inv_signature(cells, m):
    """计算一组不变量"""
    xs = [a for a, b in cells]
    ys = [b for a, b in cells]
    n = 2 * m
    # odd-coord (a,b) = (2(n-1-x)-1, 2(n-1-y)-1)
    A = [2 * (n - 1 - a) - 1 for a in xs]
    B = [2 * (n - 1 - b) - 1 for b in ys]
    trace = sum(p * p for p in A) + sum(p * p for p in B)  # = Sigma(A^2+B^2)
    # 理论 Trace = n(n^2-1)/12
    theory = n * (n * n - 1) / 12
    sx2 = sum(a * a for a in xs)
    sy2 = sum(b * b for b in ys)
    sxy = sum(a * b for a, b in cells)
    sxx_yy = sum(a * a + b * b for a, b in cells)
    sdiff2 = sum((a - b) ** 2 for a, b in cells)
    # a-b Sidon (odd coords): d = A-B = 2(b-a)? 文档: a-b = -2(x-y) where (a,b) odd coords of (x,y).
    # 这里用 cell (x=b? )... 重新按文档：对 cell (x,y) in F_G, A=2(n-1-x)-1, B=2(n-1-y)-1,
    # A-B = 2(y-x). 所以 d_i = 2(y_i - x_i). 检验每值 count<=2.
    ds = [2 * (b - a) for a, b in cells]
    dc = Counter(ds)
    sidon_ok = all(v <= 2 for v in dc.values())
    return {
        'trace': trace, 'theory_trace': theory, 'trace_match': abs(trace - theory) < 1e-6,
        'sum_x2': sx2, 'sum_y2': sy2, 'sum_xy': sxy,
        'sum_x2plusy2': sxx_yy, 'sum_diff2': sdiff2,
        'sidon_ok': sidon_ok, 'sidon_maxcount': max(dc.values()) if dc else 0,
    }

def slope_residues(cells, m):
    """(b-a) mod m 的多重集。若全相等 = 线性平移 b=a+k。"""
    res = [((b - a) % m) for a, b in cells]
    c = Counter(res)
    constant = (len(c) == 1)
    return res, constant, dict(c)

def try_formula(cells, m):
    """尝试把 cell 拟合为已知构造形式，返回命中列表。"""
    hits = []
    cells_sorted = sorted(cells)
    # 按 a 排序
    by_a = sorted(cells, key=lambda t: (t[0], t[1]))
    a_seq = [a for a, b in by_a]
    b_seq = [b for a, b in by_a]
    # 1) 线性平移 b = a + k (mod m)：检查 (b-a) mod m 常数
    res = [(b - a) % m for a, b in cells]
    if len(set(res)) == 1:
        hits.append(f"linear_shift_k={res[0]}")
    # 2) 加倍映射 b = 2a (mod m) 或 b = ka
    for k in range(1, m):
        if all(((k * a) % m) == b for a, b in by_a if a not in [x[0] for x in by_a[:by_a.index((a,b))]]):
            pass
    # 更稳妥：对每个 k 检查所有 cell 是否满足 b ≡ k*a (mod m)
    for k in range(1, m):
        if all(((k * a) % m) == b for a, b in cells):
            hits.append(f"linear_scale_k={k}")
            break
    # 3) 二次剩余型：把 a 当作 x, b 当作 y，看 b 是否 = a^2 或 x^2+y^2 型（在 F_p, p=m 素数时）
    if all(p % 1 == 0 for p in [m]):
        # 仅当 m 素数时"二次剩余"有意义
        pass
    # 4) 互补配对：是否 (a,b) 与 (b,a) 成对出现（对称 2-因子）
    cellset = set(cells)
    symmetric = all((b, a) in cellset for a, b in cells)
    if symmetric:
        hits.append("symmetric_2factor")
    return hits

def analyze_solution(pts, m):
    cells = extract_cells(pts, m)
    if len(cells) != m:
        return {'valid': False, 'msg': f'Q3 cell count {len(cells)} != {m}', 'ncells': len(cells)}
    proj = project_cells(cells, m)
    ok, msg = is_two_factor(proj, m)
    if not ok:
        return {'valid': False, 'msg': msg, 'ncells': len(cells), 'cells': cells, 'proj': proj}
    cycles = cycle_decomp(proj, m)
    ncycles = len(cycles)
    cycle_lengths = sorted(len(c) for c in cycles)
    directed = orient_perm(proj, m)
    # directed cycles lengths
    dir_lengths = sorted(len(d) for d in directed)
    res, res_const, res_dist = slope_residues(proj, m)
    inv = inv_signature(cells, m)  # Trace 等用原始 Q3 cell（奇数坐标种子）
    formulas = try_formula(proj, m)
    return {
        'valid': True,
        'm': m,
        'cells': cells,
        'proj': proj,
        'ncycles': ncycles,
        'cycle_lengths': cycle_lengths,
        'dir_cycle_lengths': dir_lengths,
        'is_single_cycle': ncycles == 1,
        'slope_constant': res_const,
        'slope_dist': res_dist,
        'invariants': inv,
        'formulas': formulas,
    }

def main():
    # 完整数据 n=6..44；大 n 抽样
    full_ns = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44]
    sample_ns = {54: 200, 56: 200}
    all_ns = full_ns + list(sample_ns.keys())

    report = {'per_n': {}, 'global': {}}
    formula_counter = Counter()
    single_cycle_counts = defaultdict(int)
    total_counts = defaultdict(int)
    slope_const_counts = defaultdict(int)
    all_slope_dists = defaultdict(lambda: defaultdict(int))  # m -> Counter of (b-a) mod m values
    cycle_len_hist = defaultdict(lambda: defaultdict(int))  # m -> Counter of ncycles
    invariant_records = []

    for n in all_ns:
        m = n // 2
        cap = sample_ns.get(n)
        sols = load_rot4(n, cap=cap)
        if not sols:
            continue
        recs = []
        for pts in sols:
            a = analyze_solution(pts, m)
            if a['valid']:
                recs.append(a)
                # 统计
                total_counts[m] += 1
                if a['is_single_cycle']:
                    single_cycle_counts[m] += 1
                if a['slope_constant']:
                    slope_const_counts[m] += 1
                cycle_len_hist[m][a['ncycles']] += 1
                for k, v in a['slope_dist'].items():
                    all_slope_dists[m][k] += v
                for f in a['formulas']:
                    formula_counter[f"{m}:{f}"] += 1
                invariant_records.append({
                    'n': n, 'm': m,
                    'trace_match': a['invariants']['trace_match'],
                    'sum_x2plusy2': a['invariants']['sum_x2plusy2'],
                    'sum_xy': a['invariants']['sum_xy'],
                    'sum_diff2': a['invariants']['sum_diff2'],
                    'sidon_ok': a['invariants']['sidon_ok'],
                    'ncycles': a['ncycles'],
                })
        report['per_n'][n] = {
            'm': m,
            'n_solutions': len(recs),
            'n_valid': len(recs),
            'single_cycle': single_cycle_counts[m],
            'slope_constant': slope_const_counts[m],
            'cycle_hist': dict(cycle_len_hist[m]),
            'sample_formulas': dict(Counter(
                f for r in recs for f in r['formulas'])),
            'sample_slope_dist_keys': dict(list(all_slope_dists[m].items())[:20]),
        }
        print(f"n={n:2d} m={m:2d}: {len(recs)} sols | single_cycle={single_cycle_counts[m]} "
              f"slope_const={slope_const_counts[m]} | cycle_hist={dict(cycle_len_hist[m])}")

    # 全局汇总
    report['global'] = {
        'formula_hits': dict(formula_counter.most_common(30)),
        'single_cycle_rate_by_m': {m: (single_cycle_counts[m] / total_counts[m] if total_counts[m] else 0)
                                   for m in sorted(total_counts)},
        'slope_const_rate_by_m': {m: (slope_const_counts[m] / total_counts[m] if total_counts[m] else 0)
                                  for m in sorted(total_counts)},
        'total_solutions': sum(total_counts.values()),
        'm_range': [min(total_counts), max(total_counts)],
    }

    # 保存
    out_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'mine_solution_essence.json')
    # cells 太大，存精简版：每解只存 cells + 关键字段，且只保留小 n 完整、大 n 抽样
    slim = {'per_n_summary': report['per_n'], 'global': report['global']}
    # 额外存每个解的 cells（用于后续升维分析），但限制大小
    slim['samples'] = []
    for n in full_ns[:8]:  # 只存小 n 样本便于复核
        m = n // 2
        sols = load_rot4(n)
        for idx, pts in enumerate(sols[:30]):
            a = analyze_solution(pts, m)
            if a['valid']:
                slim['samples'].append({
                    'n': n, 'm': m, 'idx': idx,
                    'cells': a['cells'],
                    'ncycles': a['ncycles'],
                    'cycle_lengths': a['cycle_lengths'],
                    'slope_dist': a['slope_dist'],
                    'invariants': a['invariants'],
                    'formulas': a['formulas'],
                })
    with open(out_path, 'w') as f:
        json.dump(slim, f, indent=1)
    print(f"\nSaved -> {out_path}")

    # 打印全局结论
    print("\n===== 全局结论 =====")
    print(f"总解数: {report['global']['total_solutions']}")
    print(f"公式命中 (top): {dict(formula_counter.most_common(15))}")
    print("单圈率 by m:", {m: round(report['global']['single_cycle_rate_by_m'][m], 2)
                           for m in list(sorted(report['global']['single_cycle_rate_by_m']))[:12]})
    print("斜率常数率 by m:", {m: round(report['global']['slope_const_rate_by_m'][m], 2)
                               for m in list(sorted(report['global']['slope_const_rate_by_m']))[:12]})

if __name__ == '__main__':
    main()
