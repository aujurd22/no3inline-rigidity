"""
"最后一公里" BFS 求解器：当贪心下降卡在 cost≤3 时，
用有界广度优先搜索找到到 0 的路径。
"""
import sys, itertools, random, time, json, os

def count_collinear(pi, sigma):
    """计数共线三元组"""
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

def bfs_last_mile(pi, sigma, max_depth=3, verbose=False):
    """
    从 cost≤3 状态出发，BFS 搜索到 cost=0 的路径。
    操作：swap_σ, swap_π, joint_swap。
    max_depth: 最大搜索深度（操作步数）
    """
    n = len(pi)
    initial_cost, _ = count_collinear(pi, sigma)
    
    if initial_cost == 0:
        return True, [], pi, sigma
    
    if initial_cost > 5:  # 太远，不搜
        return False, [], pi, sigma
    
    # BFS
    from collections import deque
    
    start_key = (tuple(pi), tuple(sigma))
    visited = {start_key: 0}
    parent = {start_key: None}
    queue = deque([(start_key, 0)])
    found_key = None
    
    while queue:
        key, depth = queue.popleft()
        p, s = list(key[0]), list(key[1])
        current_cost, _ = count_collinear(p, s)
        
        if current_cost == 0:
            found_key = key
            break
        
        if depth >= max_depth:
            continue
        
        # 生成所有子节点
        # 1. swap_σ
        for i in range(n):
            for j in range(i+1, n):
                s2 = s.copy()
                s2[i], s2[j] = s2[j], s2[i]
                c2, _ = count_collinear(p, s2)
                child_key = (tuple(p), tuple(s2))
                if child_key not in visited and c2 <= current_cost + 1:
                    visited[child_key] = depth + 1
                    parent[child_key] = (key, f"swap_σ({i},{j})")
                    queue.append((child_key, depth + 1))
                    if c2 == 0:
                        found_key = child_key
                        break
            if found_key:
                break
        if found_key:
            break
        
        if depth + 1 >= max_depth:
            continue
        
        # 2. swap_π
        for i in range(n):
            for j in range(i+1, n):
                p2 = p.copy()
                p2[i], p2[j] = p2[j], p2[i]
                c2, _ = count_collinear(p2, s)
                child_key = (tuple(p2), tuple(s))
                if child_key not in visited and c2 <= current_cost + 1:
                    visited[child_key] = depth + 1
                    parent[child_key] = (key, f"swap_π({i},{j})")
                    queue.append((child_key, depth + 1))
                    if c2 == 0:
                        found_key = child_key
                        break
            if found_key:
                break
        if found_key:
            break
        
        if depth + 1 >= max_depth:
            continue
        
        # 3. 联合
        for i in range(n):
            for j in range(i+1, n):
                p2 = p.copy()
                s2 = s.copy()
                p2[i], p2[j] = p2[j], p2[i]
                s2[i], s2[j] = s2[j], s2[i]
                c2, _ = count_collinear(p2, s2)
                child_key = (tuple(p2), tuple(s2))
                if child_key not in visited and c2 <= current_cost + 1:
                    visited[child_key] = depth + 1
                    parent[child_key] = (key, f"joint({i},{j})")
                    queue.append((child_key, depth + 1))
                    if c2 == 0:
                        found_key = child_key
                        break
            if found_key:
                break
    
    if found_key:
        # 回溯路径
        path = []
        key = found_key
        while parent[key] is not None:
            prev_key, op = parent[key]
            path.append(op)
            key = prev_key
        path.reverse()
        if verbose:
            print(f"  BFS 找到路径 (depth={len(path)}): {' → '.join(path)}")
        return True, path, list(found_key[0]), list(found_key[1])
    
    return False, [], pi, sigma


