"""
Analyze how the 4m C4-lifted points distribute around the 8 radial rays
from the grid center. Check clustering at 0/45/90/135/180/225/270/315 deg.
"""
import json, math, os
from collections import Counter

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def angle_from_center(px, py, cx, cy):
    """Angle in degrees from grid center, 0=right, 90=up."""
    dx = px - cx
    dy = py - cy
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return None
    a = math.degrees(math.atan2(dy, dx))
    if a < 0: a += 360
    return a

def angle_bucket(deg):
    """Assign to nearest ray direction (every 45 degrees)."""
    # 0° = right, 90° = up, etc.
    buckets = [0, 45, 90, 135, 180, 225, 270, 315]
    return min(buckets, key=lambda b: abs(deg - b))

def analyze_solution(m, cells):
    N = 2 * m
    cx = (N - 1) / 2.0  # grid center
    cy = (N - 1) / 2.0
    
    pts = [c4(c, r, N) for c in cells for r in range(4)]
    
    # Per-point angle analysis
    ray_counts = Counter()
    point_angles = []
    for p in pts:
        ang = angle_from_center(p[0], p[1], cx, cy)
        if ang is not None:
            ray = angle_bucket(ang)
            ray_counts[ray] += 1
            point_angles.append((p, ang, ray))
    
    # Also analyze just the m cells in top-left quadrant
    cell_angles = []
    cell_ray_counts = Counter()
    for (x, y) in cells:
        p = c4((x, y), 0, N)  # r=0, same as (x,y) in top-left
        ang = angle_from_center(p[0], p[1], cx, cy)
        if ang is not None:
            ray = angle_bucket(ang)
            cell_ray_counts[ray] += 1
            cell_angles.append(((x,y), ang, ray))
    
    return {
        'm': m,
        'grid_center': (cx, cy),
        'ray_counts': dict(ray_counts),
        'cell_ray_counts': dict(cell_ray_counts),
        'n_points': len(pts)
    }

def main():
    sol_dir = 'results/solutions'
    results = {}
    
    print("=== Points distribution around 8 radial rays from grid center ===\n")
    print("Ray legend: 0°=右, 90°=上, 180°=左, 270°=下\n")
    
    for fname in sorted(os.listdir(sol_dir)):
        if not fname.endswith('.json'): continue
        data = json.load(open(f'{sol_dir}/{fname}'))
        if 'cells' not in data: continue
        cells = data['cells']
        m = data.get('m', len(cells))
        
        r = analyze_solution(m, cells)
        results[str(m)] = r
        cx, cy = r['grid_center']
        
        print(f"m={m:2d} (中心=({cx:.1f},{cy:.1f}), {r['n_points']} points):")
        
        # Show ray distribution
        rc = r['ray_counts']
        c_rc = r['cell_ray_counts']
        
        # Compute entropy / uniformity
        total = sum(rc.values())
        ideal = total / 8
        max_dev = max(abs(v - ideal) for v in rc.values()) / total * 100 if total > 0 else 0
        
        print(f"   4m点角度分布:")
        for ray in [0, 45, 90, 135, 180, 225, 270, 315]:
            v = rc.get(ray, 0)
            bar = '#' * max(1, v)
            cell_v = c_rc.get(ray, 0)
            print(f"     {ray:3d}°: {v:3d} pts {'─' * (v)} (其中 {cell_v} 个为原始 cell)")
        print(f"   最大偏差: {max_dev:.1f}%")
        
        # Check if any ray is EMPTY
        empty_rays = [r for r in [0,45,90,135,180,225,270,315] if rc.get(r, 0) == 0]
        if empty_rays:
            print(f"   ⚠ 空射线: {empty_rays}")
        print()
    
    json.dump(results, open('results/ray_analysis.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
