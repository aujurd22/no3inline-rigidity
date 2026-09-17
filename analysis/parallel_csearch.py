#!/usr/bin/env python3
"""Parallel SA harness for rot4-NTIL (m=37).

Spawns N independent csearch2 workers (each its own RNG/seed, optional --init
file), runs them concurrently, and bounds the whole thing by a wall-clock
limit. This is the CPU multi-core equivalent of the GPU parallel solver
(CUDA could not compile here: no MSVC host compiler for nvcc).

Usage:
  parallel_csearch.py --m 37 --workers 6 --wall 540 [--init-dir DIR] [--tag P]
"""
import subprocess, sys, os, time, argparse, re, json, glob
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "csearch2.exe")


def parse_out(out):
    found = "FOUND m=" in out
    m = re.search(r"best_bad=(\d+)", out)
    best = int(m.group(1)) if m else None
    cells = None
    if found:
        cm = re.search(r"cells:(.*)", out)
        if cm:
            cells = cm.group(1).strip()
    return found, best, cells


def worker(seed, m, moves, init_file, wall):
    cmd = [EXE, "--m", str(m), "--seed", str(seed), "--moves", str(moves)]
    if init_file:
        cmd += ["--init", init_file]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=wall)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "")
    f, best, cells = parse_out(out)
    return {"seed": seed, "init": init_file, "found": f, "best": best, "cells": cells}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--moves", type=int, default=200000000)
    ap.add_argument("--wall", type=int, default=540)
    ap.add_argument("--init-dir", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    inits = []
    if a.init_dir:
        inits = sorted(glob.glob(os.path.join(a.init_dir, "*.txt")))
    tasks = []
    for w in range(a.workers):
        init_file = inits[w % len(inits)] if inits else None
        tasks.append((w + 1, a.m, a.moves, init_file, a.wall))

    results = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(worker, *t) for t in tasks]
        for fu in futs:
            results.append(fu.result())

    best_overall = min((r["best"] for r in results if r["best"] is not None), default=None)
    found = [r for r in results if r["found"]]
    print(f"=== parallel_csearch {a.tag} m={a.m} workers={a.workers} wall={a.wall} ===")
    print(f"best_bad_overall={best_overall}")
    print(f"found_count={len(found)}")
    for r in results:
        nm = os.path.basename(r["init"]) if r["init"] else "RANDOM"
        print(f"  worker seed={r['seed']} init={nm} best={r['best']} found={r['found']}")
    if found:
        sol = found[0]
        with open(os.path.join(HERE, "results", f"ai_found_{a.tag}.txt"), "w") as f:
            f.write("cells:" + sol["cells"] + "\n")
        print("WROTE results/ai_found_%s.txt" % a.tag)
    if a.out:
        json.dump({"tag": a.tag, "m": a.m, "best": best_overall, "found": bool(found),
                   "workers": results}, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
