#!/bin/zsh
# Daily free-tier drip: run every pipeline stage until quotas exhaust.
# Every stage is idempotent (response cache + skip logs), so this script
# is safe to run any number of times; each run makes forward progress.
# Intended to be run once a day (manually or by a scheduled task).

set -u
cd "$(dirname "$0")/.."
[ -f .env ] && source .env

# Self-logging. The scheduled task invokes this script bare (no shell pipeline,
# no redirection) so that a single exact-match permission rule covers it; the
# tee therefore lives here instead of on the caller's command line.
mkdir -p data
exec > >(tee -a data/drip.log) 2>&1

echo "=== daily drip $(date '+%Y-%m-%d %H:%M') ==="

before_resp=$(grep -c . data/responses/responses.jsonl 2>/dev/null || echo 0)
before_judg=$(cat data/judgments/*.jsonl 2>/dev/null | grep -c . || echo 0)

# 0. preconditions
python3 scripts/validate_instructions.py || exit 1

# 1. generation (finishes in the first day or two, then no-ops)
python3 src/generate.py

# 2. gold sampling: only once generation is complete
judging=yes
if [ ! -f data/gold/worklist.jsonl ]; then
  expected=$(( $(cat data/instructions/*.jsonl | grep -c .) * 4 ))
  actual=$(grep -c . data/responses/responses.jsonl 2>/dev/null || echo 0)
  if [ "$actual" -eq "$expected" ]; then
    python3 scripts/sample_gold.py
  else
    echo "generation incomplete ($actual/$expected); judging waits"
    judging=no
  fi
fi

# 3. judge matrix (each mode drains what today's quotas allow)
if [ "$judging" = "yes" ]; then
  for mode in rubric bare pairwise stability; do
    python3 src/judge.py --mode $mode
  done
fi

# 4. progress summary
python3 - <<'EOF'
import json, os
for f in ("rubric", "bare", "pairwise", "stability"):
    p = f"data/judgments/{f}.jsonl"
    n = sum(1 for l in open(p)) if os.path.exists(p) else 0
    print(f"{f:10s}: {n} judgments")
EOF

# 5. commit & push today's data increment (real work only: no-op days
#    produce no commit)
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  n_resp=$(grep -c . data/responses/responses.jsonl 2>/dev/null || echo 0)
  n_judg=$(cat data/judgments/*.jsonl 2>/dev/null | grep -c . || echo 0)
  git commit -qm "daily drip $(date +%F): ${n_resp} responses, ${n_judg} judgments"
  git push -q origin master || echo "push failed (offline?); will retry tomorrow"
fi

# 6. one-line summary the caller reports verbatim (grep for DRIP-SUMMARY)
after_resp=$(grep -c . data/responses/responses.jsonl 2>/dev/null || echo 0)
after_judg=$(cat data/judgments/*.jsonl 2>/dev/null | grep -c . || echo 0)
expected=$(( $(cat data/instructions/*.jsonl | grep -c .) * 4 ))
echo "DRIP-SUMMARY: responses ${after_resp}/${expected} (+$((after_resp - before_resp)) today), judgments ${after_judg} (+$((after_judg - before_judg)) today)"
echo "=== drip done ==="
