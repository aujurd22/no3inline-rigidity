# A seventh V20 state and its exact neutral one-flip component

**Status:** exact finite computation, independently rechecked by determinant
triple counting and canonical pair-line hashing, 2026-07-29.

The archived `v20_06` C4 state has raw collinear-triple energy 20.  Reversing
the non-loop fundamental edge

```text
(23,3) -> (3,23)
```

produces another raw-20 state.  The new point set is not D4-equivalent to any
of the six archived V20 states.  It is therefore a seventh known V20
configuration, but not evidence for a seventh independent basin: it is joined
to `v20_06` by one energy-neutral orientation flip.

The new state's 37 directed fundamental cells are

```text
(0,28)  (1,15)  (3,23)  (3,30)  (5,18)  (5,28)  (7,7)
(8,18)  (8,27)  (9,4)   (10,11) (10,21) (12,34) (13,11)
(14,22) (16,14) (17,13) (17,32) (20,2)  (20,12) (23,6)
(24,19) (24,21) (25,6)  (26,1)  (26,32) (27,16) (30,29)
(31,19) (31,22) (33,4)  (33,9)  (34,0)  (35,25) (35,29)
(36,2)  (36,15)
```

Exact enumeration of the component under a single legal orientation flip
gives:

| quantity | value |
|---|---:|
| orientation variables | 36 |
| raw-20 component states | 2 |
| neutral component edges | 1 |
| one-flip masks scored from the two states | 72 |
| boundary minimum raw energy | 28 |
| boundary states attaining 28 | 2 |

The boundary-energy histogram is

```text
28:2, 32:6, 36:2, 40:14, 44:14,
48:15, 52:9, 56:6, 60:1, 64:1.
```

The conclusion is narrow but useful.  One-flip search did miss a second point
on the same minimum plateau, yet the complete neutral component is only one
edge and every exit rises by at least eight bad triples.  The historical V20
stagnation is therefore not explained by a large hidden flat orientation
manifold.  Macro changes of the undirected factor or coupled multi-edge
reorientation remain necessary.
