"""
mixed_moment_analysis.py — Explore mixed 4th-moment invariants on known rot4-NTIL
solutions, testing the user's hypothesis that non-separable sum
  Σ (i - c)^2 * (j - c)^2   (where c = (m-1)/2)
may vary across configurations, unlike separable/additive invariants.

Usage: python mixed_moment_analysis.py
"""
import os, sys, json, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

def load_known_solutions():
    soldir = os.path.join(HERE, "results", "solutions")
    data = {}
    for fn in sorted(os.listdir(soldir)):
        if fn.endswith(".json"):
            m = int(fn[1:3])
            fp = os.path.join(soldir, fn)
            data[f"m{m}"] = json.load(open(fp))
    return data

def extract_cells(entry):
    """Extract list of (i,j) cells from a known solution entry (flexible format)."""
    if isinstance(entry, list) and entry:
        if isinstance(entry[0], list) and len(entry[0]) == 2:
            return [tuple(c) for c in entry]
        if isinstance(entry[0], dict):
            for ck in ("cells", "config", "solution"):
                val = entry[0].get(ck)
                if val:
                    if isinstance(val, list):
                        if isinstance(val[0], list) and len(val[0]) == 2:
                            return [tuple(c) for c in val]
                        if isinstance(val[0], dict) and "cells" in val[0]:
                            return [tuple(c) for c in val[0]["cells"]]
                    break
    if isinstance(entry, dict):
        for ck in ("cells",):
            val = entry.get(ck)
            if val and isinstance(val, list):
                if isinstance(val[0], list) and len(val[0]) == 2:
                    return [tuple(c) for c in val]
    return []

def mixed_moment(cells, c):
    """Σ (i - c)^2 * (j - c)^2"""
    return sum((i - c) ** 2 * (j - c) ** 2 for i, j in cells)

def bilinear_moment(cells, c):
    """Σ (i - c) * (j - c)"""
    return sum((i - c) * (j - c) for i, j in cells)

def quartic_norm(cells, c):
    """Σ ((i-c)^4 + (j-c)^4) — purely separable, may be constant"""
    return sum((i - c) ** 4 + (j - c) ** 4 for i, j in cells)

def sum_mod(cells, p):
    results = {}
    for a, b in [(1, 1), (1, 2), (2, 1), (2, 2), (3, 1)]:
        val = sum(pow(i, a, p) * pow(j, b, p) for i, j in cells) % p
        results[f"i^{a}*j^{b}"] = val
    return results

def main():
    data = load_known_solutions()
    keys = sorted(data.keys(), key=lambda k: int(k[1:]))

    print("=" * 80)
    print("Mixed-Moment Invariant Analysis on Known rot4-NTIL Solutions")
    print("=" * 80)

    # Table of moments
    rows = []
    for key in keys:
        cells = extract_cells(data[key])
        if not cells:
            print(f"  WARNING: {key}: could not extract cells, skipping")
            continue
        m = max(max(c) for c in cells) + 1
        c = (m - 1) / 2.0
        qn = quartic_norm(cells, c)
        bl = bilinear_moment(cells, c)
        m4 = mixed_moment(cells, c)
        rows.append((key, m, qn, bl, m4))

    print(f"\n{'key':<8} {'m':>4} {'quartic_norm':>16} {'bilinear':>16} {'mixed4':>16}")
    print("-" * 64)
    for r in rows:
        print(f"{r[0]:<8} {r[1]:>4} {r[2]:>16.1f} {r[3]:>16.1f} {r[4]:>16.1f}")

    # Moment constancy check
    print("\n--- Moment variation across solutions (same m should have same moments) ---")
    by_m = defaultdict(list)
    for r in rows:
        by_m[r[1]].append(r)
    for m, group in sorted(by_m.items()):
        if len(group) > 1:
            qn_vals = set(round(g[2], 4) for g in group)
            bl_vals = set(round(g[3], 4) for g in group)
            m4_vals = set(round(g[4], 4) for g in group)
            print(f"  m={m}: quartic_norm={qn_vals} bilinear={bl_vals} mixed4={m4_vals}")

    # Mod-p analysis
    print("\n--- Bilinear/Mixed moments mod small primes ---")
    for p in [2, 3, 5, 7, 11, 13]:
        print(f"\n  p={p}:")
        vals = defaultdict(set)
        for key in keys:
            cells = extract_cells(data[key])
            if not cells:
                continue
            sm = sum_mod(cells, p)
            for k, v in sm.items():
                vals[k].add(v)
        for k, vset in sorted(vals.items()):
            print(f"    {k}: {len(vset)} distinct values {sorted(vset)[:8]}")

    # m=37 configs
    print("\n--- m=37 best configurations ---")
    for fn, label in [("solver_theory_m37_long.json", "best72"),
                      ("solver_theory_m37.json", "best96")]:
        fp = os.path.join(HERE, "results", fn)
        if os.path.exists(fp):
            d = json.load(open(fp))
            cells = d.get("cells", [])
            if isinstance(cells, list) and cells and isinstance(cells[0], list):
                c = 18.0  # (37-1)/2
                m4 = mixed_moment(cells, c)
                bl = bilinear_moment(cells, c)
                qn = quartic_norm(cells, c)
                print(f"  {label}: mixed4={m4:.1f} bilinear={bl:.1f} quartic_norm={qn:.1f}")

    print("\nDone.")

if __name__ == "__main__":
    main()
