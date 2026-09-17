"""
numpy 加速的贪心 NTIL 求解器。
将共线性检查向量化，比纯 Python 快 10-50 倍。
"""
import sys, itertools, random, math, time, json, os
import numpy as np
from collections import defaultdict

# ============ numpy 加速的成本函数 ============

def build_triple_idx(n):
    """预计算所有 C(2n,3) 三元组的索引 (用于 numpy 向量化)"""
    npt = 2 * n
    triples = []
    for i, j, k in itertools.combinations(range(npt), 3):
        triples.append([i, j, k])
    return np.array(triples, dtype=np.int32)  # shape (n_triples, 3)

def cost_from_pts(pts, triple_idx):
    """
    给定点数组 pts[npt, 2]，计算共线三元组数。
    纯 numpy 向量化。
    """
    i = triple_idx[:, 0]
    j = triple_idx[:, 1]
    k = triple_idx[:, 2]
    
    x1, y1 = pts[i, 0], pts[i, 1]
    x2, y2 = pts[j, 0], pts[j, 1]
    x3, y3 = pts[k, 0], pts[k, 1]
    
    # 面积 = 0 ⇔ 共线
    cross = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    return int(np.sum(cross == 0))

def pts_from_perms(pi, sigma):
    """从双排列构造点数组"""
    n = len(pi)
    pts = np.zeros((2*n, 2), dtype=np.int32)
    pts[:n, 0] = np.arange(n)
    pts[:n, 1] = np.array(pi)
    pts[n:, 0] = np.arange(n)
    pts[n:, 1] = np.array(sigma)
    return pts

def cost_delta(pi_new, sigma_new, triple_idx, cost_before):
    """计算新排列的 △cost = new_cost - cost_before"""
    pts = pts_from_perms(pi_new, sigma_new)
    new_cost = cost_from_pts(pts, triple_idx)
    return new_cost - cost_before

# ============ 操作生成器（向量化） ============

def try_all_swap_sigma(pi, sigma, triple_idx, cost_base):
    """尝试所有 σ 交换，返回最佳 (delta, i, j)"""
    n = len(pi)
    best_delta = 0
    best_ij = None
    pi_arr = np.array(pi)
    sigma_arr = np.array(sigma)
    
    for i in range(n):
        for j in range(i+1, n):
            sigma_new = sigma_arr.copy()
            sigma_new[i], sigma_new[j] = sigma_new[j], sigma_new[i]
            pts = pts_from_perms(pi_arr, sigma_new)
            new_cost = cost_from_pts(pts, triple_idx)
            delta = cost_base - new_cost  # positive = improvement
            if delta > best_delta:
                best_delta = delta
                best_ij = (i, j)
                if delta > 5:  # big improvement, stop early
                    return best_delta, best_ij
    return best_delta, best_ij

def try_all_swap_pi(pi, sigma, triple_idx, cost_base):
    n = len(pi)
    best_delta = 0
    best_ij = None
    pi_arr = np.array(pi)
    sigma_arr = np.array(sigma)
    
    for i in range(n):
        for j in range(i+1, n):
            pi_new = pi_arr.copy()
            pi_new[i], pi_new[j] = pi_new[j], pi_new[i]
            pts = pts_from_perms(pi_new, sigma_arr)
            new_cost = cost_from_pts(pts, triple_idx)
            delta = cost_base - new_cost
            if delta > best_delta:
                best_delta = delta
                best_ij = (i, j)
                if delta > 5:
                    return best_delta, best_ij
    return best_delta, best_ij

def try_all_joint_swap(pi, sigma, triple_idx, cost_base):
    n = len(pi)
    best_delta = 0
    best_ij = None
    pi_arr = np.array(pi)
    sigma_arr = np.array(sigma)
    
    for i in range(n):
        for j in range(i+1, n):
            pi_new = pi_arr.copy()
            sigma_new = sigma_arr.copy()
            pi_new[i], pi_new[j] = pi_new[j], pi_new[i]
            sigma_new[i], sigma_new[j] = sigma_new[j], sigma_new[i]
            pts = pts_from_perms(pi_new, sigma_new)
            new_cost = cost_from_pts(pts, triple_idx)
            delta = cost_base - new_cost
            if delta > best_delta:
                best_delta = delta
                best_ij = (i, j)
                if delta > 5:
                    return best_delta, best_ij
    return best_delta, best_ij

