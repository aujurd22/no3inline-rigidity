#!/usr/bin/env bash
# Monitor the resilient m=37 attack without relying on the agent task handle.
DIR="D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
cd "$DIR" || exit 1
echo "=== live m37 process (this sandbox) ==="
ps -ef 2>/dev/null | grep "[c]psat_symmetric_ntil.py --group C4 --m 37" || echo "(none)"
echo "=== checkpoint ==="
if [ -f results/m37_ckpt.json ]; then echo "present:"; cat results/m37_ckpt.json; else echo "(none)"; fi
echo "=== done marker ==="
if [ -f results/m37_ckpt.json.done ]; then cat results/m37_ckpt.json.done; else echo "(not done)"; fi
echo "=== slice log tail ==="
tail -c 1200 results/m37_slice.log 2>/dev/null | tr '\r' '\n' | tail -15
echo "=== original attack log tail (07:54 launch, unprotected) ==="
tail -c 800 results/m37_r8g_attack.log 2>/dev/null | tr '\r' '\n' | tail -8
