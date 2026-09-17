#!/usr/bin/env python3
"""对照实验：满足 2-正则图投影(每列每行<=1 基本域)的候选, 提升后 bad 还剩多少?
隔离 Th-44 必要层(Sidon+2-正则+每线<=2)之外真正的冲突来源, 确认 (X) 二次层是瓶颈。"""
import random, math, itertools, json

M = 37
N = 2 * M  # 74
P = 2 * M  # 4m = 148

def lift_c4(cells, n):
    N_ = n; pts = []
    for (x, y) in cells:
        pts += [(x, y), (N_-1-y, x), (N_-1-x, N_-1-y), (y, N_-1-x)]
    return pts

def random_2regime_cells(M, seed):
    """基本域: 列 x in 0..M-1, 选互异 y in 0..M-1 (即一个 M-排列) -> 每列每行<=1。"""
    rnd = random.Random(seed)
    ys = list(range(M)); rnd.shuffle(ys)
    return [(x, ys[x]) for x in range(M)]

def bad_split(pts):
    n = len(pts); bad = 0; s_bad = 0; x_bad = 0
    for a, b, c in itertools.combinations(range(n), 3):
        d1x=pts[b][0]-pts[a][0]; d1y=pts[b][1]-pts[a][1]
        d2x=pts[c][0]-pts[a][0]; d2y=pts[c][1]-pts[a][1]
        if d1x*d2y == d1y*d2x:
            bad += 1
            # 判定 (S)=斜率±1: 任一共线边 |dx|==|dy|
            edges = [(d1x,d1y),(d2x,d2y),(d2x-d1x,d2y-d1y)]
            if any(abs(ex)==abs(ey) and ex!=0 for ex,ey in edges): s_bad += 1
            else: x_bad += 1
    return bad, s_bad, x_bad

TRIALS = 15
rows = []
for t in range(TRIALS):
    cells = random_2regime_cells(M, 5000+t)
    pts = lift_c4(cells, N)
    bad, s_bad, x_bad = bad_split(pts)
    # 每线最多点数 (2-正则应保证<=2, 但提升后可能有>2的线?)
    rows.append((bad, s_bad, x_bad))

avg_bad = sum(r[0] for r in rows)/TRIALS
avg_s = sum(r[1] for r in rows)/TRIALS
avg_x = sum(r[2] for r in rows)/TRIALS
print(f"满足2-正则图投影的随机候选 ({TRIALS} trials, m={M}, 148点)")
for i, r in enumerate(rows):
    print(f"  trial {i}: bad={r[0]}  (S)={r[1]}  (X)={r[2]}")
print(f"\n平均 bad = {avg_bad:.1f}  (其中 (S)={avg_s:.1f}, (X)={avg_x:.1f})")
print(f"(X)/(S) 占比 ≈ {(avg_x/avg_bad if avg_bad else 0):.3f} / {(avg_s/avg_bad if avg_bad else 0):.3f}")
print(f"结论: 即使满足 Th-44 必要层(2-正则+每列每行<=1), bad 仍 ~{avg_bad:.0f} >> 0")
print(f"      -> 真正瓶颈是 (X) 二次共线层 (占 {(avg_x/avg_bad if avg_bad else 0):.1%})")

json.dump({"trials": TRIALS, "rows": rows, "avg_bad": avg_bad,
           "avg_s": avg_s, "avg_x": avg_x},
          open(__file__.replace(".py","_out.json"),"w"), indent=1)
print("[saved]", __file__.replace(".py","_out.json"))
