"""
联合求解器：p-adic 初始化 + 富操作集 SA 退火。
目标：n=12（最小命题）→ n=16（p-adic 目标）→ 更高 n。

操作集：
  1. swap_sigma: σ[i]↔σ[j]（交替4-环）
  2. swap_pi: π[i]↔π[j]
  3. cycle3_pi: π[i]→π[j]→π[k]→π[i]（6-环）
  4. joint_swap: 同时交换 π[i]↔π[j] 和 σ[i]↔σ[j]
  5. msb_pair: p-adic MSB transposition（仅 2^k 型 n）
  6. random_jump: 随机扰动逃逸

代价函数：共线三元组计数（增量 O(n²)/操作）
"""
import sys, os, itertools, random, math, time, json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Set, Dict, Optional

# ============ 数据结构 ============

@dataclass
class State:
    """双排列状态 + 增量代价追踪"""
    n: int
    pi: List[int]   # 排列 π[0..n-1]
    sigma: List[int]  # 排列 σ[0..n-1]
    bad: Set[Tuple[int,int,int]]  # 当前坏三元组 (p1,p2,p3), p1<p2<p3
    triples_of: List[List[Tuple[int,int,int]]]  # triples_of[p] = 所有含 p 的三元组

    def total_points(self) -> int:
        return 2 * self.n

    def pt_idx(self, is_pi: bool, row: int) -> int:
        """点索引：π 用 0..n-1, σ 用 n..2n-1"""
        return row if is_pi else row + self.n

    def pt_coords(self, pidx: int) -> Tuple[int, int]:
        if pidx < self.n:
            return (pidx, self.pi[pidx])
        else:
            r = pidx - self.n
            return (r, self.sigma[r])

    def cost(self) -> int:
        return len(self.bad)

    def rebuild_bad(self):
        """全量重建 bad 集合（用于初始化）"""
        self.bad.clear()
        npt = self.total_points()
        for i, j, k in itertools.combinations(range(npt), 3):
            x1, y1 = self.pt_coords(i)
            x2, y2 = self.pt_coords(j)
            x3, y3 = self.pt_coords(k)
            if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                self.bad.add((i, j, k))

    def _compute_new_triples(self, changed_pidxs: Set[int]) -> Set[Tuple[int,int,int]]:
        """计算改变后的点参与的所有三元组，返回其中共线的"""
        new_bad = set()
        all_pidxs = set(range(self.total_points()))
        affected = set(changed_pidxs)
        # 对于每个改变的点的每个三元组
        for p in changed_pidxs:
            for trip in self.triples_of[p]:
                # 检查这个三元组在当前坐标下是否共线
                x1, y1 = self.pt_coords(trip[0])
                x2, y2 = self.pt_coords(trip[1])
                x3, y3 = self.pt_coords(trip[2])
                if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                    new_bad.add(trip)
        return new_bad

    def apply_op(self, changed_pidxs: Set[int]) -> int:
        """
        应用操作后更新 bad 集合。
        需要先修改 pi/sigma，再调用此方法。
        返回新的 cost。
        """
        # 1. 移除旧三元组（涉及改变的点）
        #    但注意：旧的三元组可能仍然坏（如果改变不影响共线性）
        #    正确做法：移除所有涉及改变点的旧三元组，重新评估
        old_bad_affected = {t for t in self.bad
                           if any(p in changed_pidxs for p in t)}
        self.bad -= old_bad_affected

        # 2. 评估新三元组
        new_bad = self._compute_new_triples(changed_pidxs)
        self.bad |= new_bad

        return len(self.bad)


def build_triples_of(n: int) -> List[List[Tuple[int,int,int]]]:
    """预计算 triples_of[p] = 所有包含点 p 的三元组 (已排序)"""
    npt = 2 * n
    triples_of = [[] for _ in range(npt)]
    for i, j, k in itertools.combinations(range(npt), 3):
        triples_of[i].append((i, j, k))
        triples_of[j].append((i, j, k))
        triples_of[k].append((i, j, k))
    return triples_of

