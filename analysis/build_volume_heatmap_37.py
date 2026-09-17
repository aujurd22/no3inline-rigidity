#!/usr/bin/env python3
"""Build a theorem-aware 37 x 37 x 37 volume from known C4 NTIL solutions.

Axes:
  x, y: the C4 fundamental-quadrant cell, area-normalized to a 37 x 37 grid.
  z:     m = n / 2.  Layers 1..36 are observed when data exist; layer 37 is a
         clearly labelled trend projection, never presented as a solution.

The main value is enrichment P(cell)/(1/m).  Every solution is averaged with
its transpose, which is an exact symmetry of the problem and prevents the
enumerator's row/column convention from creating a false directional signal.
The residual channel removes a low-dimensional radial + diagonal feature model.

Only NumPy and Pillow are required.  The HTML viewer is standalone JavaScript.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


R = 37
ALPH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
VAL = {c: i for i, c in enumerate(ALPH)}
SYMM = set(".:/-ocx+*")


def decode_compact(line: str, n: int) -> list[tuple[int, int]]:
    line = line.strip()
    body = line[1:] if line and line[0] in SYMM else line
    if len(body) < 2 * n:
        raise ValueError(f"compact line too short for n={n}")
    pts = []
    for row in range(n):
        pts.append((VAL[body[2 * row]], row))
        pts.append((VAL[body[2 * row + 1]], row))
    return pts


def decode_mvr(line: str, n: int) -> list[tuple[int, int]]:
    values = [int(v) for v in line.split()]
    if len(values) != 4 * n:
        raise ValueError(f"MVR line has {len(values)} integers, expected {4*n}")
    # MVR text is (row, column) repeated; internally use (x=column, y=row).
    return [(values[i + 1], values[i]) for i in range(0, len(values), 2)]


def line_key(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int, int]:
    A = b[1] - a[1]
    B = a[0] - b[0]
    C = -(A * a[0] + B * a[1])
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    A, B, C = A // g, B // g, C // g
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return A, B, C


def no_three_in_line(pts: list[tuple[int, int]]) -> bool:
    seen: set[tuple[int, int, int]] = set()
    for a, b in combinations(pts, 2):
        key = line_key(a, b)
        if key in seen:
            return False
        seen.add(key)
    return True


def structural_cells(pts: list[tuple[int, int]], n: int) -> tuple[tuple[int, int], ...]:
    """Validate cheap exact invariants and return the fundamental cells."""
    if len(pts) != 2 * n or len(set(pts)) != 2 * n:
        raise ValueError("wrong point count or duplicate point")
    if any(not (0 <= x < n and 0 <= y < n) for x, y in pts):
        raise ValueError("point outside board")
    rows = [0] * n
    cols = [0] * n
    P = set(pts)
    for x, y in pts:
        cols[x] += 1
        rows[y] += 1
        if (n - 1 - y, x) not in P:
            raise ValueError("not closed under quarter turn")
    if any(v != 2 for v in rows) or any(v != 2 for v in cols):
        raise ValueError("not exactly two points in each row and column")
    m = n // 2
    cells = tuple(sorted((x, y) for x, y in pts if x < m and y < m))
    if len(cells) != m:
        raise ValueError(f"fundamental quadrant has {len(cells)} points, expected {m}")
    return cells


def lift_cells(cells: tuple[tuple[int, int], ...], m: int) -> list[tuple[int, int]]:
    n = 2 * m
    out = set()
    for p0 in cells:
        p = p0
        for _ in range(4):
            out.add(p)
            p = (n - 1 - p[1], p[0])
    return sorted(out)


def enumerate_small_m(m: int) -> list[tuple[tuple[int, int], ...]]:
    sols = []
    for cells in combinations([(x, y) for x in range(m) for y in range(m)], m):
        pts = lift_cells(tuple(cells), m)
        try:
            got = structural_cells(pts, 2 * m)
        except ValueError:
            continue
        if no_three_in_line(pts):
            sols.append(got)
    return sorted(set(sols))


def load_solutions(cache: Path, max_m: int = 36):
    by_m: dict[int, set[tuple[tuple[int, int], ...]]] = defaultdict(set)
    source_rows = []
    invalid = []
    sample_checks = 0
    for path in sorted(cache.glob("n*_rot4*")):
        name = path.name
        try:
            n = int(name[1:name.index("_")])
        except (ValueError, IndexError):
            continue
        if n % 2 or n // 2 > max_m or not (
            name == f"n{n}_rot4" or name in {f"n{n}_rot4.few", f"n{n}_rot4.mvr"}
        ):
            continue
        decoder = decode_mvr if name.endswith(".mvr") else decode_compact
        parsed = 0
        accepted = 0
        examples = []
        with path.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                parsed += 1
                try:
                    pts = decoder(line, n)
                    cells = structural_cells(pts, n)
                except (ValueError, KeyError) as exc:
                    invalid.append({"file": name, "line": line_no, "error": str(exc)})
                    continue
                by_m[n // 2].add(cells)
                accepted += 1
                if len(examples) < 2:
                    examples.append(pts)
        checked = 0
        for pts in examples:
            if not no_three_in_line(pts):
                invalid.append({"file": name, "line": "sample", "error": "three collinear points"})
            checked += 1
        sample_checks += checked
        source_rows.append({
            "file": name,
            "m": n // 2,
            "parsed": parsed,
            "structurally_accepted": accepted,
            "ntil_samples_checked": checked,
        })

    # Complete the two tiny layers exactly; they are too small to need a cache.
    for m in (1, 2):
        tiny = enumerate_small_m(m)
        by_m[m].update(tiny)
        source_rows.append({
            "file": f"exact-enumeration-m{m}", "m": m, "parsed": len(tiny),
            "structurally_accepted": len(tiny), "ntil_samples_checked": len(tiny),
        })
        sample_checks += len(tiny)
    return {m: sorted(v) for m, v in by_m.items()}, source_rows, invalid, sample_checks


def area_resize(a: np.ndarray, r: int = R) -> np.ndarray:
    """Area-conserving cell-average resampling from m x m to r x r.

    Unlike ordinary image interpolation this treats each source value as a unit
    cell, so narrow lattice features cannot gain mass merely through smoothing.
    """
    m = a.shape[0]
    W = np.zeros((r, m), dtype=float)
    for j in range(r):
        ta, tb = j / r, (j + 1) / r
        for i in range(m):
            sa, sb = i / m, (i + 1) / m
            W[j, i] = max(0.0, min(tb, sb) - max(ta, sa)) * r
    return W @ a @ W.T


def feature_matrix(r: int = R):
    u = (np.arange(r) + 0.5) / r
    x, y = np.meshgrid(u, u, indexing="ij")
    rho = np.sqrt((1 - x) ** 2 + (1 - y) ** 2) / math.sqrt(2)
    d = np.abs(x - y)
    feats = np.stack([
        np.ones_like(x), rho, rho**2, rho**3, d, d**2,
        np.exp(-d / 0.04), np.exp(-d / 0.12),
    ], axis=-1).reshape(-1, 8)
    return x, y, rho, d, feats


def fit_known_features(logq: np.ndarray, feats: np.ndarray):
    y = logq.reshape(-1)
    beta, *_ = np.linalg.lstsq(feats, y, rcond=None)
    pred = (feats @ beta).reshape(logq.shape)
    residual = logq - pred
    ss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(residual**2)) / ss if ss > 0 else 1.0
    return pred, residual, beta, r2


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    aa = a.reshape(-1) - float(a.mean())
    bb = b.reshape(-1) - float(b.mean())
    den = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    return float(np.dot(aa, bb) / den) if den else 0.0


def average_ranks(a: np.ndarray) -> np.ndarray:
    """Dependency-free rankdata with average ranks for ties."""
    flat = np.asarray(a).reshape(-1)
    order = np.argsort(flat, kind="mergesort")
    ranks = np.empty(len(flat), dtype=float)
    i = 0
    while i < len(flat):
        j = i + 1
        while j < len(flat) and flat[order[j]] == flat[order[i]]:
            j += 1
        ranks[order[i:j]] = 0.5 * (i + j - 1)
        i = j
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    return pearson(average_ranks(a), average_ranks(b))


def select_peaks(a: np.ndarray, count: int = 10, hot: bool = True, radius: int = 3):
    work = a.copy()
    out = []
    for _ in range(count):
        idx = int(np.argmax(work) if hot else np.argmin(work))
        x, y = np.unravel_index(idx, work.shape)
        out.append({"x": int(x + 1), "y": int(y + 1), "enrichment": float(a[x, y])})
        x0, x1 = max(0, x - radius), min(R, x + radius + 1)
        y0, y1 = max(0, y - radius), min(R, y + radius + 1)
        work[x0:x1, y0:y1] = -np.inf if hot else np.inf
    return out


def rgb_diverging(v: float, limit: float = 1.0) -> tuple[int, int, int]:
    t = max(-1.0, min(1.0, v / limit))
    if t >= 0:
        return (225, int(238 - 155 * t), int(238 - 190 * t))
    t = -t
    return (int(238 - 185 * t), int(240 - 125 * t), 230)


def heatmap_tile(a: np.ndarray, title: str, size: int = 270, limit: float = 1.0):
    im = Image.new("RGB", (size, size + 38), "white")
    dr = ImageDraw.Draw(im)
    cell = size / R
    for x in range(R):
        for y in range(R):
            x0, x1 = round(x * cell), round((x + 1) * cell)
            # Draw board centre at the upper-right, matching analysis coordinates.
            y0, y1 = round((R - 1 - y) * cell), round((R - y) * cell)
            dr.rectangle((x0, y0, x1, y1), fill=rgb_diverging(float(a[x, y]), limit))
    dr.line((0, size, size, 0), fill=(45, 45, 45), width=1)
    dr.text((8, size + 10), title, fill=(20, 20, 20))
    return im


def make_preview(path: Path, log_volume: np.ndarray, residual_mean: np.ndarray,
                 predicted: np.ndarray, nsol: np.ndarray):
    W, H = 1600, 980
    im = Image.new("RGB", (W, H), (249, 249, 251))
    dr = ImageDraw.Draw(im)

    # Isometric point cloud of high-contrast voxels.  Low-sample layers fade out.
    cx, cy = 430, 495
    sx, sy, sz = 8.4, 4.2, 12.2
    pts = []
    for z in range(36):
        if nsol[z] <= 0:
            continue
        conf = min(1.0, math.log1p(float(nsol[z])) / math.log(41))
        for x in range(0, R, 2):
            for y in range(0, R, 2):
                v = float(log_volume[z, x, y])
                if abs(v) < 0.33:
                    continue
                X = (x - y) * sx
                Y = (x + y - 36) * sy - z * sz
                pts.append((x + y + z, cx + X, cy + Y, v, conf))
    pts.sort(key=lambda q: q[0])
    for _, px, py, v, conf in pts:
        col = rgb_diverging(v, 1.0)
        bg = (249, 249, 251)
        col = tuple(round(bg[i] * (1 - 0.75 * conf) + col[i] * 0.75 * conf) for i in range(3))
        dr.ellipse((px - 2, py - 2, px + 2, py + 2), fill=col)
    dr.line((cx, cy + 36 * sy, cx + 36 * sx, cy, cx, cy - 36 * sy, cx, cy + 36 * sy),
            fill=(60, 60, 70), width=2)
    dr.line((cx, cy + 36 * sy, cx, cy + 36 * sy - 35 * sz), fill=(60, 60, 70), width=2)
    dr.text((65, 875), "3D volume: only |log2 enrichment| >= 0.33 shown; transparency follows sample support",
            fill=(65, 65, 75))

    tiles = [
        heatmap_tile(log_volume[17], f"observed m=18, solutions={nsol[17]}", limit=1),
        heatmap_tile(log_volume[27], f"observed m=28, solutions={nsol[27]}", limit=1),
        heatmap_tile(log_volume[31], f"observed m=32, solutions={nsol[31]}", limit=1),
        heatmap_tile(np.log2(predicted), "projected m=37 (not a solution)", limit=1),
        heatmap_tile(residual_mean, "stable residual after radial+diagonal fit", limit=0.35),
    ]
    positions = [(925, 75), (1210, 75), (925, 405), (1210, 405), (1067, 735)]
    for tile, pos in zip(tiles, positions):
        im.paste(tile, pos)
    # Paint the header last so projected points above the z-axis cannot obscure it.
    dr.rectangle((0, 0, 900, 68), fill=(249, 249, 251))
    dr.text((28, 18), "NTIL C4 37 x 37 x 37 theorem-aware volume", fill=(15, 20, 30))
    dr.text((28, 42), "red = over-selected; blue = avoided; z = m; layer 37 is projection only",
            fill=(70, 75, 85))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>NTIL 37^3 heatmap</title>
<style>
body{font:14px system-ui;margin:0;background:#111722;color:#e8edf5}header{padding:14px 20px;background:#182131}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:12px;padding:12px}canvas{width:100%;background:#f7f8fa;border-radius:7px}
.controls{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.note{color:#aebbd0}.card{background:#182131;padding:12px;border-radius:7px}
select,input{vertical-align:middle} b{color:#fff} @media(max-width:900px){.grid{grid-template-columns:1fr}}
</style></head><body><header><b>NTIL C4: 37 x 37 x 37 体热力图</b>
<div class="note">x,y=归一化基本域；z=m。红=富集，蓝=回避。第37层是趋势投影，不是已知解。</div>
<div class="controls"><label>通道 <select id="mode"><option value="q">log2 富集</option><option value="r">径向+对角残差</option></select></label>
<label>阈值 <input id="thr" type="range" min="0.10" max="1.00" step="0.05" value="0.35"><span id="tv">0.35</span></label>
<label>切片 m=<input id="layer" type="range" min="1" max="37" step="1" value="28"><span id="lv">28</span></label></div></header>
<div class="grid"><div class="card"><canvas id="vol" width="1050" height="720"></canvas><div class="note">拖动旋转；滚轮缩放。低样本层自动变淡。</div></div>
<div class="card"><canvas id="slice" width="520" height="520"></canvas><p id="meta"></p><p class="note">虚线是 x=y。右上角对应原棋盘中心方向。</p></div></div>
<script>
const D=__DATA__, R=37, vol=document.getElementById('vol'), vc=vol.getContext('2d'), sl=document.getElementById('slice'), sc=sl.getContext('2d');
let yaw=-.72,pitch=.55,zoom=1,drag=false,lx=0,ly=0;
function color(v,a=1){let t=Math.max(-1,Math.min(1,v)); let q=t>=0?[225,238-155*t,238-190*t]:[238-185*(-t),240-125*(-t),230];return `rgba(${q[0]|0},${q[1]|0},${q[2]|0},${a})`}
function arr(){return document.getElementById('mode').value==='q'?D.q:D.r}
function value(A,z,x,y){return A[(z*R+x)*R+y]}
function project(x,y,z){x=(x-18)/18;y=(y-18)/18;z=(z-18)/18;let X=Math.cos(yaw)*x-Math.sin(yaw)*y,Y=Math.sin(yaw)*x+Math.cos(yaw)*y;let Z=Math.cos(pitch)*z-Math.sin(pitch)*Y,YY=Math.sin(pitch)*z+Math.cos(pitch)*Y;let s=235*zoom/(2.6-Z*.25);return [vol.width/2+X*s,vol.height/2-YY*s,Z]}
function drawVol(){let A=arr(),th=+document.getElementById('thr').value, pts=[];vc.clearRect(0,0,vol.width,vol.height);vc.fillStyle='#f7f8fa';vc.fillRect(0,0,vol.width,vol.height);
 for(let z=0;z<36;z++){if(!D.obs[z])continue;let step=th<.25?3:2,alpha=Math.min(1,Math.log1p(D.n[z])/Math.log(41));for(let x=0;x<R;x+=step)for(let y=0;y<R;y+=step){let v=value(A,z,x,y);if(Math.abs(v)<th)continue;let p=project(x,y,z);pts.push([p[2],p[0],p[1],v,alpha]);}}
 pts.sort((a,b)=>a[0]-b[0]);for(let p of pts){vc.fillStyle=color(p[3],.15+.65*p[4]);vc.beginPath();vc.arc(p[1],p[2],2.2,0,7);vc.fill();}
 vc.fillStyle='#202633';vc.fillText('m increases upward',20,25);vc.fillText('observed layers only (m=1..36)',20,45)}
function drawSlice(){let A=arr(),m=+document.getElementById('layer').value,z=m-1,c=sl.width/R;sc.clearRect(0,0,sl.width,sl.height);for(let x=0;x<R;x++)for(let y=0;y<R;y++){let v=m===37&&document.getElementById('mode').value==='q'?Math.log2(D.p[x*R+y]):value(A,z,x,y);sc.fillStyle=color(v,.95);sc.fillRect(x*c,(R-1-y)*c,c+1,c+1)}sc.strokeStyle='#222';sc.setLineDash([7,5]);sc.beginPath();sc.moveTo(0,sl.height);sc.lineTo(sl.width,0);sc.stroke();sc.setLineDash([]);
 let label=m===37?'projection only':(D.obs[z]?`${D.n[z]} unique solutions`:'no observed layer');document.getElementById('meta').innerHTML=`<b>m=${m}</b>: ${label}`}
function redraw(){document.getElementById('tv').textContent=(+document.getElementById('thr').value).toFixed(2);document.getElementById('lv').textContent=document.getElementById('layer').value;drawVol();drawSlice()}
vol.onpointerdown=e=>{drag=true;lx=e.clientX;ly=e.clientY;vol.setPointerCapture(e.pointerId)};vol.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-lx)*.008;pitch=Math.max(-1.35,Math.min(1.35,pitch+(e.clientY-ly)*.008));lx=e.clientX;ly=e.clientY;drawVol()};vol.onpointerup=()=>drag=false;vol.onwheel=e=>{e.preventDefault();zoom=Math.max(.55,Math.min(2,zoom*Math.exp(-e.deltaY*.001)));drawVol()};
for(let id of ['mode','thr','layer'])document.getElementById(id).oninput=redraw;redraw();
</script></body></html>'''


def build_html(path: Path, log_volume: np.ndarray, residual_volume: np.ndarray,
               prediction: np.ndarray, observed: np.ndarray, nsol: np.ndarray):
    payload = {
        "q": np.round(log_volume, 4).reshape(-1).tolist(),
        "r": np.round(residual_volume, 4).reshape(-1).tolist(),
        "p": np.round(prediction, 4).reshape(-1).tolist(),
        "obs": observed.astype(int).tolist(),
        "n": nsol.astype(int).tolist(),
    }
    path.write_text(HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":"))),
                    encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path(__file__).with_name("flammenkamp_cache"))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "volume_heatmap_37")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    by_m, sources, invalid, sample_checks = load_solutions(args.cache)
    if invalid:
        raise RuntimeError(f"Rejected input records: {invalid[:5]}")

    observed = np.zeros(R, dtype=bool)
    nsol = np.zeros(R, dtype=int)
    raw_volume = np.zeros((R, R, R), dtype=np.float32)
    smooth_volume = np.zeros_like(raw_volume)
    se_volume = np.zeros_like(raw_volume)
    log_volume = np.zeros_like(raw_volume)
    residual_volume = np.zeros_like(raw_volume)
    fit_rows = []
    _, _, rho, diag, feats = feature_matrix()
    alpha = 2.0

    for m in sorted(by_m):
        if not 1 <= m <= 36:
            continue
        sols = by_m[m]
        N = len(sols)
        if not N:
            continue
        observed[m - 1] = True
        nsol[m - 1] = N
        total = np.zeros((m, m), dtype=float)
        total2 = np.zeros((m, m), dtype=float)
        for cells in sols:
            a = np.zeros((m, m), dtype=float)
            for x, y in cells:
                a[x, y] += 0.5
                a[y, x] += 0.5
            total += a
            total2 += a * a
        P = total / N
        raw_q = m * P
        smooth_q = m * (total + alpha / m) / (N + alpha)
        var = np.maximum(0.0, (total2 - N * P * P) / max(1, N - 1))
        se_q = m * np.sqrt(var / N) if N > 1 else np.full_like(P, np.nan)
        raw_r = area_resize(raw_q)
        smooth_r = area_resize(smooth_q)
        # Numerical roundoff aside, area resampling preserves the null baseline.
        raw_r /= raw_r.mean()
        smooth_r /= smooth_r.mean()
        se_r = area_resize(np.nan_to_num(se_q, nan=0.0))
        logq = np.log2(np.maximum(smooth_r, 1e-9))
        _, residual, beta, r2 = fit_known_features(logq, feats)
        raw_volume[m - 1] = raw_r
        smooth_volume[m - 1] = smooth_r
        se_volume[m - 1] = se_r
        log_volume[m - 1] = logq
        residual_volume[m - 1] = residual
        fit_rows.append({"m": m, "solutions": N, "known_feature_r2": r2,
                         "feature_coefficients": beta.tolist()})

    # Keep sparse high-m layers visible in the volume, but do not let them define
    # the stable template.  The m=30/32 caches have only 32/25 examples and their
    # apparent hot pixels change sharply under resampling.
    reliable = [m for m in range(16, 29) if nsol[m - 1] >= 100]
    projection_ms = [m for m in range(18, 29) if nsol[m - 1] >= 100]
    if len(reliable) < 5:
        raise RuntimeError("Not enough reliable high-m layers for a trend projection")
    L = np.stack([log_volume[m - 1] for m in reliable])
    E = np.stack([residual_volume[m - 1] for m in reliable])

    # Per-voxel linear trend in 1/m.  This is a spatial prior, not a construction.
    LP = np.stack([log_volume[m - 1] for m in projection_ms])
    X = np.stack([np.ones(len(projection_ms)), 1.0 / np.array(projection_ms)], axis=1)
    coef = np.linalg.pinv(X) @ LP.reshape(len(projection_ms), -1)
    pure_trend_log = (np.array([1.0, 1.0 / 37.0]) @ coef).reshape(R, R)
    # Forward validation strongly prefers a stable recent-layer template to pure
    # extrapolation.  Keep only 20% of the trend and 80% of the last eight reliable
    # layers; this guards against the sparse m=30/32 layers amplifying a slope.
    projection_trend_weight = 0.20
    recent_ms = projection_ms[-8:]
    recent_template_log = np.stack([log_volume[m - 1] for m in recent_ms]).mean(axis=0)
    pred_log = (projection_trend_weight * pure_trend_log
                + (1.0 - projection_trend_weight) * recent_template_log)
    prediction = np.exp2(np.clip(pred_log, -2.0, 2.0))
    prediction /= prediction.mean()
    pred_log = np.log2(prediction)
    trend_fit = (X @ coef).reshape(LP.shape)
    trend_rmse = float(np.sqrt(np.mean((LP - trend_fit) ** 2)))

    residual_mean = E.mean(axis=0)
    sign_consistency = np.maximum((E > 0).mean(axis=0), (E < 0).mean(axis=0))
    residual_loo_corr = []
    for i in range(len(reliable)):
        residual_loo_corr.append(pearson(E[i], np.delete(E, i, axis=0).mean(axis=0)))

    centered = L.reshape(len(reliable), -1)
    centered -= centered.mean(axis=0, keepdims=True)
    sv = np.linalg.svd(centered, full_matrices=False, compute_uv=False)
    sv_var = (sv * sv) / np.sum(sv * sv)

    layer_corrs = []
    for i, a in enumerate(reliable):
        for b in reliable[i + 1:]:
            layer_corrs.append(pearson(log_volume[a - 1], log_volume[b - 1]))
    adjacent_corrs = [pearson(log_volume[a - 1], log_volume[b - 1])
                      for a, b in zip(reliable, reliable[1:])]

    # Honest rolling backtest: each target uses only smaller reliable m values.
    backtests = []
    for target in projection_ms:
        train = [m for m in projection_ms if m < target]
        if len(train) < 6:
            continue
        Xt = np.stack([np.ones(len(train)), 1.0 / np.array(train)], axis=1)
        Yt = np.stack([log_volume[m - 1] for m in train]).reshape(len(train), -1)
        ct = np.linalg.pinv(Xt) @ Yt
        pure = (np.array([1.0, 1.0 / target]) @ ct).reshape(R, R)
        template = np.stack([log_volume[m - 1] for m in train[-8:]]).mean(axis=0)
        pr = projection_trend_weight * pure + (1.0 - projection_trend_weight) * template
        actual = log_volume[target - 1]
        backtests.append({"target_m": target, "train_ms": train,
                          "correlation": pearson(pr, actual),
                          "mae_log2": float(np.mean(np.abs(pr - actual)))})

    fit_by_m = {r["m"]: r for r in fit_rows}
    feature_r2 = [fit_by_m[m]["known_feature_r2"] for m in reliable]
    stable_mask = sign_consistency >= 0.75
    stable_values = np.where(stable_mask, residual_mean, 0.0)
    residual_peaks = select_peaks(stable_values, 8, True, 3) + select_peaks(stable_values, 8, False, 3)

    # Exact theorem-side comparator already computed in this repository: co3 is
    # the pair-codegree matrix of the m=37 conflict hypergraph.  Its row sum is
    # twice the triple-conflict degree of a cell.  This tests whether the visual
    # prior is merely "pick cells of low local conflict degree".
    conflict_degree = np.zeros((R, R), dtype=float)
    conflict_stats = {"available": False}
    co3_path = Path(__file__).with_name("co3_m37.npy")
    if co3_path.exists():
        co3 = np.load(co3_path, mmap_mode="r")
        if co3.shape == (R * R, R * R):
            conflict_degree = np.asarray(co3.sum(axis=1), dtype=float).reshape(R, R) / 2.0
            conflict_degree = 0.5 * (conflict_degree + conflict_degree.T)
            observed_template = L.mean(axis=0)
            conflict_stats = {
                "available": True,
                "definition": "row-sum(co3)/2, symmetrized with transpose",
                "pearson_observed_template": pearson(conflict_degree, observed_template),
                "spearman_observed_template": spearman(conflict_degree, observed_template),
                "pearson_m37_projection": pearson(conflict_degree, pred_log),
                "spearman_m37_projection": spearman(conflict_degree, pred_log),
                "pearson_stable_residual": pearson(conflict_degree, residual_mean),
                "spearman_stable_residual": spearman(conflict_degree, residual_mean),
            }

    summary = {
        "definition": {
            "shape": [37, 37, 37], "axes": {"x": "normalized fundamental cell x",
            "y": "normalized fundamental cell y", "z": "m=n/2, layer index m-1"},
            "observed_value": "P(cell)/(1/m), symmetrized with transpose",
            "layer_37": "linear trend in 1/m over reliable observed layers; not a solution",
            "residual": "log2 enrichment after radial+diagonal 8-feature least-squares fit",
        },
        "sources": sources,
        "input_validation": {"rejected_records": invalid, "ntil_samples_checked": sample_checks,
                             "all_records_checked_for": ["2n unique in-board points", "2 per row",
                             "2 per column", "C4 closure", "m fundamental cells"]},
        "solution_counts": {str(m): int(nsol[m - 1]) for m in range(1, 37) if observed[m - 1]},
        "total_unique_solutions": int(nsol.sum()),
        "reliable_ms": reliable,
        "known_feature_fit": {
            "features": ["1", "rho", "rho^2", "rho^3", "|x-y|", "|x-y|^2",
                         "exp(-|x-y|/0.04)", "exp(-|x-y|/0.12)"],
            "per_m": fit_rows, "median_r2_reliable": float(np.median(feature_r2)),
            "min_r2_reliable": float(np.min(feature_r2)), "max_r2_reliable": float(np.max(feature_r2)),
        },
        "cross_m": {
            "mean_pairwise_correlation": float(np.mean(layer_corrs)),
            "median_pairwise_correlation": float(np.median(layer_corrs)),
            "mean_adjacent_reliable_correlation": float(np.mean(adjacent_corrs)),
            "svd_variance_first_5": sv_var[:5].tolist(),
            "residual_loo_correlation_median": float(np.median(residual_loo_corr)),
            "residual_loo_correlation_mean": float(np.mean(residual_loo_corr)),
        },
        "m37_projection": {
            "training_ms": projection_ms, "recent_template_ms": recent_ms,
            "method": "0.20 * linear trend in 1/m + 0.80 * mean of last 8 reliable layers",
            "trend_weight_selected_by_forward_validation": projection_trend_weight,
            "pure_trend_fit_rmse_log2": trend_rmse,
            "rolling_backtests": backtests,
            "median_backtest_correlation": float(np.median([x["correlation"] for x in backtests])),
            "median_backtest_mae_log2": float(np.median([x["mae_log2"] for x in backtests])),
            "hot_regions_1_based": select_peaks(prediction, 10, True, 3),
            "cold_regions_1_based": select_peaks(prediction, 10, False, 3),
        },
        "stable_residual": {
            "sign_consistency_threshold": 0.75,
            "fraction_cells_passing": float(stable_mask.mean()),
            "max_abs_mean_log2": float(np.max(np.abs(residual_mean))),
            "separated_peaks_1_based": residual_peaks,
        },
        "m37_conflict_degree_comparison": conflict_stats,
    }

    np.savez_compressed(args.out / "ntil_volume_37.npz", raw_enrichment=raw_volume,
                        smoothed_enrichment=smooth_volume, log2_enrichment=log_volume,
                        standard_error=se_volume, radial_diagonal_residual=residual_volume,
                        residual_mean=residual_mean, residual_sign_consistency=sign_consistency,
                        prediction_m37=prediction, prediction_pure_trend_log2=pure_trend_log,
                        prediction_recent_template_log2=recent_template_log,
                        conflict_degree_m37=conflict_degree,
                        observed=observed, nsol=nsol)
    (args.out / "ntil_volume_37_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    build_html(args.out / "ntil_volume_37_interactive.html", log_volume, residual_volume,
               prediction, observed, nsol)
    make_preview(args.out / "ntil_volume_37_preview.png", log_volume, residual_mean, prediction, nsol)
    print(json.dumps({
        "out": str(args.out), "unique_solutions": int(nsol.sum()), "observed_ms": int(observed.sum()),
        "reliable_ms": reliable, "median_feature_r2": summary["known_feature_fit"]["median_r2_reliable"],
        "median_backtest_corr": summary["m37_projection"]["median_backtest_correlation"],
        "median_residual_loo_corr": summary["cross_m"]["residual_loo_correlation_median"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
