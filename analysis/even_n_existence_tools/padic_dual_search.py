"""
双 transposition 搜索：同时修改 bitrev 和 gray 的 transposition 子集。
n=8: 24 transposition × 2^24≈16M 组合，是否可达 NTIL？

核心代数：
- 对排列 p，位 b 的 transposition 集合 = {(inv[y], inv[y⊕2^b]) : y&2^b=0}
- 每个 transposition 交换两个域索引的值
- 双排列联合修改 → 覆盖所有 8 型共线 (PPP/PPS/PSS/SSS 及各变体)
"""
import itertools, time, json, random, math
from collections import defaultdict

def bitrev(n, k):
    return [int(format(x, f'0{k}b')[::-1], 2) for x in range(n)]

def gray(n):
    return [x ^ (x >> 1) for x in range(n)]

def identity(n):
    return list(range(n))

def complement(n):
    return [n - 1 - x for x in range(n)]

def random_bit_perm(n, k, seed):
    """随机可逆位排列（非奇异 GF(2) 矩阵）。
    重试直到生成满秩矩阵 → 双射排列。
    """
    rng = random.Random(seed)
    max_attempts = 1000
    for _ in range(max_attempts):
        # 生成随机 k×k GF(2) 矩阵
        matrix = [[rng.randint(0, 1) for _ in range(k)] for _ in range(k)]
        # 检查满秩（高斯消元）
        m = [row[:] for row in matrix]
        rank = 0
        for col in range(k):
            pivot = None
            for row in range(rank, k):
                if m[row][col] == 1:
                    pivot = row
                    break
            if pivot is None:
                continue
            m[rank], m[pivot] = m[pivot], m[rank]
            for row in range(k):
                if row != rank and m[row][col] == 1:
                    for c in range(k):
                        m[row][c] ^= m[rank][c]
            rank += 1
        if rank == k:  # 满秩 = 可逆
            result = [0] * n
            for x in range(n):
                y = 0
                for out_bit in range(k):
                    bit_val = 0
                    for in_bit in range(k):
                        bit_val ^= ((x >> in_bit) & 1) * matrix[out_bit][in_bit]
                    y |= (bit_val << out_bit)
                result[x] = y
            if len(set(result)) == n:
                return result
    raise RuntimeError(f"Could not generate bijective bit-perm for n={n}, seed={seed}")

def build_transpositions(p, n, k):
    """为排列 p 构建所有位翻转 transposition。
    对每个位 b，对每个 y 满足 (y & (1<<b))==0：
    transposition = (inv[y], inv[y^(1<<b)])
    返回有序列表 [(a, b_val)] 去重。
    """
    inv = [0] * n
    for i in range(n):
        inv[p[i]] = i
    
    seen = set()
    tps = []
    for b in range(k):
        mask = 1 << b
        for y in range(n):
            if (y & mask) == 0:
                a = inv[y]
                b_val = inv[y ^ mask]
                key = (min(a, b_val), max(a, b_val))
                if key not in seen:
                    seen.add(key)
                    tps.append(key)
    return tps

def count_collisions(p0, p1, n):
    """完整 8 型共线计数（含同行共列 case）。
    返回 (count, collision_set)。
    """
    pts = [(i, p0[i]) for i in range(n)] + [(i, p1[i]) for i in range(n)]
    
    cols = set()
    for idx1, idx2, idx3 in itertools.combinations(range(2 * n), 3):
        x1, y1 = pts[idx1]
        x2, y2 = pts[idx2]
        x3, y3 = pts[idx3]
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            cols.add((idx1, idx2, idx3))
    return len(cols), cols

def count_collisions_incremental(p0, p1, n, changed_rows):
    """增量共线计数——仅检查涉及 changed_rows 的三元组。
    返回 (total_count, updated_collision_set)。
    需要传入当前的碰撞集合来更新。
    """
    # 简单版：全量重算（n=8 足够快）
    return count_collisions(p0, p1, n)

