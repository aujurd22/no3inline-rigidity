"""Constructive search: 3 strategies to find <408 clause 2-factors for m=37.
Full eval at 1.5s/config. ~2000 candidates = ~50 min."""
import json, time, random, math

M = 37; N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# ── C4 lift ──────────────────────────────────────────────────────
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3): x, y = N - 1 - y, x; pts.append((x, y))
    return pts
all_lifts = {(u, v): c4_lift(u, v) for u in range(M) for v in range(M)}

def is_collinear_12(lifts):
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i + 1, 12):
            xj, yj = lifts[j]
            if xi == xj and yi == yj: continue
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi: continue
                if dx * (yk - yi) == dy * (xk - xi): return True
    return False

cell_data = {}
for u in range(M):
    for v in range(M):
        pts0 = all_lifts[(u, v)]
        pts1 = all_lifts[(v, u)] if u != v else all_lifts[(u, v)]
        cell_data[(u, v)] = (pts0, pts1)

def triple_clause_count(pa0, pa1, pb0, pb1, pc0, pc1):
    count = 0
    for oa in (0, 1):
        pa = pa0 if oa == 0 else pa1
        for ob in (0, 1):
            pb = pb0 if ob == 0 else pb1
            for oc in (0, 1):
                pc = pc0 if oc == 0 else pc1
                if is_collinear_12(pa + pb + pc): count += 1
    return count

def total_clauses(edges):
    total = 0
    for a in range(M):
        pa = cell_data[edges[a]]
        for b in range(a + 1, M):
            pb = cell_data[edges[b]]
            for c in range(b + 1, M):
                total += triple_clause_count(pa[0], pa[1], pb[0], pb[1],
                                              cell_data[edges[c]][0], cell_data[edges[c]][1])
    return total

# ── Random 2-regular graph generators ────────────────────────────
def random_2regular(cycle_lengths, rng):
    vertices = list(range(M))
    rng.shuffle(vertices)
    edges = []
    pos = 0
    for clen in cycle_lengths:
        cycle = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cycle[k]; v = cycle[(k + 1) % clen]
            edges.append((min(u, v), max(u, v)))
    return edges

def two_swap(edges, rng):
    existing = set(edges)
    for _ in range(200):
        a, b = rng.randint(0, M-1), rng.randint(0, M-1)
        if b == a: continue
        i1, j1 = edges[a]; i2, j2 = edges[b]
        if len({i1, j1, i2, j2}) < 4: continue
        e1 = (min(i1, i2), max(i1, i2)); e2 = (min(j1, j2), max(j1, j2))
        edges_set_without_ab = existing - {edges[a], edges[b]}
        if e1 in edges_set_without_ab or e2 in edges_set_without_ab: continue
        if e1 == e2: continue
        new = list(edges)
        new[a] = e1; new[b] = e2
        return new
    return None

# ── Config_408 reference ─────────────────────────────────────────
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
c408_edges = [(min(u,v), max(u,v)) for u,v in data["edges"]]
c408_cl = total_clauses(c408_edges)
print(f"config_408: {c408_cl} clauses", flush=True)

rng = random.Random(999)
best_cl = 1e9
best_edges = None

# ── Strategy 1: Bipartite construction ───────────────────────────
# Partition: 18 "small" vertices in A, 19 "large" in B
# Generate random cycles and evaluate
# No strict bipartite filter — just ensure edges tend to be between A and B
print("\n=== Strategy 1: Pseudo-bipartite [28,9] ===", flush=True)
small_set = set(range(19))
for trial in range(1000):
    cells = random_2regular([28, 9], rng)
    # Quick check
    bp = sum(1 for u,v in cells if (u in small_set) != (v in small_set))
    if bp < 20: continue  # At least ~55% cross edges
    cl = total_clauses(cells)
    if cl < best_cl:
        best_cl = cl; best_edges = cells
        print(f"  ★ {best_cl} cls @ trial {trial} (bp={bp}/37)", flush=True)
        if cl < c408_cl:
            json.dump({"edges": best_edges, "clauses": cl, "strategy": "bipartite"},
                      open(f"{HERE}/results/strat1_breakthrough.json", "w"))
            print(f"  ★★★ BREAKTHROUGH! < {c408_cl}!", flush=True)

# ── Strategy 3: Permute config_408 vertex labels ─────────────────
print("\n=== Strategy 3: Permute config_408 labels ===", flush=True)
for trial in range(1000):
    perm = list(range(M))
    rng.shuffle(perm)
    permuted = [(perm[u], perm[v]) for u, v in c408_edges]
    permuted = [(min(u,v), max(u,v)) for u,v in permuted]
    deg = {}
    for u,v in permuted: deg[u]=deg.get(u,0)+1; deg[v]=deg.get(v,0)+1
    if min(deg.values()) < 2 or max(deg.values()) > 2: continue
    cl = total_clauses(permuted)
    if cl < best_cl:
        best_cl = cl; best_edges = permuted
        print(f"  ★ {best_cl} cls @ trial {trial}", flush=True)
        if cl < c408_cl:
            json.dump({"edges": best_edges, "clauses": cl, "strategy": "permute"},
                      open(f"{HERE}/results/strat3_breakthrough.json", "w"))
            print(f"  ★★★ BREAKTHROUGH!", flush=True)

# ── Strategy 4: SA from config_408 (with full eval, no incremental bug) ──
print("\n=== Strategy 4: SA from config_408 (100 steps) ===", flush=True)
edges = list(c408_edges)
current_cl = c408_cl
T = 200
for step in range(1, 101):
    new_edges = two_swap(edges, rng)
    if new_edges is None: continue
    new_cl = total_clauses(new_edges)
    delta = new_cl - current_cl
    if new_cl < best_cl or rng.random() < math.exp(-delta / T):
        edges = new_edges; current_cl = new_cl
        if current_cl < best_cl:
            best_cl = current_cl; best_edges = list(edges)
            print(f"  ★ {best_cl} cls @ SA step {step}", flush=True)
            if best_cl < c408_cl:
                json.dump({"edges": best_edges, "clauses": best_cl, "strategy": "sa"},
                          open(f"{HERE}/results/strat4_breakthrough.json", "w"))
    T = max(T * 0.97, 1.0)

print(f"\n=== Final: best_cl={best_cl} config_408={c408_cl} ===", flush=True)
if best_edges:
    json.dump({"edges": best_edges, "clauses": best_cl, "strategy": "combined"},
              open(f"{HERE}/results/constructive_best.json", "w"))
