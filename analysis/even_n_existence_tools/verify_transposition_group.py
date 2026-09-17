"""
定理：bit-flip transposition 群生成 S_n（对 bitrev 排列，n=2^k）

证明梗概：
1. bitrev 的位翻转 transposition 图 = k-维超立方体 Q_k
   - 顶点：域索引 {0, 1, ..., 2^k-1}
   - 边：{(a,b) : a,b 在 binary 下仅差一位}
   - 理由：翻转值域 bit b → 交换 inv[y] ↔ inv[y⊕2^b]
           而 inv[y] 和 inv[y⊕2^b] 的 binary 仅差 bit (k-1-b)

2. Q_k 是连通的（对任意 k≥1）
   - 任意两顶点之间有一条 path（沿坐标轴逐步翻转）

3. 连通图的所有边 transposition 生成 S_n
   - 标准群论结果：对 n 个顶点上的连通图，其边对应的
     transposition 生成整个对称群 S_n

4. 推论：从 bitrev 出发，存在 transposition 序列可达任意排列

5. 双排列版本：从 (bitrev, gray) 出发，两个排列的
   transposition 独立作用 → 可达 (S_n, S_n) 的某子群
   → 若 gray 的 transposition 图也连通 → 可达 (S_n, S_n)

对 p-adic 搜索的启发：
- 全空间可达 → 搜索等价于在 S_n×S_n 中找 NTIL 解
- 贪心+SA 在 ~0.1% 采样率下，若 NTIL 密度 >10^(-6) → 大概率命中
- 关键未知量：S_n×S_n 中 NTIL 解的密度
"""

def verify_qk_structure(n=8, k=3):
    """验证 n=8 bitrev 的 transposition 图 = Q_3"""
    from collections import defaultdict
    
    def bitrev(x, k):
        return int(format(x, f'0{k}b')[::-1], 2)
    
    # 构建 transposition 图
    graph = defaultdict(set)
    for b in range(k):
        mask = 1 << b
        for y in range(n):
            if (y & mask) == 0:
                a = bitrev(y, k)
                b_val = bitrev(y ^ mask, k)
                graph[a].add(b_val)
                graph[b_val].add(a)
    
    # 验证：每个顶点的度 = k (= Q_k 的度)
    degrees = {v: len(nb) for v, nb in graph.items()}
    all_k = all(d == k for d in degrees.values())
    
    # 验证：邻接关系 = binary 下差 1 位
    def hamming_dist(a, b):
        return bin(a ^ b).count('1')
    
    all_hamming1 = all(
        hamming_dist(v, nb) == 1
        for v, nbs in graph.items()
        for nb in nbs
    )
    
    # 验证连通性（BFS）
    visited = set()
    stack = [0]
    while stack:
        v = stack.pop()
        if v in visited: continue
        visited.add(v)
        stack.extend(nb for nb in graph[v] if nb not in visited)
    is_connected = len(visited) == n
    
    print(f"n={n} (k={k}):")
    print(f"  所有度=k: {all_k} (度分布: {dict(sorted(Counter(degrees.values()).items()))})")
    print(f"  所有边Hamming=1: {all_hamming1}")
    print(f"  连通: {is_connected} ({len(visited)}/{n} vertices)")
    print(f"  结论: transposition 图 = Q_{k}" if (all_k and all_hamming1 and is_connected) 
          else "  结构不符合Q_k")
    
    # 若 = Q_k → 生成 S_n
    if all_k and all_hamming1 and is_connected:
        print(f"  → 群论推论: edge transposition 生成 S_{n}")
    
    return graph

def verify_gray_transposition_graph(n=8, k=3):
    """验证 gray 排列的 transposition 图是否连通"""
    from collections import defaultdict
    
    def gray(x):
        return x ^ (x >> 1)
    
    # gray 逆函数（用于从值反查域索引）
    inv = [0] * n
    for i in range(n):
        inv[gray(i)] = i
    
    graph = defaultdict(set)
    for b in range(k):
        mask = 1 << b
        for y in range(n):
            if (y & mask) == 0:
                a = inv[y]
                b_val = inv[y ^ mask]
                if a != b_val:
                    graph[a].add(b_val)
                    graph[b_val].add(a)
    
    visited = set()
    stack = [0]
    while stack:
        v = stack.pop()
        if v in visited: continue
        visited.add(v)
        stack.extend(nb for nb in graph[v] if nb not in visited)
    
    is_connected = len(visited) == n
    degrees = {v: len(nb) for v, nb in graph.items()}
    avg_deg = sum(degrees.values()) / len(degrees)
    
    print(f"\ngray transposition 图 (n={n}):")
    print(f"  平均度: {avg_deg:.1f}")
    print(f"  连通: {is_connected} ({len(visited)}/{n})")
    if is_connected:
        print(f"  → 群论推论: edge transposition 生成 S_{n}")
    
    return graph

if __name__ == "__main__":
    from collections import Counter
    print("="*60)
    print("定理验证: bit-flip transposition 群 = S_n")
    print("="*60)
    
    verify_qk_structure(8, 3)
    verify_qk_structure(16, 4)
    verify_qk_structure(32, 5)
    
    print(f"\n{'='*60}")
    print("推广: gray 排列的 transposition 图")
    print("="*60)
    verify_gray_transposition_graph(8, 3)
    verify_gray_transposition_graph(16, 4)
    
    print(f"\n{'='*60}")
    print("[THEOREM] 对任意 n=2^k, bitrev 的 bit-flip transposition 群 = S_n")
    print("  证明: transposition 图 = Q_k → 连通 → 生成 S_n")
    print("  对 gray: 若 transposition 图连通 → 也生成 S_n")
    print("  双排列版: (bitrev,gray) 可达 (S_n,S_n) → 全空间搜索")
    print("="*60)
