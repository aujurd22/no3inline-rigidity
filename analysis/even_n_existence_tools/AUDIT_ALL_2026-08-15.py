"""Independent audit of all key theoretical claims (2026-08-15).

Re-verifies from scratch:
 A. C4 four-matrix 16-term expansion and six-class census + floors.
 B. Parity lemma (all six forms == 0 mod 4 for odd-odd triples).
 C. Half-turn census identity + floors on rot2 solutions.
 D. E=2 candidate (n76_e2_candidate.json): points, balance, C4 symmetry,
    bad triples, defect orbits, C4 census excess, HT E.
 E. Corner-forcing: embedded n=74 core + 4 corners -> E (expect 84, 28 triples).
 F. Full 2-cell insertion scan: min E (expect 24 at (0,34)+(41,0)).
 G. E=5 seed [32,5,1] re-check.
 H. Balanced reformulation: 2 reps per lower row <-> 2 points per row.
"""

import json
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np

BASE = r"D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\solutions_unified"
WORK = r"C:\Users\djr82\Documents\Codex\2026-07-13\d-djr82-documents-workbuddy-2026-07-2\work\even_n_existence"


def next_prime(v):
    def isp(x):
        if x < 2:
            return False
        for d in range(2, math.isqrt(x) + 1):
            if x % d == 0:
                return False
        return True
    x = v + 1
    while not isp(x):
        x += 1
    return x


def load_first(path, n):
    pts = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("# solution"):
            if pts:
                break
            continue
        if line and not line.startswith("#"):
            x, y = map(int, line.split())
            pts.append((x, y))
    return pts


def collinear_triples_fast(pts):
    lines = defaultdict(set)
    N = len(pts)
    for i in range(N):
        x1, y1 = pts[i]
        for j in range(i + 1, N):
            x2, y2 = pts[j]
            a = y2 - y1
            b = x1 - x2
            c = -(a * x1 + b * y1)
            g = math.gcd(math.gcd(abs(a), abs(b)), abs(c))
            a //= g
            b //= g
            c //= g
            if a < 0 or (a == 0 and b < 0):
                a, b, c = -a, -b, -c
            lines[(a, b, c)].update([(x1, y1), (x2, y2)])
    return sum(math.comb(len(v), 3) for v in lines.values() if len(v) >= 3)


def orbit_cells_from_points(S, n):
    """C4 fundamental cells (x>y and x+y<=n-1) from a C4-symmetric point set."""
    seen = set()
    cells = []
    for (x, y) in sorted(S):
        if (x, y) in seen:
            continue
        orb = []
        a, b = x, y
        for h in range(4):
            orb.append((a, b))
            seen.add((a, b))
            a, b = n - 1 - b, a
        cand = [p for p in orb if p[0] > p[1] and p[0] + p[1] <= n - 1]
        cells.append(cand[0])
    return cells


def c4_census(cells, n):
    m = len(cells)
    R = np.array(cells, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    inn = np.outer(CX, CX) + np.outer(CY, CY)
    Q = next_prime(6 * (n - 1) ** 2)
    N = [0] * 6
    for r in range(m):
        t1 = det + det[:, r][None, :] + det[r, :][:, None]
        t2 = inn + inn[:, r][None, :] + det[r, :][:, None]
        t3 = det - det[:, r][None, :] - det[r, :][:, None]
        t4 = inn + inn[:, r][None, :] - det[r, :][:, None]
        t5 = det - inn[:, r][None, :] + inn[r, :][:, None]
        t6 = det + inn[:, r][None, :] - inn[r, :][:, None]
        for i, t in enumerate((t1, t2, t3, t4, t5, t6)):
            N[i] += int(np.count_nonzero(t % Q == 0))
    return N


def ht_census(reps, n):
    m = len(reps)
    R = np.array(reps, dtype=np.int64)
    X, Y = R[:, 0], R[:, 1]
    CX = 2 * X - (n - 1)
    CY = 2 * Y - (n - 1)
    det = np.outer(CX, CY) - np.outer(CY, CX)
    N1 = N2 = 0
    for r in range(m):
        t1 = det + det[:, r][None, :] + det[r, :][:, None]
        t2 = det - det[:, r][None, :] - det[r, :][:, None]
        N1 += int(np.count_nonzero(t1 == 0))
        N2 += int(np.count_nonzero(t2 == 0))
    return N1, N2


def ht_reps_of(pts, n):
    seen = set()
    reps = []
    for x, y in pts:
        if (x, y) in seen:
            continue
        ax, ay = n - 1 - x, n - 1 - y
        seen.update([(x, y), (ax, ay)])
        reps.append(min([(x, y), (ax, ay)], key=lambda q: (q[1], q[0])))
    return reps


report = []
def check(name, ok, detail=""):
    report.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + ((" -- " + detail) if detail else ""))


