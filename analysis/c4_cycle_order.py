#!/usr/bin/env python3
"""For each even n with rot4 solutions, find a single-m-cycle solution and print
its vertex ordering (the cycle as a sequence of vertices 0..m-1).
Goal: discover an explicit, fast (O(m)) construction rule for the cycle order."""
import os, glob, re, json
from collections import defaultdict

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')

def decode_line(line, n):
    line = line.strip()
    if len(line) < 2: return None
    body = line[1:]
    if len(body) != 2 * n: return None
    pts = []
    per_row = len(body) // n
    for y in range(n):
        for j in range(per_row):
            ch = body[y * per_row + j]
            if ch not in ALPHABET: return None
            pts.append((ALPHABET.index(ch), y))
    return pts

def extract_edges(pts, n):
    m = n // 2
    edges = []
    for (x, y) in pts:
        if x < m and y < m:
            edges.append((x, y) if x <= y else (y, x))
    return edges

def cycle_orders(edges, m):
    adj = defaultdict(list)
    for (i, j) in edges:
        adj[i].append(j); adj[j].append(i)
    # find all cycles
    seen = set(); orders = []
    for s in range(m):
        if s in seen: continue
        # walk: pick arbitrary neighbor, avoid return
        order = [s]; prev = -1; cur = s
        while True:
            nxts = [w for w in adj[cur] if w != prev]
            if not nxts: break
            nxt = nxts[0]
            if nxt == s: break
            order.append(nxt); prev, cur = cur, nxt
            if cur in seen: break
        for v in order: seen.add(v)
        if len(order) >= 2: orders.append(tuple(order))
    return orders

def main():
    out = []
    files = sorted(glob.glob(os.path.join(CACHE, 'n*rot4*')))
    for f in files:
        base = os.path.basename(f)
        mm = re.match(r'n(\d+)_rot4', base)
        if not mm: continue
        n = int(mm.group(1)); m = n // 2
        with open(f) as fh:
            lines = [ln for ln in fh if ln.strip()]
        for ln in lines:
            pts = decode_line(ln, n)
            if pts is None: continue
            edges = extract_edges(pts, n)
            if len(edges) != m: continue
            orders = cycle_orders(edges, m)
            if len(orders) == 1 and len(orders[0]) == m:
                # single m-cycle found
                seq = orders[0]
                # rotate so it starts at 0, and choose orientation with smaller 2nd
                idx = seq.index(0)
                seq = seq[idx:] + seq[:idx]
                if seq[1] > seq[-1]:
                    seq = seq[0:1] + seq[1:][::-1]
                out.append((m, seq))
                break  # one example per n
    # print
    print("m : cycle vertex order (single m-cycle C4 solution)")
    print("-" * 70)
    for m, seq in out:
        print(f"m={m:>2} : {list(seq)}")
    # save
    with open(os.path.join(os.path.dirname(__file__), 'c4_cycle_orders.txt'), 'w') as fo:
        for m, seq in out:
            fo.write(f"m={m}: {list(seq)}\n")

if __name__ == '__main__':
    main()
