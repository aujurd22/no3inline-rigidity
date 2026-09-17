"""
direction4_packing.py — Direction 4: 4-cell obstruction packing argument.

The idea: if we can find a family of 4-cell subsets such that:
1. Each 4-subset "forces" at least 1 violation (any 2-factor containing all 4 cells
   CANNOT make all constraints satisfiable)
2. The subsets are pairwise DISJOINT (no cell shared between subsets)
3. There are ≥ 16 such disjoint subsets

Then any 2-factor on 37 vertices must have ≥ 16 violations.

This is a hypergraph packing / Turán-type argument.

Instead of brute force, we use a mathematical approach:
- From direction 3, the minimum constrained triples is ~81 for any 2-factor
- Each violation (collinear triple) involves 3 cells
- By the handshake lemma: 3 × violations ≤ 37 × (max participated per cell)
  If each cell participates in at most ~13 violations, then:
  violations ≥ 81 / 13 ≈ 6.2  (too weak)

A better bound: if the constraint hypergraph's independence number α ≤ 16,
then the hypergraph has no independent set of size 37 = the problem is unsolvable.

The conflict hypergraph has:
- |V| = 1369 (all possible cells)
- |E| = 30,992,032 (X-layer hyperedges, each a forbidden cell triple)
- Each hyperedge = 3 cells that cannot ALL be selected simultaneously

So we need to find if there's a 37-vertex independent set in this 3-uniform
hypergraph. This is equivalent to a 37-set with no constrained triples = a solution.

Approach: compute a lower bound on the independence number using
Carathéodory / Turán-type bounds for 3-uniform hypergraphs.

For a 3-uniform hypergraph H with maximum degree Δ₃:
  α(H) ≥ Σ_v (1 / (1 + Δ₃/2))  [by a greedy independent set bound]
  
At m=37, Δ₃_max = 92,488, so this gives α ≥ 1369 / (1 + 92488/2) ≈ 0.03  — useless.

The hypergraph is too dense for general bounds. We need to exploit its
EXTREME sparsity in terms of "forced" substructures.

We report our findings here rather than running heavy computations.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
print("=== Direction 4: 4-Cell Obstruction Analysis ===")
print(f"Report saved to {__file__}")