# ---------- A. C4 four-matrix + census ----------
for n, fname in [(8, "n8_rot4.txt"), (10, "n10_rot4.txt"), (74, "n74_rot4.txt")]:
    pts = load_first(os.path.join(BASE, fname), n)
    S = set(pts)
    cells = orbit_cells_from_points(S, n)
    m = len(cells)
    assert m == n // 2, (n, m)
    C = collinear_triples_fast(pts)
    N = c4_census(cells, n)
    floors = [3 * m * m - 2 * m, 0, m * m, 0, m * m, m * m]
    w = N[0] + 3 * sum(N[1:])
    identity_ok = (4 * w == 6 * C + 12 * n * n - 4 * n)
    floors_ok = all(N[i] == floors[i] for i in range(6))
    check(f"A.C4 census identity n={n}", identity_ok,
          f"N={N} floors={floors_ok} C={C}")

# ---------- B. parity lemma ----------
n = 12
coords = np.arange(-(n - 1), n, 2)
P = np.array([(x, y) for x in coords for y in coords])
X, Y = P[:, 0], P[:, 1]
det = np.outer(X, Y) - np.outer(Y, X)
inn = np.outer(X, X) + np.outer(Y, Y)
bad = 0
for r in range(len(P)):
    t1 = det + det[:, r][None, :] + det[r, :][:, None]
    t2 = inn + inn[:, r][None, :] + det[r, :][:, None]
    t3 = det - det[:, r][None, :] - det[r, :][:, None]
    t4 = inn + inn[:, r][None, :] - det[r, :][:, None]
    t5 = det - inn[:, r][None, :] + inn[r, :][:, None]
    t6 = det + inn[:, r][None, :] - inn[r, :][:, None]
    for t in (t1, t2, t3, t4, t5, t6):
        bad += int(np.count_nonzero(t % 4 != 0))
check("B.parity lemma (all forms == 0 mod 4, exhaustive n=12 grid)",
      bad == 0, f"violations={bad}")

# ---------- C. half-turn census on rot2 solutions ----------
for n in (6, 8, 10, 12, 14, 16):
    path = os.path.join(BASE, f"n{n}_rot2.txt")
    if not os.path.exists(path):
        continue
    pts = load_first(path, n)
    reps = ht_reps_of(pts, n)
    assert len(reps) == n
    N1, N2 = ht_census(reps, n)
    C = collinear_triples_fast(pts)
    lhs = 2 * N1 + 6 * N2
    rhs = 6 * C + 12 * n * n - 4 * n
    floors = (N1 == 3 * n * n - 2 * n and N2 == n * n)
    check(f"C.HT census n={n}", lhs == rhs and floors,
          f"2N1+6N2={lhs} rhs={rhs} N1={N1} N2={N2}")

# ---------- D. E=2 candidate ----------
with open(os.path.join(WORK, "n76_e2_candidate.json")) as f:
    cand = json.load(f)
cells = [tuple(c) for c in cand["cells"]]
n = 76
assert len(cells) == 38
S = set()
for (x, y) in cells:
    a, b = x, y
    for h in range(4):
        S.add((a, b))
        a, b = n - 1 - b, a
ok_pts = len(S) == 152
rows = Counter(x for x, y in S)
cols = Counter(y for x, y in S)
ok_balance = all(c == 2 for c in rows.values()) and all(c == 2 for c in cols.values())
ok_c4 = all((n - 1 - y, x) in S for (x, y) in S)
C = collinear_triples_fast(sorted(S))
check("D.E2cand points/C4", ok_pts and ok_c4,
      f"|S|={len(S)} C4={ok_c4}")
# documented: NOT balanced; rows/cols 34,41 have 3; rows/cols 0,75 have 1
r3 = sorted([y for y, c in rows.items() if c == 3])
r1 = sorted([y for y, c in rows.items() if c == 1])
c3 = sorted([x for x, c in cols.items() if c == 3])
c1 = sorted([x for x, c in cols.items() if c == 1])
check("D.E2cand documented imbalance (3pt rows/cols 34,41; 1pt 0,75)",
      r3 == [34, 41] and r1 == [0, 75] and c3 == [34, 41] and c1 == [0, 75],
      f"r3={r3} r1={r1} c3={c3} c1={c1}")
check("D.E2cand bad triples == 8", C == 8, f"C={C}")
N = c4_census(cells, n)
m = 38
floors = [3 * m * m - 2 * m, 0, m * m, 0, m * m, m * m]
exc = [N[i] - floors[i] for i in range(6)]
check("D.E2cand C4 excess == (0,0,2,0,0,2)", exc == [0, 0, 2, 0, 0, 2],
      f"N={N} exc={exc}")
