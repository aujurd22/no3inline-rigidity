"""
定向 BFS 最后一公里求解器。
只搜索涉及当前坏三元组中行的操作，大幅减少分支因子。
"""
import itertools, random, time, json, os, sys
from collections import deque

def count_collinear(pi, sigma):
    n = len(pi)
    pts = [(i, pi[i]) for i in range(n)] + [(i, sigma[i]) for i in range(n)]
    cnt = 0
    bad = []
    for i, j, k in itertools.combinations(range(2*n), 3):
        x1,y1=pts[i]; x2,y2=pts[j]; x3,y3=pts[k]
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            cnt += 1
            bad.append((i,j,k))
    return cnt, bad

def verify_ntil(pi, sigma):
    n = len(pi)
    pts = [(i, pi[i]) for i in range(n)] + [(i, sigma[i]) for i in range(n)]
    if len(set(pts)) != 2*n:
        return False, "重复点"
    for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            return False, "共线"
    return True, "OK"

def affected_rows(bad_triples, n):
    """从坏三元组提取受影响的行索引"""
    rows = set()
    for trip in bad_triples:
        for p in trip:
            if p < n:  # π 点
                rows.add(('π', p))
            else:      # σ 点
                rows.add(('σ', p - n))
    return rows

def targeted_bfs(pi, sigma, max_depth=4, verbose=False):
    """
    定向 BFS：只操作涉及坏三元组行的 swap。
    """
    n = len(pi)
    initial_cost, initial_bad = count_collinear(pi, sigma)
    
    if initial_cost == 0:
        return True, [], pi, sigma
    
    # 获取涉及的行
    involved = affected_rows(initial_bad, n)
    involved_rows_pi = sorted(set(r for t, r in involved if t == 'π'))
    involved_rows_sigma = sorted(set(r for t, r in involved if t == 'σ'))
    
    if verbose:
        print(f"  定向 BFS: cost={initial_cost}, "
              f"π_rows={involved_rows_pi}, σ_rows={involved_rows_sigma}")
    
    start_key = (tuple(pi), tuple(sigma))
    visited = {start_key: 0}
    parent = {start_key: None}
    queue = deque([(start_key, 0)])
    found_key = None
    nodes_visited = 0
    
    while queue:
        key, depth = queue.popleft()
        p, s = list(key[0]), list(key[1])
        nodes_visited += 1
        
        c, bad = count_collinear(p, s)
        if c == 0:
            found_key = key
            break
        
        if depth >= max_depth:
            continue
        
        # 重新计算涉及的行（可能变化了）
        inv = affected_rows(bad, n)
        inv_pi = sorted(set(r for t, r in inv if t == 'π'))
        inv_sigma = sorted(set(r for t, r in inv if t == 'σ'))
        
        # 1. swap_σ: 涉及 σ 行与任意行的交换
        for ri in inv_sigma:
            for rj in range(n):
                if ri == rj:
                    continue
                s2 = s.copy()
                s2[ri], s2[rj] = s2[rj], s2[ri]
                c2, _ = count_collinear(p, s2)
                child_key = (tuple(p), tuple(s2))
                if child_key not in visited and c2 <= c + 1:
                    visited[child_key] = depth + 1
                    parent[child_key] = (key, f"swap_σ({ri},{rj})")
                    queue.append((child_key, depth + 1))
                    if c2 == 0:
                        found_key = child_key
                        break
            if found_key:
                break
        if found_key:
            break
        
        # 2. swap_π
        for ri in inv_pi:
            for rj in range(n):
                if ri == rj:
                    continue
                p2 = p.copy()
                p2[ri], p2[rj] = p2[rj], p2[ri]
                c2, _ = count_collinear(p2, s)
                child_key = (tuple(p2), tuple(s))
                if child_key not in visited and c2 <= c + 1:
                    visited[child_key] = depth + 1
                    parent[child_key] = (key, f"swap_π({ri},{rj})")
                    queue.append((child_key, depth + 1))
                    if c2 == 0:
                        found_key = child_key
                        break
            if found_key:
                break
        if found_key:
            break
        
        # 3. joint_swap: 涉及同索引的联合交换
        for ri in (set(inv_pi) & set(inv_sigma)):
            for rj in range(n):
                if ri == rj:
                    continue
                p2 = p.copy()
                s2 = s.copy()
                p2[ri], p2[rj] = p2[rj], p2[ri]
                s2[ri], s2[rj] = s2[rj], s2[ri]
                c2, _ = count_collinear(p2, s2)
                child_key = (tuple(p2), tuple(s2))
                if child_key not in visited and c2 <= c + 1:
                    visited[child_key] = depth + 1
                    parent[child_key] = (key, f"joint({ri},{rj})")
                    queue.append((child_key, depth + 1))
                    if c2 == 0:
                        found_key = child_key
                        break
            if found_key:
                break
    
    if verbose:
        print(f"  定向 BFS: visited={nodes_visited} nodes")
    
    if found_key:
        path = []
        key = found_key
        while parent[key] is not None:
            prev_key, op = parent[key]
            path.append(op)
            key = prev_key
        path.reverse()
        if verbose:
            print(f"  找到路径 (depth={len(path)}): {' → '.join(path)}")
        return True, path, list(found_key[0]), list(found_key[1])
    
    return False, [], pi, sigma


