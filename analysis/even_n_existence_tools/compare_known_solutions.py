"""
对比已知解 (m=5,10,14,36) vs m=37 差异。
"""
import sys, itertools, time
from collections import Counter
sys.path.insert(0, '.')
from validate_solver import load_positive, c4_lifts_n, load_negatives

def collinear_check(pts):
    for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            return True
    return False

def count_allbad_triples(edges, N_val):
    ncells = len(edges)
    cell_pts = {}
    for idx, (u, v) in enumerate(edges):
        cell_pts[(idx, 0)] = c4_lifts_n((u, v), N_val)
        cell_pts[(idx, 1)] = c4_lifts_n((v, u), N_val)
    count = 0
    for i, j, k in itertools.combinations(range(ncells), 3):
        all_bad = True
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = cell_pts[(i, oi)] + cell_pts[(j, oj)] + cell_pts[(k, ok)]
            if not collinear_check(pts):
                all_bad = False
                break
        if all_bad:
            count += 1
    return count

def count_cnf_clauses(edges, N_val):
    ncells = len(edges)
    cell_pts = {}
    for idx, (u, v) in enumerate(edges):
        cell_pts[(idx, 0)] = c4_lifts_n((u, v), N_val)
        cell_pts[(idx, 1)] = c4_lifts_n((v, u), N_val)
    n = 0
    for i, j, k in itertools.combinations(range(ncells), 3):
        for oi, oj, ok in itertools.product([0, 1], repeat=3):
            pts = cell_pts[(i, oi)] + cell_pts[(j, oj)] + cell_pts[(k, ok)]
            if collinear_check(pts):
                n += 1
    return n

# Load data
e5, b5, _ = load_positive(5)
e10, b10, _ = load_positive(10)
e14, b14, _ = load_positive(14)
e36, b36, _ = load_positive(36)
basins = load_negatives()

print("=" * 60)
print("对比: 已知解 vs V20 盆地")
print("=" * 60)

all_data = [
    ("m=5   (质数)", e5, 10),
    ("m=10  (合数)", e10, 20),
    ("m=14  (合数)", e14, 28),
    ("m=36  (合数)", e36, 72),
    ("V20_01 (m=37)", basins[0][1], 74),
    ("V20_02 (m=37)", basins[1][1], 74),
    ("V20_03 (m=37)", basins[2][1], 74),
    ("V20_04 (m=37)", basins[3][1], 74),
    ("V20_05 (m=37)", basins[4][1], 74),
    ("V20_06 (m=37)", basins[5][1], 74),
]

print(f"{'Name':<20s} {'m':>3s} {'自环':>3s} {'2-圈':>4s} {'全坏3':>5s} {'CNF子句':>7s} {'子句/m':>6s}")
print("-" * 60)

for name, edges, N_val in all_data:
    t0 = time.time()
    n_bad3 = count_allbad_triples(edges, N_val)
    n_clauses = count_cnf_clauses(edges, N_val)
    t = time.time() - t0
    
    cnt = Counter((min(u,v), max(u,v)) for u,v in edges)
    loops = sum(1 for u,v in edges if u==v)
    two_cycles = sum(1 for c in cnt.values() if c >= 2)
    ncells = len(edges)
    
    print(f"{name:<20s} {ncells:>3d} {loops:>3d} {two_cycles:>4d} {n_bad3:>5d} {n_clauses:>7d} {n_clauses//ncells:>6d} ({t:.0f}s)")

# === 分析 ===
print(f"\n=== 分析 ===")
print("1. 全坏三元组=0 是有解的必要条件:")
for name, edges, N_val in all_data[:4]:  # 已知解
    n_bad3 = count_allbad_triples(edges, N_val)
    status = "OK" if n_bad3 == 0 else "FAIL"
    print(f"   {name}: {n_bad3} -> {status}")

print("\n2. m=37 V20 盆地的 CNF 子句数:")
for name, edges, N_val in all_data[4:]:
    n = count_cnf_clauses(edges, N_val)
    print(f"   {name}: {n} 子句 ({n//len(edges)}/cell)")

print(f"\n3. 子句密度对比:")
for name, edges, N_val in all_data:
    n = count_cnf_clauses(edges, N_val)
    nc = len(edges)
    max_clauses = nc * (nc-1) * (nc-2) // 6 * 8  # C(nc,3) * 8
    density = n / max_clauses * 100 if max_clauses > 0 else 0
    print(f"   {name}: {n}/{max_clauses} = {density:.2f}%")

# === 边跨度分析 ===
print(f"\n4. 边跨度 (|u-v|) 分布:")
for name, edges, N_val in all_data:
    spans = [abs(u-v) for u,v in edges]
    print(f"   {name}: min={min(spans)} max={max(spans)} mean={sum(spans)/len(spans):.0f} median={sorted(spans)[len(spans)//2]}")

# === 顶点度数分布 (原始 2-因子) ===
print(f"\n5. 自环位置:")
for name, edges, N_val in all_data:
    loops = [(u,v) for u,v in edges if u==v]
    print(f"   {name}: 自环数={len(loops)} 位置={loops}")
