"""
gpu_nibble_m37.py -- batched population nibble for rot4-NTIL at m=37 on GPU.

Runs B independent constructive searches in lockstep.  Each path is a random
2-factor stub-matching (== R9b feasible set) built greedily with conflict
avoidance (full per-line at-most-2) and the G spatial prior as a sampling bias.
Stuck paths are recycled (re-init).  Any completed path is a valid solution and
is independently re-verified with a full 4m-point cross-product.

This is the vectorized form of nibble_m37.py: the parallel axis is the BATCH of
paths, not a single sequential DFS.  A single GPU step advances ALL B paths by
one cell via gather/scatter, so throughput ~ B x the CPU run.

Run with the ComfyUI torch venv (CUDA 12.4, RTX 4070 SUPER).
"""
import sys, time, json, os, random, math
import torch

m = 37
B = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
LMAX = 512
TIME_CAP = int(os.environ.get("GPU_TIME_LIMIT_SEC", str(30 * 60)))
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 777
device = os.environ.get("DEV", "cuda")

random.seed(SEED)
torch.manual_seed(SEED)

sys.path.insert(0, ".")
# Inlined (no ortools dependency) -- copied verbatim from solve_m37_r9b.py so
# this script runs under the ComfyUI torch venv which lacks ortools.
from quadratic_sidon_completeness import c4, brute_collinear


