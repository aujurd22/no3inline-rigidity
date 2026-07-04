#!/usr/bin/env python3
"""
方向一：哈密顿循环置换空间搜索 (Hamiltonian Cycle GA Search)

把解编码为一个置换 π[0..n-1]，行 i 放置 (π[i], i) 和 (π[i+1], i)。
这个编码天然满足：
- 每行 2 点 ✓
- 每列 2 点 ✓  

搜索目标：找到一个置换使得：
- 无三点共线 (collinearity = 0)
- 每个距离环 ≤ 2 点 (missing-center)

使用 2-opt 局部搜索 + 随机重启。

Usage:
    python ham_cycle_search.py <n> [max_iterations] [restarts]
"""

import sys
import random
from collections import defaultdict, Counter
from itertools import combinations
import math
import time


class HamiltonianSolution:
    """A No-Three-In-Line solution encoded as a column permutation."""
    
    def __init__(self, n, perm=None):
        self.n = n
        self.cx2 = self.cy2 = n - 1
        self.perm = perm if perm else self._random_perm()
        self._cached_fitness = None
    
    def _random_perm(self):
        """Generate a random permutation of 0..n-1."""
        p = list(range(self.n))
        random.shuffle(p)
        return p
    
    def get_points(self):
        """Return list of (x, y) = (col, row) for this solution."""
        pts = []
        for i in range(self.n):
            c1 = self.perm[i]
            c2 = self.perm[(i + 1) % self.n]
            pts.append((c1, i))
            pts.append((c2, i))
        return pts
    
    def get_dist(self, x, y):
        """Squared distance from grid center."""
        dx = 2 * x - self.cx2
        dy = 2 * y - self.cy2
        return dx * dx + dy * dy
    
    def fitness(self):
        """Compute fitness: lower is better.
        0 = perfect solution (no collinearity, missing-center).
        """
        if self._cached_fitness is not None:
            return self._cached_fitness
        
        pts = self.get_points()
        k = len(pts)
        
        # Penalty 1: Collinearity
        collinear_count = 0
        for i in range(k):
            x1, y1 = pts[i]
            for j in range(i + 1, k):
                x2, y2 = pts[j]
                for m in range(j + 1, k):
                    x3, y3 = pts[m]
                    # Cross product = 0 means collinear
                    area2 = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
                    if area2 == 0:
                        collinear_count += 1
        
        # Penalty 2: Ring overload
        ring_counts = Counter()
        for x, y in pts:
            d = self.get_dist(x, y)
            ring_counts[d] += 1
        
        ring_overload = sum(max(0, c - 2) for c in ring_counts.values())
        
        # Heavier weight on collinearity (must be 0 for valid solution)
        fitness = collinear_count * 1000 + ring_overload
        
        self._cached_fitness = fitness
        return fitness
    
    def is_valid(self):
        """Check if this is a valid missing-center solution."""
        return self.fitness() == 0
    
    def swap(self, i, j):
        """Swap positions i and j in the permutation (2-opt)."""
        new_perm = list(self.perm)
        new_perm[i], new_perm[j] = new_perm[j], new_perm[i]
        return HamiltonianSolution(self.n, new_perm)
    
    def invert(self, i, j):
        """Reverse segment [i, j] in the permutation."""
        new_perm = list(self.perm)
        new_perm[i:j+1] = reversed(new_perm[i:j+1])
        return HamiltonianSolution(self.n, new_perm)
    
    def neighbor(self):
        """Generate a random neighbor by 2-opt swap."""
        i, j = random.sample(range(self.n), 2)
        return self.swap(i, j)
    
    def __str__(self):
        pts = self.get_points()
        f = self.fitness()
        is_valid = self.is_valid()
        return f"perm={self.perm}, fitness={f}, valid={'✅' if is_valid else '❌'}"


