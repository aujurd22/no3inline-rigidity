# Switch Average Drift Theorem

## 问题

Lemma 1a/1b 只证明「存在一个 2-switch 可以消掉指定冲突」，但未证明总能量 $B$ 严格下降——新冲突可能在别处产生。

## 新思路：平均漂移

定义：对构型 $f$（$m$ 个 cell 的 2-因子），令 $\mathcal{S}(f)$ 为所有合法 2-switch 的集合。每个 $s\in\mathcal{S}(f)$ 对应一对 cell $(i,j)$ 和一个操作类型 $t\in\{YSWAP,XSWAP,XYSWAP\}$，共 $3\binom m2$ 种。

定义总漂移：
$$S(f)=\sum_{s\in\mathcal{S}(f)}\Delta B(s)$$

**定理（平均漂移）**：若 $B(f)>0$，则 $S(f)<0$。

**推论**：$S(f)<0\;\Rightarrow\;$存在至少一个 $s_0\in\mathcal{S}(f)$ 使得 $\Delta B(s_0)<0$（鸽笼原理）。

## 双计数论证

将 $\Delta B(s)$ 分解为「消除的坏线数—新增的坏线数」：

$$\Delta B(s)=\sum_{L\in\text{lines}}\big[C(c_L',3)-C(c_L,3)\big]$$

其中 $c_L$ 为 switch 前线 $L$ 上的点数，$c_L'$ 为 switch 后。

每个 2-switch 只影响 8 个提升点（来自 switch 涉及的 2 个 cell 的 $4\times2$ 个旋转像）。所以只有包含这 8 个点中至少一个的线会变化。

记 $\text{aff}(s)$ 为 switch $s$ 涉及的 8 个提升点的索引集。

### 摧毁项

对当前坏线 $L$（$c_L=c\ge3$ 个点），一个 switch $s$ 消除该线的贡献为：

$$\Delta_L^-(s)=C(c,3)-C(c',3)\ge C(c,3)-C(c-1,3)=\binom{c-1}{2}$$

当 $s$ 从 $L$ 上至少移除 1 个点时（把该点所属的 cell 的坐标改变），这个贡献为正。

### 创造项

对当前非坏线 $L$（$c_L=c\le2$），一个 switch $s$ 新增该线的贡献为：

$$\Delta_L^+(s)=C(c',3)-C(c,3)$$

当 $s$ 在 $L$ 上至少新增 1 个点时。

### 总漂移的双计数

$$S(f)=\sum_{s}\sum_{L}\big[\Delta_L^-(s)-\Delta_L^+(s)\big]
=\sum_{L}\sum_{s}\big[\Delta_L^-(s)-\Delta_L^+(s)\big]$$

交换求和顺序是关键：对**每条线**分别计算「经过它的 switch 的净摧毁贡献」。

### 对一条线的分析

固定线 $L$。设 $P(L)=\{p_1,\dots,p_c\}$ 为当前在 $L$ 上的提升点集。

**摧毁来源**：任意 $i\in P(L)$，任意包含 $p_i$ 的 2-switch（即 $p_i$ 所属的 cell 被 swap），且 switch 后 $p_i$ 不再在 $L$ 上，且 $L$ 上剩余点 $<3$。

**创造来源**：任意目前不在 $L$ 上的点 $q$，若 $s$ 将 $q$ 移到 $L$ 上且 $L$ 上总点数 $\ge3$。

**界**：
- 单个点 $p$ 参与 $\le 3(m-1)$ 个 switch（与任意另一 cell 的 3 种操作）
- 而将 $q$ 移到 $L$ 上的 switch 更少——$q$ 必须来自特定 cell 的对换

> **核心观察**：对一条包含 $c$ 个点的线，存在 $\Theta(cm)$ 个 destructive switch 候选，但仅 $\Theta(m)$ 个 creative switch 候选。当 $c\ge3$ 时前者占优。

## 数值验证

在下计算 $S(f)$ 的经验值。
