import os, sys, time, json
sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints

m = 37
t0 = time.time()
reps, line_cons, twofactor = generate_constraints(m, True)
print(f"[gen] {len(reps)} reps, {len(line_cons)} lines, "
      f"{len(twofactor)} 2F cons  ({time.time()-t0:.1f}s)", flush=True)

nvar = len(reps)
# histogram of t = #cells per line
from collections import Counter
hist = Counter()
npairs = 0
ntriples = 0
nw2_lines = 0
maxw = 0
for d in line_cons:
    t = len(d)
    hist[t] += 1
    maxw = max(maxw, max(d.values()))
    # forbidden pairs (sum of weights > 2): need any pair with w_i+w_j>2
    ws = list(d.values())
    has2 = any(w >= 2 for w in ws)
    if has2:
        nw2_lines += 1
        # count pairs with w_i+w_j>2
        items = list(d.items())
        for a in range(len(items)):
            wa = items[a][1]
            for b in range(a+1, len(items)):
                if wa + items[b][1] > 2:
                    npairs += 1
    # triples always forbidden (all weights>=1 => 3 cells sum>=3>2)
    # C(t,3)
    if t >= 3:
        import math
        ntriples += math.comb(t, 3)

total_clauses = npairs + ntriples
print(f"[size] nvar={nvar}", flush=True)
print(f"[size] lines by t (top): " +
      ", ".join(f"t{k}={hist[k]}" for k in sorted(hist)[-8:]), flush=True)
print(f"[size] lines with a weight-2 cell: {nw2_lines}", flush=True)
print(f"[size] max weight on any line: {maxw}", flush=True)
print(f"[size] forbidden pairs (weight>2): {npairs}", flush=True)
print(f"[size] forbidden triples: {ntriples:,}", flush=True)
print(f"[size] TOTAL clauses ~= {total_clauses:,}", flush=True)
print(f"[size] est DIMACS bytes (clauses*4 + header) ~= {total_clauses*4/1e6:.0f} MB", flush=True)

# also: how many lines have t>=3 (only these need triples)
tge3 = sum(v for k, v in hist.items() if k >= 3)
print(f"[size] lines with t>=3: {tge3}", flush=True)
