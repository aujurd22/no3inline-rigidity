"""Independent brute-force ground-truth verifier for rot4-NTIL / m=37.

Goal: a verifier that does NOT rely on the external agent's Ising model.
It reconstructs the 148 points from (edges, bits) and counts collinear triples
by a direct determinant test over all C(148,3) triples. This is the ultimate
ground truth any claimed number must survive.

Also includes helpers reused by the search drivers:
  - c4_lifts
  - points_from(edges, bits, m)
  - is_2factor(edges, m)
  - diagonal_unsafe(edges, m)  -> True if factor is diagonal-unsafe
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # m37_continue
OUT = ROOT / "outputs"


def c4_lifts(m, cell):
    n = 2 * m
    x, y = cell
    out = []
    for _ in range(4):
        out.append((x, y))
        x, y = n - 1 - y, x
    return out


def points_from(edges, bits, m):
    """Return the 148 (or 4*len(edges)) lifted points for a (edges, bits)."""
    pts = []
    for (u, v), bit in zip(edges, bits):
        cell = (u, v) if bit == 0 else (v, u)
        pts.extend(c4_lifts(m, cell))
    return pts


def brute_bad(m, edges, bits):
    """Independent geometric bad-triple count via determinant over all triples."""
    pts = points_from(edges, bits, m)
    if len(set(pts)) != len(pts):
        raise AssertionError(f"duplicate lifted points: {len(pts)-len(set(pts))}")
    total = 0
    for p, q, r in itertools.combinations(pts, 3):
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        total += det == 0
    return total


def is_2factor(edges, m):
    deg = [0] * m
    seen = set()
    for u, v in edges:
        if not (0 <= u < m and 0 <= v < m and u <= v):
            return False, f"bad edge {(u,v)}"
        if (u, v) in seen:
            return False, f"duplicate edge {(u,v)}"
        seen.add((u, v))
        if u == v:
            deg[u] += 2
        else:
            deg[u] += 1
            deg[v] += 1
    if len(edges) != m:
        return False, f"edge count {len(edges)} != {m}"
    if any(d != 2 for d in deg):
        return False, f"degree histogram {deg}"
    return True, "ok"


def diagonal_unsafe(edges, m):
    """A 2-factor is diagonal-unsafe if it contains a slope +-1 collinear triple
    regardless of orientation. Equivalent test: does ANY orientation produce a
    bad triple lying on a diagonal line (slope +1 or -1)?

    Cheap structural test (orientation-independent): for the underlying
    undirected 2-factor, check whether the set of cells admits three lifts
    collinear on a slope+-1 line. We reuse the external diagonal_constraint idea
    but implement it independently: build points for EVERY orientation combo is
    too big; instead we test the orientation-free condition directly.

    Orientation-free condition (proven in their diagonal_constraint_test):
    rotating about the anti-diagonal / transposing (u,v)<->(v,u) preserves the
    multiset of diagonal coordinates (x-y, x+y) of each cell's C4 orbit. So the
    existence of a slope+-1 bad triple depends ONLY on the 2-factor, not on the
    orientation. Hence: pick ANY orientation (e.g. bits all 0), build points,
    and test whether ANY bad triple has slope +1 or -1. If yes -> diagonal-unsafe
    (every orientation has one). If no -> diagonal-safe.
    """
    n = 2 * m
    # pick the all-zero orientation; diagonal safety is orientation-independent
    pts = []
    for (u, v) in edges:
        pts.extend(c4_lifts(m, (u, v)))
    # group by slope; we only care about slope +1 (dy==dx) or -1 (dy==-dx)
    for p, q, r in itertools.combinations(pts, 3):
        # slope +1: q-p and r-p both have dx==dy
        def slope_is(p1, p2):
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            return dx == dy or dx == -dy
        if slope_is(p, q) and slope_is(p, r):
            # need all three on the SAME diagonal line
            # collinearity already implied if two pairwise slope matches and they share p
            det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            if det == 0:
                return True
    return False


def verify_entry(entry):
    m = 37
    edges = [tuple(e) for e in entry["edges"]]
    bits = entry["bits"]
    ok, msg = is_2factor(edges, m)
    if not ok:
        return {"valid_2factor": False, "why": msg}
    bad = brute_bad(m, edges, bits)
    reported = entry.get("value") or entry.get("geometry")
    diag = diagonal_unsafe(edges, m)
    return {
        "id": entry.get("id"),
        "valid_2factor": True,
        "brute_bad": bad,
        "reported": reported,
        "match": bad == reported,
        "diagonal_safe": (not diag),
        "reported_diag_safe": entry.get("diagonal_safe"),
    }


def main():
    arc = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    targets = sys.argv[1:] or [e["id"] for e in arc["archive"] if e["value"] <= 52]
    by_id = {e["id"]: e for e in arc["archive"]}
    rows = []
    for tid in targets:
        e = by_id.get(tid)
        if e is None:
            print(f"!! no such id {tid}")
            continue
        r = verify_entry(e)
        rows.append(r)
        print(r)
    mism = [r for r in rows if not r.get("match")]
    print(f"\nchecked {len(rows)}, mismatches={len(mism)}")
    if mism:
        print("MISMATCHES:", [r["id"] for r in mism])


if __name__ == "__main__":
    main()
