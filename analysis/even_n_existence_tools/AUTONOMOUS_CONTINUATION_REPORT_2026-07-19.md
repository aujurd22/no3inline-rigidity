# “所有偶数 \(n\) 都有 \(2n\) 点”第二轮自主推进报告

日期：2026-07-19

前置总报告：`ALL_EVEN_N_RESEARCH_REPORT_2026-07-19.md`

## 0. 本轮裁决

本轮仍未证明：

> 每个偶数 \(n\) 的 \(n\times n\) 棋盘都存在 \(2n\) 个无三点共线点。

但理论接口有三项实质推进：

1. 把“许多模素数共线三元组”升级成一个真正的**正密度算术定理**：
   渐近至少四分之一的全部三元组行列式必须含有
   \(p\ge\sqrt n\) 的素因子；
2. 找到并证明了“永久保持全部短方向线和”方案的
   **\(Q^3\) Newton 多边形壁垒**，同时构造出尺度 \(Q=1,2\) 的最小二进制
   层析 trade；
3. 把正向 switch 从模糊的局部换位改写成
   **交替圈 + 割线 transversal**，并给出严格的单点插入代价和局部隔离
   半径。

所以现在最有希望的正向路线不再是“保持所有旧约束完全不变”，而是：

> 只命中真正饱和的二点割线，并允许其余短线负载重新分配。

## 1. 中大素因子的正密度定理

对任意 \(2n\) 点 NTIL 集和固定 \(0<\alpha<1\)，令

\[
\mathcal U_\alpha=
\{T:\exists p\ge n^\alpha,\ p\mid D(T)\}.
\]

本轮证明

\[
\boxed{
|\mathcal U_\alpha|
\ge
\left(\frac{1-\alpha}{2}+o(1)\right)\binom{2n}{3}.
}
\]

特别地，

\[
\boxed{
|\mathcal U_{1/2}|
\ge
\left(\frac14+o(1)\right)\binom{2n}{3}.
}
\]

证明的关键不是粗略地“每个行列式最多有三个大素因子”，而是给每个素数赋
对数权重

\[
w_p=\frac{\log p}{2\log n}.
\]

由于 \(|D|<(n)^2\)，同一行列式的全部权重和小于一；因此

\[
|\mathcal U_\alpha|
\ge
\frac1{2\log n}
\sum_{p\ge n^\alpha}T_p\log p.
\]

再代入有限域方向分盒下界并用

\[
\sum_{n^\alpha\le p\le n}\frac{\log p}{p}
=(1-\alpha)\log n+o(\log n)
\]

即得。

文件：`MEDIUM_PRIME_DENSITY_THEOREM.md`

### 已知解数据

\(n=72\) 的已知解中：

- 全部三元组：\(\binom{144}{3}\)；
- 行列式含 \(p\ge\sqrt{72}\) 素因子的三元组：409480；
- 实际比例：\(84.02\%\)；
- 严格有限阶对数权重下界：\(18.45\%\)；
- 同一行列式实际最多含三个这类不同素因子。

随机两置换样本的比例约为 \(82.57\%\)，所以“粗糙行列式总比例”本身不是
成功解的独有指纹；需要研究这些素因子标签如何分布在共享行、共享点的三元组
上。

数据：

- `medium_prime_coverage_n6_72.json`
- `random_medium_prime_coverage_n36_n72.json`

## 2. 大素数区间的严格无重复求和

对任意素数 \(n\le p<2n-2\)，证明

\[
T_p(S)\ge
\left\lceil\frac{2n(2n-p-2)}3\right\rceil.
\]

若 \(S\) 是整数 NTIL 集，则不同 \(p,q\ge n\) 不可能标记同一个三元组，
因为

\[
pq\ge n^2>(n-1)^2\ge|D|.
\]

于是至少有

\[
B(n)=
\sum_{\substack{n\le p<2n-2\\p\ {\rm prime}}}
\left\lceil\frac{2n(2n-p-2)}3\right\rceil
=
\left(\frac13+o(1)\right)\frac{n^3}{\log n}
\]

个彼此不同的三元组含有大于等于 \(n\) 的素因子。

\(n=72\) 的已知解中，实际有 63012 个这样的不同三元组，严格下界为
24000。

