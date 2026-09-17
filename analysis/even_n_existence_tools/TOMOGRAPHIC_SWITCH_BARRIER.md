# 短方向层析 trade 的 \(Q^3\) 壁垒

日期：2026-07-19

## 1. 为什么研究 line-sum trade

若一个 signed pattern

\[
h:\mathbb Z^2\to\{-1,0,1\}
\]

的负支撑表示删除的点，正支撑表示加入的点，并且它在某个方向的每条平行线上
总和都为零，那么 switch 前后该方向的每条直线负载完全相同。

因此，若已经关闭所有本原方向尺度小于 \(Q\) 的三点冲突，一个同时保持这些
方向全部线和的 trade 是绝对安全的：它不可能重新打开任何已关闭方向。包含
横、竖方向还会自动保持每行、每列的点数。

下面的定理说明这种“完全屏蔽式”宏观 switch 有一个严格的 \(Q^3\) 几何壁垒。

## 2. 一般定理

设 \(D\) 是一组互不平行的本原整数方向，每个无向方向只取一个代表

\[
d=(a_d,b_d).
\]

设非零有限支撑函数 \(h:\mathbb Z^2\to\mathbb Q\) 在 \(D\) 中每个方向的
每条平行线上总和均为零。若 \(h\) 的支撑横向宽度为 \(W_x\)、纵向宽度为
\(W_y\)，则

\[
\boxed{
W_x\ge\sum_{d\in D}|a_d|,
\qquad
W_y\ge\sum_{d\in D}|b_d|.
}
\tag{1}
\]

这里宽度是最大坐标减最小坐标；若支撑放在 \(n\times n\) 棋盘中，
\(W_x,W_y\le n-1\)。

### 证明

定义 Laurent 多项式

\[
H(X,Y)=\sum_{(x,y)}h(x,y)X^xY^y.
\]

对本原方向 \(d=(a,b)\)，考虑环同态

\[
X\mapsto t^b,\qquad Y\mapsto t^{-a}.
\]

所得 \(t^c\) 的系数恰是法向坐标

\[
bx-ay=c
\]

那条直线上的 \(h\) 总和。全部线和为零等价于

\[
H\in\ker\psi_d.
\]

由于 \((a,b)\) 本原，

\[
\ker\psi_d=(X^aY^b-1).
\]

不同本原无向方向给出互不相伴的素 Laurent 二项式，所以

\[
\prod_{d\in D}(X^{a_d}Y^{b_d}-1)\mid H.
\tag{2}
\]

乘积的 Newton 多边形是线段 \([0,d]\) 的 Minkowski 和。其横向宽度为
\(\sum|a_d|\)，纵向宽度为 \(\sum|b_d|\)。多项式乘法的 Newton 多边形
等于两个因子的 Minkowski 和，故 \(H\) 的宽度不能更小，得到 (1)。

## 3. 尺度 \(Q\) 的推论

令 \(D_Q\) 包含全部

\[
\gcd(a,b)=1,\qquad \max(|a|,|b|)\le Q
\]

的无向本原方向，并规范取 \(a>0\)，另加 \((0,1)\)。则

\[
\sum_{d\in D_Q}|a_d|
=\sum_{d\in D_Q}|b_d|
=\left(\frac6{\pi^2}+o(1)\right)Q^3.
\tag{3}
\]

所以 \(n\times n\) 棋盘内存在非零完全屏蔽 trade 的必要条件是

\[
\boxed{
Q\le
\left(\frac{\pi^2}{6}+o(1)\right)^{1/3}n^{1/3}.
}
\tag{4}
\]

等价地，只要短方向线和一直保持不变，尺度推进到常数倍 \(n^{1/3}\) 后，
配置就已被这些 X-ray 唯一确定，不再存在任何非平凡 switch。

这不是概率障碍，而是确定性的代数唯一性定理。

## 4. 小尺度的精确 trade

直接取规范乘积

\[
P_Q(X,Y)=
\prod_{d\in D_Q}(X^{a_d}Y^{b_d}-1).
\tag{5}
\]

前五个尺度的方向数、必要宽度和系数如下：

\[
\begin{array}{c|c|c|c|c}
Q&|D_Q|&\sum|a|=\sum|b|&
|\operatorname{supp}P_Q|&\max|\operatorname{coef}P_Q|\\
\hline
1&4&3&8&1\\
2&8&9&24&1\\
3&16&27&296&2\\
4&24&51&1472&10\\
5&40&111&7960&114
\end{array}
\]

因此：

- \(Q=1\) 给出一个 \(4\times4\)、正负各四点的二进制 permutation trade；
- \(Q=2\) 给出一个 \(10\times10\)、正负各十二点、每行每列每侧至多两点
  的二进制 trade；
- 从 \(Q=3\) 起，最小 Newton 乘积本身已出现系数 \(2\)，不能直接解释为
  删除/加入点。

`search_tomographic_binary_trade.py` 的精确 CP-SAT 结果进一步给出：

\[
\begin{array}{c|c|c}
Q&\text{边长与容量}&\text{结果}\\
\hline
1&4,\ \text{每侧行列容量 }1&\texttt{OPTIMAL},\
|\operatorname{supp}|=8\\
2&10,\ \text{每侧行列容量 }2&\texttt{OPTIMAL},\
|\operatorname{supp}|=24\\
3&28,30,36,\ \text{容量 }2&\texttt{INFEASIBLE}\\
3&28,\ldots,33,\ \text{不设行列容量}&\texttt{INFEASIBLE}
\end{array}
\]

\(Q=3,n=28\) 的不可行还可直接由 Newton 多边形证明：宽度已经恰好达到
下界，商多项式只能是单项式，而 \(P_3\) 含系数 \(\pm2\)。

精确证书数据：

- `tomographic_trade_q1_l4.json`
- `tomographic_trade_q2_l10.json`
- `tomographic_trade_q3_l28_c2.json`
- `tomographic_trade_q3_l36_c2.json`
- `tomographic_trade_q3_l29_unbounded.json`
- `tomographic_trade_q3_l30_unbounded.json`
- `tomographic_trade_q3_l33_unbounded.json`

## 5. 对正向证明路线的裁决

这条结果同时带来一个正面工具和一个负面边界。

正面：

- 对任何固定的有限方向集，总能用二项式乘积制造有理或整数 line-sum trade；
- \(Q=1,2\) 已有非常小的二进制 absorber，可作为实际构造中的预埋元件；
- 选择方向的适当倍数并使子集和互异，可以对任意固定 \(D\) 构造
  \(\{-1,0,1\}\) trade，代价是很大的支撑。

负面：

- “每完成一层就永久保持此前所有线负载完全不变”最多推进到
  \(Q=O(n^{1/3})\)；
- 它不可能独自跨越全部 \(O(n)\) 方向尺度；
- 从 \(Q=3\) 开始，甚至把整数 kernel 元素转成行列容量二的二进制 switch
  已经是非平凡问题。

所以真正的多尺度 switch 必须允许短方向线和发生受控变化，只维持负载
\(\le2\)，而不是要求线和逐条不变。下一版核心引理应改写为“带 slack 的
层析 trade”，把已经饱和的二点线作为障碍集，只保护这些线，而不保护所有
短线。
