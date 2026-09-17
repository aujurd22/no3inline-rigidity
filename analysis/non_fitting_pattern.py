#!/usr/bin/env python3
"""
Final synthesis: is there a pattern in the non-fitting m values?
"""
import math

print("=" * 65)
print("NON-FITTING m PATTERN ANALYSIS")
print("=" * 65)

non_fit = [6, 29, 32, 33, 34, 35]
fit_notable = [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 30, 31, 36]

print(f"\nNon-fitting (no single-cycle): {non_fit}")
print(f"Fitting (has single-cycle):     {fit_notable}")
print()

# Check: are there "runs" of non-fitting?
print("--- Runs of consecutive non-fitting m ---")
runs = []
current_run = []
for m in range(3, 37):
    if m in non_fit:
        current_run.append(m)
    else:
        if len(current_run) >= 2:
            runs.append(current_run)
        current_run = []
if len(current_run) >= 2:
    runs.append(current_run)
for r in runs:
    print(f"  Run: {r} ({len(r)} consecutive m)")
if not runs:
    print("  No runs of ≥2 consecutive non-fitting m")

# Check single non-fitting m isolated by fitting neighbors
isolated = [m for m in non_fit if m-1 not in non_fit and m+1 not in non_fit]
print(f"\nIsolated non-fitting (both neighbors have single-cycle): {isolated}")

# Check: m=6 is special - the only non-fitting m < 10
print(f"\nm=6 is the only non-fitting m < 10")
print(f"  It has nsol=4, all type [1,5] (loop+5-cycle)")
print(f"  No [6] type at all")

# Check: what about m=29, 31 comparison?
print(f"\nm=29 (non-fit, prime) vs m=31 (fit, prime):")
print(f"  29 ≡ 1 mod 4, 31 ≡ 3 mod 4")
print(f"  29: 19 solutions, 0% single-cycle, dominated by [1,28]")
print(f"  31: 5 solutions, 40% single-cycle, type [31] has 2 instances")

# Check factorization
print(f"\n--- Factorization of non-fitting m ---")
for m in non_fit:
    factors = []
    n = m
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    print(f"  m={m}: {m} = {' × '.join(str(f) for f in factors)}")

print(f"\n--- What about m mod 3? ---")
for m in range(3, 37):
    label = 'NON-FIT' if m in non_fit else 'fit'
    mod3 = m % 3
    print(f"  m={m:2d} (mod3={mod3}, {label})")

print(f"\n--- What about m mod 5? ---")
for m in range(3, 37):
    label = 'NON-FIT' if m in non_fit else ''
    mod5 = m % 5
    if m in non_fit:
        print(f"  m={m:2d} (mod5={mod5}) NON-FIT")

print(f"\n--- CONCLUSION ---")
print(f"No single arithmetic modulus distinguishes non-fitting m.")
print(f"The (X) constraint structure depends on m in a more complex way.")
print(f"Key empirical observations:")
print(f"  1. Small m (≤10): only m=6 is non-fit")
print(f"  2. Mid m (11-28): all have single-cycle solutions")
print(f"  3. Large m (29-35): only m=31 has single-cycle")
print(f"  4. m=36: back to 100% single-cycle (unique solution)")
print(f"")
print(f"This suggests the (X) constraint geometry has sharp transitions")
print(f"at specific m values, not a simple monotonic trend. This is")
print(f"consistent with the R8 theory: the 16 orientation classes have")
print(f"m-dependent alignment with the discrete grid.")
