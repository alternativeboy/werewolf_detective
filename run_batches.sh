#!/bin/bash
# Run run.py in batches until every game is done, waiting out plan usage limits.
# SCRIPT=rejudge.py runs rejudge.py the same way (done when it exits 0; it skips finished games).
#
#   ./run_batches.sh --backend cli --cases 30 --levels L2 L4 --detective-hides 1 --seed 0 \
#       --out results/main --max-games 20
#
# All arguments go to run.py unchanged. After each batch the next one starts at once. If a
# batch stops on a usage limit, wait WAIT_HOURS (default 5) and try again; finished games are
# kept and run.py resumes with the next unplayed game. Any other error (e.g. network down): wait
# 10 min, and stop after MAX_ERRORS (default 6) such errors in a row. Optional: WAIT_FOR_PID=<pid> waits for a running batch first.
# Run under `caffeinate -i` so the Mac does not sleep during the waits.

cd "$(dirname "$0")" || exit 1
unset ANTHROPIC_API_KEY
WAIT_HOURS=${WAIT_HOURS:-5}
MAX_ERRORS=${MAX_ERRORS:-6}
SCRIPT=${SCRIPT:-run.py}
out=$(mktemp)

if [ -n "$WAIT_FOR_PID" ]; then
  echo "$(date '+%F %T') waiting for running batch (pid $WAIT_FOR_PID) to finish"
  while kill -0 "$WAIT_FOR_PID" 2>/dev/null; do sleep 30; done
fi

errors=0
while true; do
  echo "=== $(date '+%F %T') starting batch ==="
  python3 -u "$SCRIPT" "$@" 2>&1 | tee "$out"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 0 ]; then
    errors=0
    if [ "$SCRIPT" != run.py ] || grep -q ", 0 left\." "$out"; then
      echo "=== $(date '+%F %T') all games done ==="
      exit 0
    fi
  elif grep -q "Usage limit reached" "$out"; then
    errors=0
    echo "=== $(date '+%F %T') usage limit; retrying in $WAIT_HOURS h ==="
    sleep $((WAIT_HOURS * 3600))
  else
    errors=$((errors + 1))
    echo "=== $(date '+%F %T') error $errors/$MAX_ERRORS (exit $rc) ==="
    [ "$errors" -ge "$MAX_ERRORS" ] && { echo "stopping after $MAX_ERRORS errors in a row"; exit 1; }
    sleep 600
  fi
done
