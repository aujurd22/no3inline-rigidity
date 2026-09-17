"""Fast N=74 involution SA — only checks triples involving swapped rows."""
import itertools, random, time, json

def count_8type(pi, N_val, rows=None):
    """Count 8-type collisions. If rows specified, only count triples involving them."""
    cnt = 0
    for i, j, k in itertools.combinations(range(N_val), 3):
        if rows is not None and i not in rows and j not in rows and k not in rows:
            continue
        yi, yj, yk = pi[i], pi[j], pi[k]
        yis, yjs, yks = N_val-1-yi, N_val-1-yj, N_val-1-yk
        if (j-i)*(yk-yi) == (k-i)*(yj-yi): cnt += 1       # PPP
        if (j-i)*(yks-yi) == (k-i)*(yj-yi): cnt += 1       # PPS_k
        if (j-i)*(yk-yi) == (k-i)*(yjs-yi): cnt += 1       # PPS_j
        if (j-i)*(yk-yis) == (k-i)*(yj-yis): cnt += 1      # PPS_i
        if (j-i)*(yks-yis) == (k-i)*(yj-yis): cnt += 1     # PSS_i
        if (j-i)*(yks-yi) == (k-i)*(yjs-yi): cnt += 1      # PSS_j
        if (j-i)*(yk-yis) == (k-i)*(yj-yis): cnt += 1      # PSS_k
        if (j-i)*(yks-yis) == (k-i)*(yjs-yis): cnt += 1    # SSS
    return cnt


def sa(N_val, seed, max_iter=30000):
    random.seed(seed)
    pi = list(range(N_val)); random.shuffle(pi)
    cnt = count_8type(pi, N_val)
    
    best_pi, best_cnt = pi[:], cnt
    T, alpha = 2.0, 0.998
    swaps, rsts, last_rebuild = 0, 0, 0
    t0 = time.time()
    
    for it in range(max_iter):
        if cnt == 0: break
        i, j = random.sample(range(N_val), 2)
        
        # old collisions involving i or j
        old = count_8type(pi, N_val, {i, j})
        pi[i], pi[j] = pi[j], pi[i]
        new = count_8type(pi, N_val, {i, j})
        
        delta = new - old
        if delta <= 0 or random.random() < 2.71828 ** (-delta / max(T, 0.01)):
            cnt = cnt + delta
            swaps += 1
            if cnt < best_cnt:
                best_pi, best_cnt = pi[:], cnt
        else:
            pi[i], pi[j] = pi[j], pi[i]  # reject
        
        if it - last_rebuild >= 2000:
            cnt = count_8type(pi, N_val)  # full rebuild
            last_rebuild = it
        
        T *= alpha
        if it % 8000 == 7999:
            T = 2.0; rsts += 1
            if best_cnt < cnt:
                pi[:], cnt = best_pi[:], best_cnt
    
    return best_pi, best_cnt, swaps, rsts, time.time() - t0


if __name__ == "__main__":
    N = 74
    print(f"=== N={N} pure involution SA ===")
    results = []
    
    for trial in range(5):
        seed = 42 + trial * 1000
        best_pi, best_cnt, swaps, rsts, elapsed = sa(N, seed)
        status = "CONVERGED" if best_cnt == 0 else f"best={best_cnt}"
        print(f"  t{trial}: {status} swaps={swaps} rsts={rsts} ({elapsed:.1f}s)")
        results.append({"trial": trial, "best_cnt": best_cnt, "swaps": swaps,
                        "restarts": rsts, "time": elapsed})
        
        if best_cnt == 0:
            # Full NTIL verification
            pts = [(x, best_pi[x]) for x in range(N)] + \
                  [(x, N-1-best_pi[x]) for x in range(N)]
            # Check grid bounds
            in_bounds = all(0 <= x < N and 0 <= y < N for (x, y) in pts)
            row_ok = all(sum(1 for p in pts if p[0]==x) == 2 for x in range(N))
            col_ok = all(sum(1 for p in pts if p[1]==y) == 2 for y in range(N))
            collinear = sum(1 for p1,p2,p3 in itertools.combinations(pts,3)
                          if (p2[0]-p1[0])*(p3[1]-p1[1]) == (p3[0]-p1[0])*(p2[1]-p1[1]))
            
            print(f"    方格内: {in_bounds} 行列=2: {row_ok}/{col_ok} 共线: {collinear}")
            if in_bounds and row_ok and col_ok and collinear == 0:
                json.dump({"N": N, "pi": best_pi, "type": "involution", "trial": trial},
                         open("ntil_solution_n74_pure.json", "w"), indent=2)
                print(f"    ★★★ N=74 纯对合 NTIL 解已保存！")
    
    json.dump(results, open("pure_sa_n74_results.json", "w"), indent=2)
    solved = sum(1 for r in results if r['best_cnt'] == 0)
    print(f"\n收敛: {solved}/{len(results)}")