def greedy_descent_bfs(pi, sigma, max_restarts=30, max_bfs_depth=4, seed=42, verbose=True):
    """
    贪心下降 + BFS 最后一公里。
    """
    random.seed(seed)
    n = len(pi)
    
    cost, bad = count_collinear(pi, sigma)
    best_pi, best_sigma = pi.copy(), sigma.copy()
    best_cost = cost
    
    if verbose:
        print(f"[BFS-LM n={n}] init cost={cost}, max_bfs_depth={max_bfs_depth}")
    
    # 操作全集生成
    def all_ops(p, s):
        """生成所有单步操作及其效果"""
        results = []
        base_cost, _ = count_collinear(p, s)
        
        for i in range(n):
            for j in range(i+1, n):
                # swap_σ
                s2 = s.copy()
                s2[i], s2[j] = s2[j], s2[i]
                c2, _ = count_collinear(p, s2)
                delta = base_cost - c2
                results.append((delta, "swap_σ", (i,j), p.copy(), s2))
                
                # swap_π
                p2 = p.copy()
                p2[i], p2[j] = p2[j], p2[i]
                c2, _ = count_collinear(p2, s)
                delta = base_cost - c2
                results.append((delta, "swap_π", (i,j), p2, s.copy()))
                
                # joint
                p2 = p.copy()
                s2 = s.copy()
                p2[i], p2[j] = p2[j], p2[i]
                s2[i], s2[j] = s2[j], s2[i]
                c2, _ = count_collinear(p2, s2)
                delta = base_cost - c2
                results.append((delta, "joint", (i,j), p2, s2))
        
        return sorted(results, key=lambda x: -x[0])  # 改善最大的在前
    
    for restart in range(max_restarts):
        if cost == 0:
            break
        
        if verbose:
            print(f"\n--- Restart {restart+1} (cost={cost} best={best_cost}) ---")
        
        # Phase 1: 贪心下降
        steps = 0
        while True:
            prev_cost = cost
            ops = all_ops(pi, sigma)
            best_delta, best_op, best_params, best_pnew, best_snew = ops[0]
            
            if best_delta > 0:
                pi, sigma = best_pnew, best_snew
                cost -= best_delta
                steps += 1
                
                if cost < best_cost:
                    best_cost = cost
                    best_pi, best_sigma = pi.copy(), sigma.copy()
                
                if verbose and steps % 5 == 0:
                    print(f"  [{steps}] cost={cost} Δ={best_delta} op={best_op}")
                
                if cost == 0:
                    print(f"★★★★★ 贪心找到解! steps={steps}")
                    return True, pi, sigma
            else:
                break  # 局部极小
        
        if verbose:
            print(f"  贪心卡住: cost={cost}, best={best_cost}, steps={steps}")
        
        # Phase 2: BFS 最后一公里
        if 1 <= cost <= 3:
            if verbose:
                print(f"  启动 BFS (max_depth={max_bfs_depth})...")
            t0 = time.time()
            found, path, final_pi, final_sigma = bfs_last_mile(
                pi, sigma, max_depth=max_bfs_depth, verbose=verbose)
            elapsed = time.time() - t0
            if verbose:
                print(f"  BFS: found={found} ({elapsed:.1f}s)")
            
            if found:
                print(f"★★★★★ BFS 找到解! path_len={len(path)}")
                return True, final_pi, final_sigma
        
        # Phase 3: 随机扰动
        best_jumped_cost = cost
        best_jumped = (pi, sigma)
        
        for strength in [0.15, 0.20, 0.25, 0.30, 0.35]:
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
                    ops = all_ops(p2, s2)
                    if ops[0][0] > 0:
                        p2, s2 = ops[0][3], ops[0][4]
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
    ap.add_argument('--bfs-depth', type=int, default=4)
    ap.add_argument('--outdir', type=str, default='results')
    args = ap.parse_args()
    
    if args.batch:
        ns = [int(x) for x in args.batch.split(',')]
        all_results = {}
        for n in ns:
            print(f"\n{'='*64}")
            print(f"BFS-LM 求解器: n={n}")
            print(f"{'='*64}")
            t0 = time.time()
            
            pi = list(range(n))
            sigma = list(range(n))
            random.seed(args.seed)
            random.shuffle(pi)
            random.shuffle(sigma)
            
            found, final_pi, final_sigma = greedy_descent_bfs(
                pi, sigma, max_restarts=args.restarts,
                max_bfs_depth=args.bfs_depth, seed=args.seed, verbose=True)
            
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
        outpath = os.path.join(args.outdir, f'bfs_lm_batch.json')
        with open(outpath, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n已保存: {outpath}")
    else:
        n = args.n
        pi = list(range(n))
        sigma = list(range(n))
        random.seed(args.seed)
        random.shuffle(pi)
        random.shuffle(sigma)
        
        found, final_pi, final_sigma = greedy_descent_bfs(
            pi, sigma, max_restarts=args.restarts,
            max_bfs_depth=args.bfs_depth, seed=args.seed, verbose=True)
        
        cost, _ = count_collinear(final_pi, final_sigma)
        ok, msg = verify_ntil(final_pi, final_sigma) if found else (False, f"cost={cost}")
        print(f"\n最终: found={found} cost={cost} verified={ok} ({msg})")
        if found:
            print(f"π = {final_pi}")
            print(f"σ = {final_sigma}")
            outpath = os.path.join(args.outdir, f'ntil_n{n}_bfslm.json')
            os.makedirs(args.outdir, exist_ok=True)
            with open(outpath, 'w') as f:
                json.dump({'n': n, 'pi': final_pi, 'sigma': final_sigma, 'verified': ok}, f, indent=2)
            print(f"已保存: {outpath}")

if __name__ == '__main__':
    main()
