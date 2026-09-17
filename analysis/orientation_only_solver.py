"""
orientation_only_solver.py — 纯取向求解器

问题：对于 FIXED 2-因子（config_408 的 37 个 cell），寻找最佳取向分配
使得违例三元组数最小。

每个 cell 有 4 种 C4 旋转 (r=0,1,2,3)。目标：选择旋转分配使得
最少的三元组中三个旋转后的点共线。

这本质上是：37 个变量 × 4 个取值 → MaxSAT/CSP。
由于 4^37 ≈ 10^22 不可穷举，用面向问题的局部搜索。

关键观察：从之前的枚举可知，只有 280/497,280 ≈ 0.056% 的
(triple, rotation) 组合是共线的。这意味着对大多数三元组，
任何旋转组合都安全。取向优化的搜索空间比 2-因子搜索小得多。
"""

import json, random, math, sys, time
from collections import Counter, defaultdict
from itertools import combinations

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"

# ===========================================================
# 几何
# ===========================================================
def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def det_collinear(pa, pb, pc):
    return (pb[0]-pa[0])*(pc[1]-pa[1]) - (pc[0]-pa[0])*(pb[1]-pa[1])

# ===========================================================
# 预计算所有三元组的冲突表（仅存有冲突的组合）
# ===========================================================
def build_conflict_table(cells, n):
    """
    返回：conflicts[(a,b,c)] = {(ra,rb,rk), ...} 导致共线的三元旋转组合。
    只存有冲突的三元组。
    """
    conflicts = {}
    for a, b, c in combinations(range(len(cells)), 3):
        bad_rotations = set()
        p = cells[a]; q = cells[b]; r = cells[c]
        for ra in range(4):
            pa = c4(p[0], p[1], ra, n)
            for rb in range(4):
                pb = c4(q[0], q[1], rb, n)
                for rc in range(4):
                    pc = c4(r[0], r[1], rc, n)
                    if det_collinear(pa, pb, pc) == 0:
                        bad_rotations.add((ra, rb, rc))
        if bad_rotations:
            conflicts[(a, b, c)] = bad_rotations
    return conflicts

# ===========================================================
# 评估函数
# ===========================================================
def evaluate(orient, conflicts):
    """计数：在当前取向分配下，有多少三元组违反（所有 3 点共线）"""
    viol = 0
    for (a, b, c), bad_set in conflicts.items():
        if (orient[a], orient[b], orient[c]) in bad_set:
            viol += 1
    return viol

def evaluate_fast(orient, conflicts, triple_list):
    """快速版本——预计算三元组列表"""
    viol = 0
    for a, b, c, bad_set in triple_list:
        if (orient[a], orient[b], orient[c]) in bad_set:
            viol += 1
    return viol

# ===========================================================
# 贪心初始化
# ===========================================================
def greedy_init(cells, conflicts, n):
    """逐个 cell 确定取向：选择使当前违例数最小的"""
    N = len(cells)
    orient = [0] * N
    # 先给参与冲突最多的 cell 赋值
    cell_conflict_count = Counter()
    for (a, b, c) in conflicts:
        cell_conflict_count[a] += 1
        cell_conflict_count[b] += 1
        cell_conflict_count[c] += 1
    
    order = [x for x, _ in cell_conflict_count.most_common()]
    remaining = [x for x in range(N) if x not in order]
    order += remaining
    
    for cell in order:
        best_r = 0
        best_v = 1e9
        for r in range(4):
            orient[cell] = r
            v = evaluate(orient, {k: v for k, v in conflicts.items() if cell in k})
            if v < best_v:
                best_v = v
                best_r = r
        orient[cell] = best_r
    return orient