def greedy_dual_search(p0_base, p1_base, tps0, tps1, n, max_iter=500):
    """贪心双 transposition 搜索。"""
    p0 = p0_base[:]
    p1 = p1_base[:]
    
    cnt, cols = count_collisions(p0, p1, n)
    best_p0, best_p1, best_cnt = p0[:], p1[:], cnt
    
    all_tps = [('p0', a, b) for a, b in tps0] + [('p1', a, b) for a, b in tps1]
    
    for it in range(max_iter):
        if cnt == 0:
            break
        
        best_delta = 0
        best_tp = None
        
        for tp_type, a, b in all_tps:
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
                new_cnt, _ = count_collisions(p0, p1, n)
                delta = new_cnt - cnt
                p0[a], p0[b] = p0[b], p0[a]
            else:
                p1[a], p1[b] = p1[b], p1[a]
                new_cnt, _ = count_collisions(p0, p1, n)
                delta = new_cnt - cnt
                p1[a], p1[b] = p1[b], p1[a]
            
            if delta < best_delta:
                best_delta = delta
                best_tp = (tp_type, a, b)
        
        if best_tp and best_delta < 0:
            tp_type, a, b = best_tp
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
            else:
                p1[a], p1[b] = p1[b], p1[a]
            cnt += best_delta
            if cnt < best_cnt:
                best_p0, best_p1, best_cnt = p0[:], p1[:], cnt
        else:
            # 局部极小：随机扰动
            tp_type, a, b = random.choice(all_tps)
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
            else:
                p1[a], p1[b] = p1[b], p1[a]
            cnt, _ = count_collisions(p0, p1, n)
            if cnt < best_cnt:
                best_p0, best_p1, best_cnt = p0[:], p1[:], cnt
    
    return best_p0, best_p1, best_cnt


def sa_dual_search(p0_base, p1_base, tps0, tps1, n, max_iter=2000, n_restarts=10):
    """模拟退火双 transposition 搜索。"""
    all_tps = [('p0', a, b) for a, b in tps0] + [('p1', a, b) for a, b in tps1]
    
    best_overall_cnt = float('inf')
    best_overall_p0, best_overall_p1 = None, None
    
    for restart in range(n_restarts):
        p0 = p0_base[:]
        p1 = p1_base[:]
        
        # Random initial perturbation
        n_perturb = min(len(all_tps), random.randint(1, 10))
        for _ in range(n_perturb):
            tp_type, a, b = random.choice(all_tps)
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
            else:
                p1[a], p1[b] = p1[b], p1[a]
        
        cnt, _ = count_collisions(p0, p1, n)
        best_p0, best_p1, best_cnt = p0[:], p1[:], cnt
        
        T = 2.0
        for it in range(max_iter):
            if cnt == 0:
                break
            
            tp_type, a, b = random.choice(all_tps)
            if tp_type == 'p0':
                p0[a], p0[b] = p0[b], p0[a]
            else:
                p1[a], p1[b] = p1[b], p1[a]
            
            new_cnt, _ = count_collisions(p0, p1, n)
            delta = new_cnt - cnt
            
            if delta <= 0 or random.random() < math.exp(-delta / max(T, 0.01)):
                cnt = new_cnt
                if cnt < best_cnt:
                    best_p0, best_p1, best_cnt = p0[:], p1[:], cnt
            else:
                # Revert
                if tp_type == 'p0':
                    p0[a], p0[b] = p0[b], p0[a]
                else:
                    p1[a], p1[b] = p1[b], p1[a]
            
            T *= 0.995
            if it % 500 == 499:
                T = 2.0
                p0[:] = best_p0[:]
                p1[:] = best_p1[:]
                cnt = best_cnt
        
        if best_cnt < best_overall_cnt:
            best_overall_cnt = best_cnt
            best_overall_p0, best_overall_p1 = best_p0[:], best_p1[:]
            print(f"  restart {restart}: best={best_cnt}")
    
    return best_overall_p0, best_overall_p1, best_overall_cnt


