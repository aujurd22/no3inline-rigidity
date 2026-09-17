"""
Compute top-K dangerous direction vectors for n=76 (N=38, W=64) C4 solver.
Danger = number of collinear triples along that direction within fundamental domain.
Output: baked-in C++ constants for seed_initial prefilter.
"""
import math
from collections import defaultdict

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a if a > 0 else -a

def main():
    n = 76
    N = n // 2  # 38, half-side of C4 fundamental domain
    
    # For C4: fundamental domain is [0,N) x [0,N)
    # A "direction vector" is a reduced slope (dx, dy) with gcd(|dx|,|dy|)=1
    # We consider ALL possible reduced vectors where at least one point triple exists
    
    danger_scores = defaultdict(int)
    
    # Count collinear triples per direction
    # In fundamental domain [0,N) x [0,N), a line with direction (dx,dy) passing through (x0,y0)
    # contains points: (x0 + k*dx, y0 + k*dy) for integer k
    # A triple is 3+ points on such a line within the domain
    
    # Iterate over all pairs of distinct points to find their direction
    points = [(x, y) for x in range(N) for y in range(N)]
    
    for i, (x1, y1) in enumerate(points):
        for x2, y2 in points[i+1:]:
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                continue
            g = gcd(dx, dy)
            rx, ry = dx // g, dy // g
            
            # Count how many points lie on this line through (x1,y1) with direction (rx,ry)
            count = 0
            k = -100  # search backwards
            while True:
                px, py = x1 + k * rx, y1 + k * ry
                if 0 <= px < N and 0 <= py < N:
                    count += 1
                elif px < N and py < N:
                    break  # went too far back
                k += 1
                if k > 100:
                    break
            
            # Actually let's do this more carefully
            # Find all k such that (x1+k*rx, y1+k*ry) is in [0,N)^2
            ks = []
            k_min = max(-(x1 // rx) if rx > 0 else ((N-1-x1)//(-rx)) if rx < 0 else -1000,
                        -(y1 // ry) if ry > 0 else ((N-1-y1)//(-ry)) if ry < 0 else -1000)
            k_max = min(((N-1-x1)//rx) if rx > 0 else (-x1//(-rx)) if rx < 0 else 1000,
                       ((N-1-y1)//ry) if ry > 0 else (-y1//(-ry)) if ry < 0 else 1000)
            
            for k in range(k_min, k_max + 1):
                px, py = x1 + k * rx, y1 + k * ry
                if 0 <= px < N and 0 <= py < N:
                    ks.append(k)
            
            num_points = len(ks)
            if num_points >= 3:
                # Number of triples on this line segment = C(num_points, 3)
                triples = num_points * (num_points - 1) * (num_points - 2) // 6
                danger_scores[(rx, ry)] += triples
    
    # Sort by danger score descending
    ranked = sorted(danger_scores.items(), key=lambda x: -x[1])
    
    print(f"n={n}, N={N}, total directions with triples: {len(ranked)}")
    print(f"\nTop-20 dangerous directions:")
    print(f"{'Rank':>4} {'(dx,dy)':>10} {'Triples':>10} {'Notes'}")
    print("-" * 60)
    
    for i, ((dx, dy), score) in enumerate(ranked[:20]):
        note = ""
        if abs(dx) == abs(dy):
            note = "diagonal"
        elif dx == 0 or dy == 0:
            note = "axis"
        elif abs(dx) == 1 or abs(dy) == 1:
            note = "slope-1"
        print(f"{i+1:>4} ({dx:>+3d},{dy:>+3d}) {score:>10,d} {note}")
    
    # Output C++ constants for top-5
    print("\n\n=== C++ BAKE-IN for top-5 ===")
    print("// Precomputed top-5 dangerous directions for n=76 (N=38)")
    print("constexpr int DANGER_DIRS = 5;")
    print("constexpr int DANGER_DX[DANGER_DIRS] = {", end="")
    print(",".join(str(d[0][0]) for d in ranked[:5]), end="")
    print("};")
    print("constexpr int DANGER_DY[DANGER_DIRS] = {", end="")
    print(",".join(str(d[0][1]) for d in ranked[:5]), end="}")
    print("};")
    
    # Also save full data
    with open("analysis/danger_n76.txt", "w") as f:
        f.write(f"# Danger directions for n={n} (N={N})\n")
        f.write(f"# Format: dx dy triples rank\n")
        for i, ((dx, dy), score) in enumerate(ranked):
            f.write(f"{dx} {dy} {score} {i+1}\n")
    
    print(f"\nFull data saved to analysis/danger_n76.txt")

if __name__ == "__main__":
    main()