文件：`LARGE_PRIME_DISJOINT_SUPERSATURATION.md`

## 3. 完全屏蔽式层析 trade 的 \(Q^3\) 壁垒

设 signed switch \(h\) 在方向 \(d=(a,b)\) 的每条平行线上总和为零。
其 Laurent 多项式

\[
H(X,Y)=\sum h(x,y)X^xY^y
\]

必被

\[
X^aY^b-1
\]

整除。若同时保持方向集 \(D\) 的全部线和，则

\[
\prod_{d\in D}(X^{a_d}Y^{b_d}-1)\mid H.
\]

Newton 多边形立即给出

\[
\operatorname{width}_x(H)\ge\sum|a_d|,
\qquad
\operatorname{width}_y(H)\ge\sum|b_d|.
\]

对全部本原尺度 \(\le Q\) 的方向，

\[
\sum|a_d|
=\sum|b_d|
=\left(\frac6{\pi^2}+o(1)\right)Q^3.
\]

所以 \(n\times n\) 棋盘中任何非零完全屏蔽 trade 必须满足

\[
Q=O(n^{1/3}).
\]

这严格否定了“每完成一层，以后永远保持此前每条线负载完全不变”跨越全部尺度
的可能性。

### 正面的最小 trade

- \(Q=1\)：唯一最小 \(4\times4\) 二进制 permutation trade，正负各四点；
- \(Q=2\)：最小 \(10\times10\) 二进制 trade，正负各十二点，每侧每行每列
  至多二点；
- \(Q=3\)：边长 \(28\) 到 \(33\) 连不带行列容量限制的
  \(\{-1,0,1\}\) trade 都精确不可行；带每侧行列容量二时，边长 \(36\)
  仍精确不可行。

文件：`TOMOGRAPHIC_SWITCH_BARRIER.md`

## 4. 割线插入代价定理

对空格 \(z\)，令 \(\sigma_Q(z)\) 为经过 \(z\) 的短非轴二点割线数。

由于旧配置无三点线，这些割线的端点对两两不交。若一个安全 switch 加入
\(z\)，则必须：

1. 从 \(z\) 所在行至少删除一个旧点；
2. 从 \(z\) 所在列至少删除一个旧点；
3. 从每条经过 \(z\) 的旧二点割线至少删除一个端点。

三类旧点彼此不重合，所以若 switch 删除 \(r\) 点，则

\[
\boxed{
r\ge2+\sigma_Q(z).
}
\]

再把行列饱和 switch 分解成二部图交替圈，可定义严格局部半径

\[
\rho_Q(S)=
\min_C\max\left\{
|A(C)|,\,
2+\max_{z\in A(C)}\sigma_Q(z)
\right\}.
\]

任何另一短尺度安全配置都至少删除 \(\rho_Q(S)\) 个旧点。

### \(n=72\) 的严格结果

\[
\begin{array}{c|c}
Q\text{ 起点}&\rho_Q\\
\hline
2&2\\
5&3\\
17&4\\
31&5
\end{array}
\]

完整方向下：

> 任何另一行列饱和 NTIL 配置都必须至少删除五点、加入五点；对称差至少十。

这是割线覆盖与最短交替圈给出的证明，不是搜索未命中。

文件：`SECANT_INSERTION_RIGIDITY.md`

## 5. 对 switch 路线的纠错

固定两张完美匹配中的两行换位过窄。扩大到一般矩形重连后，
\(n=36\) 存在只改两旧点、两新点且保护全部尺度 \(<5\) 的 move：

\[
(9,1),(24,28)
\longmapsto
(9,28),(24,1).
\]

但一般矩形重连仍然很快枯竭：

- \(n=72\) 有 10008 个合法矩形重连；
- 保护尺度 \(<4\) 的只有八个；
- 保护尺度 \(<5\) 的为零；
- 没有一个直接到达另一完整 NTIL 解。

三边交替圈的完整枚举也没有直接 NTIL 邻居。

文件：

- `SWITCH_SCALE_EXPERIMENTS.md`
- `general_rectangle_switches_n6_72.json`
- `three_edge_cycle_switches_n12_36.json`

## 6. 现在最值得攻的正向核心引理

对当前短尺度安全配置 \(S\)，建立有向二部图：

