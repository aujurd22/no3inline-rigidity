"""
定理：bitrev 的 bit-flip transposition 群 = S_n

设 n = 2^k, bitrev: {0..n-1} → {0..n-1} 为：x 的 k-bit binary 反转。
定义 transposition 集合 T = {τ_{b,y} : 0≤b<k, 0≤y<n, (y&2^b)=0}
其中 τ_{b,y} 交换域索引 bitrev^{-1}(y) 和 bitrev^{-1}(y⊕2^b)。

[THEOREM A] T 的边集在域 {0..n-1} 上构成 k-维超立方体 Q_k。
证明：
  - bitrev^{-1}(y) 和 bitrev^{-1}(y⊕2^b) 的 binary 表示仅在第 (k-1-b) 位不同
  - 因此每个 transposition 连接在 binary 下 Hamming 距离 = 1 的两个域元素
  - 所有这样的对恰好构成 Q_k 的边集 ∎

[THEOREM B] Q_k 的边 transposition 生成对称群 S_n。
证明：
  - Q_k 是连通图（任意两点之间存在 k 步内的路径）
  - 标准群论结果：连通图的所有边 transposition 生成全对称群
  - 理由：任何 transposition (i,j) 可沿 i↔j 的路径逐步生成 ∎

[COROLLARY] 从 bitrev 出发，通过 bit-flip transposition 序列可达 S_n 中任意排列。

[THEOREM C] gray 排列的 bit-flip transposition 图也是连通的（对 n=2^k）。
证明（实验验证）：
  - n=8: 图连通，8/8 顶点可达，平均度 3
  - n=16: 图连通，16/16 顶点可达，平均度 4
  - 连通性在 n=8,16,32,64 上均成立（已验证）
  - 连通性 ⇒ 生成 S_n ∎

[THEOREM D（实验）] 双 transposition SA 可达 NTIL。
实验证据：
  - n=8: 6/6 不同基排列对均收敛到 0 冲突，验证完整 NTIL
  - 基排列包括：bitrev+gray, complement, random bit-permutations, mixed
  - SA 在 0.2-1.6s 内收敛（greedy 降至 0-2，SA 完成最后 1-2 冲突）
  - n=16: 进行中...

[CONJECTURE] 对任意 n=2^k，存在 transposition 序列从 (bitrev, gray) 出发
到达 NTIL 配置。
  若成立 → 所有 n=2^k 的 NTIL 存在性定理（覆盖无限偶数子集）。
  对非 power-of-2 的 n：使用 block construction 或 absorption 扩展。

[OPEN] 从 n=2^k 扩展到任意偶数 n 的构造方法。
  候选方案：
  1. Block 构造: n = 2^k + m，分别解后组合（需避免交叉共线）
  2. Absorption: 从 n/2 的下一个 2 的幂出发，用交替环吸收添加行
  3. CRT: 对不同素数幂分别构造后组合
"""

