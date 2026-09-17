"""
mutual_edge_test.py — Test pure mutual-edge decompositions for m=37.

Tests the patterned starter and other candidate pairings for
(S) and (X) conflict avoidance.
"""
import sys, math, itertools, json, time

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def line_key(p, q):
    """Normalized line key for points p,q."""
    x1, y1 = p; x2, y2 = q
    A = y2 - y1; B = x1 - x2; C = x2 * y1 - x1 * y2
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g: A //= g; B //= g; C //= g
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return (A, B, C)

def collinear_count(pts):
    """Count number of collinear triples among pts. Returns count."""
    n = len(pts)
    total = 0
    for i in range(n):
        xi, yi = pts[i]
        for j in range(i + 1, n):
            xj, yj = pts[j]
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, n):
                xk, yk = pts[k]
                if dx * (yk - yi) == dy * (xk - xi):
                    total += 1
    return total

def cells_to_pts(cells, m):
    N = 2 * m
    return [c4((x, y), r, N) for (x, y) in cells for r in range(4)]

def test_patterned_starter():
    """Test the patterned starter: {i, 37-i} for i=1..18, plus loop at 0."""
    m = 37
    pairs = [(i, 37 - i) for i in range(1, 19)]  # 18 pairs
    loop_at = 0
    
    for loop_pos in range(37):
        cells = list(pairs) + [(loop_pos, loop_pos)]
        pts = cells_to_pts(cells, m)
        B = collinear_count(pts)
        print(f"  loop at {loop_pos:2d}: B = {B} {'(NTIL!)' if B == 0 else ''}")
    
    return pairs

def test_quadratic_residue_starter():
    """Test the quadratic residue starter for p=37."""
    m = 37
    # QR for p=37: squares mod 37
    qrs = set()
    for i in range(1, 37):
        qrs.add((i * i) % 37)
    
    # Pair each QR r with r+1 (mod 37)
    used = set()
    pairs = []
    for r in sorted(qrs):
        a = r
        b = (r + 1) % 37
        if a not in used and b not in used and a != b:
            pairs.append((a, b))
            used.add(a)
            used.add(b)
    
    print(f"  QR starter produced {len(pairs)} pairs (expected 18)")
    if len(pairs) == 18:
        for loop_pos in range(37):
            cells = list(pairs) + [(loop_pos, loop_pos)]
            pts = cells_to_pts(cells, m)
            B = collinear_count(pts)
            print(f"  QR + loop at {loop_pos:2d}: B = {B} {'(NTIL!)' if B == 0 else ''}")
    
    return pairs

def test_general_pairs(pairs, name="custom"):
    """Test arbitrary collection of 18 mutual pairs + all loop positions."""
    m = 37
    print(f"  === {name} ===")
    min_B = 10**9
    best_loop = -1
    B_vals = []
    for loop_pos in range(37):
        cells = list(pairs) + [(loop_pos, loop_pos)]
        pts = cells_to_pts(cells, m)
        B = collinear_count(pts)
        B_vals.append(B)
        if B < min_B:
            min_B = B
            best_loop = loop_pos
        if B == 0:
            print(f"  *** FOUND NTIL! loop at {loop_pos}, pairs={pairs}")
            return True, loop_pos
    avg_B = sum(B_vals) / len(B_vals)
    print(f"  B range: {min(B_vals)}-{max(B_vals)}, avg={avg_B:.1f}, best_loop={best_loop}")
    # Show sample B values for first 5 loop positions
    print(f"  Sample B: loop 0..4 = {B_vals[:5]}")
    return False, None

if __name__ == "__main__":
    m = 37
    print(f"=== Mutual-edge test for m={m} ===")
    print()
    
    # Test 1: Patterned starter
    print("Test 1: Patterned starter {i, 37-i}")
    pairs1 = [(i, 37 - i) for i in range(1, 19)]
    found, lp = test_general_pairs(pairs1, "patterned")
    print()
    
    # Test 2: Cyclic shift of patterned starter
    print("Test 2: Cyclic shifted patterned {i+5, 37-i+5} mod 37")
    pairs2 = [((i + 5) % 37, (37 - i + 5) % 37) for i in range(1, 19)]
    # Ensure all values 0..36 used exactly once
    used = set()
    clean_pairs = []
    for a, b in pairs2:
        if a not in used and b not in used:
            clean_pairs.append((a, b))
            used.add(a); used.add(b)
    print(f"  Clean pairs: {len(clean_pairs)}")
    found, lp = test_general_pairs(clean_pairs, "cyclic_shift")
    print()
    
    # Test 3: Difference-1 pairs (i, i+1) for even i
    print("Test 3: Adjacent pairs (2k, 2k+1)")
    pairs3 = [(2*k, 2*k+1) for k in range(18)]
    found, lp = test_general_pairs(pairs3, "adjacent")
    print()
    
    # Test 4: Random valid pairings (a few samples)
    print("Test 4: Random pairings")
    import random
    random.seed(7)
    for trial in range(10):
        vertices = list(range(37))
        random.shuffle(vertices)
        pairs4 = [(vertices[2*k], vertices[2*k+1]) for k in range(18)]
        found, lp = test_general_pairs(pairs4, f"random_{trial}")
        if found:
            print(f"  *** RANDOM trial {trial} FOUND NTIL! ***")
    print()
    
    print("=== All tests complete ===")
