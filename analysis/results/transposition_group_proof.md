# p-adic 三群论 —— 严格证明

## 定义

设 n = 2^k。对任意排列 π ∈ S_n，定义其 **比特翻转 transposition 集**：

$$T(\pi) = \{(\pi(x), \pi(y)) \in S_n : \text{Hamming}(x, y) = 1\}$$

即对超立方体 Q_k = {0,1}^k 的每条边 (x, y)，产生排列值空间中的一个交换。

## 定理 1：bitrev 的 T(bitrev) 生成 S_n

**证明**：

1. bitrev: {0,1}^k → {0,1}^k 是双射。因此 T(bitrev) 与 Q_k 的边集之间存在自然双射。

2. Q_k 是连通图（任意两点由最多 k 步 Hamming 路径连接）。

3. **引理**：若 G = (V, E) 是连通图，则边 transposition 集 `{(u,v) : (u,v) ∈ E}` 生成 S_{|V|}（顶点集上的全对称群）。

   **引理证明**：
   - 取 G 的任意生成树 T。
   - 对 T 的任意边 (a,b)，其 transposition (a,b) 在生成集中。
   - 对任意两个顶点 u,v，找到它们在 T 中的路径 u = v₀—v₁—…—v_t = v。
   - 归纳：若路径长度 t=1，则 (u,v) 已是边 transposition。
   - 若 t=2：已知 (u,w) 和 (w,v)，则 (u,v) = (u,w)(w,v)(u,w)（共轭）。
   - 对 t>2 递推：由归纳假设，所有长度 < t 的路径端点 transposition 均可生成，故长度为 t 的亦然。
   - 因此所有 transposition (u,v) 均在生成子群中。
   - 所有 transposition 的集合生成 S_n。∎

4. 将引理应用于 G = Q_k（k-维超立方体），|V| = 2^k = n。T(bitrev) 恰为 Q_k 边 transposition 在 bitrev 同构下的像，故生成 S_n。∎

## 定理 2：Gray 的 T(gray) 生成 S_n

**证明**：

Gray 编码 G(x) = x ⊕ (x >> 1) 是 {0,1}^k 上的双射。该映射下，Q_k 的边集映射为另一组 transposition。由于 G 是双射，新的边集构成的图同构于 Q_k（可能不是原始 Q_k，但仍是连通图——Gray 码的相邻性保证 Hamming-1 对映射后仍连通）。

**计算验证** [COMPUTATIONAL CERTIFICATE]：
- n=8 (k=3)：T(gray) 的 transposition 图有 12 条边（= k·2^(k-1)），连通，因此生成 S_8。
- n=16 (k=4)：T(gray) 图有 32 条边，连通，生成 S_16。

**理论论证**：Gray 映射保持 Hamming 邻接性（G 是线性映射 x → Mx，其中 M 是 GF(2) 上的可逆矩阵）。可逆线性映射保持图的度序列和连通性。因此 G(Q_k) 仍是 k-正则连通图，边 transposition 生成 S_n。∎

## 定理 3：两个 transposition 集的联合作用

**命题**：设 G₁, G₂ 是 {0,…,n-1} 上两个连通图。则它们边 transposition 的并集生成 S_n。

**证明**：令 H = ⟨T(G₁) ∪ T(G₂)⟩。由于 G₁ 连通，⟨T(G₁)⟩ = S_n。因此 H = S_n。∎

## 推论：p-adic transposition 搜索空间的完备性

对任意 n=2^k，bitrev + gray 的 transposition 联合集生成 S_n × S_n（on VALUE space）。这意味着：

> **任何一对排列 (π₀, π₁) 都可以通过有限序列的边 transposition 从 (bitrev, gray) 到达。**

特别地，若 NTIL 解存在，则存在 transposition 序列将其从 (bitrev, gray) 构造出来。SA 搜索的收敛性问题是**算法性的**（搜索复杂度），而非**存在性的**（路径必定存在，由群论保证）。
