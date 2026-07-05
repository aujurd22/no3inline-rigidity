"""
Apply the missing-center (circumcenter) invariant to the MINIMAL version 
of the No-Three-In-Line problem (a.k.a. geometric dominating set / 
Martin Gardner's minimal no-3-in-a-line problem).

Instead of asking "how many points can we place", the MIN version asks:
"What is the SMALLEST set S (no three collinear) such that adding ANY 
other grid point creates a collinear triple?"

We analyze whether such minimal dominating sets also have the grid center 
as a circumcenter, and compare with our MAX-solution results.
"""

import itertools, random, math
from collections import Counter

def collinear(p1, p2, p3):
    """Check if three points are collinear."""
    x1,y1 = p1; x2,y2 = p2; x3,y3 = p3
    return (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1)

def is_no3(pts_set):
    """Check if a set of points has no three collinear."""
    pts = list(pts_set)
    for i in range(len(pts)):
        for j in range(i+1, len(pts)):
            for k in range(j+1, len(pts)):
                if collinear(pts[i], pts[j], pts[k]):
                    return False
    return True

def is_maximal(n, pts_set):
    """Check if a set is maximal: any additional grid point creates collinearity."""
    pts_list = list(pts_set)
    # For each grid point not in the set
    for i in range(n):
        for j in range(n):
            p = (i, j)
            if p in pts_set:
                continue
            # Check if adding p creates a collinear triple
            creates_collinear = False
            for a in pts_list:
                for b in pts_list:
                    if a >= b: continue
                    if collinear(a, b, p):
                        creates_collinear = True
                        break
                if creates_collinear:
                    break
            if not creates_collinear:
                return False  # Found a point we can add without creating collinearity
    return True

def center_rings(n, pts):
    """Compute distance ring distribution from the grid center."""
    ctr = (n-1)/2.0
    rings = Counter()
    for i,j in pts:
        d2 = int(round((i-ctr)**2 + (j-ctr)**2))
        rings[d2] += 1
    return rings

def is_missing_center(n, pts):
    """Check if grid center is NOT a circumcenter (no ring has >=3 pts)."""
    rings = center_rings(n, pts)
    return all(v < 3 for v in rings.values())

def random_search(n, target_k, iterations=50000):
    """Random search for a maximal no-3-in-line set of size target_k."""
    all_points = [(i,j) for i in range(n) for j in range(n)]
    
    best = 0
    best_set = None
    
    for _ in range(iterations):
        # Start with a random set of size target_k
        candidate = set(random.sample(all_points, target_k))
        
        # Check no three collinear
        if not is_no3(candidate):
            continue
        
        # Check maximality (expensive — only do for promising candidates)
        if is_maximal(n, candidate):
            return candidate  # Found one!
        
        # Track closest to maximal
        pts_list = list(candidate)
        count_extendable = 0
        for i in range(n):
            for j in range(n):
                p = (i, j)
                if p in candidate: continue
                ok = True
                for a in pts_list:
                    for b in pts_list:
                        if a >= b: continue
                        if collinear(a, b, p):
                            ok = False
                            break
                    if not ok: break
                if ok: count_extendable += 1
        
        max_extendable = n*n - target_k
        score = max_extendable - count_extendable
        if score > best:
            best = score
            best_set = candidate
    
    return None, best, best_set

# Known minimal values from OEIS A277433 / Cooper et al.
known_min = {1:1, 2:4, 3:4, 4:4, 5:6, 6:6, 7:8, 8:8, 9:8, 10:8, 11:10, 12:10}

print("=" * 80)
print("CIRCUMCENTER ANALYSIS: MINIMAL No-3-In-Line (Dominating Set Version)")
print("=" * 80)
print()

