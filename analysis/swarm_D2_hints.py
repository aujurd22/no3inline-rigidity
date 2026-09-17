"""swarm_D2_hints.py -- derive loop-free CP-SAT hints for m=37 from m=36 solution.

A known m=36 rot4-NTIL is a valid 2-factor on {0..35}.  To make a FULL m=37
2-factor (37 edges, degree exactly 2 at every vertex 0..36) WITHOUT using a loop
edge (which the CP-SAT engine handles specially), we perform one 2-switch that
introduces vertex 36:
    remove edge {a,b} in the m=36 factor,
    add edges {a,36} and {b,36}.
This keeps every vertex degree-2, is simple (no multiedge/2-cycle since 36 is
new), and yields 37 edges.  We produce several distinct hints by (i) rotating
the m=36 fundamental cells by 0/1/2 90-degree steps and (ii) splitting a
different edge of the m=36 factor, so CP-SAT explores different branches.
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37


def rot_cell(c, k, m):
    x, y = c
    for _ in range(k % 4):
        x, y = (m - 1 - y, x)
    return (x, y)


def main():
    sol = json.load(open(os.path.join(HERE, "results", "solutions", "m36.json")))
    cells36 = [tuple(int(v) for v in c) for c in sol["cells"]]
    edges36 = [(min(x, y), max(x, y)) for (x, y) in cells36]
    print(f"m36 solution: {len(edges36)} edges (expected 36)")

    out = {}
    # Only identity (k=0) and 180-degree (k=2) rotations are vertex relabelings
    # that preserve 2-factor degree structure; 90-degree (k=1) does NOT.
    specs = []
    for k in (0, 2):
        for si in (0, 8, 16, 24, 32):
            specs.append((k, si))
    valid_hints = []
    for (k, si) in specs:
        # rotated m36 edges/cells
        redges, rcells = [], []
        for (x, y) in cells36:
            nx, ny = rot_cell((x, y), k, 36)
            redges.append((min(nx, ny), max(nx, ny)))
            rcells.append((nx, ny))
        # pick an edge to split (must be a non-loop edge)
        idx = si % len(redges)
        while redges[idx][0] == redges[idx][1]:
            idx = (idx + 1) % len(redges)
        a, b = redges[idx]
        # remove {a,b}, add {a,36},{b,36}
        hedges = [e for j, e in enumerate(redges) if j != idx]
        hcells = [c for j, c in enumerate(rcells) if j != idx]
        hedges.append((min(a, 36), max(a, 36)))
        hedges.append((min(b, 36), max(b, 36)))
        hcells.append((a, 36))
        hcells.append((b, 36))
        # validity: simple 2-regular on {0..36}, no loops
        deg = [0] * M
        ok = (len(hedges) == M)
        from collections import Counter
        ec = Counter(hedges)
        multi = [e for e, c in ec.items() if c > 1]
        for (u, v) in hedges:
            w = 2 if u == v else 1
            deg[u] += w
            deg[v] += w
        if any(d != 2 for d in deg) or multi:
            ok = False
        out[f"m36k{k}_split{idx}"] = {"valid": ok, "multi": multi,
                                      "degbad": [(i, d) for i, d in enumerate(deg) if d != 2]}
        fn = os.path.join(HERE, "results", f"swarm_D2_hint_m36rot{k}_s{idx}.json")
        with open(fn, "w") as f:
            json.dump({"m": M, "edges": hedges, "cells": hcells}, f, indent=2)
        if ok:
            valid_hints.append(fn)
        print(f"  hint m36k{k}_s{idx}: valid={ok} multi={multi} "
              f"deg!=2={[(i,d) for i,d in enumerate(deg) if d!=2]} -> {fn}")

    with open(os.path.join(HERE, "results", "swarm_D2_hints_index.json"), "w") as f:
        json.dump({kk: vv["valid"] for kk, vv in out.items()}, f, indent=2)


if __name__ == "__main__":
    main()
