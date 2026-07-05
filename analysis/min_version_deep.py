"""
Deep analysis: Missing-center invariant in MIN dominating sets (n=7 to n=12).

Questions:
1. Does the 80% missing-center rate hold for larger n?
2. What distinguishes the has-center minority? (symmetry, structure?)
3. Is there a pattern in the missing-center ones?
4. Compare ring utilization: MIN vs MAX
"""

import random, itertools, math
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

def is_maximal(n, pts):
    pl = list(pts)
    for i in range(n):
        for j in range(n):
            p=(i,j)
            if p in pts: continue
            ok=True
            for a in pl:
                for b in pl:
                    if a>=b: continue
                    if collinear(a,b,p): ok=False;break
                if not ok: break
            if ok: return False
    return True

def ring_info(n, pts):
    ctr=(n-1)/2.0
    rng=Counter()
    for i,j in pts:
        d2=int(round((i-ctr)**2+(j-ctr)**2))
        rng[d2]+=1
    maxpop=max(rng.values())
    missing = all(v<3 for v in rng.values())
    return {'rings': len(rng), 'maxpop': maxpop, 'missing': missing, 'dist': dict(sorted(rng.items()))}

def rot2_symmetry(n, pts):
    """Check 180-degree rotational symmetry (rot2)."""
    R2 = lambda p: (n-1-p[0], n-1-p[1])
    return all(R2(p) in pts for p in pts)

def center_used(n, pts):
    ctr=(n-1)/2.0
    return ctr%1==0 and (int(ctr), int(ctr)) in pts

def find_min_sets(n, k, trials=5000):
    """Hill-climbing search for minimal dominating sets of size k."""
    all_pts = [(i,j) for i in range(n) for j in range(n)]
    found = []
    
    for trial in range(trials):
        random.seed(trial*137+42)
        while True:
            cand = set(random.sample(all_pts, k))
            if is_no3(cand): break
        
        best = cand.copy()
        best_score = sum(1 for i in range(n) for j in range(n)
                        if (i,j) not in best and 
                        any(collinear(a,b,(i,j)) for a in best for b in best if a<b))
        
        improved = True
        for _ in range(100):
            if not improved: break
            improved = False
            for p_out in list(best):
                for p_in in all_pts:
                    if p_in in best: continue
                    new_set = (best - {p_out}) | {p_in}
                    if not is_no3(new_set): continue
                    score = sum(1 for i in range(n) for j in range(n)
                               if (i,j) not in new_set and
                               any(collinear(a,b,(i,j)) for a in new_set for b in new_set if a<b))
                    if score > best_score:
                        best = new_set.copy()
                        best_score = score
                        improved = True
                        break
                if improved: break
        
        if best_score == n*n - k:
            if is_maximal(n, best):
                if best not in found:
                    found.append(best.copy())
                    ri = ring_info(n, best)
                    rot2 = rot2_symmetry(n, best)
                    cu = center_used(n, best)
                    if len(found) >= 20:
                        break
    
    return found

# ============================================================
print("=" * 80)
print("DEEP ANALYSIS: Missing-Center in MIN Dominating Sets")
print("=" * 80)

