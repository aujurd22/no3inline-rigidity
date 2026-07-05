"""
Direction B: Ring Collision Graph — Number-Theoretic Analysis

For each n, the grid partitions into distance rings (sets of points at equal 
squared distance from center). Two rings are "in collision" if there exists 
a collinear triple using points from these two rings.

Conjecture: A ring's collision degree (% of other rings it conflicts with)
is determined by its sum-of-two-squares structure. Specifically, rings with
more representations as x²+y² (= more integer points on the ring) should 
have higher collision degree because more points means more opportunities
for collinearity with other rings.

This script:
1. Builds the ring collision graph for n=12..30
2. Computes r₂(d) and 4k+1 prime factor counts for each ring
3. Tests the correlation
"""

from collections import Counter
import math
import urllib.request

def r2(n):
    """Number of representations of n as sum of two squares (x²+y²=n)."""
    cnt = 0
    for x in range(-int(n**0.5), int(n**0.5)+1):
        x2 = x*x
        y2 = n - x2
        if y2 < 0: continue
        y = int(round(y2**0.5))
        if y*y == y2:
            cnt += 1
    return cnt

def prime_factors(n):
    """Return prime factorization as list of (prime, exponent)."""
    factors = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            exp = 0
            while n % d == 0:
                n //= d
                exp += 1
            factors.append((d, exp))
        d += 1 if d == 2 else 2  # after 2, check only odd
    if n > 1:
        factors.append((n, 1))
    return factors

def count_4k1_primes(n):
    """Count distinct 4k+1 prime factors."""
    cnt = 0
    for p, _ in prime_factors(n):
        if p % 4 == 1:
            cnt += 1
    return cnt

def max_4k1_prime_power(n):
    """Sum of exponents of 4k+1 primes (max power)."""
    total_exp = 0
    for p, exp in prime_factors(n):
        if p % 4 == 1:
            total_exp += exp
    return total_exp

