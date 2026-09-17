"""Six-triple certificate for compatible permutations of Z/8Z.

A compatible permutation has triangular binary digits

  y0 = x0 xor c0
  y1 = x1 xor g1(x0)
  y2 = x2 xor g2(x0,x1).

There are 2^(1+2+4)=128 choices.  The six row triples below cover all of
them: for every choice, at least one triple of graph points is collinear.
The script uses only integer arithmetic and is intended as a tiny,
independently checkable base certificate for the induction to every 2^k.
"""

from __future__ import annotations

import itertools
import json


ROW_TRIPLES = (
    (0, 1, 2),
    (0, 1, 3),
    (1, 4, 7),
    (3, 4, 7),
    (3, 5, 7),
    (3, 6, 7),
)


def compatible_permutations_mod_8():
    for c0 in range(2):
        for g10 in range(2):
            for g11 in range(2):
                for g2_mask in range(16):
                    values = []
                    for x in range(8):
                        x0 = x & 1
                        x1 = (x >> 1) & 1
                        x2 = (x >> 2) & 1
                        y0 = x0 ^ c0
                        y1 = x1 ^ (g10 if x0 == 0 else g11)
                        y2 = x2 ^ ((g2_mask >> (x0 + 2 * x1)) & 1)
                        values.append(y0 + 2 * y1 + 4 * y2)
                    yield (c0, g10, g11, g2_mask), tuple(values)


def graph_rows_are_collinear(
    permutation: tuple[int, ...], rows: tuple[int, int, int]
) -> bool:
    first, middle, last = rows
    return (middle - first) * (
        permutation[last] - permutation[first]
    ) == (last - first) * (permutation[middle] - permutation[first])


def main() -> None:
    records = []
    coverage_counts = {rows: 0 for rows in ROW_TRIPLES}
    for parameters, permutation in compatible_permutations_mod_8():
        assert len(set(permutation)) == 8
        witnesses = [
            rows
            for rows in ROW_TRIPLES
            if graph_rows_are_collinear(permutation, rows)
        ]
        assert witnesses, (parameters, permutation)
        for rows in witnesses:
            coverage_counts[rows] += 1
        records.append(
            {
                "parameters": parameters,
                "permutation": permutation,
                "first_witness": witnesses[0],
            }
        )
    assert len(records) == 128
    assert len({tuple(record["permutation"]) for record in records}) == 128
    print(
        json.dumps(
            {
                "compatible_permutations": len(records),
                "certificate_row_triples": ROW_TRIPLES,
                "coverage_counts": [
                    coverage_counts[rows] for rows in ROW_TRIPLES
                ],
                "all_covered": True,
            }
        )
    )


if __name__ == "__main__":
    main()
