#!/bin/zsh
# Daily free-tier drip: run every pipeline stage until quotas exhaust.
# Every stage is idempotent (response cache + skip logs), so this script
# is safe to run any number of times; each run makes forward progress.
# Intended to be run once a day (manually or by a scheduled task).

set -u
cd "$(dirname "$0")/.."
[ -f .env ] && source .env

echo "=== daily drip $(date '+%Y-%m-%d %H:%M') ==="

# 0. preconditions
python3 scripts/validate_instructions.py || exit 1

# 1. generation (finishes in the first day or two, then no-ops)
python3 src/generate.py

# 2. gold sampling: only once generation is complete
if [ ! -f data/gold/worklist.jsonl ]; then
  expected=$(( $(cat data/instructions/*.jsonl | grep -c .) * 4 ))
  actual=$(grep -c . data/responses/responses.jsonl 2>/dev/null || echo 0)
  if [ "$actual" -eq "$expected" ]; then
    python3 scripts/sample_gold.py
  else
    echo "generation incomplete ($actual/$expected); judging waits"
    exit 0
  fi
fi

# 3. judge matrix (each mode drains what today's quotas allow)
for mode in rubric bare pairwise stability; do
  python3 src/judge.py --mode $mode
done

# 4. progress summary
python3 - <<'EOF'
import json, os
for f in ("rubric", "bare", "pairwise", "stability"):
    p = f"data/judgments/{f}.jsonl"
    n = sum(1 for l in open(p)) if os.path.exists(p) else 0
    print(f"{f:10s}: {n} judgments")
EOF
echo "=== drip done ==="
