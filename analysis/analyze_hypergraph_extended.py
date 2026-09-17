#!/usr/bin/env python3
"""
Extended hypergraph analysis for multiple n values.
Computes H_n^dir: direction-based 3-uniform collinearity hypergraph.
Saves results to JSON for further analysis.

n=12,16,20: O(m^3) triple loops in Python (baseline verified)
n=24:     ~3.9M triples (expected ~2 min)
n=28:     ~10M triples  (expected ~5-10 min)
n=32:     ~22M triples  (expected ~15-30 min)
"""
import os, math, random, itertools, json, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "flammenkamp_cache")
ALPH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
VAL = {c: i for i, c in enumerate(ALPH)}
TARGETS = [12, 16, 20, 24, 28, 32]

def decode_line(line, n):
    line = line.rstrip("\n").rstrip("\r")
    if not line:
        return None
    pre = line[0]
    body = line[1:] if pre in ".:/-ocx+*" else line
    if len(body) < 2 * n:
        return None
    cols = []
    for r in range(n):
        c1 = VAL.get(body[2 * r]); c2 = VAL.get(body[2 * r + 1])
        if c1 is None or c2 is None or not (0 <= c1 < n and 0 <= c2 < n):
            return None
        cols += [c1, c2]
    return cols

def load_rot4_all(n):
    for ext in ["", ".few"]:
        p = os.path.join(CACHE, f"n{n}_rot4{ext}")
        if os.path.exists(p):
            out = []
            with open(p) as f:
                for line in f:
                    c = decode_line(line, n)
                    if c:
                        out.append(c)
            if out:
                return out
    return []

def r180(p, n):
    return (n - 1 - p[0], n - 1 - p[1])

def dir_of(p, n):
    a = 2 * p[0] - (n - 1); b = 2 * p[1] - (n - 1)
    g = math.gcd(a, b) or 1; a, b = a // g, b // g
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    return (a, b)

def collinear3(pts):
    for a in range(3):
        x1, y1 = pts[a]
        for b in range(a + 1, 3):
            x2, y2 = pts[b]
            for c in range(b + 1, 3):
                x3, y3 = pts[c]
                if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                    return True
    return False

def build_orbits(n):
    """All R180-orbits on the even-n grid, each as (dir, (p, q))."""
    seen = set(); orbits = []
    for r in range(n):
        for c in range(n):
            p = (r, c)
            if p in seen:
                continue
            q = r180(p, n)
            seen.add(p); seen.add(q)
            orbits.append((dir_of(p, n), (p, q)))
    return orbits

def analyze_n(n, rseed=20260709):
    sols = load_rot4_all(n)
    orbits = build_orbits(n)
    m = len(orbits)
    pts_of = [o[1] for o in orbits]
    dirs_of = [o[0] for o in orbits]
    
    t0 = time.time()
    forbidden_triples = 0
    total = 0
    danger = Counter()
    
    for i in range(m):
        p_i = pts_of[i]
        for j in range(i + 1, m):
            p_j = pts_of[j]
            pts_ij = p_i + p_j  # 4 points
            for k in range(j + 1, m):
                total += 1
                six = pts_ij + pts_of[k]
                if collinear3(six):
                    forbidden_triples += 1
                    danger[dirs_of[i]] += 1
                    danger[dirs_of[j]] += 1
                    danger[dirs_of[k]] += 1
    
    elapsed = time.time() - t0
    
    # Top dangerous directions
    top_dir = sorted(danger.items(), key=lambda kv: -kv[1])[:10]
    
    # Solution analysis (independent set check + mean danger)
    sol_data = {"total": len(sols), "independent": 0, "mean_danger": []}
    for cols in sols:
        pts = [(r, cols[2*r]) for r in range(n)] + [(r, cols[2*r+1]) for r in range(n)]
        seen = set(); dsol = []
        for p in pts:
            if p in seen: continue
            q = r180(p, n); seen.add(p); seen.add(q)
            dsol.append(dir_of(p, n))
        # Independent set check
        idx_map = {}
        for idx, (d, _) in enumerate(orbits):
            idx_map[d] = idx
        idxs = [idx_map[d] for d in dsol]
        bad = False
        for a in range(len(idxs)):
            for b in range(a+1, len(idxs)):
                for c in range(b+1, len(idxs)):
                    if collinear3(pts_of[idxs[a]] + pts_of[idxs[b]] + pts_of[idxs[c]]):
                        bad = True; break
                if bad: break
            if bad: break
        if not bad:
            sol_data["independent"] += 1
        sol_data["mean_danger"].append(sum(danger[d] for d in dsol) / len(dsol))
    
    # Random n-subset baseline
    rand_means = []
    random.seed(rseed)
    for _ in range(100):
        chosen = random.sample(range(m), n)
        dm = sum(danger[dirs_of[idx]] for idx in chosen) / n
        rand_means.append(dm)
    
    result = {
        "n": n,
        "orbits": m,
        "total_triples": total,
        "forbidden_triples": forbidden_triples,
        "edge_density": forbidden_triples / total if total > 0 else 0,
        "elapsed_sec": round(elapsed, 1),
        "danger_directions": len(danger),
        "danger_mean": sum(danger.values()) / len(danger) if danger else 0,
        "danger_max": max(danger.values()) if danger else 0,
        "top10_directions": top_dir,
        "solutions": sol_data,
        "random_mean_danger": sum(rand_means) / len(rand_means),
        "solution_mean_danger": sum(sol_data["mean_danger"]) / len(sol_data["mean_danger"]) if sol_data["mean_danger"] else 0,
    }
    return result

def main():
    results = []
    for n in TARGETS:
        print(f"\n{'='*60}\nAnalyzing n={n}...")
        r = analyze_n(n)
        results.append(r)
        print(f"  orbits={r['orbits']}  triples={r['total_triples']:,}  forbidden={r['forbidden_triples']:,}")
        print(f"  edge_density={r['edge_density']*100:.3f}%  elapsed={r['elapsed_sec']}s")
        print(f"  top-3 dangerous: {r['top10_directions'][:3]}")
        print(f"  soln indep={r['solutions']['independent']}/{r['solutions']['total']}")
        print(f"  soln mean danger={r['solution_mean_danger']:.1f} vs random={r['random_mean_danger']:.1f}")
    
    report = {"targets": TARGETS, "results": results}
    path = os.path.join(HERE, "hypergraph_data.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n[written] {path}")
    
    # Summary table
    print(f"\n{'='*60}")
    print(f"{'n':>4}  {'orbits':>7}  {'triples':>10}  {'forbidden':>10}  {'density%':>8}  {'time(s)':>8}  {'soln/rand':>10}")
    print("-"*65)
    for r in results:
        sr_ratio = r['solution_mean_danger'] / r['random_mean_danger'] if r['random_mean_danger'] > 0 else 0
        print(f"{r['n']:>4}  {r['orbits']:>7}  {r['total_triples']:>10,}  {r['forbidden_triples']:>10,}  {r['edge_density']*100:>8.3f}  {r['elapsed_sec']:>8.1f}  {sr_ratio:>10.3f}")

if __name__ == "__main__":
    main()
