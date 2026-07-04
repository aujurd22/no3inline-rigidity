#!/usr/bin/env python3
"""
analyze_rle.py — Parse RLE-format No-Three-In-Line solutions from
mvr/no-three-in-line (https://github.com/mvr/no-three-in-line) and
check for missing-center (circumcenter-free) solutions.

The RLE format:
  b = empty cell, o = occupied cell (point),
  $ = new row, ! = end of solution, digits = repeat count

Usage:
    python3 analyze_rle.py <rle_file> [--verbose]

Example:
    python3 analyze_rle.py results_14.out
"""

import sys
import os
import re
from collections import Counter

def parse_rle(content, n):
    """Parse RLE content into a list of (x,y) point lists."""
    solutions = []
    raw_sols = content.split('!')
    
    for raw in raw_sols:
        raw = raw.strip()
        if not raw:
            continue
        
        # Expand RLE: convert to expanded string
        expanded = []
        i = 0
        while i < len(raw):
            if raw[i].isdigit():
                j = i
                while j < len(raw) and raw[j].isdigit():
                    j += 1
                count = int(raw[i:j])
                i = j
            else:
                count = 1
            
            if i < len(raw):
                ch = raw[i]
                if ch in 'bo':
                    expanded.append(ch * count)
                elif ch == '$':
                    expanded.append('\n')
                i += 1
        
        rle_str = ''.join(expanded)
        rows = rle_str.split('\n')
        
        pts = []
        for r, row in enumerate(rows):
            if r >= n:
                break
            for c, ch in enumerate(row):
                if c >= n:
                    break
                if ch == 'o':
                    pts.append((c, r))
        
        if len(pts) == 2 * n:
            solutions.append(pts)
    
    return solutions


def check_missing_center(pts, n):
    """Check if grid center is NOT a circumcenter of any triple."""
    if n % 2 == 0:
        cx2, cy2 = n - 1, n - 1
    else:
        c = 2 * (n // 2)
        cx2, cy2 = c, c
    
    dist_counts = Counter()
    for x, y in pts:
        dx = 2 * x - cx2
        dy = 2 * y - cy2
        d = dx * dx + dy * dy
        dist_counts[d] += 1
    
    max_share = max(dist_counts.values())
    has_center = max_share >= 3
    return not has_center, max_share


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_rle.py <rle_file> [--verbose]")
        sys.exit(1)
    
    rle_path = sys.argv[1]
    verbose = '--verbose' in sys.argv
    
    with open(rle_path, 'r') as f:
        content = f.read()
    
    basename = os.path.basename(rle_path)
    m = re.search(r'(\d+)\.out', basename)
    if not m:
        print("Cannot determine n from filename.")
        sys.exit(1)
    n = int(m.group(1))
    
    print(f"Parsing n={n} from {basename}...")
    
    solutions = parse_rle(content, n)
    print(f"Found {len(solutions)} solutions.")
    
    missing_count = 0
    center_count = 0
    
    for idx, pts in enumerate(solutions):
        missing, max_share = check_missing_center(pts, n)
        if missing:
            missing_count += 1
            if verbose:
                print(f"  #{idx}: MISSING (max ring={max_share})")
        else:
            center_count += 1
    
    print(f"\n{'='*50}")
    print(f"n={n} Results:")
    print(f"  Total (inequivalent): {len(solutions)}")
    print(f"  With center         : {center_count}")
    print(f"  Missing center      : {missing_count}")
    print(f"  Missing rate        : {missing_count/len(solutions)*100:.1f}%")


if __name__ == '__main__':
    main()
