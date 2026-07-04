#!/usr/bin/env python3
"""
Quick analysis: what makes the working ring assignment special?
Test a few focused hypotheses, then generate n=14 candidate.
"""
import subprocess, os, sys
from collections import defaultdict

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
    fname = os.path.join(WORKDIR, "_tmp_assig.txt")
    with open(fname, 'w') as f:
        for d, c in sorted(assig.items()):
            if c > 0: f.write(f"{d} {c}\n")
    total = sum(assig.values())
    if total != 2*n: return False, 0, f"invalid(total={total})"
    try:
        r = subprocess.run([SOLVER, str(n), "1", fname], capture_output=True, text=True, timeout=60)
        o = r.stdout + r.stderr
        if "Found" in o:
            for l in o.split('\n'):
                if 'Found' in l and '(' in l:
                    return True, float(l.split('(')[1].split('s')[0]), "ok"
            return True, 0, "ok"
        elif "No valid" in o:
            for l in o.split('\n'):
                if 'No valid' in l and '(' in l:
                    return False, float(l.split('(')[1].split('s')[0]), "none"
            return False, 0, "none"
        return False, 0, o[:80]
    except:
        return False, 120, "timeout"

# ===== n=12 Analysis =====
n = 12
rings = build_rings(n)
ring_list = sorted(rings.keys())
caps = {d: len(pts) for d, pts in rings.items()}

# Known working: d=10,26,34,74,82,90,98,106,122,130,170,202
KW = {10, 26, 34, 74, 82, 90, 98, 106, 122, 130, 170, 202}
skipped = [d for d in ring_list if d not in KW]
used = [d for d in ring_list if d in KW]

print(f"n=12 Known Working Set:")
print(f"  Used (12): {used}")
print(f"  Skipped (7): {skipped}")
print(f"  Ring capacities:")
for d in ring_list:
    marker = " ← SKIP" if d in skipped else " ← USE"
    print(f"    d={d:4d}: {caps[d]:2d} pts{marker}")

# Hypothesis: skipped rings share a common property
print(f"\n  Analyzing skipped rings:")
for d in skipped:
    pts = rings[d]
    print(f"    d={d:4d}: points={sorted(pts)}, min_row={min(p[0] for p in pts)}, max_row={max(p[0] for p in pts)}")

print(f"\n  Analyzing used rings:")
for d in used:
    pts = rings[d]
    print(f"    d={d:4d}: points={sorted(pts)}, min_row={min(p[0] for p in pts)}, max_row={max(p[0] for p in pts)}")

# ===== n=14 candidate generation =====
print(f"\n{'='*70}")
print(f"n=14 Candidate Generation")
print(f"{'='*70}")

# Compute parity/property of rings for n=14
n14 = 14
rings14 = build_rings(n14)
ring14_list = sorted(rings14.keys())
caps14 = {d: len(pts) for d, pts in rings14.items()}

print(f"  All rings for n=14:")
for d in ring14_list:
    print(f"    d={d:4d}: {caps14[d]:2d} pts")

# Strategy: mimic n=12 pattern
# n=12: skip smallest d rings, use mostly 8-pt rings
# For n=14: 14×2 = 28pts needed
# 14×2 = 28. If we use 14 rings × 2pt = 28pts, we skip the rest.
# Or: 13×2 + 2×1 = 28, skip some

# Check: what ring capacities give us what?
# n=14 has ... let me count
print(f"  n=14 has {len(ring14_list)} rings, need {2*n14} pts")

# Try: use d=130,170,202,etc. (8-pt rings) first, skip small ones
# Copy the n=12 skip pattern: skip innermost + some outer 4-pt rings
# n=12: used={10,26,34,74,82,90,98,106,122,130,170,202}, skipped={2,18,50,58,146,162,242}
# Note: n=12 skipped d=2,18 (inner), 50,58 (inner-mid), 146,162 (mid-outer), 242 (outermost 4-pt)
# Pattern: skip the d values that have only 4 pts (small inner or isolated)
# For n=14, 4-pt rings are: d=2,18,50,98,162,242,338

# Try pattern: skip 4-pt rings + some others
four_pt_rings = [d for d in ring14_list if caps14[d] == 4]
eight_pt_rings = [d for d in ring14_list if caps14[d] == 8]
print(f"\n  n=14 rings by capacity:")
print(f"    4-pt: {four_pt_rings}")
print(f"    8-pt: {eight_pt_rings}")

# For 28 pts with 14 2-pt rings: need to skip 14-? = ? rings
# Total rings = ? for n=14
# Let me compute
print(f"\n  Total rings: {len(ring14_list)}")
# If we skip all 4-pt rings: remaining = total - len(four_pt_rings) = ?
# Use those as 2-pt rings
remaining14 = [d for d in ring14_list if d not in four_pt_rings]
print(f"  Rings after skipping all 4-pt: {len(remaining14)}")
print(f"  If all used as 2-pt: {2*len(remaining14)} pts")

# Heuristic: use first 14 rings (largest or most central)
# Try: use the 8-pt rings first (they have the most geometric flexibility)
# 8-pt rings have diversity for row/col assignment
candidate14 = eight_pt_rings[:14]
if len(candidate14) < 14:
    # Supplement with 4-pt rings
    remaining = [d for d in ring14_list if d not in candidate14]
    candidate14.extend(remaining[:14 - len(candidate14)])

print(f"\n  Candidate: {len(candidate14)} rings × 2pt")
print(f"  Used: {sorted(candidate14)}")
print(f"  Skipped: {[d for d in ring14_list if d not in candidate14]}")

# Test it
assig14 = {d: 2 if d in candidate14 else 0 for d in ring14_list}
print(f"\n  Testing n=14 candidate...")
found, t, status = test(assig14, 14, "n14 14×2pt using 8-pt rings")
sym = "✅" if found else "❌"
print(f"  {sym} {status} ({t:.3f}s)")

# Test 2 for n=14: 13×2pt + 2×1pt = 28
print(f"\n  Test 2: 13×2pt + 2×1pt...")
assig14b = {}
for i, d in enumerate(ring14_list):
    if i < 13:
        assig14b[d] = 2
    elif i < 15:
        assig14b[d] = 1
    else:
        assig14b[d] = 0
if sum(assig14b.values()) == 28:
    found, t, status = test(assig14b, 14, "n14 13×2pt+2×1pt first rings")
    sym = "✅" if found else "❌"
    print(f"  {sym} {status} ({t:.3f}s)")

# Test 3: skip some inner rings, use medium ones
print(f"\n  Test 3: skip first 7 rings, use next 14 × 2pt...")
assig14c = {}
for i, d in enumerate(ring14_list):
    if i >= 7 and i < 21:  # 14 rings
        assig14c[d] = 2
    else:
        assig14c[d] = 0
if sum(assig14c.values()) == 28:
    used_rings = [d for d, c in assig14c.items() if c > 0]
    print(f"    Used: {used_rings}")
    found, t, status = test(assig14c, 14, "n14 skip 7 inner, use 14×2pt")
    sym = "✅" if found else "❌"
    print(f"  {sym} {status} ({t:.3f}s)")
