"""
贪心下降 + 扰动逃逸 NTIL 求解器。
每步穷举所有操作选最优 Δ，无改善时随机扰动，重复至收敛或重启。

核心操作（全穷举，不采样）：
  1. swap_σ(i,j): 交换 σ[i]↔σ[j]
  2. swap_π(i,j): 交换 π[i]↔π[j]
  3. joint_swap(i,j): 同时交换 π 和 σ
  4. msb_pair(i): p-adic MSB 配对交换（2^k 型 n）
  5. cycle3_π(i,j,k): π 的三循环
"""
import sys, itertools, random, math, time, json, os
from collections import defaultdict

# ============ 核心引擎 ============

class NTILState:
    """双排列状态 + 全量代价（简单可靠）"""
    
    def __init__(self, n, pi, sigma):
        self.n = n
        self.pi = pi
        self.sigma = sigma
        self.bad = set()  # 坏三元组 (p1,p2,p3), p1<p2<p3
        self._rebuild()
    
    def _rebuild(self):
        """全量重建坏三元组集合"""
        self.bad.clear()
        npt = 2 * self.n
        pts = []
        for i in range(self.n):
            pts.append((i, self.pi[i]))
        for i in range(self.n):
            pts.append((i, self.sigma[i]))
        for i, j, k in itertools.combinations(range(npt), 3):
            x1,y1=pts[i]; x2,y2=pts[j]; x3,y3=pts[k]
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                self.bad.add((i,j,k))
    
    def cost(self):
        return len(self.bad)
    
    def copy(self):
        s = NTILState(self.n, self.pi.copy(), self.sigma.copy())
        return s
    
    def verify(self):
        """完整验证"""
        pts = [(i, self.pi[i]) for i in range(self.n)] + \
              [(i, self.sigma[i]) for i in range(self.n)]
        if len(set(pts)) != 2*self.n:
            return False, "重复点"
        for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                return False, f"共线: {(x1,y1)},{(x2,y2)},{(x3,y3)}"
        return True, "OK"

# ============ 操作生成器 ============

def all_swap_sigma(state):
    """所有 σ 交换"""
    n = state.n
    moves = []
    for i in range(n):
        for j in range(i+1, n):
            s = state.copy()
            s.sigma[i], s.sigma[j] = s.sigma[j], s.sigma[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"swap_σ({i},{j})"))
    return moves

def all_swap_pi(state):
    n = state.n
    moves = []
    for i in range(n):
        for j in range(i+1, n):
            s = state.copy()
            s.pi[i], s.pi[j] = s.pi[j], s.pi[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"swap_π({i},{j})"))
    return moves

def all_joint_swap(state):
    n = state.n
    moves = []
    for i in range(n):
        for j in range(i+1, n):
            s = state.copy()
            s.pi[i], s.pi[j] = s.pi[j], s.pi[i]
            s.sigma[i], s.sigma[j] = s.sigma[j], s.sigma[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"joint({i},{j})"))
    return moves

def all_msb_pair(state):
    """p-adic MSB 对交换"""
    n = state.n
    if (n & (n-1)) != 0:
        return []
    k = int(math.log2(n))
    msb = 1 << (k-1)
    moves = []
    for i in range(n):
        j = i ^ msb
        if j <= i or j >= n:
            continue
        s = state.copy()
        s.pi[i], s.pi[j] = s.pi[j], s.pi[i]
        s.sigma[i], s.sigma[j] = s.sigma[j], s.sigma[i]
        s._rebuild()
        moves.append((s, state.cost() - s.cost(), f"msb({i},{j})"))
    return moves

def all_cycle3_pi(state):
    """三循环 π[i]→π[j]→π[k]→π[i]（抽样，全量太大）"""
    n = state.n
    if n <= 10:
        # 全量
        moves = []
        for i, j, k in itertools.combinations(range(n), 3):
            s = state.copy()
            s.pi[i], s.pi[j], s.pi[k] = s.pi[j], s.pi[k], s.pi[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"c3π({i},{j},{k})"))
        return moves
    else:
        # 抽样 200 个
        moves = []
        rng = random.Random()
        all_trips = list(itertools.combinations(range(n), 3))
        rng.shuffle(all_trips)
        for i, j, k in all_trips[:200]:
            s = state.copy()
            s.pi[i], s.pi[j], s.pi[k] = s.pi[j], s.pi[k], s.pi[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"c3π({i},{j},{k})"))
        return moves

