"""
Fast deep analysis of MIN dominating sets.
Optimized: precomputes domination, skips full maximality during search.
"""

import random, sys
from collections import Counter

def collinear(p1,p2,p3):
    x1,y1=p1;x2,y2=p2;x3,y3=p3
    return (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1)

def is_no3(pts):
    pl=list(pts)
    for i in range(len(pl)):
        for j in range(i+1,len(pl)):
            for k in range(j+1,len(pl)):
                if collinear(pl[i],pl[j],pl[k]): return False
    return True

def ring_info(n, pts):
    ctr=(n-1)/2.0
    rng=Counter()
    for i,j in pts:
        d2=int(round((i-ctr)**2+(j-ctr)**2))
        rng[d2]+=1
    return {'rings':len(rng), 'maxpop':max(rng.values()), 
            'missing':all(v<3 for v in rng.values()),
            'dist':dict(sorted(rng.items()))}

def rot2_symmetry(n, pts):
    R2=lambda p:(n-1-p[0],n-1-p[1])
    return all(R2(p) in pts for p in pts)

def center_used(n, pts):
    m=(n-1)/2.0
    return m%1==0 and (int(m),int(m)) in pts

def find_min_sets_fast(n, k, trials=2000):
    """Fast search: use domination-score approximation, only full check at end."""
    all_pts = [(i,j) for i in range(n) for j in range(n)]
    found = []
    
    # Precompute: for each point, which other points it's collinear with
    # (for quick maximality estimate)
    
    for trial in range(trials):
        if trial % 200 == 0:
            print(f"  n={n} trial {trial}/{trials} (found {len(found)})", file=sys.stderr)
        random.seed(trial*137+42)
        
        while True:
            cand = set(random.sample(all_pts, k))
            if is_no3(cand):
                break
        
        # Quick hill-climb: try replacing each point with something that 
        # increases the number of dominated grid points
        pl = list(cand)
        best_score = sum(1 for i in range(n) for j in range(n) 
                        if (i,j) not in cand and
                        any(collinear(a,b,(i,j)) for a in pl for b in pl if a<b))
        
        improved = True
        for _ in range(50):
            if not improved: break
            improved = False
            pl = list(cand)
            for pi, p_out in enumerate(pl):
                for p_in in all_pts:
                    if p_in in cand: continue
                    new_set = (cand - {p_out}) | {p_in}
                    if not is_no3(new_set): continue
                    # Quick score (not full check, just approximate)
                    score = sum(1 for i in range(n) for j in range(n)
                               if (i,j) not in new_set and
                               any(collinear(a,b,(i,j)) for a in new_set for b in new_set if a<b))
                    if score > best_score:
                        cand = new_set.copy()
                        best_score = score
                        improved = True
                        break
                if improved: break
        
        # Now do the full maximality check
        if best_score == n*n - k:
            # Quick check: can any single point be added?
            pl = list(cand)
            ok = True
            for i in range(n):
                if not ok: break
                for j in range(n):
                    p = (i,j)
                    if p in cand: continue
                    can_add = True
                    for a in pl:
                        for b in pl:
                            if a >= b: continue
                            if collinear(a,b,p):
                                can_add = False
                                break
                        if not can_add: break
                    if can_add:
                        ok = False
                        break
            if ok:
                # Also check no three collinear in the set
                if is_no3(cand):
                    if cand not in found:
                        found.append(cand.copy())
                        if len(found) >= 30:
                            return found
    return found

print("=" * 80)
print("DEEP ANALYSIS: Missing-Center in MIN Dominating Sets")
print("=" * 80)

for n in [7, 8, 9]:
    k = {7:8, 8:8, 9:8}[n]
    trials = {7:2000, 8:3000, 9:4000}[n]
    
    print(f"\n--- n={n} (target k={k}, trials={trials}) ---")
    found = find_min_sets_fast(n, k, trials)
    
    if not found:
        print("  No dominating sets found")
        continue
    
    print(f"  Found {len(found)} distinct dominating sets")
    
    missing_ct = sum(1 for s in found if ring_info(n, s)['missing'])
    has_ct = len(found) - missing_ct
    print(f"  Missing-center: {missing_ct}/{len(found)} = {missing_ct/len(found)*100:.1f}%")
    print(f"  Has-center:     {has_ct}/{len(found)} = {has_ct/len(found)*100:.1f}%")
    
    rot2_ct = sum(1 for s in found if rot2_symmetry(n, s))
    print(f"  rot2: {rot2_ct}/{len(found)} = {rot2_ct/len(found)*100:.1f}%")
    
    # Structural comparison
    miss_rings = [ring_info(n,s)['rings'] for s in found if ring_info(n,s)['missing']]
    has_rings_l = [ring_info(n,s)['rings'] for s in found if not ring_info(n,s)['missing']]
    if miss_rings:
        print(f"  Missing: avg_rings={sum(miss_rings)/len(miss_rings):.1f}")
    if has_rings_l:
        print(f"  Has-center: avg_rings={sum(has_rings_l)/len(has_rings_l):.1f}")
    
    # Show ring distributions for each type
    for label, cond in [("MISSING", True), ("HAS-CENTER", False)]:
        examples = [s for s in found if ring_info(n,s)['missing']==cond][:3]
        if examples:
            print(f"\n  {label} examples:")
            for s in examples:
                ri = ring_info(n, s)
                print(f"    {sorted(s)}")
                print(f"      rings={ri['rings']}, maxpop={ri['maxpop']}, rot2={rot2_symmetry(n,s)}, center={center_used(n,s)}")

print("\nDone!")