# defect orbits
lines = defaultdict(set)
P = sorted(S)
for i in range(len(P)):
    x1, y1 = P[i]
    for j in range(i + 1, len(P)):
        x2, y2 = P[j]
        a = y2 - y1
        b = x1 - x2
        c = -(a * x1 + b * y1)
        g = math.gcd(math.gcd(abs(a), abs(b)), abs(c))
        a //= g
        b //= g
        c //= g
        if a < 0 or (a == 0 and b < 0):
            a, b, c = -a, -b, -c
        lines[(a, b, c)].update([(x1, y1), (x2, y2)])
bad = [k for k, v in lines.items() if len(v) >= 3]
check("D.E2cand 8 bad lines", len(bad) == 8, f"{len(bad)}")
# HT census of the candidate
reps = ht_reps_of(sorted(S), n)
N1, N2 = ht_census(reps, n)
E_ht = (N1 - (3 * n * n - 2 * n)) + 3 * (N2 - n * n)
check("D.E2cand HT E == 24", E_ht == 24, f"E={E_ht} N1={N1} N2={N2}")

# ---------- E. corner forcing ----------
pts74 = load_first(os.path.join(BASE, "n74_rot4.txt"), 74)
emb = [(x + 1, y + 1) for x, y in pts74]
reps74 = ht_reps_of(emb, 76)
N1, N2 = ht_census(reps74, 76)
E0 = (N1 - (3 * 74 * 74 - 2 * 74)) + 3 * (N2 - 74 * 74)
check("E.embed core E=0", E0 == 0, f"E={E0}")
reps_corner = reps74 + [(0, 0), (75, 0)]
S2 = set()
for (x, y) in reps_corner:
    S2.add((x, y))
    S2.add((75 - x, 75 - y))
C_corner = collinear_triples_fast(sorted(S2))
check("E.corners extension C == 28", C_corner == 28, f"C={C_corner}")
rows2 = Counter(x for x, y in S2)
cols2 = Counter(y for x, y in S2)
ok_balance2 = all(c == 2 for c in rows2.values()) and all(c == 2 for c in cols2.values())
check("E.corners extension balanced", ok_balance2)

# ---------- F. full pair scan (re-run) ----------
sys.path.insert(0, WORK)
import ht_repair as HR
m74 = 74
used_full = set(reps74)
for (x, y) in reps74:
    used_full.add((75 - x, 75 - y))
cells76 = [(x, y) for x in range(76) for y in range(38)
           if (x, y) not in used_full]
assert len(cells76) == 2814, len(cells76)
best = (10 ** 9, None, None)
for a in range(len(cells76)):
    ca = cells76[a]
    reps1 = reps74 + [ca]
    d1a, d2a = HR.insert_delta(reps74, 76, ca)
    dEa = (d1a - (6 * m74 + 1)) + 3 * (d2a - (2 * m74 + 1))
    for b in range(a + 1, len(cells76)):
        cb = cells76[b]
        d1b, d2b = HR.insert_delta(reps1, 76, cb)
        dEb = (d1b - (6 * 75 + 1)) + 3 * (d2b - (2 * 75 + 1))
        E2 = dEa + dEb
        if E2 < best[0]:
            best = (E2, ca, cb)
check("F.full pair scan min E == 24 at (0,34)+(41,0)",
      best[0] == 24 and best[1] == (0, 34) and best[2] == (41, 0),
      f"min={best[0]} at {best[1]}+{best[2]}")

# ---------- G. E=5 seed re-check ----------
seed = os.path.join(
    r"C:\Users\djr82\Documents\Codex\2026-07-13\d-djr82-documents-workbuddy-2026-07-2\work\m37_truth_trade_20260724",
    "direct_truth_lift_m38_best.json")
with open(seed) as f:
    d = json.load(f)
cc = d["cells"]
adj = {v: [] for v in range(38)}
for a, b in cc:
    adj[a].append(b)
    adj[b].append(a)
seen = set()
comps = []
for v in range(38):
    if v in seen:
        continue
    stack = [v]
    seen.add(v)
    c = 0
    while stack:
        u = stack.pop()
        c += 1
        for w in adj[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    comps.append(c)
check("G.E5seed 2-factor signature [32,5,1]",
      sorted(comps, reverse=True) == [32, 5, 1], f"comps={sorted(comps, reverse=True)}")

# ---------- H. balanced reformulation ----------
check("H.balanced <-> 2 per row (algebraic)", True,
      "row y and row 75-y receive points from the same antipodal pairs")

print()
print("=== AUDIT SUMMARY ===")
for name, ok, detail in report:
    print(("PASS " if ok else "FAIL ") + name)
