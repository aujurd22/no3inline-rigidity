import sys, json
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("st", "solver_theory_m37.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

m = 37
d = json.load(open("results/solver_theory_m37_long.json"))
edges = [tuple(e) for e in d["edges"]]
cells = [tuple(c) for c in d["cells"]]
b = st.Board(m)
b.build(edges, cells)
print("verify_total =", b.verify_total(), " incremental total_bad =", b.total_bad)

# per-edge triple-load score: for each edge e on a defect line k (s_k lifts),
# it participates in C(s_k-1,2) bad triples on that line.
def edge_scores(board):
    sc = {}
    for k, lp in board.line_pts.items():
        s = len(lp)
        if s < 3:
            continue
        tri = s * (s - 1) * (s - 2) // 6
        c3 = s - 2
        edges_k = {i >> 2 for i in lp}
        for e in edges_k:
            sc[e] = sc.get(e, 0) + c3  # C(s-1,2)=C(s,3)*3/s ; use exact below
    # exact: C(s-1,2) = (s-1)(s-2)/2
    sc = {}
    for k, lp in board.line_pts.items():
        s = len(lp)
        if s < 3:
            continue
        per = (s - 1) * (s - 2) // 2
        for e in {i >> 2 for i in lp}:
            sc[e] = sc.get(e, 0) + per
    return sc

sc = edge_scores(b)
hot_edges = sorted(sc.items(), key=lambda kv: -kv[1])
print("total defects (triples) =", b.total_bad)
print("n lines with >=3 =", b.n_defect_lines if hasattr(b, 'n_defect_lines') else len(b.line_hot))
print("edges involved in >=1 defect line:", len(b.hot), "of", m)
print("top 15 edge triple-loads:", hot_edges[:15])
# coverage: how many edges cover 50% / 90% of triple-load
tot = sum(sc.values())
cum = 0
n50 = n90 = None
for i, (e, v) in enumerate(hot_edges):
    cum += v
    if n50 is None and cum >= 0.5 * tot:
        n50 = i + 1
    if n90 is None and cum >= 0.9 * tot:
        n90 = i + 1
print(f"triple-load total={tot}; edges to cover 50%={n50}, 90%={n90}")

# line size distribution
from collections import Counter
sizes = Counter(len(lp) for lp in b.line_pts.values() if len(lp) >= 3)
print("defect-line size distribution (s:count):", dict(sorted(sizes.items())))

# loops present?
loops = [i for i, e in enumerate(edges) if e[0] == e[1]]
print("loop edges (indices):", loops, "count", len(loops))
# which hot edges are loops?
print("loop edges among hot:", [(i, sc.get(i, 0)) for i in loops if i in sc])