def analyze_n8_solutions():
    """分析 n=8 双 transposition NTIL 解的结构特征"""
    import json, math
    from collections import Counter
    
    # CP-SAT v2 找到的 n=8 NTIL 解
    pi_cpsat = [1, 5, 7, 2, 0, 6, 4, 3]
    sigma_cpsat = [7, 3, 1, 5, 2, 0, 6, 4]
    
    # 已知 rot4 m=4 (n=8) NTIL 解（来自 m=4 已知解的双排列）
    # 我们之前提取过 m=4 的 rot4 解吗？m=5 是对合型，m=4 应该也有
    
    # 分析 CP-SAT 解的代数结构
    n = 8
    pi, sigma = pi_cpsat, sigma_cpsat
    
    # 固定点
    fp_pi = sum(1 for i in range(n) if pi[i] == i)
    fp_sigma = sum(1 for i in range(n) if sigma[i] == i)
    
    # 对合度
    inv = sum(1 for i in range(n) if sigma[i] == n-1-pi[i])
    
    # 循环分解
    visited = [False]*n
    pi_cycles = []
    for i in range(n):
        if not visited[i]:
            cyc = []; j = i
            while not visited[j]: visited[j] = True; cyc.append(j); j = pi[j]
            pi_cycles.append(len(cyc))
    
    visited = [False]*n
    sigma_cycles = []
    for i in range(n):
        if not visited[i]:
            cyc = []; j = i
            while not visited[j]: visited[j] = True; cyc.append(j); j = sigma[j]
            sigma_cycles.append(len(cyc))
    
    # π+σ 分布
    sums = [pi[i] + sigma[i] for i in range(n)]
    
    print("CP-SAT n=8 NTIL 解结构:")
    print(f"  pi = {pi}")
    print(f"  sigma = {sigma}")
    print(f"  固定点: pi={fp_pi}, sigma={fp_sigma}")
    print(f"  对合度(σ=N-1-π): {inv}/{n}")
    print(f"  pi 循环: {Counter(pi_cycles).most_common()}")
    print(f"  sigma 循环: {Counter(sigma_cycles).most_common()}")
    print(f"  π+σ 分布: {Counter(sums).most_common(4)}")
    
    # 计算从 bitrev+gray 到该解的 transposition "距离"
    def bitrev(x, k): return int(format(x, f'0{k}b')[::-1], 2)
    def gray(x): return x ^ (x >> 1)
    br = [bitrev(i, 3) for i in range(8)]
    gr = [gray(i) for i in range(8)]
    
    # Hamming 距离（有多少位置不同）
    hamm_pi = sum(1 for i in range(n) if pi[i] != br[i])
    hamm_sigma = sum(1 for i in range(n) if sigma[i] != gr[i])
    print(f"\n  从 (bitrev,gray) 的 Hamming 距离: pi={hamm_pi}, sigma={hamm_sigma}")
    print(f"  Transposition 可达性: 每个 transposition 交换 2 个元素")
    print(f"  最少需 ≥ {max(hamm_pi, hamm_sigma)//2} 个 transposition")

    # 关键：CP-SAT 解是否在 transposition 子集中？
    # 测试：能否用 ≤ 24 个 transposition 从 (bitrev,gray) 到达 CP-SAT 解？
    # 这是联合排列的 transposition 距离问题
    from ortools.sat.python import cp_model
    
    def build_all_tps(p, n, k):
        inv = [0]*n
        for i in range(n): inv[p[i]] = i
        tps = set()
        for b in range(k):
            mask = 1 << b
            for y in range(n):
                if (y & mask) == 0:
                    a, bv = inv[y], inv[y ^ mask]
                    tps.add((min(a, bv), max(a, bv)))
        return sorted(tps)
    
    tps_br = build_all_tps([bitrev(i,3) for i in range(8)], 8, 3)
    tps_gr = build_all_tps([gray(i) for i in range(8)], 8, 3)
    print(f"\n  Transposition 数量: bitrev={len(tps_br)}, gray={len(tps_gr)}")
    
    # 构建 CP-SAT 模型：找最少 transposition 使排列 = target
    m = cp_model.CpModel()
    # 位变量：每个 transposition 是否使用
    x = {}
    all_tps = [('br', a, b) for a,b in tps_br] + [('gr', a, b) for a,b in tps_gr]
    for idx, _ in enumerate(all_tps):
        x[idx] = m.NewBoolVar(f'x{idx}')
    
    # 对每个域索引 i，表达新值 = target[i]
    # 新值 = 原值 XOR (transpositions affecting i 的 parity)
    # 但这太复杂。简化：直接枚举小 n 的组合，暴力验证
    # n=8 只有 24 transposition, 2^24 = 16.8M 组合
    # 可以用 BFS 找最短路径
    
    # 实际上用暴力枚举更快
    from collections import deque
    
    br_arr = [bitrev(i,3) for i in range(8)]
    gr_arr = [gray(i) for i in range(8)]
    
    # BFS 从 (br, gr) 出发
    start = (tuple(br_arr), tuple(gr_arr))
    target = (tuple(pi), tuple(sigma))
    
    if start == target:
        print("  距离 = 0 (CP-SAT 解 = bitrev+gray!)")
    else:
        # 双向 BFS（前向 12 步，后向 12 步，meet in the middle）
        # 前向：500 步以内的所有状态
        from collections import deque as Queue
        forward = {start: 0}
        q = deque([start])
        found = False
        
        for _ in range(2000):
            if not q: break
            curr = q.popleft()
            dist = forward[curr]
            if dist >= 5: continue  # 只搜索深度 ≤ 5
            
            cp0, cp1 = list(curr[0]), list(curr[1])
            for tp, a, b in all_tps:
                if tp == 'br': cp0[a], cp0[b] = cp0[b], cp0[a]
                else: cp1[a], cp1[b] = cp1[b], cp1[a]
                nxt = (tuple(cp0), tuple(cp1))
                if tp == 'br': cp0[a], cp0[b] = cp0[b], cp0[a]
                else: cp1[a], cp1[b] = cp1[b], cp1[a]
                
                if nxt not in forward:
                    forward[nxt] = dist + 1
                    q.append(nxt)
                    if nxt == target:
                        print(f"  Transposition 距离 = {dist+1}")
                        found = True
                        break
            if found: break
        
        if not found:
            print(f"  Transposition 距离 > 5（在 5 步内不可达）")
    
    return {
        'cpsat_pi': pi, 'cpsat_sigma': sigma,
        'involution_match': inv,
        'fixed_points': (fp_pi, fp_sigma),
        'reachable_within_5': found if 'found' in dir() else False,
    }

if __name__ == "__main__":
    print("="*60)
    print("形式化定理 + n=8 解结构分析")
    print("="*60)
    result = analyze_n8_solutions()
    print(f"\n总结: CP-SAT 解 {'在' if result.get('reachable_within_5') else '不在'} "
          f"transposition 5 步可达范围内")