# ============ 初始化 ============

def padic_init(n: int):
    """p-adic 初始化：bitrev + complement（仅对 2^k 型 n 有效）"""
    k = int(math.log2(n))
    if 2**k != n:
        raise ValueError(f"n={n} 不是 2 的幂")
    
    def bitrev(x, k):
        return int(format(x, f'0{k}b')[::-1], 2)
    
    pi = [bitrev(i, k) for i in range(n)]
    # complement: σ[i] = n-1-π[i]
    sigma = [(n - 1 - pi[i]) for i in range(n)]
    return pi, sigma

def random_init(n: int, seed: int = None):
    """随机双排列初始化"""
    rng = random.Random(seed)
    pi = list(range(n))
    sigma = list(range(n))
    rng.shuffle(pi)
    rng.shuffle(sigma)
    return pi, sigma

def create_state(n: int, pi: List[int], sigma: List[int]) -> State:
    triples_of = build_triples_of(n)
    state = State(n=n, pi=pi, sigma=sigma, bad=set(), triples_of=triples_of)
    state.rebuild_bad()
    return state

# ============ 操作定义 ============

class Operator:
    """操作的抽象基类"""
    name: str = "base"

    def probe(self, state: State, rng: random.Random) -> Optional[Tuple[Set[int], int]]:
        """
        尝试一个操作，返回 (affected_pidxs, new_cost) 或 None（无法执行）。
        不修改 state，仅计算效果。
        """
        raise NotImplementedError

    def apply(self, state: State, affected_pidxs: Set[int]):
        """实际应用操作到 state 上"""
        raise NotImplementedError

class SwapSigma(Operator):
    name = "swap_σ"

    def probe(self, state, rng):
        n = state.n
        i, j = rng.sample(range(n), 2)
        old_si, old_sj = state.sigma[i], state.sigma[j]
        # 暂态交换
        state.sigma[i], state.sigma[j] = old_sj, old_si
        changed = {state.pt_idx(False, i), state.pt_idx(False, j)}
        new_cost = state.apply_op(changed)
        # 恢复
        state.sigma[i], state.sigma[j] = old_si, old_sj
        state.apply_op(changed)  # 恢复 bad 集合
        return changed, new_cost

    def apply(self, state, changed):
        # 已经被 probe 修改过了？不，probe 恢复了。
        # 重新执行交换
        i = next(p for p in changed if p >= state.n)  # Hmm, this is fragile
        # 实际上应该保存操作参数
        pass


# 上面 Operator 基类设计有问题——probe 修改了 state 又恢复，太复杂。
# 简化：用 lambda / 闭包风格。

