"""
FRESH ATTACK on the no-three-in-line problem.
No prior framing (C4 / missing-center / rings / manifold). Pure question:

    Is D(n) = 2n (Guy-Kelly) always achievable, or is there a structural
    reason it must fail for large n?

Four independent probes, all driven by the real solution data (n <= 72):

  PART A  Absolute solution count V(n), its GROWTH, and the DECAY of density
         among all 2-per-row configs.  If V(n) ever drops below 1 -> D(n)<2n
         (disproof).  If V(n) keeps growing -> 2n is robustly achievable.

  PART B  EXPLICIT CONSTRUCTION search: do affine column-permutations
         pi_k(y) = a_k*y + b_k (mod n) ever yield a valid 2n-set for ALL n?
         Finding one family = a constructive proof of the conjecture.

  PART C  SLOPE SPECTRUM: which rational slopes are FORBIDDEN in every
         solution (a hidden invariant that could cap D(n)).

  PART D  MODULAR INVARIANT scan: is any simple mod-p signature constant
         across ALL solutions of a fixed n?  A constant signature that
         becomes unsatisfiable at some n would disprove D(n)=2n.

All outputs written to truth_probe.txt.
"""
import os, math, glob, json
from itertools import combinations
from collections import Counter

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# ---- orbit weight per Flammenkamp symmetry class -------------------------
WEIGHT = {'iden':8, 'rot2':4, 'dia1':4, 'dia2':4, 'ort1':4, 'ort2':4,
          'rot4':2, 'rct4':2, 'full':1}
CLASSES = list(WEIGHT.keys())

def count_file(n, c):
    for ext in ('', '.few'):
        f = os.path.join(CACHE, f"n{n}_{c}{ext}")
        if os.path.exists(f):
            with open(f) as fh:
                return sum(1 for _ in fh)
    return 0

def V_total(n):
    return sum(WEIGHT[c] * count_file(n, c) for c in CLASSES)

# =========================================================================
# PART A  --  count / growth / density decay
# =========================================================================
def part_a():
    out = []
    out.append("="*78)
    out.append("PART A : absolute count V(n), growth, density decay")
    out.append("="*78)
    Ns = list(range(4, 73))
    V = {}
    for n in Ns:
        v = V_total(n)
        if v > 0:
            V[n] = v
    out.append(f"{'n':>3} {'V(n)':>12} {'V(n)/V(n-2)':>10} {'log10 V':>9}  classes_present")
    prev = None
    for n in sorted(V):
        classes = [c for c in CLASSES if count_file(n,c)>0]
        ratio = (f"{V[n]/prev:6.2f}" if prev else "    -  ")
        out.append(f"{n:>3} {V[n]:>12} {ratio:>10} {math.log10(V[n]):9.3f}  {','.join(classes)}")
        prev = V[n]
    # density among all 2-per-row configs T(n) = C(n,2)^n
    out.append("")
    out.append("Density among all 2-per-row placements  R(n)=V(n)/C(n,2)^n :")
    out.append(f"{'n':>3} {'log10 R(n)':>12}   (R = fraction of 2-per-row that are valid)")
    dens = {}
    for n in sorted(V):
        if n < 6: continue
        T = math.comb(n,2) ** n
        r = V[n] / T
        dens[n] = r
        out.append(f"{n:>3} {math.log10(r):12.3f}")
    # linear fit of log R vs n over the reliable small-n window (iden present)
    reliable = [n for n in dens if n <= 20 and count_file(n,'iden')>0]
    if len(reliable) >= 4:
        xs = [float(n) for n in reliable]
        ys = [math.log(dens[n]) for n in reliable]
        m_x = sum(xs)/len(xs); m_y = sum(ys)/len(ys)
        b = sum((x-m_x)*(y-m_y) for x,y in zip(xs,ys)) / sum((x-m_x)**2 for x in xs)
        a = m_y - b*m_x
        out.append("")
        out.append(f"Linear fit  log R(n) ~ {a:.3f} + ({b:.4f})*n   over n in {reliable[0]}..{reliable[-1]}")
        out.append(f"  -> R(n) decays like exp({b:.4f} n)  (~{(math.e**b):.4f}^n)")
        # threshold where V(n) ~ 1 (i.e. R(n)*T(n) ~ 1). Solve V(n)=1 using fit on V itself:
        # log V(n) = log V(n0) + (b_V)*(n-n0);  V=1 -> n* = n0 - log V(n0)/b_V
        # but V is GROWING in this window, so b_V > 0 -> no finite drop in window.
        # Instead estimate drop threshold by fitting log V over the SAME window:
        ysV = [math.log(V[n]) for n in reliable]
        bV = sum((x-m_x)*(y-sum(ysV)/len(ysV)) for x,y in zip(xs,ysV)) / sum((x-m_x)**2 for x in xs)
        aV = sum(ysV)/len(ysV) - bV*m_x
        out.append(f"  log V(n) fit ~ {aV:.2f} + ({bV:.3f})*n  -> V(n) {'GROWING' if bV>0 else 'DECAYING'} in window")
        if bV <= 0:
            nstar = -aV/bV
            out.append(f"  => V(n) drops below 1 near n* ~ {nstar:.1f}  (DISPROVAL CANDIDATE)")
        else:
            out.append(f"  => V(n) still GROWING at n={reliable[-1]}; no drop visible -> D(n)=2n robust so far")
    out.append("")
    return "\n".join(out)

