"""
p-adic transposition SA — rigorous version.
Unified bit convention: mask bit 0→i, bit 1→j, bit 2→k.
count_colls and verify use the SAME convention.
Output: ntil_n{N}_sa.json if NTIL reached.
"""
import itertools, json, math, random, time, sys

# ============================================================
# Helpers
# ============================================================

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]

def gray(n):
    return [x ^ (x >> 1) for x in range(n)]

def build_transpositions(perm, n, k):
    """Return list of (a,b) transpositions forming Q_k edge set on perm's image."""
    tps = set()
    for x in range(n):
        for b in range(k):
            y = x ^ (1 << b)
            if y > x:
                a, bb = perm[x], perm[y]
                tps.add((min(a, bb), max(a, bb)))
    return sorted(tps)


# ============================================================
# Collision counting — UNIFIED CONVENTION
# mask bits: 0=i (pi), 1=j (pj), 2=k (pk)
# 0 → use p0[v], 1 → use p1[v]
# ============================================================

def count_collisions(p0, p1, n):
    """Count all 8-type collinear triples for given double-permutation.
    
    For each triple (i,j,k) sorted i<j<k, check all 8 assignments
    of functions (p0/p1) to the three rows.
    
    Returns: (total_collisions, set_of_(i,j,k,mask)_keys_or_None)
    """
    cnt = 0
    for i, j, k in itertools.combinations(range(n), 3):
        a0i, a0j, a0k = p0[i], p0[j], p0[k]
        a1i, a1j, a1k = p1[i], p1[j], p1[k]
        dxj = j - i
        dxk = k - i
        
        # mask 000: all p0  (i,j,k all 0)
        if dxj * (a0k - a0i) == dxk * (a0j - a0i):
            cnt += 1
        # mask 001: only k from p1  (i=0,j=0,k=1)
        if dxj * (a1k - a0i) == dxk * (a0j - a0i):
            cnt += 1
        # mask 010: only j from p1  (i=0,j=1,k=0)
        if dxj * (a0k - a0i) == dxk * (a1j - a0i):
            cnt += 1
        # mask 011: j,k from p1  (i=0,j=1,k=1)
        if dxj * (a1k - a0i) == dxk * (a1j - a0i):
            cnt += 1
        # mask 100: only i from p1  (i=1,j=0,k=0)
        if dxj * (a0k - a1i) == dxk * (a0j - a1i):
            cnt += 1
        # mask 101: i,k from p1  (i=1,j=0,k=1)
        if dxj * (a1k - a1i) == dxk * (a0j - a1i):
            cnt += 1
        # mask 110: i,j from p1  (i=1,j=1,k=0)
        if dxj * (a0k - a1i) == dxk * (a1j - a1i):
            cnt += 1
        # mask 111: all p1  (i=1,j=1,k=1)
        if dxj * (a1k - a1i) == dxk * (a1j - a1i):
            cnt += 1
    return cnt


# Cross-validation: independent grid-point verifier using the SAME bit convention
def verify_grid(p0, p1, n):
    """Grid-based NTIL verifier — independently confirms count_collisions.
    
    Builds all 2n grid points (x, y) and checks all triples for collinearity.
    This is NOT the same as count_collisions — it checks ALL triples of 
    the 2n points, including triples from the same row (degenerate).
    Returns True iff no 3 points are collinear.
    """
    pts = [(x, p0[x]) for x in range(n)] + [(x, p1[x]) for x in range(n)]
    for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(pts, 3):
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            return False
    return True


# ============================================================
# SA with full collision count (correct, O(n^3))
# ============================================================

