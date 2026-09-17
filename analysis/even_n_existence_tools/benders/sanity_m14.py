"""快速健全性检查：m=14 (N=28 网格 rot4 NTIL) 应存在解。
目的：证明本工作模型在 rot4 可行实例上能返回 SAT，消除"m=37 全 UNSAT 是模型假阴性"风险。
小 m 解密集、DPLL 快，几分钟可完成。完全隔离，不加载 m=37 环境。
找到 sat_solution => 模型健全（假阴性已被排除），m=37 的 UNSAT 可信。
"""
import random, json, itertools, math, time, sys

# ---- 本地参数：m=14 => N=28 网格，14 cell ----
N = 28
M = 14

def c4_lifts(cell):
    x, y = cell
    result = []
    for _ in range(4):
        result.append((x, y))
        x, y = N - 1 - y, x
    return tuple(result)

def directed_cells(edges, bits):
    return tuple((v, u) if int(bit) else (u, v) for (u, v), bit in zip(edges, bits))

def line_key(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        raise ValueError("dup")
    d = math.gcd(abs(dx), abs(dy))
    a, b = dy // d, -dx // d
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    return a, b, a * p[0] + b * p[1]

def random_2factor(rng):
    while True:
        perm = list(range(M))
        rng.shuffle(perm)
        if any(perm[perm[i]] == i and perm[i] != i for i in range(M)):
            continue
        es = set()
        for i in range(M):
            u, v = i, perm[i]
            if u == v:
                continue
            es.add((min(u, v), max(u, v)))
        if len(es) != M:
            continue
        edges = sorted(es)
        deg = {}
        for u, v in edges:
            deg[u] = deg.get(u, 0) + 1
            deg[v] = deg.get(v, 0) + 1
        if all(d == 2 for d in deg.values()):
            return edges

def fast_build_3cnf(edges):
    all_pts = []
    tags = []
    for i, (u, v) in enumerate(edges):
        for b in (0, 1):
            cd = directed_cells([(u, v)], [b])[0]
            for pt in c4_lifts(cd):
                all_pts.append(pt)
                tags.append((i, b))
    lm = {}
    np_ = len(all_pts)
    for i in range(np_):
        for j in range(i + 1, np_):
            try:
                key = line_key(all_pts[i], all_pts[j])
            except ValueError:
                continue
            lm.setdefault(key, []).append(i)
            lm[key].append(j)
    cs = set()
    for mem in lm.values():
        if len(mem) < 3:
            continue
        for i, j, k in itertools.combinations(mem, 3):
            ci, ai = tags[i]
            cj, aj = tags[j]
            ck, ak = tags[k]
            if ci == cj or ci == ck or cj == ck:
                continue
            lits = frozenset([(2 * ci + ai) ^ 1, (2 * cj + aj) ^ 1, (2 * ck + ak) ^ 1])
            cs.add(lits)
    return [list(c) for c in cs], len(edges)

def geometry_bad_triples(edges, bits):
    pts = []
    for (u, v), b in zip(edges, bits):
        cell = (v, u) if b else (u, v)
        pts.extend(c4_lifts(cell))
    lm = {}
    np_ = len(pts)
    for i in range(np_):
        for j in range(i + 1, np_):
            try:
                key = line_key(pts[i], pts[j])
            except ValueError:
                continue
            lm.setdefault(key, set()).add(i)
            lm[key].add(j)
    bad = 0
    for mem in lm.values():
        if len(mem) < 3:
            continue
        for i, j, k in itertools.combinations(sorted(mem), 3):
            bad += 1
    return bad

def dpll_model(clauses, nvars, node_budget=3_000_000):
    """迭代 DPLL，返回 (status, model)。status: True=UNSAT, False=SAT, None=超预算。"""
    n = 2 * nvars
    assign = [-1] * n
    active = set()
    for cl in clauses:
        for lit in cl:
            active.add(lit)
    freq = [0] * n
    for cl in clauses:
        for lit in cl:
            freq[lit] += 1
    nodes = [0]

    def unit_prop():
        changed = True
        while changed:
            changed = False
            for cl in clauses:
                un = []
                sat = False
                for lit in cl:
                    if assign[lit] == 1:
                        sat = True
                        break
                    if assign[lit] == 0:
                        un.append(lit)
                if sat:
                    continue
                if len(un) == 0:
                    return False
                if len(un) == 1:
                    assign[un[0]] = 1
                    assign[un[0] ^ 1] = 0
                    changed = True
        return True

    stack = [(0, list(assign))]
    while stack:
        depth, saved = stack.pop()
        nodes[0] += 1
        if nodes[0] > node_budget:
            return None, None
        assign[:] = saved
        if not unit_prop():
            for i in range(n):
                assign[i] = -1 if saved[i] == -1 else assign[i]
            for i in range(n):
                if saved[i] == -1:
                    assign[i] = -1
            continue
        branch = -1
        for v in range(n):
            if assign[v] == -1:
                branch = v
                break
        if branch == -1:
            model = [0] * nvars
            for i in range(nvars):
                model[i] = assign[2 * i]
            return False, model
        cand = [l for l in (branch, branch ^ 1)]
        best = max(cand, key=lambda l: freq[l] + (assign[l] == -1))
        for lit in (best, best ^ 1):
            snap = list(assign)
            assign[lit] = 1
            assign[lit ^ 1] = 0
            stack.append((depth + 1, snap))
    return True, None

def decode_bits(model):
    bits = []
    for ci in range(M):
        b0 = model[2 * ci + 0]
        b1 = model[2 * ci + 1]
        bit = 1 if (b1 and not b0) else 0
        bits.append(bit)
    return bits

def main():
    rng = random.Random(20260721)
    TRIALS = 4000
    t0 = time.time()
    verdicts = {}
    found_sat = None
    for t in range(TRIALS):
        edges = random_2factor(rng)
        clauses, nvars = fast_build_3cnf(edges)
        status, model = dpll_model(clauses, nvars, node_budget=3_000_000)
        if status is True:
            v = "unsat"
        elif status is None:
            v = "unknown"
        else:
            bits = decode_bits(model)
            bad = geometry_bad_triples(edges, bits)
            if bad == 0:
                v = "sat_solution"
                found_sat = {"trial": t, "edges": edges, "bits": bits}
                verdicts[v] = verdicts.get(v, 0) + 1
                break
            else:
                v = "sat_blocked"
        verdicts[v] = verdicts.get(v, 0) + 1
        if (t + 1) % 200 == 0:
            print(f"[{t+1}] {time.time()-t0:.0f}s {verdicts}", flush=True)
    out = {
        "M": M, "N": N, "trials_run": (found_sat["trial"]+1 if found_sat else TRIALS),
        "verdicts": verdicts,
        "found_sat_solution": found_sat is not None,
        "first_sat_solution_trial": (found_sat["trial"] if found_sat else None),
        "elapsed_s": round(time.time() - t0, 1),
    }
    json.dump(out, open("sanity_m14_result.json", "w"), ensure_ascii=False, indent=2)
    print("DONE found_sat_solution=", found_sat is not None, "verdicts=", verdicts, flush=True)

if __name__ == "__main__":
    main()
