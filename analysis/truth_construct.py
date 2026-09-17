"""
Final fresh construction attempt: POWER / QUADRATIC column permutations.
For prime n=p, the map y -> y^d (mod p) is a permutation iff gcd(d,p-1)=1
(these are the "power permutations" / Costas-like over F_p).
Test pairs of such maps (and quadratic a*y^2+b*y+c) as the two columns
of a 2n-set. If a pair works for ALL primes up to some bound, that is a
CONSTRUCTIVE PROOF of D(p)=2p for infinitely many p.

Also test the single-curve cap y->y^2 (should be valid alone: parabola
has no 3 collinear over F_p -> a cap of size p), confirming the method.
"""
import math
from itertools import combinations

def collinear(a,b,c):
    (x1,y1),(x2,y2),(x3,y3)=a,b,c
    return (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1)

def valid(n, cols1, cols2):
    # cols1[y], cols2[y] are the two column indices for row y
    pts=[]
    for y in range(n):
        c1,c2=cols1[y],cols2[y]
        if c1==c2: return False
        pts.append((c1,y)); pts.append((c2,y))
    N=len(pts)
    seen=set()
    for i in range(N):
        x1,y1=pts[i]
        for j in range(i+1,N):
            x2,y2=pts[j]
            dx=x2-x1; dy=y2-y1
            g=math.gcd(dx,dy)
            if g!=0: dx//=g; dy//=g
            if dx<0 or (dx==0 and dy<0): dx=-dx; dy=-dy
            key=(dx,dy,x1*dy-y1*dx)
            if key in seen: return False
            seen.add(key)
    return True

def power_cols(n,d):
    return [pow(y,d,n) if y!=0 else 0 for y in range(n)]

def quad_cols(n,a,b,c):
    return [ (a*y*y+b*y+c)%n for y in range(n) ]

def units(p):
    return [d for d in range(1,p) if math.gcd(d,p-1)==1]

def main():
    out=[]
    out.append("="*78)
    out.append("POWER / QUADRATIC construction search (prime n)")
    out.append("="*78)
    # single curve y->y^2 should be a cap (valid alone, 1 point per row)
    out.append("\n[1] Single-curve cap test: cols=y^2 mod p  (expect VALID, size p)")
    for p in [5,7,11,13,17,19,23,29,31]:
        cols=[ (y*y)%p for y in range(p) ]
        ok=valid(p, cols, [ (y*y)%p for y in range(p) ])
        # valid() demands 2 distinct cols/row, so test the cap differently:
        # a single parabola as a p-point set (one point per row) has no 3 collinear?
        pts=[(cols[y],y) for y in range(p)]
        cap_ok = not any(collinear(pts[i],pts[j],pts[k])
                          for i in range(p) for j in range(i+1,p) for k in range(j+1,p))
        out.append(f"  p={p}: parabola-cap valid alone? {cap_ok}")
    # two power permutations
    out.append("\n[2] Two power permutations cols=(y^d1, y^d2) mod p")
    hits_by_p={}
    for p in [5,7,11,13,17,19,23,29,31]:
        U=units(p)
        hits=[]
        for d1 in U:
            c1=power_cols(p,d1)
            for d2 in U:
                if d1==d2: continue
                c2=power_cols(p,d2)
                if valid(p,c1,c2):
                    hits.append((d1,d2))
        hits_by_p[p]=hits
        out.append(f"  p={p}: {len(hits)} valid power pairs  e.g. {hits[:4]}")
    # any pair (d1,d2) working for MANY primes?
    paircount={}
    for p,h in hits_by_p.items():
        for d1,d2 in h:
            paircount[(d1,d2)]+=1
    out.append("\n  Power pairs valid for the most primes:")
    for (d1,d2),c in sorted(paircount.items(), key=lambda kv:-kv[1])[:8]:
        out.append(f"    (d1,d2)=({d1},{d2}): valid for {c} primes")
    # quadratic pairs (a,b,c) for small p
    out.append("\n[3] Quadratic columns (a*y^2+b*y+c) mod p, pairs, p<=13")
    for p in [5,7,11,13]:
        hits=[]
        for a in range(p):
            for b in range(p):
                for c in range(p):
                    c1=quad_cols(p,a,b,c)
                    if len(set(c1))<p: continue  # must be permutation
                    for a2 in range(p):
                        for b2 in range(p):
                            for c2 in range(p):
                                if a==a2 and b==b2 and c==c2: continue
                                c2_=quad_cols(p,a2,b2,c2)
                                if len(set(c2_))<p: continue
                                if valid(p,c1,c2_):
                                    hits.append(((a,b,c),(a2,b2,c2)))
                                    break
                            if hits and hits[-1][0]==(a,b,c): break
                        if hits and hits[-1][0]==(a,b,c): break
                    if len(hits)>20: break
        out.append(f"  p={p}: found {len(hits)} valid quadratic pairs (capped)  e.g. {hits[:3]}")
    out.append("")
    full="\n".join(out)
    print(full)
    with open("truth_construct.txt","w") as fo: fo.write(full)

if __name__=="__main__":
    main()