# For n=7, known minimal is 8
for n in [7, 8]:
    k = known_min[n]
    print(f"Searching n={n} (target k={k})...")
    
    result = random_search(n, k, iterations=20000)
    if result[0] is not None:
        sol = result[0]
        rings = center_rings(n, sol)
        missing = is_missing_center(n, sol)
        max_ring = max(rings.values())
        print(f"  FOUND: {sol}")
        print(f"  Rings: {dict(sorted(rings.items()))}")
        print(f"  Max ring population: {max_ring}")
        print(f"  Center is circumcenter: {'NO (missing!)' if missing else 'YES'}")
    else:
        print(f"  Not found by random search (best score={result[1]})")

print()
print("=" * 80)
print("COMPARISON: MAX-solution (2n pts) vs MIN-solution (k pts)")
print("=" * 80)
print()

# Compare n=7: take a MAX solution and a MIN solution
# For the MAX solution, use our existing data
# For the MIN solution, we'll construct from literature

# Known minimal solutions from literature (Cooper et al. 2012 + OEIS)
# These are CONSTRUCTED, not searched
known_min_solutions = {
    7: [(0,0),(1,1),(2,4),(3,2),(4,2),(5,4),(6,1),(0,3)],  # Need to verify
}

# Actually, let me use a smarter construction approach:
# I'll iteratively grow a set from scratch to find a proper minimal dominating set

print("Constructing minimal dominating sets iteratively...")
print()

# For n=7, try to construct using known pattern from literature
# A known 8-point solution for n=7: the "vee" pattern
# Let me try the construction from Gardner's column

# Known construction: place points on two parallel lines
# The minimal set for n=7 is known to be 8 points
# Let's use a well-known pattern: points along 45-degree diagonals

# Let me try known solutions from the Cooper et al. paper:
# For n=7, a solution is: (0,0), (1,2), (2,4), (3,6), (4,1), (5,3), (6,5), plus one more

# Actually, let me try a simple construction first
candidates_7 = [
    # Set 1: center-crossing pattern
    {(0,0), (0,6), (3,0), (3,6), (6,0), (6,6), (0,3), (6,3)},
    # Set 2: staggered diagonals
    {(0,1), (1,3), (2,5), (3,0), (4,2), (5,4), (6,6), (3,3)},
    # Set 3: 4-corner + 4-edge
    {(0,0), (0,6), (6,0), (6,6), (0,3), (3,0), (3,6), (6,3)},
    # Set 4: parabola + extra
    {(0,0), (1,1), (2,4), (3,2), (4,2), (5,4), (6,1), (6,0)},
]

print("n=7 candidates:")
for idx, cand in enumerate(candidates_7):
    no3 = is_no3(cand)
    if no3:
        mx = is_maximal(7, cand)
        rings = center_rings(7, cand)
        miss = is_missing_center(7, cand)
        print(f"  Cand #{idx}: no3={no3}, maximal={mx}, missing-center={miss}, rings={dict(sorted(rings.items()))}")
    else:
        print(f"  Cand #{idx}: has collinearities")

print()
print("Trying iterative construction for n=7...")

# Greedy construction: start empty, add points that are "most dominating"
# until we have a maximal no-3-in-line set

def greedy_construct_min(n, max_attempts=100):
    """Greedily construct a minimal dominating set."""
    all_grid = [(i,j) for i in range(n) for j in range(n)]
    
    for attempt in range(max_attempts):
        random.shuffle(all_grid)
        chosen = []
        chosen_set = set()
        
        for p in all_grid:
            # Check if adding p creates collinearity
            ok = True
            for a in chosen:
                for b in chosen:
                    if a >= b: continue
                    if collinear(a, b, p):
                        ok = False
                        break
                if not ok: break
            if ok:
                chosen.append(p)
                chosen_set.add(p)
                if len(chosen_set) == 2*n:  # safety limit
                    break
        
        # Now check if this set is maximal
        if is_maximal(n, chosen_set):
            return chosen_set
    
    # If not maximal, try to find a superset
    return None

min_set_7 = greedy_construct_min(7, 50)
if min_set_7:
    print(f"  Found by greedy construction: {len(min_set_7)} points")
    rings = center_rings(7, min_set_7)
    miss = is_missing_center(7, min_set_7)
    print(f"  Points: {sorted(min_set_7)}")
    print(f"  Rings: {dict(sorted(rings.items()))}")
    print(f"  Missing-center: {miss}")
