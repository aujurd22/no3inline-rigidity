#!/usr/bin/env python3
"""
recovery_exp.py -- 用已知解做"魔方式恢复"实验（用户发散思路）：

  1. 取已知 rot4-NTIL 解 (analysis/results/solutions/mXX.json) 当完美初始态
  2. 打乱 k 个点（移到随机其它位置）
  3. 用局部搜索恢复：单点移动 / 多点同时移动（move_size）
  4. 比较：吸引域半径(k)、move_size、局部化修复(focus=打乱点) vs 全局
  5. [可选, --m37-warm] 发散：m=37 热启动探测（默认关闭，先小 m 摸规律）

坐标约定严格复用 quadratic_sidon_completeness.c4（奇数坐标 + C4 提升）。
增量共线计数：每条线维护点集合，移动一个 cell(4 点) 只改 O(8P) 处，P=4m。

默认运行（小 m 规律）:
  python recovery_exp.py --ms 8,10,12,14,16 --ks 1,2,3,5,8,12 --move-sizes 1,2,3
"""
import sys, os, json, time, math, random, argparse
from collections import defaultdict

# ── 坐标约定（与 quadratic_sidon_completeness.c4 一致）──────────────────────
def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def lift(cells, m):
    n = 2 * m
    pts = []
    for (x, y) in cells:
        for r in range(4):
            pts.append(c4((x, y), r, n))
    return pts

def brute_collinear(cells, m):
    pts = lift(cells, m)
    P = len(pts)
    for i in range(P):
        x1, y1 = pts[i]
        for j in range(i + 1, P):
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            for k in range(j + 1, P):
                if dx * (pts[k][1] - y1) == dy * (pts[k][0] - x1):
                    return True
    return False

# ── 增量共线计数器 ────────────────────────────────────────────────────────
def line_key(p1, p2):
    x1, y1 = p1; x2, y2 = p2
    A = y2 - y1; B = x1 - x2; C = x2 * y1 - x1 * y2
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g != 0:
        A //= g; B //= g; C //= g
    for v in (A, B, C):
        if v != 0:
            if v < 0:
                A = -A; B = -B; C = -C
            break
    return (A, B, C)

class BadCounter:
    """维护 lines[key] = 在该直线上的点索引集合；bad = sum C(|S|,3)。"""
    def __init__(self, cells, m):
        self.m = m; self.n = 2 * m
        self.cells = [tuple(c) for c in cells]
        self.pts = lift(self.cells, m)
        self.lines = defaultdict(set)
        P = len(self.pts)
        for i in range(P):
            pi = self.pts[i]
            for j in range(i + 1, P):
                k = line_key(pi, self.pts[j])
                self.lines[k].add(i); self.lines[k].add(j)
        self.bad = self._recompute()

    def _recompute(self):
        return sum(math.comb(len(s), 3) for s in self.lines.values())

    def move_cell(self, idx, newcell):
        old = self.cells[idx]
        # 移除旧 4 点
        for r in range(4):
            pi = idx * 4 + r
            p = self.pts[pi]
            for j in range(len(self.pts)):
                if j == pi:
                    continue
                k = line_key(p, self.pts[j])
                s = self.lines.get(k)
                if s is not None:
                    s.discard(pi)
                    if not s:
                        del self.lines[k]
        # 放新 4 点
        self.cells[idx] = tuple(newcell)
        newpts = [c4(newcell, r, self.n) for r in range(4)]
        for r in range(4):
            pi = idx * 4 + r; p = newpts[r]; self.pts[pi] = p
            for j in range(len(self.pts)):
                if j == pi:
                    continue
                k = line_key(p, self.pts[j])
                self.lines[k].add(pi)
        self.bad = self._recompute()
        return self.bad

# ── 已知解加载 ────────────────────────────────────────────────────────────
def load_ref(m, base="analysis/results/solutions"):
    path = os.path.join(base, f"m{m:02d}.json")
    with open(path) as f:
        d = json.load(f)
    return [tuple(c) for c in d["cells"]]

# ── 打乱 ──────────────────────────────────────────────────────────────────
def scramble(cells, k, rng):
    cells = [tuple(c) for c in cells]
    occ = set(cells)
    idxs = rng.sample(range(len(cells)), min(k, len(cells)))
    for i in idxs:
        while True:
            nc = (rng.randrange(len(cells)), rng.randrange(len(cells)))
            if nc not in occ:
                break
        occ.discard(cells[i]); occ.add(nc)
        cells[i] = nc
    return cells, idxs