def cell_xy(a, b, m):
    return (m - (a + 1) // 2, m - (b + 1) // 2)


def orbit_c4(cell, n):
    return [c4(cell, r, n) for r in range(4)]


def reduced_dirs(n):
    dirs = set()
    for dx in range(-(n - 1), n):
        for dy in range(0, n):
            if dx == 0 and dy == 0:
                continue
            g = math.gcd(abs(dx), dy) or 1
            rdx, rdy = dx // g, dy // g
            if rdx < 0 or (rdx == 0 and rdy < 0):
                rdx, rdy = -rdx, -rdy
            dirs.add((rdx, rdy))
    return dirs


def generate_constraints(m, use_2factor=True):
    """Top-left fundamental quadrant reps; fast per-line weighted at-most-2."""
    n = 2 * m
    reps = [(x, y) for x in range(m) for y in range(m)]
    orbits = [orbit_c4(c, n) for c in reps]
    D = reduced_dirs(n)
    line_w = {}
    for i, (x, y) in enumerate(reps):
        for (X, Y) in orbits[i]:
            for (dx, dy) in D:
                perp = (-dy, dx)
                key = perp[0] * X + perp[1] * Y
                d = line_w.setdefault((dx, dy), {})
                k = d.setdefault(key, {})
                k[i] = k.get(i, 0) + 1
    line_cons = []
    for d, lines in line_w.items():
        for key, pos_w in lines.items():
            if sum(pos_w.values()) > 2:
                line_cons.append(dict(pos_w))
    twofactor = list(range(m)) if use_2factor else []
    return reps, line_cons, twofactor


def verify_cells(cells, m):
    pairs = [(2 * (m - x) - 1, 2 * (m - y) - 1) for (x, y) in cells]
    return (not brute_collinear(pairs, m)), len(cells)


t0 = time.time()
reps, line_cons, _ = generate_constraints(m, use_2factor=False)
print(f"[build] {len(reps)} reps, {len(line_cons)} lines "
      f"in {time.time()-t0:.1f}s", flush=True)
ncell, nline = len(reps), len(line_cons)

# cell_of[i,j] (CPU)
cell_of_cpu = torch.full((m, m), -1, dtype=torch.long)
for i, (a, b) in enumerate(reps):
    cell_of_cpu[a, b] = i

# pad cell -> lines (CPU)
cell_line_pad = torch.full((ncell, LMAX), -1, dtype=torch.long)
cell_w_pad = torch.zeros((ncell, LMAX), dtype=torch.int8)
deg = [0] * ncell
for L, d in enumerate(line_cons):
    for c, w in d.items():
        if deg[c] < LMAX:
            cell_line_pad[c, deg[c]] = L
            cell_w_pad[c, deg[c]] = w
            deg[c] += 1
maxdeg = max(deg)
print(f"[pad] max lines per cell = {maxdeg} (LMAX={LMAX})", flush=True)
assert maxdeg <= LMAX, "increase LMAX"

cell_line_pad = cell_line_pad.to(device)
cell_w_pad = cell_w_pad.to(device)
cell_of = cell_of_cpu.to(device)

# G spatial prior bias (avoid diagonal, prefer mid-ring) -- the theory lever
cx = (m - 1) / 2.0
maxr = (2.0 ** 0.5) * cx
bias = torch.ones(m, m)
for i in range(m):
    for j in range(m):
        r = ((i - cx) ** 2 + (j - cx) ** 2) ** 0.5 / maxr
        ring = 1.0
        if r < 0.35:
            ring = 0.5
        elif 0.55 < r < 0.85:
            ring = 1.4
        elif r > 0.92:
            ring = 0.6
        diag = 0.5 if i == j else 1.0
        bias[i, j] = ring * diag
bias = bias.to(device)

# ---- allocate GPU state (with OOM fallback) ----
def alloc(B_):
    load = torch.zeros((B_, nline), dtype=torch.int32, device=device)
    in_avail = torch.zeros((B_, m), dtype=torch.int8, device=device)
    out_order = torch.zeros((B_, m), dtype=torch.long, device=device)
    cur = torch.zeros(B_, dtype=torch.long, device=device)
    chosen = torch.zeros((B_, m), dtype=torch.long, device=device)
    return load, in_avail, out_order, cur, chosen

try:
    load, in_avail, out_order, cur, chosen = alloc(B)
except torch.cuda.OutOfMemoryError:
    torch.cuda.empty_cache()
    B = B // 2
    print(f"[oom] reduced B -> {B}", flush=True)
    load, in_avail, out_order, cur, chosen = alloc(B)

def init_path(b):
    k = random.choice([0, 0, 1, 1, 1, 2])  # bias toward k=1 ([1,m-1] real type)
    o = [1] * m
    if k > 0:
        vs = random.sample(range(m), 2 * k)
        for v in vs[:k]:
            o[v] = 2
        for v in vs[k:]:
            o[v] = 0
    in_cnt = [2 - o[i] for i in range(m)]
    out_list = []
    for i in range(m):
        out_list += [i] * o[i]
    random.shuffle(out_list)
    out_order[b].copy_(torch.tensor(out_list, dtype=torch.long, device=device))
    in_avail[b].copy_(torch.tensor(in_cnt, dtype=torch.int8, device=device))
    load[b].zero_()
    cur[b] = 0
    chosen[b].zero_()

for b in range(B):
    init_path(b)

ar = torch.arange(B, device=device)
ROWS = torch.arange(B, device=device).repeat_interleave(m * LMAX)
ROW1 = torch.arange(B, device=device).repeat_interleave(LMAX)
ONES = torch.ones(B, dtype=torch.long, device=device)

print(f"[run] B={B} device={device} cap={TIME_CAP}s seed={SEED}", flush=True)
t_start = time.time()
iters = 0
restarts = 0
found = None
status_path = os.path.join(os.path.dirname(__file__), "..", "results",
                           "nibble_m37_gpu_status.json")
last_hb = time.time()

try:
    while time.time() - t_start < TIME_CAP:
        iters += 1
        i_cur = out_order[ar, cur]                 # (B,)
        cand = cell_of[i_cur, :]                   # (B,m)
        lines = cell_line_pad[cand]                # (B,m,LMAX)
        w = cell_w_pad[cand]                       # (B,m,LMAX)
        idx = lines.reshape(-1).clamp(min=0)
        flat = ROWS * nline + idx
        lg = load.reshape(-1)[flat].reshape(B, m, LMAX).to(torch.int32)
        valid = lines >= 0
        added = torch.where(valid, lg + w.to(torch.int32),
                            torch.tensor(-100, device=device))
        maxadd, _ = added.max(dim=2)               # (B,m)
        legal = (maxadd <= 2) & (in_avail[ar, :] > 0)

        wj = bias[i_cur, :]                        # (B,m)
        logits = torch.where(legal, torch.log(wj.clamp(min=1e-3)),
                             torch.tensor(-1e9, device=device))
        g = -torch.log(-torch.log(torch.rand(B, m, device=device) + 1e-9))
        jsel = (logits + g).argmax(dim=1)          # (B,)
        any_legal = legal.any(dim=1)

        chosen_cell = cand[ar, jsel]               # (B,)
        place_lines = cell_line_pad[chosen_cell]   # (B,LMAX)
        place_w = cell_w_pad[chosen_cell]          # (B,LMAX)
        pvalid = place_lines >= 0
        pidx = place_lines.reshape(-1).clamp(min=0)
        pflat = ROW1 * nline + pidx
        psrc = torch.where(pvalid.reshape(-1),
                           place_w.reshape(-1).to(torch.int32),
                           torch.zeros(1, dtype=torch.int32, device=device))
        # illegal paths contribute nothing
        psrc = psrc * any_legal.repeat_interleave(LMAX).reshape(-1).to(torch.int32)
        load.reshape(-1).scatter_add_(0, pflat, psrc)

        in_avail[ar, jsel] -= any_legal.to(torch.int8)
        chosen_snap = cur.clone()
        chosen[ar, chosen_snap] = chosen_cell
        cur += any_legal.to(torch.long)

        # recycle stuck paths
        restart_mask = ~any_legal
        for b in restart_mask.nonzero(as_tuple=False).flatten().tolist():
            init_path(b)
            restarts += 1

        # completion check -- handle ALL completed paths this iteration
        # (critical: with B parallel paths, several can finish in the same
        #  step; only consuming the first left others at cur==m and crashed
        #  the next-step out_order[ar, cur] gather with index 37).
        done_mask = cur >= m
        if done_mask.any():
            break_out = False
            for b in done_mask.nonzero(as_tuple=False).flatten().tolist():
                sol = [tuple(reps[c]) for c in chosen[b].tolist()[:m]]
                ok, n = verify_cells(sol, m)
                if ok:
                    found = sol
                    print(f"[FOUND] B={B} iters={iters} restarts={restarts} "
                          f"cells={n} verified=True", flush=True)
                    break_out = True
                    break
                else:
                    init_path(b)   # spurious; recycle
                    restarts += 1
            if break_out:
                break

        if time.time() - last_hb > 30:
            last_hb = time.time()
            st = {"m": m, "B": B, "seed": SEED, "elapsed": time.time() - t_start,
                  "iters": iters, "restarts": restarts, "found": found is not None}
            with open(status_path, "w") as f:
                json.dump(st, f, indent=2)
            print(f"[hb] t={time.time()-t_start:.0f}s iters={iters} "
                  f"restarts={restarts}", flush=True)
except KeyboardInterrupt:
    print("[int] interrupted", flush=True)
except Exception as e:
    print(f"[fatal] {e!r}", flush=True)

elapsed = time.time() - t_start
if found is not None:
    out = {"m": m, "B": B, "seed": SEED, "elapsed": elapsed, "found": True,
           "cells": found, "iters": iters, "restarts": restarts}
    with open(os.path.join(os.path.dirname(__file__), "..", "results",
                           "solution_m37_gpu.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[done] SOLUTION FOUND in {elapsed:.1f}s "
          f"(iters={iters}, restarts={restarts})", flush=True)
else:
    print(f"[done] no solution in {elapsed:.1f}s "
          f"(iters={iters}, restarts={restarts}) -> m=37 still OPEN by this run",
          flush=True)
with open(status_path, "w") as f:
    json.dump({"m": m, "B": B, "seed": SEED, "elapsed": elapsed,
               "iters": iters, "restarts": restarts,
               "found": found is not None}, f, indent=2)
