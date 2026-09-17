"""A-priori number-theoretic characterization of the 666 extreme high-codegree
pairs at m=37. Goal: predict WITHOUT building the full hypergraph which
transpose pairs (i,j)<->(j,i) become extreme (co3 > 800), so they can serve as
a cheap SAT preprocessor and as a structural theorem.

Outputs:
  results/extreme_pair_structure.md   (report)
  results/extreme_pair_structure.json (raw stats)
"""
import numpy as np, json, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve_m37_r9b import generate_constraints

m = 37
t0 = time.time()
reps, line_cons, twofactor = generate_constraints(m, False)
nrep = len(reps)
print(f"[load] reps={nrep} lines={len(line_cons)} ({time.time()-t0:.1f}s)", flush=True)

# ---- build co3 matrix (full, for verification) ----
# line_cons is a list of {rep_idx: weight}; (X) codegree per pair = (L-2)
# where L = number of distinct cells on the line (same as codegree_m37.py).
co3 = np.zeros((nrep, nrep), dtype=np.int32)
for pos_w in line_cons:
    cells = list(pos_w.keys())
    L = len(cells)
    if L < 3:
        continue
    idx = np.array(cells, dtype=np.int32)
    iu, ju = np.triu_indices(L, k=1)
    np.add.at(co3, (idx[iu], idx[ju]), L - 2)
    np.add.at(co3, (idx[ju], idx[iu]), L - 2)
print(f"[co3] built max={co3.max()} ({time.time()-t0:.1f}s)", flush=True)

# ---- coordinate -> index map ----
coord_idx = {(x, y): i for i, (x, y) in enumerate(reps)}

# ---- collect all transpose pairs (a,b) with a<b ----
trans = []          # (a,b,co3)
for a in range(nrep):
    x, y = reps[a]
    b = coord_idx.get((y, x))
    if b is not None and b > a:
        trans.append((a, b, int(co3[a, b])))
print(f"[trans] {len(trans)} transpose pairs", flush=True)

# global extremes
uu = np.triu_indices(nrep, k=1)
gvals = co3[uu[0], uu[1]]
extreme_global = int((gvals > 800).sum())
max_co3 = int(gvals.max())
print(f"[extreme] co3>800 global pairs = {extreme_global}, max = {max_co3}", flush=True)

# ---- among transpose pairs, distribution ----
tco3 = np.array([c for (_, _, c) in trans])
print(f"[trans] co3: max={tco3.max()} mean={tco3.mean():.1f} "
      f"#(>800)={int((tco3>800).sum())} #(>400)={int((tco3>400).sum())}", flush=True)

# ---- feature extraction for extreme transpose pairs ----
extreme_trans = [(a, b, c) for (a, b, c) in trans if c > 800]
feat = []
for (a, b, c) in extreme_trans:
    x, y = reps[a]
    # (x,y) and (y,x) are the pair
    s = x + y                       # anti-diagonal coordinate
    d = x - y                       # off-anti-diagonal
    g = np.gcd(x, y)
    # in 2m-board coords the 4 lift points of (x,y) sit at (2(m-x)-1, ...);
    # center offset of fundamental cell:
    cx = m - 0.5 - x
    cy = m - 0.5 - y
    r2 = cx * cx + cy * cy          # squared distance to C4 center
    feat.append(dict(x=x, y=y, s=s, d=d, gcd=g, r2=r2, co3=c))

# ---- statistics on features ----
import collections
def hist(vals, bins):
    h = collections.Counter()
    for v in vals:
        for lo, hi in bins:
            if lo <= v < hi:
                h[(lo, hi)] += 1
                break
    return dict(h)

s_vals = [f['s'] for f in feat]
d_vals = [f['d'] for f in feat]
g_vals = [f['gcd'] for f in feat]

# how many extreme pairs have s near the anti-diagonal through center?
# anti-diagonal through center cell: x+y = m-1 (since coords 0..m-1)
s_center = m - 1
near_center = sum(1 for s in s_vals if abs(s - s_center) <= 2)

# gcd>=2 fraction
gcd_ge2 = sum(1 for g in g_vals if g >= 2)

# d = x-y : extreme pairs should have small |d| if near anti-diagonal
d_small = sum(1 for d in d_vals if abs(d) <= 3)

# ---- contrast: ALL transpose pairs feature distribution ----
all_s = [reps[a][0] + reps[a][1] for (a, b, c) in trans]
all_d = [reps[a][0] - reps[a][1] for (a, b, c) in trans]
all_g = [int(np.gcd(reps[a][0], reps[a][1])) for (a, b, c) in trans]