def all_cycle3_sigma(state):
    """σ 三循环（抽样）"""
    n = state.n
    if n <= 10:
        moves = []
        for i, j, k in itertools.combinations(range(n), 3):
            s = state.copy()
            s.sigma[i], s.sigma[j], s.sigma[k] = s.sigma[j], s.sigma[k], s.sigma[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"c3σ({i},{j},{k})"))
        return moves
    else:
        moves = []
        rng = random.Random()
        all_trips = list(itertools.combinations(range(n), 3))
        rng.shuffle(all_trips)
        for i, j, k in all_trips[:200]:
            s = state.copy()
            s.sigma[i], s.sigma[j], s.sigma[k] = s.sigma[j], s.sigma[k], s.sigma[i]
            s._rebuild()
            moves.append((s, state.cost() - s.cost(), f"c3σ({i},{j},{k})"))
        return moves

# ============ 贪心求解器 ============

OP_GENERATORS = [
    ("swap_σ", all_swap_sigma),
    ("swap_π", all_swap_pi),
    ("joint", all_joint_swap),
    ("msb", all_msb_pair),
    ("c3π", all_cycle3_pi),
    ("c3σ", all_cycle3_sigma),
]

def random_jump(state, strength=0.2):
    """随机扰动"""
    n = state.n
    k = max(3, int(n * strength))
    s = state.copy()
    indices = random.sample(range(n), k)
    vals_pi = [s.pi[i] for i in indices]
    vals_sigma = [s.sigma[i] for i in indices]
    random.shuffle(vals_pi)
    random.shuffle(vals_sigma)
    for idx, i in enumerate(indices):
        s.pi[i] = vals_pi[idx]
        s.sigma[i] = vals_sigma[idx]
    s._rebuild()
    return s

def random_init(n):
    """随机初始化"""
    pi = list(range(n))
    sigma = list(range(n))
    random.shuffle(pi)
    random.shuffle(sigma)
    return pi, sigma

def padic_init(n):
    """p-adic 初始化（2^k 型 n）"""
    k = int(math.log2(n))
    if 2**k != n:
        return random_init(n)
    def bitrev(x, k):
        return int(format(x, f'0{k}b')[::-1], 2)
    pi = [bitrev(i, k) for i in range(n)]
    sigma = [(n-1-pi[i]) for i in range(n)]
    return pi, sigma

def greedy_descent(state, verbose=False):
    """
    贪心下降：循环尝试所有操作类型，每次选最优 Δ>0 的操作。
    返回是否收敛到局部极小。
    """
    n = state.n
    it = 0
    stuck = 0
    best_ever_cost = state.cost()
    best_ever = state.copy()
    
    while True:
        cost_before = state.cost()
        best_delta = 0
        best_next = None
        best_op = ""
        
        # 按优先级尝试各操作类型
        for op_name, gen_func in OP_GENERATORS:
            if best_delta > 0:
                break  # 已经找到改善，不继续
            moves = gen_func(state)
            for st, delta, desc in moves:
                if delta > best_delta:
                    best_delta = delta
                    best_next = st
                    best_op = desc
        
        if best_delta > 0:
            state.pi = best_next.pi
            state.sigma = best_next.sigma
            state.bad = best_next.bad
            it += 1
            
            if state.cost() < best_ever_cost:
                best_ever_cost = state.cost()
                best_ever = state.copy()
            
            if verbose and it % 20 == 0:
                print(f"  [{it}] cost={state.cost()} best={best_ever_cost} "
                      f"op={best_op}")
            
            if state.cost() == 0:
                return True, it, best_ever
        else:
            # 局部极小
            return False, it, best_ever

