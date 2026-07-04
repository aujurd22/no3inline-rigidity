#!/usr/bin/env python3
"""
Systematic ring assignment testing for n=12.
Fix the total-points issue: test only valid assignments (sum=24).
"""

import subprocess
import os
from collections import defaultdict
from itertools import combinations

SOLVER = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/ring_guided_solver.exe"
WORKDIR = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36"

def build_rings(n):
    cx2 = cy2 = n - 1
    rings = defaultdict(list)
    for r in range(n):
        for c in range(n):
            d = (2*c - cx2)**2 + (2*r - cy2)**2
            rings[d].append((r, c))
    return dict(sorted(rings.items()))

def test_assignment(assig, n, label=""):
    fname = os.path.join(WORKDIR, "_tmp_assig.txt")
    with open(fname, 'w') as f:
        for d, c in sorted(assig.items()):
            if c > 0:
                f.write(f"{d} {c}\n")
    total = sum(assig.values())
    
    if total != 2 * n:
        return False, 0, "invalid"
    
    try:
        result = subprocess.run(
            [SOLVER, str(n), "1", fname],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        
        if "Found a valid placement" in output:
            for line in output.split('\n'):
                if 'Found' in line and '(' in line:
                    time_str = line.split('(')[1].split('s')[0]
                    t = float(time_str)
                    return True, t, "found"
            return True, 0, "found"
        elif "No valid placement" in output:
            for line in output.split('\n'):
                if 'No valid' in line and '(' in line:
                    time_str = line.split('(')[1].split('s')[0]
                    t = float(time_str)
                    return False, t, "none"
            return False, 0, "none"
        else:
            return False, 0, f"unknown: {output[:100]}"
    except subprocess.TimeoutExpired:
        return False, 120, "timeout"

def main():
    n = 12
    rings = build_rings(n)
    ring_list = sorted(rings.keys())
    
    print(f"=" * 60)
    print(f"Systematic Ring Assignment Tests: n={n}")
    print(f"Target: {2*n} pts, {len(ring_list)} rings")
    print(f"=" * 60)
    
    # Known working set: d=10,26,34,74,82,90,98,106,122,130,170,202
    known_working = {10, 26, 34, 74, 82, 90, 98, 106, 122, 130, 170, 202}
    
    # ========== Test 1: Verify known working ==========
    print("\n--- Test 1: Verify known working assignment ---")
    assig = {d: 2 if d in known_working else 0 for d in ring_list}
    found, t, status = test_assignment(assig, n, "Known working (from RLE)")
    print(f"  {'✅' if found else '❌'} Known working: {status} ({t:.3f}s)")
    
    # ========== Test 2: One-ring replacements ==========
    print("\n--- Test 2: Replace one ring in working set ---")
    
    # Replace each ring in working set with an unused ring
    unused = [d for d in ring_list if d not in known_working]
    
    replacements_with_d2 = []
    for replace_out in sorted(known_working):
        for replace_in in unused:
            new_set = set(known_working) - {replace_out} | {replace_in}
            assig = {d: 2 if d in new_set else 0 for d in ring_list}
            found, t, status = test_assignment(assig, n, f"Replace {replace_out}→{replace_in}")
            if found:
                replacements_with_d2.append((replace_out, replace_in, t))
            sym = "✅" if found else "❌"
            print(f"  {sym} Replace {replace_out:4d}→{replace_in:4d}: {status} ({t:.3f}s)")
    
    print(f"\n  Successful replacements: {len(replacements_with_d2)}")
    for out_d, in_d, t in replacements_with_d2:
        print(f"    Replace {out_d}→{in_d}: {t:.3f}s")
    
    if len(replacements_with_d2) == 0:
        print("    (None - working set is isolated)")
    
    # ========== Test 3: Remove one ring from working set, add 1pt to another ==========
    print("\n--- Test 3: Downgrade to 1pt (instead of full replacement) ---")
    # Instead of replacing, downgrade one 2-pt ring to 1-pt and add a 1-pt ring elsewhere
    print("  (Test: 11 rings × 2pt + 2 rings × 1pt = 24)")
    
    count_2pt = 11
    count_1pt = 2
    found_any = 0
    
    for rm_2pt in sorted(known_working):
        base = set(known_working) - {rm_2pt}
        candidates = [d for d in ring_list if d not in base]
        
        for add_1pt1, add_1pt2 in combinations(candidates, 2):
            assig = {}
            for d in ring_list:
                if d in base:
                    assig[d] = 2
                elif d == add_1pt1 or d == add_1pt2:
                    assig[d] = 1
                else:
                    assig[d] = 0
            if sum(assig.values()) != 24:
                continue
            
            found, t, status = test_assignment(assig, n, f"{count_2pt}×2pt [+{add_1pt1},{add_1pt2}] -{rm_2pt}")
            if found:
                found_any += 1
                print(f"  ✅ Success! Downgrade {rm_2pt} from 2→0, add 1pt at {add_1pt1},{add_1pt2} ({t:.3f}s)")
    
    if found_any == 0:
        print("  ❌ No success with 11×2pt + 2×1pt pattern")
    
    # ========== Summary ==========
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"  Known 12×2pt working set: {sorted(known_working)}")
    print(f"  Working set isolated by replacement: {len(replacements_with_d2) == 0}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