def try_sampled_cycle3(pi, sigma, triple_idx, cost_base, n_samples=100):
    """抽样三循环操作"""
    n = len(pi)
    best_delta = 0
    best_ijk = None
    pi_arr = np.array(pi)
    sigma_arr = np.array(sigma)
    
    all_trips = list(itertools.combinations(range(n), 3))
    random.shuffle(all_trips)
    
    for i, j, k in all_trips[:n_samples]:
        pi_new = pi_arr.copy()
        pi_new[i], pi_new[j], pi_new[k] = pi_new[j], pi_new[k], pi_new[i]
        pts = pts_from_perms(pi_new, sigma_arr)
        new_cost = cost_from_pts(pts, triple_idx)
        delta = cost_base - new_cost
        if delta > best_delta:
            best_delta = delta
            best_ijk = (i, j, k)
            if delta > 5:
                return best_delta, best_ijk
    
    return best_delta, best_ijk

# ============ 贪心求解主循环 ============

def random_jump(pi, sigma, strength=0.2):
    """随机扰动"""
    n = len(pi)
    k = max(3, int(n * strength))
    pi = pi.copy()
    sigma = sigma.copy()
    indices = random.sample(range(n), k)
    vals_pi = [pi[i] for i in indices]
    vals_sigma = [sigma[i] for i in indices]
    random.shuffle(vals_pi)
    random.shuffle(vals_sigma)
    for idx, i in enumerate(indices):
        pi[i] = vals_pi[idx]
        sigma[i] = vals_sigma[idx]
    return pi, sigma

def solve_numpy(n, max_restarts=20, max_jumps=10, seed=42, verbose=True):
    """numpy 加速贪心求解器"""
    random.seed(seed)
    np.random.seed(seed)
    
    # 预计算三元组索引
    triple_idx = build_triple_idx(n)
    
    # 初始化
    pi = list(range(n))
    sigma = list(range(n))
    random.shuffle(pi)
    random.shuffle(sigma)
    
    pts = pts_from_perms(pi, sigma)
    cost = cost_from_pts(pts, triple_idx)
    best_pi, best_sigma = pi.copy(), sigma.copy()
    best_cost = cost
    
    if verbose:
        print(f"[numpy n={n}] random init, cost={cost}")
    
    for restart in range(max_restarts):
        if cost == 0:
            break
            
        if verbose:
            print(f"\n--- Restart {restart+1}: greedy descent (cost={cost}) ---")
        
        # Phase 1: 贪心下降
        steps = 0
        while True:
            prev_cost = cost
            
            # 尝试各操作类型
            ops = [
                ("swap_σ", try_all_swap_sigma),
                ("swap_π", try_all_swap_pi),
                ("joint", try_all_joint_swap),
            ]
            
            for op_name, op_func in ops:
                delta, params = op_func(pi, sigma, triple_idx, cost)
                if delta > 0:
                    if op_name == "swap_σ":
                        i, j = params
                        sigma[i], sigma[j] = sigma[j], sigma[i]
                    elif op_name == "swap_π":
                        i, j = params
                        pi[i], pi[j] = pi[j], pi[i]
                    elif op_name == "joint":
                        i, j = params
                        pi[i], pi[j] = pi[j], pi[i]
                        sigma[i], sigma[j] = sigma[j], sigma[i]
                    
                    cost -= delta
                    steps += 1
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_pi, best_sigma = pi.copy(), sigma.copy()
                    
                    if verbose and steps % 10 == 0:
                        print(f"  [{steps}] cost={cost} best={best_cost} "
                              f"op={op_name} Δ={delta}")
                    
                    if cost == 0:
                        print(f"\n★★★★★ 找到 NTIL 解! restart={restart+1} steps={steps}")
                        return True, best_pi, best_sigma, best_cost
                    
                    break  # restart operation loop with new state
            
            if cost == prev_cost:
                break  # local minimum
        
        if verbose:
            print(f"  局部极小: cost={cost}, best={best_cost}, steps={steps}")
        
        # Phase 2: 扰动逃逸
        improved = False
        for jump_idx in range(max_jumps):
            strength = 0.15 + 0.05 * (jump_idx % 4)
            best_jumped_cost = float('inf')
            best_jumped = None
            
            for _ in range(5):
                p2, s2 = random_jump(pi, sigma, strength)
                # 微贪心（只做 swap，不做 cycle3）
                for _ in range(3):
                    improved_inner = False
                    for op_name, op_func in ops:
                        delta, params = op_func(p2, s2, triple_idx, 
                                                cost_from_pts(pts_from_perms(p2, s2), triple_idx))
                        if delta > 0:
                            if op_name == "swap_σ":
                                i, j = params
                                s2[i], s2[j] = s2[j], s2[i]
                            elif op_name == "swap_π":
                                i, j = params
                                p2[i], p2[j] = p2[j], p2[i]
                            elif op_name == "joint":
                                i, j = params
                                p2[i], p2[j] = p2[j], p2[i]
                                s2[i], s2[j] = s2[j], s2[i]
                            improved_inner = True
                            break
                    if not improved_inner:
                        break
                
                c2 = cost_from_pts(pts_from_perms(p2, s2), triple_idx)
                if c2 < best_jumped_cost:
                    best_jumped_cost = c2
                    best_jumped = (p2, s2)
            
            if best_jumped_cost < cost:
                pi, sigma = best_jumped
                cost = best_jumped_cost
                if verbose:
                    print(f"  jump {jump_idx+1}: → cost={cost}")
                improved = True
                if cost == 0:
                    return True, pi, sigma, 0
                break
        
        if not improved:
            if verbose:
                print(f"  无改善，全局重启...")
            pi = list(range(n))
            sigma = list(range(n))
            random.shuffle(pi)
            random.shuffle(sigma)
            pts = pts_from_perms(pi, sigma)
            cost = cost_from_pts(pts, triple_idx)
    
    return best_cost == 0, best_pi, best_sigma, best_cost