# ===========================================================
# 模拟退火
# ===========================================================
def sa_orient(conflicts, triple_list, N, n_iter=50000, seed=42, verbose=True):
    rng = random.Random(seed)
    
    # 初始解
    orient = [rng.randint(0, 3) for _ in range(N)]
    curr_v = evaluate_fast(orient, conflicts, triple_list)
    best_orient = list(orient)
    best_v = curr_v
    
    # 冷却参数
    T0 = 2.0
    T_end = 0.01
    
    for it in range(n_iter):
        T = T0 * (T_end / T0) ** (it / n_iter)
        
        # 随机更改一个 cell 的取向
        cell = rng.randint(0, N - 1)
        old_r = orient[cell]
        new_r = (old_r + rng.randint(1, 3)) % 4
        
        orient[cell] = new_r
        new_v = evaluate_fast(orient, conflicts, triple_list)
        delta = new_v - curr_v
        
        if delta < 0 or rng.random() < math.exp(-delta / T):
            curr_v = new_v
            if curr_v < best_v:
                best_v = curr_v
                best_orient = list(orient)
                if verbose and best_v <= 15:
                    print(f"    iter {it}: best_v = {best_v}")
        else:
            orient[cell] = old_r  # revert
        
        # 逃逸机制：长时间无改进则重启
        if it > 10000 and best_v == curr_v and it % 5000 == 0 and T < 0.5:
            # 部分重启：保留一部分好的取向，随机化其余
            n_keep = N // 2
            keep_set = set(rng.sample(range(N), n_keep))
            for c in range(N):
                if c not in keep_set:
                    orient[c] = rng.randint(0, 3)
            curr_v = evaluate_fast(orient, conflicts, triple_list)
    
    return best_orient, best_v

# ===========================================================
# 主要流程
# ===========================================================
print("=" * 60)
print("PURE ORIENTATION SOLVER — config_408")
print("=" * 60)

# 加载 2-因子
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
cells = [tuple(e) for e in data["edges"]]
N = len(cells)
n = 2 * 37  # 74

print(f"\n  2-factor: {N} cells")
print(f"  Building conflict table...", end=" ", flush=True)
t0 = time.time()

conflicts = build_conflict_table(cells, n)
elapsed = time.time() - t0
print(f"done ({elapsed:.1f}s)")
print(f"  Triples with at least 1 bad orientation: {len(conflicts)} out of {N*(N-1)*(N-2)//6}")

# 统计每三元组的冲突数分布
conflict_dist = Counter()
for bad_set in conflicts.values():
    conflict_dist[len(bad_set)] += 1
print(f"  Conflict count per triple:")
for k in sorted(conflict_dist):
    print(f"    {k} bad orientations: {conflict_dist[k]} triples")

# 预计算三元组列表（加速评估）
triple_list = [(a, b, c, bad_set) for (a, b, c), bad_set in conflicts.items()]

# ===========================================================
# 多轮 SA
# ===========================================================
print(f"\n{'='*60}")
print("RUNNING SA (multiple restarts)")
print(f"{'='*60}")

n_restarts = 20
n_iter_per = 50000
global_best_v = 1e9
global_best_orient = None

for restart in range(n_restarts):
    seed = 1000 + restart
    orient, v = sa_orient(conflicts, triple_list, N, n_iter=n_iter_per, 
                          seed=seed, verbose=(v <= 16 if 'v' in dir() else False))
    if v < global_best_v:
        global_best_v = v
        global_best_orient = orient
        print(f"\n  🏆 Restart {restart+1}: NEW BEST = {v} violations!")
    elif restart % 5 == 4:
        print(f"  Restart {restart+1}: {v} violations (best so far: {global_best_v})")

print(f"\n{'='*60}")
print(f"FINAL RESULT for config_408 2-factor:")
print(f"  Best violations found: {global_best_v}")
print(f"  SDP lower bound: 12.5 → ceil = 13")
print(f"  {'✅' if global_best_v <= 15 else '❌'} {'Below 16 barrier!' if global_best_v <= 15 else 'Still at 16'}")
print(f"{'='*60}")

# 如果优于当前 SA 结果，保存
if global_best_v < 16:
    result = {
        "m": 37,
        "edges": data["edges"],
        "best_violations": global_best_v,
        "best_orientation": global_best_orient,
        "sdp_lb": 12.5,
        "note": "Pure orientation solver. Better than combined SA."
    }
    path = f"{HERE}/results/config_408_best_orient.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=1)
    print(f"\n  Saved to: {path}")
else:
    print(f"\n  Orientation SA couldn't beat combined SA's 16.")
    print(f"  SDP bound 12.5 suggests true minimum ≥ 13, but orientation search found max 16.")
    print(f"  Either SA orientation search is insufficient, or SDP bound is not tight.")
