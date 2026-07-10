# Th-19 定理理论文档

## Motzkin 高度—π 分布恒等式

**定理（Th-19）**。对任意 NTIL 解，令 sig ∈ {L,B,R}ⁿ 为列共享签名，h(c)=L(≤c)-R(≤c) 为 Motzkin 路径高度，count_π(≤c) 为 ≤c 的 π 值个数。则：

$$h(c) = \text{count}_\pi(\leq c) - (c+1)$$

对所有 c∈[0,n-1] 成立。

**证明**：

$$\begin{aligned}
\text{count}_\pi(\leq c) &= \sum_{j=0}^{c} m_\pi(j) \\
&= \sum_{j=0}^{c} [2\cdot \mathbf{1}_{\text{sig}[j]=L} + 1\cdot \mathbf{1}_{\text{sig}[j]=B} + 0\cdot \mathbf{1}_{\text{sig}[j]=R}] \\
&= 2L(\leq c) + B(\leq c) \\
&= 2L(\leq c) + [(c+1) - L(\leq c) - R(\leq c)] \\
&= L(\leq c) + (c+1) - R(\leq c) \\
&= (c+1) + [L(\leq c)-R(\leq c)] \\
&= (c+1) + h(c) \quad \square
\end{aligned}$$

**验证**：21,701 rot4 解 + 1,146 rct4 解，零反例。

### 推论

1. **Dyck 条件**（Th-16 代数形式）：h(c)≥0 ⇔ count_π(≤c) ≥ c+1
2. **前缀饱和**：h(c)=0 ⇔ count_π(≤c)=c+1，即 π 完全填满前 c+1 个列
3. **C₄ 高度镜像对称**：h(n-1-i) = h(i-1)（由 C₄ 互补性 sig[n-1-i]=complement(sig[i]) 导出）
4. **Motzkin 不可约性**（Th-18 代数解释）：首次归零处 h(c)=0 ⇒ π 前 c+1 个列完全填满

### 意义

Th-19 在**NTIL 解的组合数据结构与 Motzkin 路径框架之间建立了精确的代数桥梁**。它将几何概念（签名）与代数结构（π 值的累积分布）直接连接。这是继 Th-17（Motzkin 路径定理）之后最深层的结构恒等式。
