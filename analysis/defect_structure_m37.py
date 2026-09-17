import json, os, importlib.util
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("solver", os.path.join(HERE, "solver_theory_m37.py"))
solver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solver)

m = 37
data = json.load(open(os.path.join(HERE, "results", "solver_theory_m37.json")))
edges = [tuple(e) for e in data["edges"]]
cells = [tuple(c) for c in data["cells"]]
board = solver.Board(m)
board.build(edges, cells)

groups = defaultdict(list)
N = len(board.lifts)
for a in range(N):
    pa = board.lifts[a]
    for b in range(a + 1, N):
        pb = board.lifts[b]
        if pa == pb:
            continue
        k = solver.line_of(pa, pb)
        groups[k].append((a, b))

defect_lines = []
cell_inv = Counter()
slope_cnt = Counter()
for k, pairs in groups.items():
    pts = set()
    for (a, b) in pairs:
        pts.add(a); pts.add(b)
    s = len(pts)
    if s >= 3:
        triples = s * (s - 1) * (s - 2) // 6
        defect_lines.append((k, s, triples, pts))
        slope_cnt[k[:2]] += 1
        for idx in pts:
            cell_inv[idx // 4] += 1

print(f"m={m}  total defect lines={len(defect_lines)}  "
      f"total triples={sum(d[2] for d in defect_lines)}  "
      f"max_line_size={max(d[1] for d in defect_lines)}")
print("\nTop 15 cells (edge idx) by #defect-lifts involved:")
for idx, c in cell_inv.most_common(15):
    print(f"  edge {idx} {edges[idx]}: {c}")
print(f"\nDistinct slopes among defect lines: {len(slope_cnt)}")
print("Top 15 slopes (A,B) by #defect-lines:")
for sl, c in slope_cnt.most_common(15):
    print(f"  {sl}: {c}")
tot = sum(cell_inv.values())
cum = 0; ntop = 0
for idx, c in cell_inv.most_common():
    cum += c; ntop += 1
    if cum >= tot / 2:
        break
print(f"\nCell-involvement total={tot}; top {ntop} edges cover >=50% of defect-lift "
      f"involvements (out of {len(edges)} edges).")
# how concentrated: edges involved at all
print(f"Edges involved in >=1 defect: {len(cell_inv)} / {len(edges)}")