# =========================================================================
# PART B  --  affine construction search
# =========================================================================
def collinear(a,b,c):
    (x1,y1),(x2,y2),(x3,y3)=a,b,c
    return (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1)

def affine_valid(n,a1,b1,a2,b2):
    pts=[]
    for y in range(n):
        c1=(a1*y+b1)%n
        c2=(a2*y+b2)%n
        if c1==c2: return False
        pts.append((c1,y)); pts.append((c2,y))
    # 2n points; check no 3 collinear (O(N^2) direction hash)
    N=len(pts)
    seen=set()
    for i in range(N):
        x1,y1=pts[i]
        for j in range(i+1,N):
            x2,y2=pts[j]
            dx=x2-x1; dy=y2-y1
            g=math.gcd(dx,dy)
            if g!=0: dx//=g; dy//=g
            key=(dx,dy,x1*dy-y1*dx)
            if key in seen: return False
            seen.add(key)
    return True

def part_b():
    out=[]
    out.append("="*78)
    out.append("PART B : affine construction  pi_k(y)=a_k*y+b_k (mod n)")
    out.append("         search for a family valid for ALL n (=> proof of D(n)=2n)")
    out.append("="*78)
    findings={}
    for n in range(3,25):
        hits=[]
        for a1 in range(n):
            if math.gcd(a1,n)!=1: continue
            for a2 in range(n):
                if math.gcd(a2,n)!=1: continue
                if a1==a2: continue
                for b1 in range(n):
                    for b2 in range(n):
                        if affine_valid(n,a1,b1,a2,b2):
                            hits.append((a1,b1,a2,b2))
        findings[n]=hits
        out.append(f"n={n:2d}: {len(hits)} affine valid pairs  e.g. {hits[:3]}")
    # pattern analysis: does a fixed (a1,a2) pair work for many n?
    out.append("")
    out.append("Pairs (a1,a2) that succeed for the MOST consecutive/small n:")
    paircount=Counter()
    for n,hits in findings.items():
        for (a1,b1,a2,b2) in hits:
            paircount[(a1,a2)]+=1
    for (a1,a2),cnt in paircount.most_common(10):
        out.append(f"  (a1,a2)=({a1},{a2}) valid for {cnt} values of n")
    out.append("")
    return "\n".join(out), findings

