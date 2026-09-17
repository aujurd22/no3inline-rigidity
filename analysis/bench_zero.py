"""
Quick benchmark: zero-orient clause time for 1 config.
"""
import sys, time, json
sys.path.insert(0, "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis")

M = 37
N = 74

def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_orbits_0 = {}
for u in range(M):
    for v in range(M):
        all_orbits_0[(u, v)] = c4_lift(u, v)

def zero_orient_count(edges):
    from itertools import combinations
    total = 0
    for a, b, c in combinations(range(M), 3):
        u1, v1 = edges[a]
        u2, v2 = edges[b]
        u3, v3 = edges[c]
        lifts = (all_orbits_0[(u1, v1)] + all_orbits_0[(u2, v2)] + all_orbits_0[(u3, v3)])
        for i in range(12):
            xi, yi = lifts[i]
            for j in range(i+1, 12):
                xj, yj = lifts[j]
                if xi == xj and yi == yj: continue
                dx1, dy1 = xj - xi, yj - yi
                for k in range(j+1, 12):
                    xk, yk = lifts[k]
                    if xk == xi and yk == yi: continue
                    if dx1 * (yk - yi) == dy1 * (xk - xi):
                        total += 1
                        break
                else: continue
                break
            else: continue
            break
    return total

with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\config_408_edges.json") as f:
    data = json.load(f)
edges = [tuple(e) for e in data["edges"]]

t0 = time.time()
cnt = zero_orient_count(edges)
t = time.time() - t0
print(f"zero-orient clauses for config_408: {cnt}")
print(f"time: {t:.3f}s")