def solve_targeted(n, max_restarts=30, max_bfs_depth=5, seed=42, verbose=True):
    """贪心下降 + 定向 BFS"""
    random.seed(seed)
    
    pi = list(range(n))
    sigma = list(range(n))
    random.shuffle(pi)
    random.shuffle(sigma)
    
    cost, bad = count_collinear(pi, sigma)
    best_pi, best_sigma = pi.copy(), sigma.copy()
    best_cost = cost
    
    if verbose:
        print(f"[Targeted n={n}] init cost={cost}, max_bfs_depth={max_bfs_depth}")
    
    for restart in range(max_restarts):
        if cost == 0:
            break
        
        if verbose:
            print(f"\n--- Restart {restart+1} (cost={cost} best={best_cost}) ---")
        
        # Phase 1: 贪心下降
        steps = 0
        while True:
            prev_cost = cost
            best_delta = 0
            best_action = None
            
            # 穷举所有 swap_σ, swap_π, joint_swap
            for i in range(n):
                for j in range(i+1, n):
                    base = cost
                    
                    # swap_σ
                    s2 = sigma.copy()
                    s2[i], s2[j] = s2[j], s2[i]
                    c2, _ = count_collinear(pi, s2)
                    if base - c2 > best_delta:
                        best_delta = base - c2
                        best_action = ('σ', i, j, pi.copy(), s2)
                    
                    # swap_π
                    p2 = pi.copy()
                    p2[i], p2[j] = p2[j], p2[i]
                    c2, _ = count_collinear(p2, sigma)
                    if base - c2 > best_delta:
                        best_delta = base - c2
                        best_action = ('π', i, j, p2, sigma.copy())
                    
                    # joint
                    p2 = pi.copy()
                    s2 = sigma.copy()
                    p2[i], p2[j] = p2[j], p2[i]
                    s2[i], s2[j] = s2[j], s2[i]
                    c2, _ = count_collinear(p2, s2)
                    if base - c2 > best_delta:
                        best_delta = base - c2
                        best_action = ('joint', i, j, p2, s2)
                    
                    if best_delta > 3:
                        break  # early exit on big improvement
                if best_delta > 3:
                    break
            
            if best_delta > 0:
                atype, ai, aj, new_pi, new_sigma = best_action
                pi, sigma = new_pi, new_sigma
                cost -= best_delta
                steps += 1
                
                if cost < best_cost:
                    best_cost = cost
                    best_pi, best_sigma = pi.copy(), sigma.copy()
                
                if verbose and steps % 3 == 0:
                    print(f"  [{steps}] cost={cost} Δ={best_delta} op={atype}")
                
                if cost == 0:
                    print(f"★★★★★ 贪心找到解! steps={steps}")
                    return True, pi, sigma
            else:
                break
        
        if verbose:
            print(f"  贪心卡住: cost={cost}, steps={steps}")
        
        # Phase 2: 定向 BFS
        if 1 <= cost <= 5:
            t0 = time.time()
            found, path, final_pi, final_sigma = targeted_bfs(
                pi, sigma, max_depth=max_bfs_depth, verbose=verbose)
            elapsed = time.time() - t0
            
            if found:
                print(f"★★★★★ 定向 BFS 找到解! path_len={len(path)} ({elapsed:.1f}s)")
                return True, final_pi, final_sigma
            
            if verbose:
                print(f"  定向 BFS 未找到 ({elapsed:.1f}s)")
        
        # Phase 3: 扰动
        best_jumped_cost = cost
        best_jumped = (pi, sigma)
        
        for strength in [0.15, 0.20, 0.25, 0.30]:
            for _ in range(3):
                k = max(3, int(n * strength))
                indices = random.sample(range(n), k)
                p2 = pi.copy()
                s2 = sigma.copy()
                vals_pi = [p2[i] for i in indices]
                vals_sigma = [s2[i] for i in indices]
                random.shuffle(vals_pi)
                random.shuffle(vals_sigma)
                for idx, i in enumerate(indices):
                    p2[i] = vals_pi[idx]
                    s2[i] = vals_sigma[idx]
                
                # 微贪心
                for _ in range(5):
                    best_d = 0
                    best_a = None
                    for i in range(n):
                        for j in range(i+1, n):
                            s3 = s2.copy()
                            s3[i], s3[j] = s3[j], s3[i]
                            c3, _ = count_collinear(p2, s3)
                            d = cost - c3
                            if d > best_d:
                                best_d = d
                                best_a = ('σ', i, j)
                            p3 = p2.copy()
                            p3[i], p3[j] = p3[j], p3[i]
                            c3, _ = count_collinear(p3, s2)
                            d = cost - c3
                            if d > best_d:
                                best_d = d
                                best_a = ('π', i, j)
                    if best_d > 0:
                        if best_a[0] == 'σ':
                            s2[best_a[1]], s2[best_a[2]] = s2[best_a[2]], s2[best_a[1]]
                        else:
                            p2[best_a[1]], p2[best_a[2]] = p2[best_a[2]], p2[best_a[1]]
                    else:
                        break
                
                c2, _ = count_collinear(p2, s2)
                if c2 < best_jumped_cost:
                    best_jumped_cost = c2
                    best_jumped = (p2, s2)
        
        if best_jumped_cost < cost:
            pi, sigma = best_jumped
            cost = best_jumped_cost
            if verbose:
                print(f"  扰动: → cost={cost}")
            if cost == 0:
                return True, pi, sigma
        else:
            if verbose:
                print(f"  无改善，全局重启")
            pi = list(range(n))
            sigma = list(range(n))
            random.shuffle(pi)
            random.shuffle(sigma)
            cost, _ = count_collinear(pi, sigma)
    
    return best_cost == 0, best_pi, best_sigma


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int, nargs='?', default=12)
    ap.add_argument('--batch', type=str, default=None)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--restarts', type=int, default=30)
    ap.add_argument('--bfs-depth', type=int, default=5)
    ap.add_argument('--outdir', type=str, default='results')
    args = ap.parse_args()
    
    if args.batch:
        ns = [int(x) for x in args.batch.split(',')]
        all_results = {}
        for n in ns:
            print(f"\n{'='*64}")
            print(f"定向 BFS 求解器: n={n}")
            print(f"{'='*64}")
            t0 = time.time()
            found, final_pi, final_sigma = solve_targeted(
                n, max_restarts=args.restarts, max_bfs_depth=args.bfs_depth,
                seed=args.seed, verbose=True)
            elapsed = time.time() - t0
            cost, _ = count_collinear(final_pi, final_sigma)
            ok, msg = verify_ntil(final_pi, final_sigma) if found else (False, f"cost={cost}")
            all_results[str(n)] = {
                'found': found, 'cost': cost, 'verified': ok, 'msg': msg,
                'time': elapsed,
                'pi': final_pi if found else None,
                'sigma': final_sigma if found else None
            }
            print(f"  n={n}: found={found} cost={cost} verified={ok} ({msg}) time={elapsed:.1f}s")
        
        os.makedirs(args.outdir, exist_ok=True)
        outpath = os.path.join(args.outdir, f'targeted_bfs_batch.json')
        with open(outpath, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n已保存: {outpath}")
    else:
        n = args.n
        found, final_pi, final_sigma = solve_targeted(
            n, max_restarts=args.restarts, max_bfs_depth=args.bfs_depth,
            seed=args.seed, verbose=True)
        cost, _ = count_collinear(final_pi, final_sigma)
        ok, msg = verify_ntil(final_pi, final_sigma) if found else (False, f"cost={cost}")
        print(f"\n最终: found={found} cost={cost} verified={ok} ({msg})")
        if found:
            print(f"π = {final_pi}")
            print(f"σ = {final_sigma}")
            outpath = os.path.join(args.outdir, f'ntil_n{n}_targeted.json')
            os.makedirs(args.outdir, exist_ok=True)
            with open(outpath, 'w') as f:
                json.dump({'n': n, 'pi': final_pi, 'sigma': final_sigma, 'verified': ok}, f, indent=2)
            print(f"已保存: {outpath}")

if __name__ == '__main__':
    main()