# ---- attempt a predictive rule ----
# Hypothesis: extreme iff (x+y close to center anti-diagonal) AND (|x-y| small)
rule_hits = 0
rule_total_extreme = len(extreme_trans)
rule_false_pos = 0
rule_false_neg = 0
for (a, b, c) in trans:
    x, y = reps[a]
    pred = (abs((x + y) - s_center) <= 2) and (abs(x - y) <= 3)
    if pred and c > 800:
        rule_hits += 1
    elif pred and c <= 800:
        rule_false_pos += 1
    elif (not pred) and c > 800:
        rule_false_neg += 1

# ---- emit ----
report = {}
report['m'] = m
report['nrep'] = nrep
report['n_lines'] = len(line_cons)
report['extreme_global_pairs_co3gt800'] = extreme_global
report['max_co3'] = max_co3
report['n_transpose_pairs'] = len(trans)
report['transpose_pairs_co3gt800'] = int((tco3 > 800).sum())
report['transpose_pairs_co3gt400'] = int((tco3 > 400).sum())
report['extreme_trans_count'] = len(extreme_trans)
report['extreme_fraction_of_all_transpose'] = len(extreme_trans) / len(trans)
report['feature_s_center'] = s_center
report['extreme_s_near_center_frac'] = near_center / len(extreme_trans)
report['extreme_gcd_ge2_frac'] = gcd_ge2 / len(extreme_trans)
report['extreme_small_d_frac'] = d_small / len(extreme_trans)
report['all_transpose_mean_s'] = float(np.mean(all_s))
report['all_transpose_mean_d'] = float(np.mean(all_d))
report['all_transpose_gcd_ge2_frac'] = sum(1 for g in all_g if g >= 2) / len(all_g)
report['predict_rule'] = dict(cond="abs(x+y-(m-1))<=2 AND abs(x-y)<=3",
                              hits=rule_hits, false_pos=rule_false_pos,
                              false_neg=rule_false_neg,
                              precision=rule_hits / max(1, rule_hits + rule_false_pos),
                              recall=rule_hits / max(1, rule_fits := rule_hits + rule_false_neg))

with open('results/extreme_pair_structure.json', 'w') as f:
    json.dump({'report': report,
               'extreme_pairs': [(reps[a][0], reps[a][1], c) for (a, b, c) in extreme_trans]},
              f, indent=1)

L = []
L.append(f"# Extreme transpose-pair structure at m={m}\n")
L.append(f"- nrep(候选cells)={nrep}, 线数={len(line_cons)}")
L.append(f"- **全局 co3>800 配对: {extreme_global}**（max_co3={max_co3}）")
L.append(f"- 转置对总数: {len(trans)}；其中 co3>800: {int((tco3>800).sum())}；co3>400: {int((tco3>400).sum())}")
L.append(f"- 极端转置对(>800)数: **{len(extreme_trans)}** —— 占全部转置对 {len(extreme_trans)/len(trans)*100:.1f}%\n")
L.append("## 特征统计（极端转置对 vs 所有转置对）\n")
L.append(f"- 极端对中 s=x+y 接近中心反对角(m-1={s_center}) 的比例: **{near_center/len(extreme_trans)*100:.1f}%**")
L.append(f"- 极端对中 gcd(x,y)>=2 比例: **{gcd_ge2/len(extreme_trans)*100:.1f}%**（所有转置对仅 {sum(1 for g in all_g if g>=2)/len(all_g)*100:.1f}%）")
L.append(f"- 极端对中 |x-y|<=3 比例: **{d_small/len(extreme_trans)*100:.1f}%**")
L.append(f"- 所有转置对: mean s={np.mean(all_s):.1f}, mean |d|={np.mean(np.abs(all_d)):.1f}\n")
L.append("## 预测规则尝试\n")
L.append(f"- 规则: `abs(x+y-(m-1))<=2 AND abs(x-y)<=3`")
L.append(f"  - 命中(极端且预测): {rule_hits}")
L.append(f"  - 假阳性(预测极端但co3<=800): {rule_false_pos}")
L.append(f"  - 假阴性(极端但未预测): {rule_false_neg}")
if rule_hits + rule_false_pos > 0:
    L.append(f"  - 精确率(precision)= {rule_hits/(rule_hits+rule_false_pos):.3f}")
L.append(f"  - 召回率(recall)= {rule_hits/max(1,rule_hits+rule_false_neg):.3f}\n")
L.append("## 解读\n")
L.append("- 若 precision/recall 都高，则极端对可由简单数论条件 a-priori 预测，")
L.append("  无需建完整超图即可作为 SAT 预处理器硬禁。")
L.append("- 否则极端对是 emergent（需完整共线计数），只能事后提取。")
with open('results/extreme_pair_structure.md', 'w') as f:
    f.write("\n".join(L))

print("[done] wrote results/extreme_pair_structure.md / .json", flush=True)
print(f"  extreme_trans={len(extreme_trans)} s_near_center={near_center/len(extreme_trans):.2f} "
      f"gcd_ge2={gcd_ge2/len(extreme_trans):.2f} rule_recall={rule_hits/max(1,rule_hits+rule_false_neg):.2f}", flush=True)
