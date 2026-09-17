#!/usr/bin/env bash
# Resilient m=37 (n=74, C4) CP-SAT attack — survives container teardown.
#   - resumes from checkpoint (warm-start via AddHint)
#   - checkpoints every incumbent (a found solution is never lost)
#   - unbuffered logging (live progress in results/m37_slice.log)
#   - skips if a live m37 solve is already running in THIS sandbox
#   - stops when results/m37_ckpt.json.done exists
set -u
DIR="D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
cd "$DIR" || exit 1

CKPT="results/m37_ckpt.json"
if [ -f "$CKPT.done" ]; then
  echo "$(date) DONE marker present; nothing to do"
  exit 0
fi
if ps -ef 2>/dev/null | grep -q "[c]psat_symmetric_ntil.py --group C4 --m 37"; then
  echo "$(date) SKIP: m37 solve already running in this sandbox"
  exit 0
fi

PY="C:/Users/djr82/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
export PYTHONUNBUFFERED=1
echo "$(date) launching 30-min m37 chunk (resume + checkpoint)"
"$PY" -u cpsat_symmetric_ntil.py --group C4 --m 37 --timelimit 1800 --workers 8 \
  --checkpoint "$CKPT" --resume "$CKPT" \
  > results/m37_slice.log 2>&1
echo "$(date) chunk finished (exit $?)"