# ── 恢复（局部搜索，支持多点同时移动）────────────────────────────────────
def recover(cells0, m, move_size, mode, iters, rng, focus=None,
            T0=None, T1=0.2, traj_every=200):
    bc = BadCounter(cells0, m)
    bad = bc.bad
    best = bad; best_cells = list(bc.cells)
    free = list(focus) if focus is not None else list(range(m))
    if not free:
        return False, False, best, [best], best_cells
    if T0 is None:
        T0 = max(2.0, m * 1.0)
    traj = [bad]
    for it in range(iters):
        if bad == 0:
            break
        T = T0 * ((T1 / T0) ** (it / iters)) if mode == "sa" else 0.0
        picks = rng.sample(free, min(move_size, len(free)))
        olds = [bc.cells[k] for k in picks]
        occupied = set(bc.cells) - set(olds)
        news = []
        for k in picks:
            while True:
                nc = (rng.randrange(m), rng.randrange(m))
                if nc not in occupied and nc not in news:
                    break
            news.append(nc); occupied.add(nc)
        for k, nc in zip(picks, news):
            bc.move_cell(k, nc)
        nb = bc.bad
        delta = nb - bad
        accept = (delta <= 0) or (mode == "sa" and (rng.random() < math.exp(-delta / T) if T > 0 else False))
        if accept:
            bad = nb
            if bad < best:
                best = bad; best_cells = list(bc.cells)
        else:
            for k, oc in zip(picks, olds):
                bc.move_cell(k, oc)
        if it % traj_every == 0:
            traj.append(bad)
    solved = (best == 0)
    verified = solved and (not brute_collinear(best_cells, m))
    return solved, verified, best, traj, best_cells

# ── 实验1：吸引域 / move_size / 局部化 扫描 ───────────────────────────────
def run_basin(args):
    rng = random.Random(args.seed)
    out = {}
    ms = [int(x) for x in args.ms.split(",")]
    ks = [int(x) for x in args.ks.split(",")]
    mvs = [int(x) for x in args.move_sizes.split(",")]
    R = args.restarts
    IT = args.iters
    TRAJ_EVERY = 200
    for m in ms:
        ref = load_ref(m)
        assert len(ref) == m, f"ref m={m} has {len(ref)} cells"
        out[m] = {}
        for k in ks:
            out[m][k] = {}
            for mv in mvs:
                for focus_mode in ("all", "scrambled"):
                    succ = 0; iters_succ = []; minbad = []
                    ex_traj = None
                    for r in range(R):
                        scrambled, moved = scramble(ref, k, rng)
                        focus = moved if focus_mode == "scrambled" else None
                        solved, ver, best, traj, bc = recover(
                            scrambled, m, mv, "sa", IT, rng, focus=focus,
                            traj_every=TRAJ_EVERY)
                        if solved and ver:
                            succ += 1
                            zero_at = next((i for i, v in enumerate(traj) if v == 0), len(traj))
                            iters_succ.append(zero_at * TRAJ_EVERY)
                        minbad.append(best)
                        if ex_traj is None and (solved and ver):
                            ex_traj = traj
                    key = f"mv{mv}_{focus_mode}"
                    out[m][k][key] = {
                        "success": succ, "rate": succ / R,
                        "mean_iters_when_solved": (sum(iters_succ) / len(iters_succ)) if iters_succ else None,
                        "min_bad_mean": sum(minbad) / len(minbad),
                        "example_traj": ex_traj,
                    }
                    print(f"m={m} k={k} {key}: rate={succ}/{R} "
                          f"minbad_avg={sum(minbad)/len(minbad):.1f}", flush=True)
    return out

# ── 实验2（可选/发散）：m=37 热启动探测 ─────────────────────────────────
def run_m37_warm(args):
    rng = random.Random(args.seed)
    ref36 = load_ref(36)
    m = 37
    IT = args.iters * 5
    R = args.restarts
    print("=== m=37 WARM START (m=36 ref reinterpret + 1 random) ===", flush=True)
    warm_bad_init = []; warm_bad_final = []
    for r in range(R):
        cells = [tuple(c) for c in ref36]  # 36 个
        occ = set(cells)
        while True:
            nc = (rng.randrange(m), rng.randrange(m))
            if nc not in occ:
                break
        cells.append(nc)  # 37 个
        # 全自由恢复（含多点）
        solved, ver, best, traj, bc = recover(cells, m, 3, "sa", IT, rng)
        warm_bad_init.append(traj[0]); warm_bad_final.append(best)
        print(f"  r{r}: init_bad={traj[0]} final_bad={best} solved={solved}", flush=True)
    # 对照：纯随机起步
    print("=== m=37 RANDOM START (对照) ===", flush=True)
    rand_bad_final = []
    for r in range(R):
        cells = []
        occ = set()
        while len(cells) < m:
            nc = (rng.randrange(m), rng.randrange(m))
            if nc not in occ:
                cells.append(nc); occ.add(nc)
        solved, ver, best, traj, bc = recover(cells, m, 3, "sa", IT, rng)
        rand_bad_final.append(best)
        print(f"  r{r}: init_bad={traj[0]} final_bad={best} solved={solved}", flush=True)
    return {
        "warm": {"init_mean": sum(warm_bad_init)/R, "final_mean": sum(warm_bad_final)/R},
        "random": {"final_mean": sum(rand_bad_final)/R},
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", default="8,10,12,14,16")
    ap.add_argument("--ks", default="1,2,3,5,8,12")
    ap.add_argument("--move-sizes", default="1,2,3")
    ap.add_argument("--restarts", type=int, default=20)
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--m37-warm", action="store_true",
                    help="[发散] 额外跑 m=37 热启动探测（默认关闭，先小 m 摸规律）")
    ap.add_argument("--out", default="results/recovery_basin.json")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    t0 = time.time()
    res = {"basin": run_basin(args)}
    if args.m37_warm:
        res["m37_warm"] = run_m37_warm(args)
    res["meta"] = {"args": vars(args), "elapsed_sec": time.time() - t0}
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(f"# saved -> {args.out}  ({time.time()-t0:.1f}s)")

if __name__ == "__main__":
    main()