# =========================================================================
# PART C  --  slope spectrum (forbidden slopes)
# =========================================================================
def decode(line,n):
    line=line.strip()
    if len(line)<2: return None
    body=line[1:]
    if len(body)!=2*n: return None
    per=len(body)//n
    pts=[]
    for y in range(n):
        for j in range(per):
            ch=body[y*per+j]
            if ch not in ALPHABET: return None
            pts.append((ALPHABET.index(ch),y))
    return pts

def gcd_sign(dx,dy):
    if dx==0 and dy==0: return (0,0)
    g=math.gcd(dx,dy)
    if g==0: return (0,0)
    dx//=g; dy//=g
    if dx<0 or (dx==0 and dy<0): dx=-dx; dy=-dy
    return (dx,dy)

def part_c():
    out=[]
    out.append("="*78)
    out.append("PART C : slope spectrum -- slopes that NEVER appear")
    out.append("="*78)
    cand_slopes=[(0,1),(1,0),(1,1),(-1,1),(1,2),(2,1),(1,3),(3,1),(2,3),(3,2),(1,4),(4,1)]
    out.append("Checking candidate slopes (dx,dy): "+", ".join(f"{d[0]}/{d[1]}" for d in cand_slopes))
    for n in [10,12,14,16,18,20]:
        f=os.path.join(CACHE,f"n{n}_iden")
        if not os.path.exists(f): 
            continue
        with open(f) as fh:
            lines=fh.readlines()
        sample=lines[:300]
        appears=Counter()
        for ln in sample:
            pts=decode(ln,n)
            if not pts: continue
            sl=set()
            for i in range(len(pts)):
                for j in range(i+1,len(pts)):
                    s=gcd_sign(pts[j][0]-pts[i][0], pts[j][1]-pts[i][1])
                    if s!=(0,0): sl.add(s)
            for s in sl: appears[s]+=1
        forbidden=[s for s in cand_slopes if appears[s]==0]
        out.append(f"n={n:2d} (sample {len(sample)} iden sols): FORBIDDEN slopes = "
                   + ", ".join(f"{d[0]}/{d[1]}" for d in forbidden) + "  (appears count>0 for others)")
    out.append("")
    return "\n".join(out)

# =========================================================================
# PART D  --  modular invariant scan
# =========================================================================
def part_d():
    out=[]
    out.append("="*78)
    out.append("PART D : modular invariant scan across ALL solutions of fixed n")
    out.append("="*78)
    for n in [10,12,14,16,18,20]:
        f=os.path.join(CACHE,f"n{n}_iden")
        if not os.path.exists(f): continue
        with open(f) as fh:
            lines=fh.readlines()
        sample=lines[:400]
        sigs={p:Counter() for p in (2,3,4)}
        for ln in sample:
            pts=decode(ln,n)
            if not pts: continue
            for p in (2,3,4):
                s=sum((x*x+y*y)%p for x,y in pts)
                sigs[p][s%p]+=1
        out.append(f"--- n={n} (sample {len(sample)}) ---")
        for p in (2,3,4):
            total=sum(sigs[p].values())
            top=sigs[p].most_common(3)
            # variance / entropy: is the signature concentrated (invariant-like)?
            ent=-sum((c/total)*math.log2(c/total) for c in sigs[p].values())
            maxfrac=max(sigs[p].values())/total
            out.append(f"  mod {p}: entropy={ent:.2f} bits (max={math.log2(p):.2f}), "
                       f"top signature share={maxfrac:.2f}, top={top}")
        out.append("  (entropy near log2(p) => signature VARIES => NOT invariant; "
                   "share near 1.0 => nearly CONSTANT => candidate invariant)")
    out.append("")
    return "\n".join(out)

def main():
    rep=[]
    rep.append(part_a()); 
    btxt, _ = part_b(); rep.append(btxt)
    rep.append(part_c())
    rep.append(part_d())
    full="\n".join(rep)
    print(full)
    with open(os.path.join(os.path.dirname(__file__),'truth_probe.txt'),'w') as fo:
        fo.write(full)

if __name__=="__main__":
    main()
