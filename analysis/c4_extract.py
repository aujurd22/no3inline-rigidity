#!/usr/bin/env python3
"""
Extract the 2-factor (Row-Degree theorem) from every real C4 (rot4) solution
in the Flammenkamp cache, and study its construction-theoretic structure.

Mapping (Row-Degree theorem):
  C4 solution on n=2m grid  <-->  2-regular graph on vertices {0,...,m-1}
  edge {i,j}  <-->  fundamental-domain point (i,j) with 0<=i,j<m
  The 4-orbit is O(i,j) = {(i,j),(j,n-1-i),(n-1-i,n-1-j),(n-1-j,i)}.
  Among the 4 orbit points, exactly one has BOTH coordinates < m:  that is (i,j).

So: decode a rot4 solution -> all (x,y) points -> keep those with x<m and y<m
-> each gives an edge {x,y} -> should form a 2-regular graph (m edges).
"""
import os, glob, json
from collections import defaultdict, Counter

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def decode_line(line, n):
    line = line.strip()
    if len(line) < 2:
        return None
    body = line[1:]
    if len(body) != 2 * n:
        return None
    pts = []
    per_row = len(body) // n
    for y in range(n):
        for j in range(per_row):
            ch = body[y * per_row + j]
            if ch not in ALPHABET:
                return None
            x = ALPHABET.index(ch)
            pts.append((x, y))
    return pts

def extract_2factor(pts, n):
    """Return (edges, ok) where edges is list of (i,j) with i<=j on vertices 0..m-1."""
    m = n // 2
    fund = [(x, y) for (x, y) in pts if x < m and y < m]
    edges = []
    for (x, y) in fund:
        i, j = (x, y) if x <= y else (y, x)
        edges.append((i, j))
    # verify 2-regular
    deg = Counter()
    for (i, j) in edges:
        deg[i] += 1
        deg[j] += 1
    ok = (len(edges) == m and all(deg[v] == 2 for v in range(m)))
    return edges, ok

def cycle_decomp(edges, m):
    """Return sorted tuple of cycle lengths of the 2-regular graph."""
    adj = defaultdict(set)
    for (i, j) in edges:
        adj[i].add(j)
        adj[j].add(i)
    seen = set()
    cycles = []
    for v in range(m):
        if v in seen:
            continue
        cur = v
        prev = -1
        length = 0
        while cur not in seen:
            seen.add(cur)
            nxt = [w for w in adj[cur] if w != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            length += 1
        if length:
            cycles.append(length)
    return tuple(sorted(cycles))

def main():
    out = []
    w = out.append
    files = sorted(glob.glob(os.path.join(CACHE, 'n*rot4*')))
    w("=" * 78)
    w("C4 2-FACTOR EXTRACTION  (real rot4 solutions from Flammenkamp cache)")
    w("=" * 78)

    # Per-n: store all edge sets (as canonical strings) and structural summaries
    per_n_edges = {}        # n -> list of edge-set strings
    per_n_first = {}        # n -> first edge list (for detailed print)
    per_n_cyc = defaultdict(Counter)  # n -> Counter of cycle-decomp signatures

    for f in files:
        base = os.path.basename(f)
        # parse n from filename n{n}_rot4[.few]
        import re
        mm = re.match(r'n(\d+)_rot4', base)
        if not mm:
            continue
        n = int(mm.group(1))
        m = n // 2
        with open(f) as fh:
            lines = [ln for ln in fh if ln.strip()]
        edgesets = []
        for ln in lines:
            pts = decode_line(ln, n)
            if pts is None:
                continue
            edges, ok = extract_2factor(pts, n)
            if not ok:
                w(f"  [WARN] n={n} decode gave non-2-regular ({len(edges)} edges); skip")
                continue
            sig = tuple(sorted(edges))
            edgesets.append(sig)
        if not edgesets:
            continue
        per_n_edges[n] = edgesets
        per_n_first[n] = edgesets[0]
        for sig in edgesets:
            per_n_cyc[n][cycle_decomp(list(sig), m)] += 1
        w(f"n={n:>2} (m={m:>2}): {len(edgesets):>5} solutions, "
          f"distinct 2-factors={len(set(edgesets))}, "
          f"cycle-decomps={dict(per_n_cyc[n])}")

    # Detailed print of FIRST solution per n (the edge sets)
    w("")
    w("-" * 78)
    w("FIRST SOLUTION 2-FACTOR (edge set as sorted (i,j), i<=j) per n")
    w("-" * 78)
    for n in sorted(per_n_first):
        m = n // 2
        edges = per_n_first[n]
        # pretty: show as adjacency / cycle
        w(f"n={n} (m={m}): {edges}")

    # Save machine-readable
    dump = {n: [list(s) for s in per_n_edges[n]] for n in per_n_edges}
    with open(os.path.join(os.path.dirname(__file__), 'c4_2factors.json'), 'w') as fo:
        json.dump(dump, fo)
    report = '\n'.join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__), 'c4_extract.txt'), 'w') as fo:
        fo.write(report + '\n')

if __name__ == '__main__':
    main()