else:
    print("  Greedy construction didn't find a maximal set")
    # Let's try to find by brute force for n=7 with small k
    print("  Trying brute force for n=7, k=8...")

# For n=7, k=8, total C(49,8) is too large, but we can try to be smarter
# We know from literature that minimal dominating sets exist at k=8
# Let's just analyze the ring structure of the TWO types of solutions:
# MAX (14 points) vs MIN (8 points)

# For the MAX type, use our existing iDEN solution from Flammenkamp
import urllib.request
ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
char_to_val = {c:i for i,c in enumerate(ALPHABET)}

url = 'https://wwwhomes.uni-bielefeld.de/achim/no3in/download/configurations/n7_iden'
with urllib.request.urlopen(url, timeout=10) as f:
    lines = [l for l in f.read().decode().strip().split(chr(10)) if l.strip()]

if lines:
    line = lines[0].strip()
    rest = line[1:]
    n7 = 7
    pts_max = []
    for r in range(n7):
        pts_max.append((r, char_to_val[rest[2*r]]))
        pts_max.append((r, char_to_val[rest[2*r+1]]))
    
    rings_max = center_rings(n7, pts_max)
    miss_max = is_missing_center(n7, pts_max)
    
    print()
    print("=" * 80)
    print(f"COMPARISON TABLE: MAX (14-pt) vs MIN (8-pt)")
    print("=" * 80)
    print()
    print(f"MAX solution (n=7 iden): {len(pts_max)} pts")
    print(f"  Points: {sorted(pts_max)}")
    print(f"  Rings: {dict(sorted(rings_max.items()))}")
    print(f"  Missing-center: {miss_max}")
    print(f"  # distinct rings: {len(rings_max)}")
    
    # For the MIN type, try to find by random sampling + hill climbing
    print()
    print("Searching for MIN (8-pt) dominating sets with hill climbing...")
    
    best_sets = []
    all_pts = [(i,j) for i in range(7) for j in range(7)]
    
    for seed in range(100):
        random.seed(seed)
        # Generate a random 8-point set with no collinearity
        while True:
            cand = set(random.sample(all_pts, 8))
            if is_no3(cand):
                break
        
        # Check maximality
        if is_maximal(7, cand):
            best_sets.append(cand)
    
    print(f"  Found {len(best_sets)} maximal 8-point sets (out of 100 random attempts)")
    
    if best_sets:
        for idx, sol in enumerate(best_sets[:5]):
            rings_min = center_rings(7, sol)
            miss_min = is_missing_center(7, sol)
            print(f"  MIN set #{idx}: {sorted(sol)}")
            print(f"    Rings: {dict(sorted(rings_min.items()))}")
            print(f"    Missing-center: {miss_min}")
            print(f"    # distinct rings: {len(rings_min)}")
    
    # Key comparison
    print()
    print("=" * 80)
    print("KEY INSIGHT: MAX (2n-pt) vs MIN (k-pt) circumcenter properties")
    print("=" * 80)
    print()
    print(f"{'Metric':<40} {'MAX (14pts)':<15} {'MIN (8pts)':<15}")
    print("-" * 70)
    
    # MAX metrics (from the one sample)
    max_rings = len(rings_max)
    max_maxpop = max(rings_max.values())
    
    if best_sets:
        min0 = best_sets[0]
        rings_min0 = center_rings(7, min0)
        min_rings = len(rings_min0)
        min_maxpop = max(rings_min0.values())
        
        print(f"{'# distinct distance rings':<40} {max_rings:<15} {min_rings:<15}")
        print(f"{'Max ring population':<40} {max_maxpop:<15} {min_maxpop:<15}")
        print(f"{'Missing-center?':<40} {'YES' if miss_max else 'NO':<15} {'YES' if is_missing_center(7, min0) else 'NO':<15}")