def test_base_permutations(n, k, base_pairs):
    """测试多对基排列的双 transposition 搜索。"""
    results = []
    
    for name, (p0_func, p1_func) in base_pairs.items():
        p0_base = p0_func(n, k) if callable(p0_func) else p0_func
        p1_base = p1_func(n, k) if callable(p1_func) else p1_func
        
        # 确保是排列
        assert len(set(p0_base)) == n == len(set(p1_base))
        assert p0_base != p1_base
        
        base_cnt, _ = count_collisions(p0_base, p1_base, n)
        
        t0 = time.time()
        tps0 = build_transpositions(p0_base, n, k)
        tps1 = build_transpositions(p1_base, n, k)
        
        # Greedy phase
        gp0, gp1, gc = greedy_dual_search(p0_base, p1_base, tps0, tps1, n, max_iter=300)
        
        # SA phase (if greedy didn't solve)
        if gc > 0:
            sp0, sp1, sc = sa_dual_search(gp0, gp1, tps0, tps1, n, 
                                          max_iter=2000, n_restarts=10)
        else:
            sp0, sp1, sc = gp0, gp1, 0
        
        elapsed = time.time() - t0
        
        ntp0, ntp1 = len(tps0), len(tps1)
        result = {
            'name': name,
            'base_collisions': base_cnt,
            'greedy_collisions': gc,
            'sa_collisions': sc,
            'ntps_p0': ntp0,
            'ntps_p1': ntp1,
            'ntps_total': ntp0 + ntp1,
            'time': round(elapsed, 1),
            'sa_p0': sp0,
            'sa_p1': sp1,
        }
        results.append(result)
        
        status = "✓ NTIL!" if sc == 0 else f"{sc} residual"
        print(f"  {name}: base={base_cnt} → greedy={gc} → SA: {status} "
              f"({elapsed:.1f}s, {ntp0+ntp1} tps)")
        
        if sc == 0:
            # 验证!
            check_p0, check_p1 = sp0, sp1
            pts = [(i, check_p0[i]) for i in range(n)] + [(i, check_p1[i]) for i in range(n)]
            verify = sum(1 for p1p,p2p,p3p in itertools.combinations(pts, 3)
                        if (p2p[0]-p1p[0])*(p3p[1]-p1p[1])==(p3p[0]-p1p[0])*(p2p[1]-p1p[1]))
            result['verified'] = (verify == 0)
            print(f"    Verified: {verify} collinear (should be 0)")
    
    return results

# ===== 测试 =====
if __name__ == "__main__":
    print("=" * 64)
    print("p-adic 双 transposition 搜索: n=8")
    print("=" * 64)
    
    n, k = 8, 3
    
    # 基排列对
    base_pairs = {
        'bitrev+gray': (lambda n,k: bitrev(n,k), lambda n,k: gray(n)),
        'bitrev+complement': (lambda n,k: bitrev(n,k), lambda n,k: complement(n)),
        'bitrev+bitrev_shift1': (lambda n,k: bitrev(n,k), 
                                  lambda n,k: [(bitrev(n,k)[i] + 1) % n for i in range(n)]),
        'rand_bitperm+rand_bitperm': (
            lambda n,k: random_bit_perm(n, k, 42),
            lambda n,k: random_bit_perm(n, k, 43)
        ),
        'rand_bitperm2+rand_bitperm2': (
            lambda n,k: random_bit_perm(n, k, 100),
            lambda n,k: random_bit_perm(n, k, 200)
        ),
        'bitrev+rand_bitperm': (
            lambda n,k: bitrev(n,k),
            lambda n,k: random_bit_perm(n, k, 500)
        ),
    }
    
    results = test_base_permutations(n, k, base_pairs)
    
    # 保存
    json.dump([{k: v for k, v in r.items() if k not in ('sa_p0', 'sa_p1')} 
              for r in results], 
              open('padic_dual_search_n8.json', 'w'), indent=2)
    
    print(f"\n===== 汇总 =====")
    for r in results:
        icon = "✓" if r['sa_collisions'] == 0 else "✗"
        print(f"  {icon} {r['name']}: base={r['base_collisions']} → "
              f"greedy={r['greedy_collisions']} → SA={r['sa_collisions']} "
              f"({r['time']}s, {r['ntps_total']} tps)")
    
    n_solved = sum(1 for r in results if r['sa_collisions'] == 0)
    print(f"\nNTIL 可达率: {n_solved}/{len(results)}")
    
    if n_solved == 0:
        # 分析最优残存
        best = min(results, key=lambda r: r['sa_collisions'])
        print(f"\n最优: {best['name']} → {best['sa_collisions']} 残存共线")
        print(f"  p0 = {best['sa_p0']}")
        print(f"  p1 = {best['sa_p1']}")
        print(f"\n[OPEN] n=8 双 transposition 未达 NTIL → 需要更丰富的操作集")
        print(f"  建议：可能 S_{2^k} 的子群可及性有结构障碍")
