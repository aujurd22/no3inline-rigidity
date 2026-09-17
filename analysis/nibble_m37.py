"""
nibble_m37.py -- constructive conflict-free 2-factor nibble for rot4-NTIL at m=37.

Model (matches research_H/I "stub-matching space"):
  * reps = m^2 candidate cells (a,b) in the fundamental quadrant.
  * A valid rot4-NTIL solution = a 2-factor (each vertex i has outdeg+indeg=2)
    that is per-line at-most-2.
  * 2-factor == perfect matching on 2m stubs: each vertex i contributes
    o_i out-stubs + i_i in-stubs with o_i+i_i=2, and sum o_i = m.  Matching an
    out-stub of i to an in-stub of j yields the directed cell (i,j).  Exactly
    the full 2-factor space (no "permutation family" narrowing).

Algorithm (constructive nibble with backtracking):
  * Fix a type assignment {o_i} (i.e. a stub multiset).
  * Process out-stubs in random order; for each, pick a compatible in-stub j
    (in_avail[j]>0 AND placing (i,j) keeps every line load <=2).  Randomized
    depth-first search with a per-restart node budget; on dead-end, backtrack;
    on budget exhaustion, restart with a fresh type assignment + order.
  * First success -> verify (brute no-3-collinear on the 4m lifted points) and
    stop.

Safety (won't freeze, won't silently die):
  * single process, single core, BelowNormal priority (Windows).
  * one-time build of the constraint model (~70s); reused by all restarts.
  * hard 30-min wall-clock cap; exception inside a restart -> logged, restart.
  * heartbeat JSON written every 30s; final result JSON on exit.
"""
import sys, time, random, json, os
try:
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(
        ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL
except Exception:
    pass

sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints, verify_cells

m = 37
TIME_CAP = 30 * 60          # wall-clock seconds
HEARTBEAT = 30             # seconds between status writes
NODE_BUDGET = 200_000      # max DFS nodes per restart
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
random.seed(SEED)

t0 = time.time()
reps, line_cons, _ = generate_constraints(m, use_2factor=False)
print(f"[build] {len(reps)} reps, {len(line_cons)} lines "
      f"in {time.time()-t0:.1f}s", flush=True)

# cell index lookup
cell_index = {}
for i, (a, b) in enumerate(reps):
    cell_index[(a, b)] = i

# compact cell -> lines CSR
ncell, nline = len(reps), len(line_cons)
cell_deg = [0] * ncell
for d in line_cons:
    for c in d:
        cell_deg[c] += 1
total_inc = sum(cell_deg)
cell_off = [0] * (ncell + 1)
for c in range(ncell):
    cell_off[c + 1] = cell_off[c] + cell_deg[c]
cell_line = [0] * total_inc
cell_w = [0] * total_inc
cursor = cell_off[:]
for L, d in enumerate(line_cons):
    for c, w in d.items():
        p = cursor[c]
        cell_line[p] = L
        cell_w[p] = w
        cursor[c] += 1
print(f"[csr] total incidences = {total_inc:,}", flush=True)

load = [0] * nline

def can_place(c):
    base, end = cell_off[c], cell_off[c + 1]
    for idx in range(base, end):
        if load[cell_line[idx]] + cell_w[idx] > 2:
            return False
    return True

def place(c):
    base, end = cell_off[c], cell_off[c + 1]
    for idx in range(base, end):
        load[cell_line[idx]] += cell_w[idx]

def unplace(c):
    base, end = cell_off[c], cell_off[c + 1]
    for idx in range(base, end):
        load[cell_line[idx]] -= cell_w[idx]

def new_type():
    # bias toward small k (known solution cycle types are [m] and [1,m-1])
    r = random.random()
    if r < 0.30:
        k = 0
    elif r < 0.70:
        k = 1
    else:
        k = random.randint(2, m // 2)
    o = [1] * m
    if k > 0:
        idxs = random.sample(range(m), 2 * k)
        for v in idxs[:k]:
            o[v] = 2
        for v in idxs[k:]:
            o[v] = 0
    return o

def dfs(pos, out_list, in_avail, chosen, nodes):
    if pos == len(out_list):
        return chosen[:]
    if nodes[0] >= NODE_BUDGET:
        return None
    i = out_list[pos]
    # candidate in-stubs: available and placing (i,j) keeps all lines <=2
    cands = [j for j in range(m)
             if in_avail[j] > 0 and can_place(cell_index[(i, j)])]
    # heuristic: use scarce in-stubs first (minimum remaining values)
    cands.sort(key=lambda j: in_avail[j])
    random.shuffle(cands)  # keep randomness among equal-scarcity
    for j in cands:
        nodes[0] += 1
        c = cell_index[(i, j)]
        place(c)
        in_avail[j] -= 1
        chosen.append((i, j))
        res = dfs(pos + 1, out_list, in_avail, chosen, nodes)
        if res is not None:
            return res
        chosen.pop()
        in_avail[j] += 1
        unplace(c)
    return None

def restart():
    o = new_type()
    in_cnt = [2 - o[i] for i in range(m)]
    out_list = []
    for i in range(m):
        out_list += [i] * o[i]
    random.shuffle(out_list)
    in_avail = in_cnt[:]
    nodes = [0]
    # reset load
    for L in range(nline):
        load[L] = 0
    return dfs(0, out_list, in_avail, [], nodes), nodes[0]

STATUS = os.path.join(os.path.dirname(__file__),
                      "..", "results", "nibble_m37_status.json")

def write_status(restarts, fails, nodes_total, best_nodes, found):
    st = {
        "m": m, "seed": SEED, "elapsed": time.time() - t0,
        "restarts": restarts, "fails": fails, "nodes_total": nodes_total,
        "best_nodes": best_nodes, "found": found,
    }
    try:
        with open(STATUS, "w") as f:
            json.dump(st, f, indent=2)
    except Exception:
        pass

restarts = 0
fails = 0
nodes_total = 0
best_nodes = 0
found = None
last_hb = time.time()

print(f"[run] seed={SEED} cap={TIME_CAP}s node_budget={NODE_BUDGET} ...", flush=True)
try:
    while time.time() - t0 < TIME_CAP:
        restarts += 1
        try:
            sol, nd = restart()
        except Exception as e:
            fails += 1
            print(f"[warn] restart {restarts} exception: {e!r}", flush=True)
            continue
        nodes_total += nd
        best_nodes = max(best_nodes, nd)
        if sol is not None:
            # verify
            ok, n = verify_cells(sol, m)
            if ok:
                found = sol
                print(f"[FOUND] seed={SEED} restart={restarts} nodes={nd} "
                      f"cells={n} verified=True", flush=True)
                break
            else:
                # internal invariant broken -- should not happen
                print(f"[warn] restart {restarts} produced {n} cells but "
                      f"verify failed; treating as fail", flush=True)
                fails += 1
        if time.time() - last_hb > HEARTBEAT:
            last_hb = time.time()
            write_status(restarts, fails, nodes_total, best_nodes, found)
            print(f"[hb] t={time.time()-t0:.0f}s restarts={restarts} "
                  f"fails={fails} nodes={nodes_total:,}", flush=True)
except KeyboardInterrupt:
    print("[int] interrupted", flush=True)
except Exception as e:
    print(f"[fatal] {e!r}", flush=True)

elapsed = time.time() - t0
if found is not None:
    out = {
        "m": m, "seed": SEED, "elapsed": elapsed, "found": True,
        "cells": found, "restarts": restarts, "nodes_total": nodes_total,
    }
    with open(os.path.join(os.path.dirname(__file__),
                           "..", "results", "solution_m37_nibble.json"),
              "w") as f:
        json.dump(out, f, indent=2)
    print(f"[done] SOLUTION FOUND in {elapsed:.1f}s after {restarts} restarts",
          flush=True)
else:
    print(f"[done] no solution in {elapsed:.1f}s "
          f"(restarts={restarts}, fails={fails}, nodes={nodes_total:,}) "
          f"-> m=37 still OPEN by this run", flush=True)
write_status(restarts, fails, nodes_total, best_nodes, found is not None)