def solve_greedy(n, max_restarts=20, max_jumps_per_restart=10, 
                 seed=42, verbose=True):
    """
    贪心 + 扰动求解器主循环。
    每轮：贪心下降 → 扰动 × N → 贪心下降 → 重复。
    """
    random.seed(seed)
    
    # 初始化
    if (n & (n-1)) == 0 and n >= 4:
        pi, sigma = padic_init(n)
        init_method = f"padic"
    else:
        pi, sigma = random_init(n)
        init_method = f"random"
    
    state = NTILState(n, pi, sigma)
    best = state.copy()
    best_cost = state.cost()
    
    if verbose:
        print(f"[n={n}] {init_method} init, cost={best_cost}")
        print(f"[n={n}] max_restarts={max_restarts}, "
              f"jumps_per={max_jumps_per_restart}")
    
    for restart in range(max_restarts):
        # Phase 1: 贪心下降
        if verbose:
            print(f"\n--- Restart {restart+1}: greedy descent (cost={state.cost()}) ---")
        
        converged, iters, local_best = greedy_descent(state, verbose=verbose)
        
        if local_best.cost() < best_cost:
            best = local_best.copy()
            best_cost = best.cost()
        
        if state.cost() == 0:
            if verbose:
                print(f"\n★★★★★ 找到 NTIL 解! restart={restart+1} iters={iters}")
            return True, best
        
        if verbose:
            print(f"  局部极小: cost={state.cost()}, best={best_cost}")
        
        # Phase 2: 扰动逃逸
        improved = False
        for jump_idx in range(max_jumps_per_restart):
            strength = 0.15 + 0.05 * (jump_idx % 4)
            ntrials = 5
            
            best_jumped = None
            best_jumped_cost = float('inf')
            
            for _ in range(ntrials):
                jumped = random_jump(state, strength)
                # 微贪心
                conv, it, lb = greedy_descent(jumped, verbose=False)
                if lb.cost() < best_jumped_cost:
                    best_jumped = lb
                    best_jumped_cost = lb.cost()
            
            if best_jumped_cost < state.cost():
                state = best_jumped
                if verbose:
                    print(f"  jump {jump_idx+1}: → cost={state.cost()} "
                          f"(jump_strength={strength:.2f})")
                improved = True
                if state.cost() == 0:
                    return True, state
                break
        
        if not improved:
            if verbose:
                print(f"  扰动无改善，全局重启...")
            # 全局重启
            pi, sigma = random_init(n)
            state = NTILState(n, pi, sigma)
    
    return False, best

# ============ 批量测试 ============

def test_n_values(ns, seed=42):
    """测试多个 n 值"""
    results = {}
    for n in ns:
        print(f"\n{'='*64}")
        print(f"n={n}")
        print(f"{'='*64}")
        t0 = time.time()
        found, sol = solve_greedy(n, max_restarts=15, max_jumps_per_restart=8,
                                  seed=seed, verbose=True)
        elapsed = time.time() - t0
        ok, msg = sol.verify()
        results[n] = {
            'found': found,
            'cost': sol.cost(),
            'verified': ok,
            'msg': msg,
            'time': elapsed
        }
        print(f"\n  n={n}: found={found} cost={sol.cost()} "
              f"verified={ok} ({msg}) time={elapsed:.0f}s")
    return results

# ============ 主程序 ============

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int, nargs='?', default=12)
    ap.add_argument('--batch', type=str, default=None, help='逗号分隔的 n 列表')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--restarts', type=int, default=20)
    ap.add_argument('--jumps', type=int, default=10)
    ap.add_argument('--outdir', type=str, default='results')
    args = ap.parse_args()
    
    if args.batch:
        ns = [int(x) for x in args.batch.split(',')]
        results = test_n_values(ns, seed=args.seed)
        outpath = os.path.join(args.outdir, f'greedy_batch_results.json')
        os.makedirs(args.outdir, exist_ok=True)
        with open(outpath, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n已保存: {outpath}")
    else:
        n = args.n
        found, sol = solve_greedy(n, max_restarts=args.restarts,
                                  max_jumps_per_restart=args.jumps,
                                  seed=args.seed, verbose=True)
        ok, msg = sol.verify()
        print(f"\n最终: found={found} cost={sol.cost()} verified={ok} ({msg})")
        
        if found:
            print(f"π = {sol.pi}")
            print(f"σ = {sol.sigma}")
            outpath = os.path.join(args.outdir, f'ntil_n{n}_greedy.json')
            os.makedirs(args.outdir, exist_ok=True)
            with open(outpath, 'w') as f:
                json.dump({'n': n, 'pi': sol.pi, 'sigma': sol.sigma,
                           'verified': ok}, f, indent=2)
            print(f"已保存: {outpath}")

if __name__ == '__main__':
    main()