- 旧点边由列指向行，表示可删除；
- 空格边由行指向列，表示可加入；
- 空格 \(z\) 携带一个由旧割线端点对组成的 matching
  \(\mathcal H_z\)。

需要寻找有向交替圈 \(C\)，使：

1. 删除边集 \(R(C)\) 命中每个 \(z\in A(C)\) 的全部
   \(\mathcal H_z\)；
2. 任意两个新增点与任何保留旧点不共线；
3. 新增点内部无三点线。

若能证明下列形式的引理，正向多尺度归纳才真正成立：

> 在关闭尺度 \(<Q\) 后，每个 \(Q\)-尺度冲突附近都存在长度
> \(Q^{O(1)}\) 的交替圈，且其删除边同时是所有新增点割线 matching 的
> transversal；圈之间具有足够小的 codegree，可并行选择线性多个。

这比上一轮的“固定比例随机安全 switch”更具体，也自动避开：

- 固定两置换分解；
- 完全 X-ray 保持的 \(Q^3\) 唯一性壁垒；
- 常数半径局部极小。

及时止损条件：

- 若所需圈长必为 \(\exp(\Omega(Q^2))\)，无法跨越全部尺度；
- 若割线 matching 的联合 transversal 典型大小与新增点数之比持续大于一，
  闭包过程是超临界的，正向路线应停止。

## 7. 现在最值得攻的反向核心引理

每组三行给出八个行列式值，它们组成一个三维仿射整数立方：

\[
D_{\varepsilon_1,\varepsilon_2,\varepsilon_3}
=D_0+\varepsilon_1A+\varepsilon_2B+\varepsilon_3C.
\]

中大素因子定理说明，跨全部行三元组，这些八值立方至少有四分之一的顶点带
\(\ge\sqrt n\) 的素因子。

反向最具体的接口是研究：

1. 一个大素数能在同一八值立方中标记多少顶点；
2. 列饱和条件如何耦合不同三行立方的 \(A,B,C\)；
3. 零行列式被完全排除时，大素数标签是否被迫异常集中；
4. 这种集中能否由筛法、加法能量或容器定理否定。

这条路线现在有明确的常数目标：任何上界若不能压到全部三元组的 \(1/4\)
以下，就不可能与新定理形成矛盾。

## 8. 最终方向排序

1. **首选正向：割线 transversal 交替圈。**
   它是目前唯一同时尊重全 2-factor 自由度和短尺度障碍的构造接口。
2. **首选反向：八行列式立方上的中大素因子标签。**
   新的 \(1/4\) 密度下界提供了可量化目标。
3. **辅助工具：\(Q=1,2\) 层析 absorber。**
   可用来预埋最短方向的完全安全修补元件，但不能独立跨越
   \(Q\gg n^{1/3}\)。
4. **停止投入：**
   固定匹配换位、保持全部旧线和、只对大素数计数不处理标签相关性，以及继续
   单点加算力搜索。

## 9. 本轮新增程序与数据

- `analyze_large_prime_carries.py`
- `large_prime_carries_n6_72.json`
- `analyze_medium_prime_coverage.py`
- `medium_prime_coverage_n6_72.json`
- `sample_random_medium_prime_coverage.py`
- `random_medium_prime_coverage_n36_n72.json`
- `analyze_switch_scale_safety.py`
- `switch_scale_safety_n6_72.json`
- `analyze_general_rectangle_switches.py`
- `general_rectangle_switches_n6_72.json`
- `analyze_three_edge_cycle_switches.py`
- `nearest_short_scale_neighbor_sat.py`
- `analyze_secant_insertion_cost.py`
- `secant_insertion_cost_full_n6_72.json`
- `secant_insertion_cost_n72_all_scales.json`
- `search_tomographic_binary_trade.py`
- `tomographic_trade_q1_l4.json`
- `tomographic_trade_q2_l10.json`

## 10. 最简结论

本轮没有把开放问题直接闭合，但已经排除了两个过强的证明模板，并把正反两侧
都压缩到可写成精确引理的对象：

- 正向是“交替圈能否同时命中全部割线 matching”；
- 反向是“八值行列式立方能否承载至少四分之一的中大素因子标签而永远避开零”。

如果继续推进，应该只围绕这两个对象做定理，不再扩散到新的漂亮公式族。
