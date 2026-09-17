"""
swarm_D5_axis2.py -- D5 direction (final probe).

Theorem D5-B (row/col exact-2 is AUTOMATIC for any 2-factor):
  For a rot4 config from a 2-factor on {0..m-1}, every board row and every board
  column contains EXACTLY 2 lifts.  Proof: row r (0<=r<=m-1) gets lifts only from
  cells with x=r or y=r (since the other two row-indices n-1-r would exceed m-1);
  count = X_r + Y_r = 2 by the 2-factor.  Row r>=m mirrors to label 73-r.  Hence
  horizontal/vertical (X) is FREE -- no 3-in-a-row possible for ANY 2-factor.

So the only real (X) work is on slope +1 / -1 (diag/antidiag) lines and all other
slopes.  We:
 (1) verify D5-B on random 2-factors + known solutions (max row/col occ == 2 always);
 (2) quick local search to MINIMIZE max anti-diagonal/diagonal occupancy at m=36 vs
     m=37, to detect any m=37-specific obstruction signal in the non-automatic part.
"""
import os, sys, json, math, random
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E

def max_occ(lifts, m, kind):
    n=2*m
    if kind=='row':
        c=[0]*n
        for (x,y) in lifts: c[y]+=1
        return max(c)
    if kind=='col':
        c=[0]*n
        for (x,y) in lifts: c[x]+=1
        return max(c)
    if kind=='anti':
        c=[0]*(2*n-1)
        for (x,y) in lifts: c[x+y]+=1
        return max(c)
    if kind=='diag':
        # diagonal index x-y ranges -(n-1)..(n-1)
        c=defaultdict(int)
        for (x,y) in lifts: c[x-y]+=1
        return max(c.values())

def sols():
    s={}
    sd=os.path.join(HERE,'results','solutions')
    for fn in sorted(os.listdir(sd)):
        if fn.startswith('m') and fn.endswith('.json'):
            d=json.load(open(os.path.join(sd,fn)))
            s[d['m']]=d['cells']
    return s

def local_minimize_diag(m, iters=4000, seed=1):
    """Random 2-factor; local moves (flip+two-switch) to minimize max(anti,diag) occ."""
    rng=random.Random(seed)
    edges=E.generate_2factor(m,rng)
    cells=E.orient(edges,rng)
    board=E.Board(m); board.build(edges,cells)
    best=max(max_occ(board.lifts,m,'anti'), max_occ(board.lifts,m,'diag'))
    for _ in range(iters):
        if rng.random()<0.5:
            e=rng.randrange(m)
            if board.edges[e][0]!=board.edges[e][1]:
                board.flip_orientation(e)
        else:
            e1=rng.randrange(m); e2=rng.randrange(m)
            if e1!=e2:
                d,undo=board.two_switch(e1,e2)
                if undo is None:
                    continue
        cur=max(max_occ(board.lifts,m,'anti'), max_occ(board.lifts,m,'diag'))
        if cur<best:
            best=cur
        elif rng.random()<0.1:
            # occasionally revert to keep exploring (cheap: rebuild from best not tracked, just accept)
            pass
    return best

def main():
    print("=== Theorem D5-B: row/col exact-2 automatic for ANY 2-factor ===")
    rng=random.Random(99)
    worst_row=0; worst_col=0
    for _ in range(500):
        m=37
        edges=E.generate_2factor(m,rng)
        if edges is None: continue
        cells=E.orient(edges,rng)
        board=E.Board(m); board.build(edges,cells)
        worst_row=max(worst_row, max_occ(board.lifts,m,'row'))
        worst_col=max(worst_col, max_occ(board.lifts,m,'col'))
    print(f"  over 500 random m=37 2-factors: max row occ={worst_row}, max col occ={worst_col} (both should be 2)")

    # known solutions also have exact 2 by D5-B (sanity)
    ss=sols()
    bad=[]
    for m in ss:
        cells=ss[m]
        n=2*m
        L=[]
        for (x,y) in cells: L.extend(E.c4(x,y,r,n) for r in range(4))
        if max_occ(L,m,'row')!=2 or max_occ(L,m,'col')!=2:
            bad.append(m)
    print(f"  known solutions with row/col occ != 2: {bad} (should be empty)")

    print("\n=== Non-automatic part: min achievable max(anti,diag) occupancy ===")
    print("    (valid solution needs this <= 2; if stuck >2 for m=37 but reaches 2 for m=36 -> obstruction signal)")
    for m in [10, 20, 30, 36, 37]:
        best=min(local_minimize_diag(m, iters=3000, seed=s) for s in range(3))
        print(f"    m={m:2d}: min max(anti,diag) occ over 3 runs = {best}  (need <=2 for (X))")

    print("\n=== Re-classify 72-config defects (clean) ===")
    d=json.load(open(os.path.join(HERE,'results','solver_theory_m37_long.json')))
    L=d['lifts']; m=37
    print(f"    row max={max_occ(L,m,'row')} col max={max_occ(L,m,'col')} "
          f"anti max={max_occ(L,m,'anti')} diag max={max_occ(L,m,'diag')}")
    print("    -> rows/cols exact-2 (automatic); residual bad triples live on")
    print("       anti-diagonal / diagonal / other slopes (the genuine hard part).")

if __name__=='__main__':
    main()
