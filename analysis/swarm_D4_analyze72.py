"""Analyze the known 72-baseline config (solver_theory_m37_long.json): characterize
the defect lines to understand the deep local-min wall. Quick, read-only."""
import os, sys, json
from math import isqrt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import Board

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'results', 'solver_theory_m37_long.json')))
m = d['m']
b = Board(m); b.build(d['edges'], d['cells'])
vt = b.verify_total()
print(f"m={m} best_bad={d['best_bad']} verify_total={vt} (should match)")
print(f"n_defect_lines={d.get('n_defect_lines')} max_line_size={d.get('max_line_size')}")

# group defects by the set of edges (vertices) they touch
edges = [tuple(e) for e in d['edges']]
# map edge -> vertices
def verts(e): return set(e)
from collections import Counter
# how many defect lines are pure-size-3?
sizes = Counter()
for dl in d.get('defect_lines', []):
    sizes[dl['points']] += 1
print("defect-line size histogram (from top-60 stored):", dict(sizes))

# For each defect line, which vertices (edge indices) are touched?
# Recompute properly from pc
touched_edges = set()
line_types = Counter()
for k, p in b.pc.items():
    s = (1 + isqrt(1 + 8*p)) // 2
    if s >= 3:
        touched_edges.update(i >> 2 for i in b.line_pts[k])
print(f"distinct edges touched by >=1 defect line: {len(touched_edges)} / {m}")

# Is the wall spread uniformly or concentrated?
import statistics
deg = [0]*m
for e in edges:
    for v in e: deg[v]+=1
print("edge degree distribution (expect all 2):", Counter(deg))

# For each vertex, count how many defect lines it participates in (hot)
hot = b.hot
hot_sorted = sorted(hot.items(), key=lambda kv: -kv[1])
print("top-10 vertices by #defect-lines touched:", hot_sorted[:10])
print("vertices with 0 defect-lines:", m - len(hot))
