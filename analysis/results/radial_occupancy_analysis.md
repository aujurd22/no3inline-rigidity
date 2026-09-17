# Radial-layer occupancy analysis (all cached rot4 solutions, m=5..19)

## Q1: rings with exactly 2 points
  **NONE.** Every C4 orbit has size exactly 4, so board-point occupancy on
  any ring is always a multiple of 4. No ring ever contains exactly 2 points.

## Q2/Q3: occupancy distribution (board points per ring)

Global ring-count by occupancy value (summed over all solutions & all m):
  occupancy   4: 14188 rings
  occupancy   8: 600 rings
  occupancy  12: 16 rings

Per-m breakdown (occ -> #rings):
  m= 5 (nsol=  6, max_occ=4): {4: 30}
  m= 6 (nsol=  4, max_occ=4): {4: 24}
  m= 7 (nsol= 13, max_occ=8): {4: 83, 8: 4}
  m= 8 (nsol= 13, max_occ=8): {4: 100, 8: 2}
  m= 9 (nsol=  7, max_occ=8): {4: 59, 8: 2}
  m=10 (nsol= 16, max_occ=8): {4: 138, 8: 11}
  m=11 (nsol=  8, max_occ=8): {4: 78, 8: 5}
  m=12 (nsol= 23, max_occ=8): {4: 256, 8: 10}
  m=13 (nsol= 36, max_occ=12): {4: 397, 8: 34, 12: 1}
  m=14 (nsol= 58, max_occ=12): {8: 33, 4: 740, 12: 2}
  m=15 (nsol= 92, max_occ=12): {4: 1278, 8: 42, 12: 6}
  m=16 (nsol=101, max_occ=12): {8: 71, 4: 1468, 12: 2}
  m=17 (nsol=172, max_occ=12): {8: 127, 4: 2664, 12: 2}
  m=18 (nsol=200, max_occ=12): {4: 3351, 8: 123, 12: 1}
  m=19 (nsol=200, max_occ=12): {4: 3522, 8: 136, 12: 2}

## Where do >4-point rings sit? (normalized radial position, 0=innermost,1=outermost)
  occ=  8: n=  600, mean_norm=0.522, range=[0.0,1.0], d range=[34,1586]
  occ= 12: n=   16, mean_norm=0.648, range=[0.0,1.0], d range=[250,850]

## Is >4 usually 8?
  Rings with >4 points: 616 total.  Of these, exactly 8: 600 (97.4%).
  By value: 8:600, 12:16