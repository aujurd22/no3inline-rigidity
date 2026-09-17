"""
check_seed_board_dependence.py
Verify the board-size dependence claim:
  - the m=36 seed cells, lifted on N=72, should be (X)-free (valid m=36 rot4 NTIL)
  - the SAME cells, lifted on N=74, have ~164 (X)-violations (surgery breaks)
This confirms naive coordinate-reuse surgery is obstructed by C4-lift N-dependence.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rot4_loader import decode_line

HERE = os.path.dirname(os.path.abspath(__file__))
m_old = 36

with open(os.path.join(HERE, "flammenkamp_cache", "n72_rot4.few")) as f:
    first = f.readline().strip()
pts72 = decode_line(first, 72)
seed = sorted([(x, y) for (x, y) in pts72 if x < m_old and y < m_old])
print(f"[seed] {len(seed)} cells")

def c4(p, r, N):
    x, y = p
    for _ in range(r % 4):
        x, y = (N - 1 - y), x
    return (x, y)

def lift(cells, N):
    out = []
    for (x, y) in cells:
        for r in range(4):
            out.append(c4((x, y), r, N))
    return out

def n_collinear(pts):
    n = len(pts)
    bad = 0
    for i in range(n):
        for j in range(i+1, n):
            for k in range(j+1, n):
                if (pts[j][0]-pts[i][0])*(pts[k][1]-pts[i][1]) == \
                   (pts[k][0]-pts[i][0])*(pts[j][1]-pts[i][1]):
                    bad += 1
    return bad

for N in (72, 74):
    pts = lift(seed, N)
    print(f"  N={N}: lifted {len(pts)} pts, collinear triples = {n_collinear(pts)}")