class RichSA:
    """富操作集 SA 求解器"""
    
    def __init__(self, n: int, seed: int = 42):
        self.n = n
        self.rng = random.Random(seed)
        self.triples_of = build_triples_of(n)
        
        # 初始化
        if (n & (n-1)) == 0 and n >= 4:
            try:
                pi, sigma = padic_init(n)
                self.init_method = f"padic(n={n})"
            except:
                pi, sigma = random_init(n, seed)
                self.init_method = f"random(seed={seed})"
        else:
            pi, sigma = random_init(n, seed)
            self.init_method = f"random(seed={seed})"
        
        self.state = self._make_state(pi, sigma)
        self.init_cost = self.state.cost()
        
        # 最佳记录
        self.best_pi = pi.copy()
        self.best_sigma = sigma.copy()
        self.best_cost = self.init_cost
        self.history = [(0, self.init_cost)]
        
    def _make_state(self, pi, sigma):
        state = State(n=self.n, pi=pi, sigma=sigma, bad=set(), triples_of=self.triples_of)
        state.rebuild_bad()
        return state
    
    def _apply_and_update(self, pi, sigma, changed_pidxs, cost_before):
        """原子操作：更新排列 + 更新 bad 集合 + 返回新代价"""
        self.state.pi = pi
        self.state.sigma = sigma
        return self.state.apply_op(changed_pidxs)
    
    def _probe_swap_sigma(self):
        """随机交换 σ[i]↔σ[j]，返回 (pi, sigma, changed, cost_before)"""
        i, j = self.rng.sample(range(self.n), 2)
        pi = self.state.pi
        sigma = self.state.sigma.copy()
        sigma[i], sigma[j] = sigma[j], sigma[i]
        changed = {self.state.pt_idx(False, i), self.state.pt_idx(False, j)}
        return pi, sigma, changed, self.state.cost()
    
    def _probe_swap_pi(self):
        i, j = self.rng.sample(range(self.n), 2)
        sigma = self.state.sigma
        pi = self.state.pi.copy()
        pi[i], pi[j] = pi[j], pi[i]
        changed = {self.state.pt_idx(True, i), self.state.pt_idx(True, j)}
        return pi, sigma, changed, self.state.cost()
    
    def _probe_cycle3_pi(self):
        i, j, k = self.rng.sample(range(self.n), 3)
        sigma = self.state.sigma
        pi = self.state.pi.copy()
        pi[i], pi[j], pi[k] = pi[j], pi[k], pi[i]
        changed = {self.state.pt_idx(True, i), self.state.pt_idx(True, j), self.state.pt_idx(True, k)}
        return pi, sigma, changed, self.state.cost()
    
    def _probe_joint_swap(self):
        i, j = self.rng.sample(range(self.n), 2)
        pi = self.state.pi.copy()
        sigma = self.state.sigma.copy()
        pi[i], pi[j] = pi[j], pi[i]
        sigma[i], sigma[j] = sigma[j], sigma[i]
        changed = {self.state.pt_idx(True, i), self.state.pt_idx(True, j),
                   self.state.pt_idx(False, i), self.state.pt_idx(False, j)}
        return pi, sigma, changed, self.state.cost()
    
    def _probe_msb_pair(self):
        """p-adic MSB transposition: 翻转一对位置的 MSB 位（仅 2^k 型 n）"""
        n = self.n
        if (n & (n-1)) != 0:
            return None
        k = int(math.log2(n))
        msb = 1 << (k-1)
        # 随机选一个位置，搭档是其 MSB 翻转
        i = self.rng.randrange(n)
        j = i ^ msb
        if j >= n:
            return None
        
        pi = self.state.pi.copy()
        sigma = self.state.sigma.copy()
        pi[i], pi[j] = pi[j], pi[i]
        sigma[i], sigma[j] = sigma[j], sigma[i]
        changed = {self.state.pt_idx(True, i), self.state.pt_idx(True, j),
                   self.state.pt_idx(False, i), self.state.pt_idx(False, j)}
        return pi, sigma, changed, self.state.cost()
    
    def _probe_random_jump(self, strength=0.15):
        """随机扰动多个位置以逃逸局部极值"""
        n = self.n
        k = max(2, int(n * strength))
        indices = self.rng.sample(range(n), k)
        pi = self.state.pi.copy()
        sigma = self.state.sigma.copy()
        # 在选中的位置间随机重排
        vals_pi = [pi[i] for i in indices]
        vals_sigma = [sigma[i] for i in indices]
        self.rng.shuffle(vals_pi)
        self.rng.shuffle(vals_sigma)
        for idx, i in enumerate(indices):
            pi[i] = vals_pi[idx]
            sigma[i] = vals_sigma[idx]
        changed = set()
        for i in indices:
            changed.add(self.state.pt_idx(True, i))
            changed.add(self.state.pt_idx(False, i))
        return pi, sigma, changed, self.state.cost()
    
    def _probe_targeted_fix(self):
        """定向修复：找出参与坏三元组最多的点，将其值与另一点交换"""
        n = self.n
        if self.state.cost() == 0:
            return None
        
        # 统计每个点参与了多少坏三元组
        point_bad_count = defaultdict(int)
        for trip in self.state.bad:
            for p in trip:
                point_bad_count[p] += 1
        
        if not point_bad_count:
            return None
        
        # 找最"坏"的点
        worst_p = max(point_bad_count, key=point_bad_count.get)
        is_pi = worst_p < n
        row = worst_p if is_pi else worst_p - n
        
        # 与另一个随机行交换值（保持排列性）
        other = self.rng.choice([r for r in range(n) if r != row])
        if is_pi:
            pi = self.state.pi.copy()
            sigma = self.state.sigma
            pi[row], pi[other] = pi[other], pi[row]
            changed = {self.state.pt_idx(True, row), self.state.pt_idx(True, other)}
        else:
            pi = self.state.pi
            sigma = self.state.sigma.copy()
            sigma[row], sigma[other] = sigma[other], sigma[row]
            changed = {self.state.pt_idx(False, row), self.state.pt_idx(False, other)}
        
        return pi, sigma, changed, self.state.cost()
    
    OP_WEIGHTS = [
        ("swap_σ", 0.20),
        ("swap_π", 0.20),
        ("cycle3_π", 0.15),
        ("joint_swap", 0.15),
        ("msb_pair", 0.10),
        ("targeted_fix", 0.15),
        ("random_jump", 0.05),
    ]
    
    def _sample_op(self):
        """按权重采样操作名"""
        names, weights = zip(*self.OP_WEIGHTS)
        return self.rng.choices(names, weights=weights, k=1)[0]
    
    def _probe_op(self, op_name):
        probes = {
            "swap_σ": self._probe_swap_sigma,
            "swap_π": self._probe_swap_pi,
            "cycle3_π": self._probe_cycle3_pi,
            "joint_swap": self._probe_joint_swap,
            "msb_pair": self._probe_msb_pair,
            "random_jump": lambda: self._probe_random_jump(0.15),
            "targeted_fix": self._probe_targeted_fix,
        }
        result = probes[op_name]()
        if result is None:
            return None, None, None, None
        return result
    
    def run(self, max_iter=50000, T_start=10.0, T_end=0.01, 
            cool_rate=0.9995, report_interval=500, patience=3000):
        """SA 主循环"""
        n = self.n
        cost = self.state.cost()
        best_cost = cost
        T = T_start
        stuck_count = 0
        accepted = 0
        total = 0
        
        print(f"[n={n}] 初始化: {self.init_method}, cost={cost}")
        print(f"[n={n}] SA 参数: T_start={T_start}, T_end={T_end}, "
              f"cool={cool_rate}, max_iter={max_iter}")
        
        for it in range(max_iter):
            if cost == 0:
                print(f"\n★★★★★ 迭代 {it}: 达到 0 冲突！NTIL 解已找到！")
                self.best_pi = self.state.pi.copy()
                self.best_sigma = self.state.sigma.copy()
                self.best_cost = 0
                self.history.append((it, 0))
                return True
            
            # 温度衰减
            T = max(T_end, T * cool_rate)
            total += 1
            
            # 采样操作
            pi_new, sigma_new, changed, cost_before = self._probe_op(self._sample_op())
            if pi_new is None:
                continue
            
            # 计算新代价（临时应用操作）
            temp_state = self._make_state(pi_new, sigma_new)
            new_cost = temp_state.cost()
            
            delta = new_cost - cost_before
            
            # SA 接受准则
            accept = (delta <= 0) or (self.rng.random() < math.exp(-delta / T))
            
            if accept:
                # 正式应用操作
                self._apply_and_update(pi_new, sigma_new, changed, cost_before)
                cost = new_cost
                accepted += 1
                stuck_count = 0
                
                if cost < best_cost:
                    best_cost = cost
                    self.best_pi = pi_new.copy()
                    self.best_sigma = sigma_new.copy()
                    self.best_cost = best_cost
                    self.history.append((it, best_cost))
            else:
                stuck_count += 1
            
            # 周期性报告
            if it % report_interval == 0 and it > 0:
                acc_rate = accepted / total if total > 0 else 0
                print(f"  [{it:6d}] cost={cost:4d} best={best_cost:4d} "
                      f"T={T:.3f} acc_rate={acc_rate:.2f}")
            
            # 逃逸机制：如果卡住太久，增强随机扰动
            if stuck_count > patience and cost > 0:
                print(f"  [{it:6d}] 卡住 {stuck_count} 步，随机跳跃逃逸...")
                pi_new, sigma_new, changed, cost_before = self._probe_random_jump(0.25)
                self._apply_and_update(pi_new, sigma_new, changed, cost_before)
                cost = self.state.cost()
                stuck_count = 0
                T = min(T * 2, T_start)  # 升温
        
        # 报告最终状态
        print(f"\n[n={n}] SA 结束: best_cost={best_cost}, "
              f"acc_rate={accepted/total:.2f} ({accepted}/{total})")
        self.best_pi = self.state.pi.copy()
        self.best_sigma = self.state.sigma.copy()
        self.best_cost = cost
        return cost == 0
    
    def verify(self):
        """完整验证：2n 唯一点 + 无三点共线"""
        pts = []
        for i in range(self.n):
            pts.append((i, self.best_pi[i]))
        for i in range(self.n):
            pts.append((i, self.best_sigma[i]))
        
        # 唯一点检查
        if len(set(pts)) != 2 * self.n:
            return False, f"重复点: {2*self.n - len(set(pts))} 个重复"
        
        # 共线检查
        bad = []
        for (x1,y1),(x2,y2),(x3,y3) in itertools.combinations(pts, 3):
            if (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1):
                bad.append(((x1,y1),(x2,y2),(x3,y3)))
        
        if bad:
            return False, f"共线三元组: {len(bad)}"
        return True, "OK"
    
    def save(self, filepath):
        """保存解"""
        result = {
            'n': self.n,
            'pi': self.best_pi,
            'sigma': self.best_sigma,
            'cost': self.best_cost,
            'init_method': self.init_method,
            'history': self.history,
            'verified': self.verify() if self.best_cost == 0 else (False, "not NTIL")
        }
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)
        return result


