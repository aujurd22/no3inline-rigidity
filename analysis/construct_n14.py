#!/usr/bin/env python3
"""
Constructive approach for n=14: start from 5 universal rings,
systematically find which additional rings can complete a valid assignment.
"""
import subprocess, os, sys
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

def test(assig, n, label):
    fname = os.path.join(WORKDIR, "_tmp_n14.txt")
    with open(fname, 'w') as f:
        for d, c in sorted(assig.items()):
            if c > 0: f.write(f"{d} {c}\n")
    total = sum(assig.values())
    if total != 2*n: return False, 0
    try:
        r = subprocess.run([SOLVER, str(n), "1", fname], capture_output=True, text=True, timeout=60)
        o = r.stdout + r.stderr
        if "Found" in o: return True, 0
        return False, 0
    except: return False, 120

n = 14
rings = build_rings(n)
ring_list = sorted(rings.keys())

# Universal rings for n=14 (used in ALL 11 missing-center solutions)
universal = {122, 130, 170, 178, 194}

# Solution #2's full working set (14×2pt)
sol2 = {26, 58, 74, 82, 90, 98, 146, 162, 290}
full_working = universal | sol2

# Verify: does the full set work?
print(f"n=14 constructive approach")
print(f"  Universal (5): {sorted(universal)}")
print(f"  Solution #2 remaining (9): {sorted(sol2)}")
print(f"  Full (14): {sorted(full_working)}")

assig_full = {d: (2 if d in full_working else 0) for d in ring_list}
ok, _ = test(assig_full, n, "Full working")
print(f"  Full working: {'✅' if ok else '❌'}")

# ===== Test 1: Fix universal, try all single-ring replacements =====
print(f"\n  --- Test 1: Single-ring replacements (fix universal + 8/9 of sol2) ---")
other_rings = [d for d in ring_list if d not in full_working]
print(f"    20 other candidate rings: {other_rings}")

successful_replacements = []
for remove_ring in sorted(sol2):
    base = set(sol2) - {remove_ring}
    
    for add_ring in other_rings:
        candidate = universal | base | {add_ring}
        assig = {d: (2 if d in candidate else 0) for d in ring_list}
        
        ok, _ = test(assig, n, f"  remove {remove_ring}, add {add_ring}")
        
        if ok:
            successful_replacements.append((remove_ring, add_ring))
            print(f"    ✅ Replace {remove_ring}→{add_ring}: WORKS!")
        
        print(f"    {'✅' if ok else '❌'} Remove {remove_ring:4d}, add {add_ring:4d}", end="\r")

print(f"\n\n  Successful single replacements: {len(successful_replacements)}")
for rm, add in successful_replacements:
    print(f"    Replace {rm}→{add}")

# ===== Test 2: Try to build from just the 5 universal rings =====
# Add rings one at a time from the remaining set, checking feasibility
print(f"\n  --- Test 2: Step-by-step construction from 5 universal ---")

# Rings ordered by decreasing usage in known missing-center solutions
# From: d=10(64%), 26(73%), 34(73%), 50(91%), 58(91%), 74(91%), 82(82%),
#        90(91%), 98(82%), 106(91%), 122(100%), 130(100%), 146(82%), 
#        162(45%), 170(100%), 178(100%), 194(100%), 202(91%), 218(73%),
#        242(55%), 250(64%), 290(82%), 338(18%)
usage_order = [122,130,170,178,194,  # 100%
               50,58,74,90,106,202,  # 91%
               82,98,146,290,        # 82%
               26,34,218,            # 73%
               10,250,               # 64%
               242,                  # 55%
               162,                  # 45%
               2,18,338]             # lowest

# Starting from 5 universal, add rings greedily
current = set(universal)
assig = {d: 2 if d in current else 0 for d in ring_list}
print(f"    Starting with {len(current)} rings = {sum(assig.values())}pts")

for next_d in usage_order:
    if next_d in current:
        continue
    
    candidate = current | {next_d}
    if len(candidate) * 2 > 28:
        # Need exactly 14 rings × 2pt = 28 total
        # If we have 13 rings (26pts), we need 1 more ring with 2pt → 28
        # Or if we have 12 rings (24pts), we need 2 more rings with 2pt → 28
        # Actually, final must be exactly 14 rings × 2pt = 28pts
        break
    
    test_set = set(current) | {next_d}
    
    # Check if this partial set is feasible by adding dummy rings
    # Actually, the solver needs FULL assignment. Let me just verify
    # by trying the full assignment with additional rings.
    
    # Skip - this test requires full assignment
    pass

# Instead: find which 14-ring supersets of universal work
# Try all C(20,9) = 167960? Too many.
# Instead try a smarter approach: use the rings in frequency order
print(f"\n  --- Test 3: Optimal 14-ring supersets of universal ---")
print(f"    (Using ring frequency from known solutions)")

# The remaining 9 rings from sol2 are already working
# Can we find other working sets?
# Try replacing pairs from sol2

if len(successful_replacements) == 0:
    print(f"    No single replacement works - assignment is very fragile")
    
    # Try 2-ring replacements
    print(f"\n  --- Test 4: Two-ring replacements ---")
    for rm_combo in combinations(sorted(sol2), 2):
        base = set(sol2) - set(rm_combo)
        for add1, add2 in combinations(other_rings, 2):
            candidate = universal | base | {add1, add2}
            if len(candidate) != 14:
                continue
            assig = {d: 2 if d in candidate else 0 for d in ring_list}
            if sum(assig.values()) != 28:
                continue
            
            ok, _ = test(assig, n, "")
            if ok:
                print(f"    ✅ Replace {rm_combo} → {add1},{add2}")
    else:
        print(f"    Found {len(successful_replacements)} single replacements")
