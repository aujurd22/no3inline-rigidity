#!/usr/bin/env bash
# Resilient m=37 (n=74, C4) R9b attack — fast per-line build + 2-factor structure.
#   - kills the O(m^6) per-line build (cpsat_symmetric_ntil.py) in favour of the
#     60s fast builder in solve_m37_r9b.py
#   - resumes from checkpoint (warm-start via AddHint)
#   - checkpoints any found solution (never lost on container teardown)
#   - unbuffered logging; skips if a live R9b solve is already running here
set -u
DIR="D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
cd "$DIR" || exit 1

CKPT="results/m37_r9b_ckpt.json"
if [ -f "$CKPT.done" ]; then
  echo "$(date) DONE marker present; nothing to do"
  exit 0
fi
# Robust liveness: a pid must respond to kill -0.  Plain `ps -ef | grep` also
# matches defunct/zombie entries (no /proc), which would false-SKIP a restart.
LIVE=0
for p in $(ps -ef 2>/dev/null | grep "[s]olve_m37_r9b.py --m 37" | awk '{print $2}'); do
  if kill -0 "$p" 2>/dev/null; then LIVE=1; break; fi
done
if [ "$LIVE" -eq 1 ]; then
  echo "$(date) SKIP: R9b m37 solve already running in this sandbox"
  exit 0
fi

PY="C:/Users/djr82/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
export PYTHONUNBUFFERED=1
echo "$(date) launching R9b m37 chunk (resume + checkpoint)"
"$PY" -u solve_m37_r9b.py --m 37 --timelimit 7200 --workers 8 \
  --checkpoint "$CKPT" --resume "$CKPT" \
  > results/m37_r9b.log 2>&1
echo "$(date) chunk finished (exit $?)"
