"""Enumerate exact cyclic deletion-window profiles without choosing positions.

For a factor-cycle component, a proper nonempty deletion set is described by
the cyclic lengths of its deletion runs and positive gaps.  If the deletion
run lengths are ``ell_i``, then the counts of consecutive all-deleted windows
of lengths 2, 3, and 4 are respectively

    sum max(ell_i - 1, 0),
    sum max(ell_i - 2, 0),
    sum max(ell_i - 3, 0).

Only the existence of positive gap lengths matters, so an ordered run
composition is realisable precisely when the number of runs is at most the
number of retained edges.  Whole-component deletion is handled separately:
every cyclic window is then all deleted.
"""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path


HERE = Path(__file__).resolve().parent


def compositions(total: int, parts: int):
    """Yield ordered positive compositions of total into exactly parts."""
    if parts == 1:
        yield (total,)
        return
    for first in range(1, total - parts + 2):
        for rest in compositions(total - first, parts - 1):
            yield (first,) + rest


@lru_cache(maxsize=None)
def component_profiles(length: int, max_deleted: int):
    """Return (k,A,B,C) profiles for one factor-cycle component."""
    profiles = {(0, 0, 0, 0)}
    for deleted in range(1, min(length, max_deleted) + 1):
        if deleted == length:
            profiles.add((deleted, deleted, deleted, deleted))
            continue
        retained = length - deleted
        for runs in range(1, min(deleted, retained) + 1):
            for run_lengths in compositions(deleted, runs):
                a = sum(max(value - 1, 0) for value in run_lengths)
                b = sum(max(value - 2, 0) for value in run_lengths)
                c = sum(max(value - 3, 0) for value in run_lengths)
                profiles.add((deleted, a, b, c))
    return tuple(sorted(profiles))


def factor_profiles(cycle_lengths: tuple[int, ...], deleted: int):
    """Convolve component profiles, retaining only totals up to deleted."""
    profiles = {(0, 0, 0, 0)}
    for length in cycle_lengths:
        updated = set()
        for left in profiles:
            for right in component_profiles(length, deleted):
                combined = tuple(left[i] + right[i] for i in range(4))
                if combined[0] <= deleted:
                    updated.add(combined)
        profiles = updated
    return sorted(profile for profile in profiles if profile[0] == deleted)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", required=True)
    parser.add_argument("--deleted", type=int, required=True)
    parser.add_argument("--adjacency", type=int, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    cycles = tuple(int(value) for value in args.cycles.split(","))
    profiles = factor_profiles(cycles, args.deleted)
    if args.adjacency is not None:
        profiles = [p for p in profiles if p[1] == args.adjacency]
    grouped = {}
    for _, a, b, c in profiles:
        grouped.setdefault(str(a), []).append([b, c])
    payload = {
        "parameters": vars(args),
        "profile_count": len(profiles),
        "profiles": [
            {"deleted": k, "adjacent": a, "triple": b, "quadruple": c}
            for k, a, b, c in profiles
        ],
        "triple_quadruple_by_adjacency": grouped,
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        path = HERE / args.out
        path.write_text(text, encoding="utf-8")
        print(path)
    else:
        print(text)


if __name__ == "__main__":
    main()