for n in [7, 8, 9, 10]:
    k_known = {7:8, 8:8, 9:8, 10:8, 11:10, 12:10}
    k = k_known[n]
    
    print(f"\n--- n={n} (target k={k}) ---")
    found = find_min_sets(n, k, trials=8000)
    
    if not found:
        print("  No dominating sets found")
        continue
    
    print(f"  Found {len(found)} distinct dominating sets")
    
    # Analysis
    missing_ct = sum(1 for s in found if ring_info(n, s)['missing'])
    has_ct = len(found) - missing_ct
    
    print(f"  Missing-center: {missing_ct}/{len(found)} = {missing_ct/len(found)*100:.1f}%")
    print(f"  Has-center:     {has_ct}/{len(found)} = {has_ct/len(found)*100:.1f}%")
    
    # Rot2 symmetry analysis
    rot2_ct = sum(1 for s in found if rot2_symmetry(n, s))
    print(f"  rot2 symmetric: {rot2_ct}/{len(found)} = {rot2_ct/len(found)*100:.1f}%")
    
    # Center usage
    cu_ct = sum(1 for s in found if center_used(n, s))
    print(f"  Uses center: {cu_ct}/{len(found)} = {cu_ct/len(found)*100:.1f}%")
    
    # Compare missing vs has-center ring distributions
    missing_rings = []
    has_rings = []
    for s in found:
        ri = ring_info(n, s)
        if ri['missing']:
            missing_rings.append(ri['rings'])
        else:
            has_rings.append(ri['rings'])
    
    if missing_rings:
        print(f"  Missing-center: avg rings={sum(missing_rings)/len(missing_rings):.1f}, range={min(missing_rings)}-{max(missing_rings)}")
    if has_rings:
        print(f"  Has-center:     avg rings={sum(has_rings)/len(has_rings):.1f}, range={min(has_rings)}-{max(has_rings)}")
    
    # Compare maxpop
    missing_maxpops = [ring_info(n, s)['maxpop'] for s in found if ring_info(n, s)['missing']]
    has_maxpops = [ring_info(n, s)['maxpop'] for s in found if not ring_info(n, s)['missing']]
    if missing_maxpops:
        print(f"  Missing-center: avg max_ring_pop={sum(missing_maxpops)/len(missing_maxpops):.1f}")
    if has_maxpops:
        print(f"  Has-center:     avg max_ring_pop={sum(has_maxpops)/len(has_maxpops):.1f}")
    
    # Show 2 example solutions of each type
    missing_examples = [s for s in found if ring_info(n, s)['missing']][:2]
    has_examples = [s for s in found if not ring_info(n, s)['missing']][:2]
    
    print()
    for label, examples in [("MISSING-CENTER", missing_examples), ("HAS-CENTER", has_examples)]:
        if examples:
            print(f"  {label}:")
            for s in examples:
                ri = ring_info(n, s)
                r2 = rot2_symmetry(n, s)
                cu = center_used(n, s)
                print(f"    {sorted(s)}")
                print(f"      rings={ri['rings']}, maxpop={ri['maxpop']}, rot2={r2}, center={cu}")

# ============================================================
print("\n" + "=" * 80)
print("COMPARISON: MIN vs MAX ring utilization")
print("=" * 80)

# For MAX solutions, use our Flammenkamp data
import urllib.request
ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
char_to_val = {c:i for i,c in enumerate(ALPHABET)}

for n in [7, 8, 9]:
    # MAX data
    max_rings_list = []
    for symm in ['iden', 'rot2']:
        url = f'https://wwwhomes.uni-bielefeld.de/achim/no3in/download/configurations/n{n}_{symm}'
        try:
            with urllib.request.urlopen(url, timeout=10) as f:
                lines = [l for l in f.read().decode().strip().split(chr(10)) if l.strip() and 'html' not in l.lower()[:10]]
        except:
            continue
        for line in lines[:40]:
            rest = line.strip()[1:]
            pts = [(r, char_to_val[rest[2*r]]) for r in range(n)] + [(r, char_to_val[rest[2*r+1]]) for r in range(n)]
            ri = ring_info(n, set(pts))
            max_rings_list.append(ri)
    
    # MIN data
    k_known = {7:8, 8:8, 9:8}
    k = k_known[n]
    min_sets = find_min_sets(n, k, trials=3000)
    min_rings_list = [ring_info(n, s) for s in min_sets[:40] if ring_info(n, s)['missing']]
    
    print(f"\nn={n}:")
    max_r = [ri['rings'] for ri in max_rings_list]
    max_m = [ri['maxpop'] for ri in max_rings_list]
    min_r = [ri['rings'] for ri in min_rings_list]
    min_m = [ri['maxpop'] for ri in min_rings_list]
    
    print(f"  MAX ({2*n} pts): avg_rings={sum(max_r)/len(max_r):.1f}, avg_maxpop={sum(max_m)/len(max_m):.1f}")
    if min_r:
        print(f"  MIN ({k} pts):  avg_rings={sum(min_r)/len(min_r):.1f}, avg_maxpop={sum(min_m)/len(min_m):.1f}")
        print(f"  Ring utilization ratio (pts/ring): MAX={2*n/(sum(max_r)/len(max_r)):.1f}, MIN={k/(sum(min_r)/len(min_r)):.1f}")