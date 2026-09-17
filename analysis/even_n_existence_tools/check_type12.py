"""
检查 Type 1/2 全坏三元组在随机 D=0/L=1 2-因子中的普适性。
Type 1: 三 cell 满足 a+b=常数 → 6 点全在 y=-x+C 上 → 全坏
"""
import sys, random, itertools
from collections import Counter
sys.path.insert(0, '.')
sys.path.insert(0, 'benders')
from benders.benders_global import build_master, y_to_edges
from ortools.sat.python import cp_model

M = 37
random.seed(12345)

def has_type1_triple(edges):
    """含自环的 Type 1 (a+b=const) 三元组"""
    loops = [(i,u,v) for i,(u,v) in enumerate(edges) if u==v]
    cycles = [(i,u,v) for i,(u,v) in enumerate(edges) if u!=v]
    for li, su, sv in loops:
        C = su + sv
        matching = [(i,u,v) for i,u,v in cycles if u+v==C]
        for (i1,u1,v1),(i2,u2,v2) in itertools.combinations(matching, 2):
            if su in {u1,v1,u2,v2}: continue
            return True, (su,sv), (u1,v1), (u2,v2)
    # 也检查不含自环的 Type 1 (纯 cycle 三元组)
    for (i1,u1,v1),(i2,u2,v2),(i3,u3,v3) in itertools.combinations(cycles, 3):
        s1,s2,s3 = u1+v1, u2+v2, u3+v3
        if s1==s2==s3:
            return True, ("cycle",), (u1,v1), (u2,v2), (u3,v3)
    return False, None

def has_type2_triple(edges):
    """含自环的 Type 2 (|b-a|=const) 三元组"""
    loops = [(i,u,v) for i,(u,v) in enumerate(edges) if u==v]
    cycles = [(i,u,v) for i,(u,v) in enumerate(edges) if u!=v]
    for li, su, sv in loops:
        for (i1,u1,v1),(i2,u2,v2) in itertools.combinations(cycles, 2):
            if abs(v1-u1) == abs(v2-u2):
                if su not in {u1,v1,u2,v2}:
                    return True, (su,sv), (u1,v1), (u2,v2)
    # 非自环 Type 2
    for (i1,u1,v1),(i2,u2,v2),(i3,u3,v3) in itertools.combinations(cycles, 3):
        d1,d2,d3 = abs(v1-u1), abs(v2-u2), abs(v3-u3)
        if d1==d2==d3:
            return True, ("cycle",), (u1,v1), (u2,v2), (u3,v3)
    return False, None

# 构建主问题
model, y, positions, pos2idx = build_master(M, random_obj=True, seed=42)
for (u,v) in positions:
    if u<v: model.Add(y[(u,v)] <= 1)
model.Add(sum([y[(i,i)] for i in range(M)]) == 1)

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 10
solver.parameters.num_search_workers = 1

n_t1, n_t2, n_none = 0, 0, 0
seen = set()
N_SAMPLES = 50

print(f"Type1/2 检查 ({N_SAMPLES} D=0/L=1 随机因子)")

for trial in range(N_SAMPLES * 2):
    if len(seen) >= N_SAMPLES: break
    st = solver.Solve(model)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): break
    edges = y_to_edges(solver, y, positions)
    eset = frozenset((min(u,v), max(u,v)) for u,v in edges)
    if eset in seen:
        cnt = Counter((min(u,v),max(u,v)) for u,v in edges)
        conds = [model.NewBoolVar(f"n{trial}_{up}") for up in cnt]
        for cond, (up, rp) in zip(conds, cnt.items()):
            model.Add(y[up] != rp).OnlyEnforceIf(cond)
        model.AddBoolOr(conds)
        continue
    seen.add(eset)
    
    t1 = has_type1_triple(edges)[0]
    t2 = has_type2_triple(edges)[0]
    if t1: n_t1+=1
    if t2: n_t2+=1
    if not t1 and not t2: n_none+=1
    
    if len(seen) <= 5 or (not t1 and not t2):
        print(f"  [{len(seen)}] T1={t1} T2={t2}")
    
    cnt = Counter((min(u,v),max(u,v)) for u,v in edges)
    conds = [model.NewBoolVar(f"x{trial}_{up}") for up in cnt]
    for cond, (up, rp) in zip(conds, cnt.items()):
        model.Add(y[up] != rp).OnlyEnforceIf(cond)
    model.AddBoolOr(conds)

print(f"\nType1={n_t1} Type2={n_t2} None={n_none} / {len(seen)}")

# 检查 m=36 解
from validate_solver import load_positive
e36, b36, _ = load_positive(36)
t1_36, _ = has_type1_triple(e36)
t2_36, _ = has_type2_triple(e36)
print(f"m=36 解: T1={t1_36} T2={t2_36}")

# 如果在无 Type1/2 的因子上做 GB 检查...
if n_none > 0:
    print(f"\n存在 {n_none} 个无 Type1/2 的因子 → 障碍来自更大的 cell 组合")
else:
    print(f"\n所有 50 个因子都有 Type1 或 Type2 → 可能为普适性质！")