def verify_ntil(pi, sigma):
    """验证 NTIL"""
    n = len(pi)
    pts = [(i, pi[i]) for i in range(n)] + [(i, sigma[i]) for i in range(n)]
    if len(set(pts)) != 2*n:
        return False, "重复点"
    for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
        if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
            return False, f"共线: {(x1,y1)},{(x2,y2)},{(x3,y3)}"
    return True, "OK"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int, nargs='?', default=12)
    ap.add_argument('--batch', type=str, default=None)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--restarts', type=int, default=20)
    ap.add_argument('--jumps', type=int, default=10)
    ap.add_argument('--outdir', type=str, default='results')
    args = ap.parse_args()
    
    if args.batch:
        ns = [int(x) for x in args.batch.split(',')]
        all_results = {}
        for n in ns:
            print(f"\n{'='*64}")
            print(f"numpy gready: n={n}")
            print(f"{'='*64}")
            t0 = time.time()
            found, pi, sigma, cost = solve_numpy(n, max_restarts=args.restarts,
                                                  max_jumps=args.jumps, seed=args.seed)
            elapsed = time.time() - t0
            ok, msg = verify_ntil(pi, sigma) if found else (False, f"cost={cost}")
            all_results[str(n)] = {
                'found': found, 'cost': cost, 'verified': ok, 'msg': msg,
                'time': elapsed, 'pi': pi if found else None, 'sigma': sigma if found else None
            }
            print(f"  n={n}: found={found} cost={cost} verified={ok} ({msg}) time={elapsed:.1f}s")
        
        os.makedirs(args.outdir, exist_ok=True)
        outpath = os.path.join(args.outdir, f'greedy_numpy_batch.json')
        with open(outpath, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n已保存: {outpath}")
    else:
        n = args.n
        found, pi, sigma, cost = solve_numpy(n, max_restarts=args.restarts,
                                              max_jumps=args.jumps, seed=args.seed)
        ok, msg = verify_ntil(pi, sigma) if found else (False, f"cost={cost}")
        print(f"\n最终: found={found} cost={cost} verified={ok} ({msg})")
        if found:
            print(f"π = {pi}")
            print(f"σ = {sigma}")
            outpath = os.path.join(args.outdir, f'ntil_n{n}_numpy.json')
            os.makedirs(args.outdir, exist_ok=True)
            with open(outpath, 'w') as f:
                json.dump({'n': n, 'pi': pi, 'sigma': sigma, 'verified': ok}, f, indent=2)
            print(f"已保存: {outpath}")

if __name__ == '__main__':
    main()