def local_search(initial, max_iterations=10000, patience=500):
    """Hill climbing with random neighbor and restart."""
    current = initial
    best = initial
    best_fitness = initial.fitness()
    
    iterations_without_improvement = 0
    
    for iteration in range(max_iterations):
        neighbor = current.neighbor()
        nf = neighbor.fitness()
        
        if nf < best_fitness:
            best = neighbor
            best_fitness = nf
            iterations_without_improvement = 0
            
            if nf == 0:
                return best, iteration, True
        
        if nf <= current.fitness():
            current = neighbor
        
        iterations_without_improvement += 1
        if iterations_without_improvement >= patience:
            # Restart from a new random solution
            current = HamiltonianSolution(current.n)
            iterations_without_improvement = 0
    
    return best, max_iterations, best_fitness == 0


def search(n, restarts=100, max_iter=10000, patience=500):
    """Main search: multiple restarts with local search."""
    print(f"Searching n={n}: {restarts} restarts, {max_iter} iter each")
    print(f"  Permutation space: {n}! possibilities")
    print()
    
    best_ever = None
    best_fitness_ever = float('inf')
    total_attempts = 0
    start_time = time.time()
    
    for restart in range(restarts):
        initial = HamiltonianSolution(n)
        best_sol, iters, found = local_search(initial, max_iter, patience)
        total_attempts += iters
        
        bf = best_sol.fitness()
        if bf < best_fitness_ever:
            best_fitness_ever = bf
            best_ever = best_sol
            print(f"  Restart {restart+1}: fitness improved to {bf} (iter={iters})")
            
            if found:
                elapsed = time.time() - start_time
                print(f"\n✅ FOUND VALID SOLUTION! ({elapsed:.1f}s)")
                print(f"  Permutation: {best_ever.perm}")
                print(f"  Points: {sorted(best_ever.get_points())}")
                return best_ever
        
        if (restart + 1) % 10 == 0:
            elapsed = time.time() - start_time
            print(f"  [{restart+1}/{restarts}] best={best_fitness_ever}, {elapsed:.0f}s")
    
    elapsed = time.time() - start_time
    print(f"\nNo valid solution found in {restarts} restarts ({elapsed:.1f}s)")
    print(f"Best fitness: {best_fitness_ever}")
    
    if best_ever:
        print(f"Best permutation: {best_ever.perm}")
        # Analyze what went wrong with the best solution
        pts = best_ever.get_points()
        ring_counts = Counter()
        for x, y in pts:
            d = best_ever.get_dist(x, y)
            ring_counts[d] += 1
        print(f"Ring counts: {dict(sorted(ring_counts.items()))}")
    
    return best_ever


def exhaustive_perm_search(n):
    """Try ALL permutations (only for small n like n ≤ 6)."""
    import itertools
    
    print(f"Exhaustive search n={n}...")
    found = []
    
    for idx, perm in enumerate(itertools.permutations(range(n))):
        sol = HamiltonianSolution(n, list(perm))
        if sol.is_valid():
            found.append(perm)
            print(f"  #{len(found)}: {perm}")
    
    print(f"Found {len(found)} valid solutions")
    return found


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    restarts = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    max_iter = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    
    if n <= 6:
        # For small n, exhaustive search is feasible
        exhaustive_perm_search(n)
    else:
        sol = search(n, restarts=restarts, max_iter=max_iter)
        if sol and sol.is_valid():
            # Verify
            pts = sol.get_points()
            print(f"\nVerification:")
            ok, msg = True, "OK"
            for i in range(len(pts)):
                for j in range(i+1, len(pts)):
                    for k in range(j+1, len(pts)):
                        x1,y1 = pts[i]; x2,y2 = pts[j]; x3,y3 = pts[k]
                        if (x2-x1)*(y3-y1) - (x3-x1)*(y2-y1) == 0:
                            ok = False
                            msg = f"Collinear: {pts[i]}, {pts[j]}, {pts[k]}"
                            break
                    if not ok: break
                if not ok: break
            print(f"  {'✅' if ok else '❌'} {msg}")