def sa_rigorous(p0, p1, all_tps, n, n_iter=5000, n_restarts=8, 
                verbose=True):
    """Simulated annealing with FULL collision count at each step.
    
    Uses Metropolis acceptance: accepts worsening moves with 
    probability exp(-delta/T) where delta = new_cnt - old_cnt > 0.
    """
    cnt = count_collisions(p0, p1, n)
    best_p0, best_p1 = p0[:], p1[:]
    best_cnt = cnt
    swaps_done = 0
    
    for rst in range(n_restarts):
        T = 5.0
        alpha = (0.01 / T) ** (1.0 / n_iter)  # anneal T=5→0.01 over n_iter
        
        for it in range(n_iter):
            if cnt == 0:
                break
            
            tp_type, a, b = random.choice(all_tps)
            p0_save, p1_save = p0[a], p1[a]
            
            # Apply transposition
            if tp_type == 'p0':
                p0_new, p0_clone = p0[:], None
                p0_new[a], p0_new[b] = p0_new[b], p0_new[a]
                new_cnt = count_collisions(p0_new, p1, n)
            else:
                p1_new = p1[:]
                p1_new[a], p1_new[b] = p1_new[b], p1_new[a]
                new_cnt = count_collisions(p0, p1_new, n)
            
            delta = new_cnt - cnt
            
            # Accept if better, or with Metropolis probability if worse
            accept = delta <= 0 or random.random() < math.exp(-delta / T)
            
            if accept:
                if tp_type == 'p0':
                    p0[a], p0[b] = p0[b], p0[a]
                else:
                    p1[a], p1[b] = p1[b], p1[a]
                cnt = new_cnt
                swaps_done += 1
                
                if cnt < best_cnt:
                    best_p0 = p0[:]
                    best_p1 = p1[:]
                    best_cnt = cnt
            
            T *= alpha
        
        # Restart from best state
        if cnt > 0:
            p0[:] = best_p0[:]
            p1[:] = best_p1[:]
            cnt = best_cnt
        
        if verbose:
            print(f"    r{rst}: cnt={cnt} best={best_cnt} swaps={swaps_done}")
    
    return best_p0, best_p1, best_cnt


# ============================================================
# Main experiment
# ============================================================

def main():
    random.seed(42)
    results = []
    
    for n in [8, 16, 32]:
        k = n.bit_length() - 1
        p0_orig = bitrev(n, k)
        p1_orig = gray(n)
        
        # Verify both are permutations and distinct
        assert len(set(p0_orig)) == n, f"bitrev not perm for n={n}"
        assert len(set(p1_orig)) == n, f"gray not perm for n={n}"
        assert p0_orig != p1_orig, f"bitrev == gray for n={n}"
        
        base_cnt = count_collisions(p0_orig, p1_orig, n)
        
        tps0 = build_transpositions(p0_orig, n, k)
        tps1 = build_transpositions(p1_orig, n, k)
        all_tps = [('p0', a, b) for (a, b) in tps0] + \
                  [('p1', a, b) for (a, b) in tps1]
        
        n_orig = k * n // 2  # Q_k has k * 2^(k-1) edges
        print(f"\nn={n} k={k} base_collisions={base_cnt}")
        print(f"  transpositions: {len(tps0)} (p0) + {len(tps1)} (p1) = {len(all_tps)}")
        print(f"  theory Q_k edges: {n_orig} per perm")
        
        # Heavier settings for larger n
        n_iter = 3000 if n <= 16 else 1000
        n_restarts = 8 if n <= 16 else 4
        
        t0 = time.time()
        p0_final, p1_final, final_cnt = sa_rigorous(
            p0_orig, p1_orig, all_tps, n,
            n_iter=n_iter, n_restarts=n_restarts
        )
        elapsed = time.time() - t0
        
        # Cross-validate
        c1 = count_collisions(p0_final, p1_final, n)
        c2_ntil = verify_grid(p0_final, p1_final, n)
        consistent = (c1 == 0) == c2_ntil
        
        print(f"  final: base={base_cnt}→{final_cnt}")
        print(f"  verify: count_colls={c1} grid_ntil={c2_ntil} consistent={consistent}")
        print(f"  time: {elapsed:.1f}s")
        
        result = {
            'n': n, 'k': k,
            'base_collisions': base_cnt,
            'final_collisions': final_cnt,
            'verify_count': c1,
            'verify_grid': c2_ntil,
            'consistent': consistent,
            'time': elapsed,
        }
        results.append(result)
        
        if c2_ntil:
            sol = {
                'n': n, 'k': k,
                'p0': p0_final, 'p1': p1_final,
                'base_collisions': base_cnt,
                'method': 'bitrev+gray transposition SA',
                'time': elapsed,
            }
            fname = f'ntil_n{n}_sa.json'
            with open(fname, 'w') as f:
                json.dump(sol, f, indent=2)
            print(f"  ★★★ NTIL solution saved to {fname}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for r in results:
        status = "★ NTIL" if r['verify_grid'] else f"✗ {r['final_collisions']}c"
        cons = "✓" if r['consistent'] else "✗ MISMATCH"
        print(f"  n={r['n']}: {status} base={r['base_collisions']}→{r['final_collisions']} "
              f"consistent={cons} {r['time']:.1f}s")
    
    with open('padic_sa_rigorous_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == '__main__':
    main()
