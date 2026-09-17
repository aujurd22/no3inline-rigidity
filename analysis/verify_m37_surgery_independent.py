"""
verify_m37_surgery_independent.py
INDEPENDENT verification of the claimed m=37 rot4 NTIL in
results/m37_surgery_result.json.  No reuse of surgery code / seed loader.
Checks from scratch:
  (1) 2-factor: for each i in 0..36, rowSum[i]+colSum[i] == 2
  (2) lift 37 cells via C4 on N=74 -> 148 points
  (3) brute-force NO 3 collinear among all C(148,3) triples (the (X) / rot4 condition)
  (4) (S): all 148 lifted points distinct
If all pass -> m=37 IS SOLVED (and the "OPEN" premise is wrong).
"""
import json, math

HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
SRC = f"{HERE}/results/m37_surgery_result.json"

with open(SRC) as f:
    data = json.load(f)
cells = [tuple(c) for c in data["cells"]]
m = data["m"]
assert m == 37, m
N = 2 * m
print(f"[load] m={m} N={N}  n_cells claimed={data.get('n_cells')}  "
      f"n_points claimed={data.get('n_points')}  verify field={data.get('verify_no_collinear')}")

# ---- (1) 2-factor ----
print("\n[1] 2-factor check (rowSum[i]+colSum[i]==2 for i in 0..m-1)")
sel = [[0] * m for _ in range(m)]
for (x, y) in cells:
    assert 0 <= x < m and 0 <= y < m, (x, y)
    sel[x][y] = 1
ok2f = True
for i in range(m):
    if sum(sel[i]) + sum(sel[r][i] for r in range(m)) != 2:
        ok2f = False
        print(f"  FAIL at vertex {i}: row+col sum = "
              f"{sum(sel[i]) + sum(sel[r][i] for r in range(m))}")
print(f"  2-factor valid: {ok2f}   (cells={len(cells)}, expected {m})")
if len(cells) != m:
    print(f"  >>> CELL COUNT MISMATCH: {len(cells)} != {m}")

# ---- lift via C4 ----
def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    return (y, N - 1 - x)

pts = []
for (x, y) in cells:
    for r in range(4):
        pts.append(c4((x, y), r, N))
print(f"\n[2] lifted {len(pts)} points (expected {4*m}={4*m})")

# ---- (4) distinctness ----
print("[3] distinctness of lifted points")
print(f"  distinct = {len(set(pts))} / {len(pts)}")

# ---- (3) brute-force no 3 collinear ----
print("[4] brute-force no-3-collinear over all C(%d,3) triples..." % len(pts))
def cross(o, a, b):
    # signed area *2 ; collinear iff 0
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])

bad = []
n = len(pts)
for i in range(n):
    xi, yi = pts[i]
    for j in range(i+1, n):
        xj, yj = pts[j]
        for k in range(j+1, n):
            if cross(pts[i], pts[j], pts[k]) == 0:
                bad.append((i, j, k))
print(f"  collinear triples found: {len(bad)}")
if bad:
    print("  examples:", bad[:5])

print("\n==== FINAL VERDICT ====")
if ok2f and len(cells) == m and len(set(pts)) == len(pts) and not bad:
    print("  *** m=37 rot4 NTIL VERIFIED INDEPENDENTLY -> SOLVED ***")
else:
    print("  NOT a valid solution. Reasons:")
    print(f"    2-factor ok={ok2f}  cellcount ok={len(cells)==m}  "
          f"distinct={len(set(pts))==len(pts)}  no_collinear={not bad}")