# ============ 主程序 ============

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int, nargs='?', default=12, help='网格大小')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--max-iter', type=int, default=100000)
    ap.add_argument('--patience', type=int, default=3000)
    ap.add_argument('--restarts', type=int, default=5, help='多重启次数')
    ap.add_argument('--outdir', type=str, default='results')
    args = ap.parse_args()
    
    n = args.n
    print(f"{'='*64}")
    print(f"富操作集 SA 求解器: n={n}")
    print(f"{'='*64}")
    
    best_overall_cost = float('inf')
    best_solution = None
    
    for restart in range(args.restarts):
        seed = args.seed + restart * 1000
        print(f"\n--- Restart {restart+1}/{args.restarts} (seed={seed}) ---")
        
        solver = RichSA(n, seed=seed)
        found = solver.run(
            max_iter=args.max_iter,
            patience=args.patience,
            T_start=10.0,
            T_end=0.01,
            cool_rate=0.9995 if n <= 16 else 0.9999
        )
        
        if solver.best_cost < best_overall_cost:
            best_overall_cost = solver.best_cost
            best_solution = solver
        
        if found:
            break
    
    # 验证
    if best_solution:
        ok, msg = best_solution.verify()
        status = "✔ NTIL" if ok else f"✗ {msg}"
        print(f"\n最终验证: {status}, cost={best_overall_cost}")
        
        outpath = os.path.join(args.outdir, f'ntil_n{n}_rich_sa.json')
        best_solution.save(outpath)
        print(f"已保存: {outpath}")
        
        if ok:
            print(f"\n★ NTIL 解详情:")
            print(f"  π = {best_solution.best_pi}")
            print(f"  σ = {best_solution.best_sigma}")
    
    return best_overall_cost

if __name__ == '__main__':
    main()
