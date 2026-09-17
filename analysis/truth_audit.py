"""
AUDIT of truth_probe.py findings -- verify or kill each candidate discovery.

(1) Slope scan with CORRECT normalization: which slopes are genuinely
    absent/rare in real solutions? (Pigeonhole forces 0, inf, +1, -1.)
(2) Triviality check: do RANDOM 2-per-row (NOT necessarily valid) configs
    also satisfy the mod-2 / mod-4 "invariants"? If yes -> trivial.
(3) Recover REAL V(n) completeness: confirm large-n collapse is missing
    symmetry classes, not real disappearance (rot4 witnesses persist).
"""
import os, math, random
from collections import Counter

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

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

def norm(dx,dy):
    if dx==0 and dy==0: return (0,0)
    g=math.gcd(dx,dy)
    dx//=g; dy//=g
    if dx<0 or (dx==0 and dy<0): dx=-dx; dy=-dy
    return (dx,dy)

def slopes_of(pts):
    s=set()
    N=len(pts)
    for i in range(N):
        for j in range(i+1,N):
            s.add(norm(pts[j][0]-pts[i][0], pts[j][1]-pts[i][1]))
    return s

# ---------- (1) corrected slope spectrum ----------
def slope_scan():
    out=[]
    out.append("CORRECTED SLOPE SPECTRUM (normalized keys)")
    targets=[(0,1),(1,0),(1,1),(1,-1),(1,2),(2,1),(1,3),(3,1),(2,3),(3,2),(1,4),(4,1),(1,5),(5,1)]
    for n in [10,14,18]:
        f=os.path.join(CACHE,f"n{n}_iden")
        if not os.path.exists(f): continue
        with open(f) as fh: lines=fh.readlines()
        sample=lines[:300]
        appears=Counter()
        for ln in sample:
            pts=decode(ln,n)
            if not pts: continue
            for s in slopes_of(pts): appears[s]+=1
        absent=[t for t in targets if appears.get(t,0)==0]
        out.append(f"n={n}: absent among {len(sample)} sols (of {len(targets)} targets): "
                   + ", ".join(f"{t[0]}/{t[1]}" for t in absent))
        # show relative frequencies of nontrivial slopes
        freqs=[(t, appears.get(t,0)/len(sample)) for t in targets if t not in [(0,1),(1,0),(1,1),(1,-1)]]
        out.append("   nontrivial slope frequencies: "+
                   ", ".join(f"{t[0]}/{t[1]}:{fr:.2f}" for t,fr in freqs))
    return "\n".join(out)

# ---------- (2) triviality of mod invariants on RANDOM 2-per-row ----------
def random_2perrow(n):
    pts=[]
    for y in range(n):
        cols=random.sample(range(n),2)
        for c in cols: pts.append((c,y))
    return pts

def mod_sig(pts,p):
    return sum((x*x+y*y)%p for x,y in pts)%p

def triviality():
    out=[]
    out.append("")
    out.append("TRIVIALITY CHECK: mod-p invariants on RANDOM 2-per-row configs")
    out.append("(no no-3-in-line constraint)")
    for n in [10,12,16,20]:
        sigs={p:Counter() for p in (2,3,4)}
        for _ in range(500):
            pts=random_2perrow(n)
            for p in (2,3,4):
                sigs[p][mod_sig(pts,p)]+=1
        out.append(f"--- n={n} (500 random 2-per-row) ---")
        for p in (2,3,4):
            top=sigs[p].most_common(2)
            out.append(f"  mod {p}: distribution top={top} "
                       f"(entropy={entropy(sigs[p]):.2f} of {math.log2(p):.2f})")
    return "\n".join(out)

def entropy(c):
    tot=sum(c.values())
    if tot==0: return 0.0
    return -sum((v/tot)*math.log2(v/tot) for v in c.values())

# ---------- (3) real completeness of V(n) ----------
def completeness():
    out=[]
    out.append("")
    out.append("REAL completeness check: rot4 (always computed) gives D(n)=2n witness")
    out.append("even where iden/rot2 classes are missing from cache.")
    import glob
    for n in [34,40,50,54,60,66,70,72]:
        f=os.path.join(CACHE,f"n{n}_rot4")
        fe=os.path.join(CACHE,f"n{n}_rot4.few")
        cnt=0
        for ff in (f,fe):
            if os.path.exists(ff):
                with open(ff) as fh: cnt+=sum(1 for _ in fh)
        out.append(f"  n={n}: rot4-class solutions present = {cnt}  "
                   f"-> D({n})={2*n} WITNESSED" if cnt>0 else f"  n={n}: NONE")
    return "\n".join(out)

def main():
    rep=[slope_scan(), triviality(), completeness()]
    full="\n".join(rep)
    print(full)
    with open(os.path.join(os.path.dirname(__file__),'truth_audit.txt'),'w') as fo:
        fo.write(full)

if __name__=="__main__":
    main()
