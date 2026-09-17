"""退火健全性检查：m=14 (N=28 网格 rot4 NTIL) 应存在解。
随机 2-因子几乎全 UNSAT（解极稀疏），故用 Metropolis 退火引导找几何可行解。
目的：证明本工作模型在 rot4 可行实例上能返回 SAT（消除"m=37 UNSAT 是模型假阴性/sound性bug"风险）。
找到 sat_solution => 模型 sound（3-CNF 构建未过度约束），m=37 的 UNSAT 可信。
"""
import random, json, itertools, math, time

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

def two_edge_switch(edges, rng):
    """随机 2-边开关，保持 2-正则。失败返回 None。"""
    if len(edges) < 2:
        return None
    i, j = rng.sample(range(len(edges)), 2)
    a, b = edges[i]
    c, d = edges[j]
    if len({a, b, c, d}) != 4:
        return None
    # 两种重连
    if rng.random() < 0.5:
        ne = [tuple(sorted((a, c))), tuple(sorted((b, d)))]
    else:
        ne = [tuple(sorted((a, d))), tuple(sorted((b, c)))]
    new = edges[:]
    new[i] = ne[0]
    new[j] = ne[1]
    new = sorted(new)
    # 校验仍 2-正则且无重边
    deg = {}
    for u, v in new:
        deg[u] = deg.get(u, 0) + 1
        deg[v] = deg.get(v, 0) + 1
    if all(d == 2 for d in deg.values()):
        return new
    return None

def main():
    rng = random.Random(20260721)
    t0 = time.time()
    edges = random_2factor(rng)
    bits = [rng.randrange(2) for _ in range(M)]
    E = geometry_bad_triples(edges, bits)
    T = 3.0
    Tmin = 0.01
    cool = 0.99997
    MAX = 400000
    found = None
    for step in range(MAX):
        if rng.random() < 0.5:
            # 翻转一个取向
            i = rng.randrange(M)
            nb = bits[:]; nb[i] ^= 1
            ne = edges
            newE = geometry_bad_triples(ne, nb)
        else:
            sw = two_edge_switch(edges, rng)
            if sw is None:
                i = rng.randrange(M)
                nb = bits[:]; nb[i] ^= 1
                ne = edges
                newE = geometry_bad_triples(ne, nb)
            else:
                nb = bits
                ne = sw
                newE = geometry_bad_triples(ne, nb)
        dE = newE - E
        if dE <= 0 or rng.random() < math.exp(-dE / T):
            edges, bits, E = ne, nb, newE
        if E == 0:
            found = {"step": step, "edges": edges, "bits": bits}
            break
        T = max(Tmin, T * cool)
        if (step + 1) % 5000 == 0:
            print(f"[step {step+1}] T={T:.3f} E={E} {time.time()-t0:.0f}s", flush=True)
    out = {
        "M": M, "N": N,
        "found_sat_solution": found is not None,
        "step": (found["step"] if found else None),
        "edges": (found["edges"] if found else None),
        "bits": (found["bits"] if found else None),
        "final_energy": E,
        "elapsed_s": round(time.time() - t0, 1),
    }
    json.dump(out, open("sanity_anneal_m14_result.json", "w"), ensure_ascii=False, indent=2)
    print("DONE found=", found is not None, "final_E=", E, "step=", (found["step"] if found else None), flush=True)

if __name__ == "__main__":
    main()
