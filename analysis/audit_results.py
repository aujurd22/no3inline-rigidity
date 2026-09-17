"""Quick audit of all saved result files for validity."""
import os, sys, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
M = 37

def audit(name, path):
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception as e:
        print(f"  {name}: ❌ Can't load ({e})")
        return
    
    edges = [tuple(e) for e in d.get("edges", [])]
    if not edges:
        # Maybe cells format
        edges = [tuple(e) for e in d.get("cells", d.get("edges", []))]
    
    n = len(edges)
    uniq = len(set(edges))
    dupes = [(e, c) for e, c in Counter(edges).items() if c > 1]
    
    deg = Counter()
    for u,v in edges:
        deg[u] += 1
        deg[v] += 1
    bad_deg = [k for k,v in deg.items() if v != 2]
    
    status = "✅" if (n == M and uniq == M and not bad_deg) else "❌"
    issues = []
    if n != M: issues.append(f"count={n}")
    if uniq != M: issues.append(f"dupes={len(dupes)} {[e for e,c in dupes[:3]]}")
    if bad_deg: issues.append(f"deg_errors={bad_deg}")
    
    note = "; ".join(issues) if issues else "valid"
    print(f"  {name:50s}: {status}  ({n} edges, {uniq} unique)  {note}")

print("=== AUDIT OF ALL GENERATED RESULT FILES ===")
print()
audit("config_408_edges.json", os.path.join(HERE, "results", "config_408_edges.json"))
print("--- Files from direction3b_focus (cycle type, 50 samples) ---")
for f in sorted(os.listdir(os.path.join(HERE, "results"))):
    if f.startswith("best_") and f.endswith("_edges.json") and f != "best_gv_63_edges.json" and f != "config_408_edges.json":
        audit(f, os.path.join(HERE, "results", f))
print("--- best_gv_63 from direction3c ---")
audit("best_gv_63_edges.json", os.path.join(HERE, "results", "best_gv_63_edges.json"))
print("--- Mutation results ---")
for f in sorted(os.listdir(os.path.join(HERE, "results"))):
    if f.startswith("mutate_gv"):
        audit(f, os.path.join(HERE, "results", f))
