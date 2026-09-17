"""Generate prefilter_config.h for n=76 (N=38) using direction-based danger.
Marks cells on top dangerous directions at increasing radius from center.

Danger directions (from n<=72 analysis, ranked by collinear triple count):
  (1,1):  73M      — main diagonal
  (1,-1): ~73M     — anti-diagonal (symmetric)
  (1,2):  8.3M     — gentle slope
  (2,1):  8.3M     
  (1,3):  1.7M     
  (3,1):  1.7M
  (1,4):  moderate — steeper, less dangerous

Strength levels:
  moderate:  radius ±3 → ~30 cells
  aggressive: radius ±5 → ~55 cells  
  very_agg:  radius ±8 → ~90 cells
"""
import os, sys

N = 38  # n/2

# Generate cells on direction (dr, dc) within radius R of center
def cells_on_direction(dr, dc, R):
    """Return {(r,c)} pairs where (r-cx, c-cy) = k*(dr,dc) for |k|<=R."""
    cx = cy = N // 2  # center
    cells = set()
    for k in range(-R, R+1):
        if k == 0:
            continue
        r = cx + k * dr
        c = cy + k * dc
        if 0 <= r < N and 0 <= c < N:
            cells.add((r, c))
    return cells

def generate(level):
    if level == "moderate":
        R = 3
    elif level == "aggressive":
        R = 5
    elif level == "very_agg":
        R = 8
    else:
        raise ValueError(f"Unknown level: {level}")

    # Top dangerous directions (non-axis)
    directions = [(1,1), (1,-1), (1,2), (2,1), (1,3), (3,1), (1,4), (4,1)]

    all_cells = set()
    for dr, dc in directions:
        all_cells |= cells_on_direction(dr, dc, R)

    # Sort for reproducibility
    sorted_cells = sorted(all_cells)

    # Write prefilter_config.h
    mvr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mvr_reference")
    path = os.path.join(mvr_dir, "prefilter_config.h")

    cell_pairs = ", ".join(f"{{{r},{c}}}" for r, c in sorted_cells)
    content = f"""// Auto-generated prefilter for n=76 (N=38): level={level}, radius={R}
// Marks {len(sorted_cells)} cells on top-{len(directions)} dangerous directions.
#define PREFILTER_ENABLED   1
#define NUM_PREFILTER_CELLS {len(sorted_cells)}
#define PREFILTER_CELLS {cell_pairs}
"""
    with open(path, "w") as f:
        f.write(content)

    pct = 100 * len(sorted_cells) / (N*N)
    print(f"[{level}] radius={R} → {len(sorted_cells)} cells ({pct:.1f}% of domain)")
    return len(sorted_cells)

if __name__ == "__main__":
    for lvl in ["moderate", "aggressive", "very_agg"]:
        generate(lvl)