def collinear(p1, p2, p3):
    """Check if three grid points are collinear."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)

def get_distance_rings(n):
    """Get all distance rings for n×n grid.
    Returns dict: d² -> list of (i,j) points
    """
    ctr = (n - 1) / 2.0
    rings = {}
    for i in range(n):
        for j in range(n):
            d2 = int(round((i - ctr)**2 + (j - ctr)**2))
            if d2 not in rings:
                rings[d2] = []
            rings[d2].append((i, j))
    return rings

def build_collision_graph(n, rings, sample_size=200):
    """
    Build collision graph between distance rings.
    Two rings collide if there exist points p∈A, q∈B, r∈A∪B such that 
    p,q,r are collinear.
    
    To manage complexity, sample a subset of points from each ring.
    Returns dict: d² -> set of d² it collides with
    """
    d2_list = sorted(rings.keys())
    collision = {d: set() for d in d2_list}
    
    # Sample points from each ring (max sample_size per ring)
    sampled = {}
    for d2, pts in rings.items():
        step = max(1, len(pts) // sample_size)
        sampled[d2] = pts[::step]
    
    print(f"  Rings: {len(d2_list)}, checking pairwise collisions...")
    
    # For each pair of rings, check all combinations of up to 3 points
    # Optimization: we check if ANY triple from two rings is collinear
    for i in range(len(d2_list)):
        d1 = d2_list[i]
        pts1 = sampled[d1]
        if len(pts1) == 0: continue
        
        for j in range(i+1, len(d2_list)):
            d2 = d2_list[j]
            pts2 = sampled[d2]
            if len(pts2) == 0: continue
            
            collides = False
            
            # Check: 2 from ring1 + 1 from ring2
            for a in range(len(pts1)):
                if collides: break
                for b in range(a+1, len(pts1)):
                    if collides: break
                    for c in range(len(pts2)):
                        if collinear(pts1[a], pts1[b], pts2[c]):
                            collides = True
                            break
            
            if not collides:
                # Check: 1 from ring1 + 2 from ring2
                for a in range(len(pts1)):
                    if collides: break
                    for b in range(len(pts2)):
                        if collides: break
                        for c in range(b+1, len(pts2)):
                            if collinear(pts1[a], pts2[b], pts2[c]):
                                collides = True
                                break
            
            if collides:
                collision[d1].add(d2)
                collision[d2].add(d1)
    
    return collision

def analyze_rings(n):
    """Full analysis for a single n."""
    print(f"\n{'='*70}")
    print(f"n={n} analysis")
    print(f"{'='*70}")
    
    rings = get_distance_rings(n)
    print(f"Total distance rings: {len(rings)}")
    
    # Compute r2(d) for each d² value
    ring_data = []
    for d2, pts in sorted(rings.items()):
        r2_val = r2(d2)
        k1_count = count_4k1_primes(d2)
        k1_power = max_4k1_prime_power(d2)
        ring_data.append((d2, len(pts), r2_val, k1_count, k1_power))
    
    print(f"\nRing details (first 10):")
    print(f"  d²  pop  r₂(d)  4k1_cnt  4k1_pow")
    for d2, pop, r2v, k1c, k1p in ring_data[:10]:
        print(f"  {d2:>3} {pop:>4} {r2v:>6} {k1c:>8} {k1p:>7}")
    
    # Build collision graph
    collision = build_collision_graph(n, rings)
    
    # Compute degrees
    n_rings = len(d2_list := sorted(rings.keys()))
    degrees = {}
    for d2 in d2_list:
        deg = len(collision.get(d2, set()))
        degrees[d2] = deg / max(1, n_rings - 1) * 100  # percentage
    
    # Print high-collision rings
    print(f"\nHighest collision degree rings:")
    d_by_deg = sorted(degrees.items(), key=lambda x: -x[1])
    for d2, deg in d_by_deg[:8]:
        pop = len(rings[d2])
        r2v = r2(d2)
        k1c = count_4k1_primes(d2)
        pf = prime_factors(d2)
        print(f"  d²={d2:>4}: {deg:>5.1f}%  pop={pop:>2}  r₂={r2v:>3}  "
              f"4k1={k1c}  factors={pf}")
    
    # Correlate collision degree with ring properties
    # Group rings by properties
    print(f"\nCollision degree by ring population size:")
    by_pop = {}
    for d2, deg in degrees.items():
        pop = len(rings[d2])
        key = min(pop, 12)  # cap at 12 for grouping
        if key not in by_pop:
            by_pop[key] = []
        by_pop[key].append(deg)
    for pop in sorted(by_pop.keys()):
        vals = by_pop[pop]
        print(f"  pop={pop:>2}: avg_deg={sum(vals)/len(vals):>5.1f}% "
              f"min={min(vals):>4.1f}% max={max(vals):>4.1f}% ({len(vals)} rings)")
    
    print(f"\nCollision degree by r₂(d) value:")
    by_r2 = {}
    for d2, deg in degrees.items():
        r2v = r2(d2)
        if r2v not in by_r2:
            by_r2[r2v] = []
        by_r2[r2v].append(deg)
    for r2v in sorted(by_r2.keys()):
        vals = by_r2[r2v]
        print(f"  r₂={r2v:>2}: avg_deg={sum(vals)/len(vals):>5.1f}% "
              f"({len(vals)} rings)")
    
    return {
        'n': n,
        'rings': len(rings),
        'degrees': degrees,
        'collision': collision,
        'ring_data': ring_data
    }

# ========== MAIN ==========
print("=" * 70)
print("DIRECTION B: Ring Collision Graph — Sum-of-Two-Squares Analysis")
print("=" * 70)
print()
print("Hypothesis: A distance ring's collision degree is determined by its")
print("4k+1 prime factor structure. More 4k+1 factors → more integer points")
print("→ higher probability of collinear collisions with other rings.")
print()

for n in [12, 14, 16, 18, 20, 22, 24, 27, 30]:
    try:
        analyze_rings(n)
    except Exception as e:
        print(f"\n  ERROR for n={n}: {e}")

print("\n\nDone!")
